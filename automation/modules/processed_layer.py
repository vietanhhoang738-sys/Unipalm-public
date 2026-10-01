"""Shop-scoped processed-layer builder for Multi-Shop staging outputs.

This module promotes only PASSed local staging artifacts into a deterministic,
shop/month partition. It never writes the legacy processed tree, production Data
Mart, or UI.

Core guarantees:
- namespace = shop_key + period;
- every JSONL business row must carry exactly the expected shop_id;
- source/output row semantics are validated after declared deterministic transforms;
- volatile ingestion metadata is excluded from processed business facts;
- build_fingerprint is deterministic for identical business facts;
- control state grain = shop_id + source_domain + period;
- partition replacement is performed as a same-filesystem directory swap.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Tuple

from .pipeline_state import PipelineState, aggregate_shop_readiness, validate_state_rows


DEFAULT_CONTRACT_PATH=Path(__file__).resolve().parents[2]/"config"/"processed_layer_contract.json"


def _s(v:Any)->str:
    return "" if v is None else str(v).strip()


def load_processed_contract(path:str|Path="")->Dict[str,Any]:
    p=Path(path) if path else DEFAULT_CONTRACT_PATH
    data=json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data.get("domains"),dict) or not data["domains"]:
        raise ValueError("processed layer contract has no domains")
    required=list(data.get("required_ready_domains") or [])
    unknown=[x for x in required if x not in data["domains"]]
    if unknown:
        raise ValueError(f"processed layer required domains missing from contract: {unknown}")
    return data


def sha256_file(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk=f.read(1024*1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def sha256_json(value:Any)->str:
    raw=json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":"),default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def read_jsonl(path:Path)->Iterable[Dict[str,Any]]:
    with path.open("r",encoding="utf-8") as f:
        for line_no,line in enumerate(f,1):
            if not line.strip():
                continue
            try:
                row=json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}: invalid JSONL at line {line_no}: {exc}") from exc
            if not isinstance(row,dict):
                raise ValueError(f"{path}: JSONL line {line_no} is not an object")
            yield row


def inspect_jsonl(path:Path, *, expected_shop_id:str)->Dict[str,Any]:
    rows=0
    missing_shop_id=0
    foreign_shop_ids=set()
    for row in read_jsonl(path):
        rows+=1
        sid=_s(row.get("shop_id"))
        if not sid:
            missing_shop_id+=1
        elif sid!=expected_shop_id:
            foreign_shop_ids.add(sid)
    return {
        "row_count":rows,
        "missing_shop_id_rows":missing_shop_id,
        "foreign_shop_ids":sorted(foreign_shop_ids),
        "shop_isolation_pass":missing_shop_id==0 and not foreign_shop_ids,
    }

def _write_processed_jsonl(
    source:Path,
    target:Path,
    *,
    expected_shop_id:str,
    drop_fields:Iterable[str]=(),
)->Dict[str,Any]:
    """Write deterministic processed JSONL after declared field drops."""
    drop={_s(x) for x in drop_fields if _s(x)}
    source_audit=inspect_jsonl(source,expected_shop_id=expected_shop_id)
    if not source_audit["shop_isolation_pass"]:
        raise ValueError(
            f"{source.name}: shop isolation failed "
            f"missing_shop_id_rows={source_audit['missing_shop_id_rows']} "
            f"foreign_shop_ids={source_audit['foreign_shop_ids']}"
        )

    target.parent.mkdir(parents=True,exist_ok=True)
    if not drop:
        shutil.copyfile(source,target)
    else:
        with target.open("w",encoding="utf-8") as f:
            for row in read_jsonl(source):
                clean={k:v for k,v in row.items() if k not in drop}
                f.write(json.dumps(clean,ensure_ascii=False,sort_keys=True)+"\n")

    output_audit=inspect_jsonl(target,expected_shop_id=expected_shop_id)
    if not output_audit["shop_isolation_pass"]:
        raise ValueError(f"{target}: output shop isolation failed")
    if output_audit["row_count"]!=source_audit["row_count"]:
        raise ValueError(
            f"{source.name}: processed row count changed "
            f"{source_audit['row_count']} -> {output_audit['row_count']}"
        )
    if drop:
        leaked=[]
        for row in read_jsonl(target):
            leaked.extend(x for x in drop if x in row)
            if leaked:
                break
        if leaked:
            raise ValueError(f"{source.name}: volatile fields leaked into processed output: {sorted(set(leaked))}")

    return {
        "row_count":output_audit["row_count"],
        "source_sha256":sha256_file(source),
        "sha256":sha256_file(target),
        "drop_fields":sorted(drop),
    }



def _verified_through(path:Path, spec:Mapping[str,Any])->str:
    field=_s(spec.get("field"))
    mode=_s(spec.get("mode"))
    if not field:
        return ""
    values=[]
    for row in read_jsonl(path):
        value=_s(row.get(field))
        if not value:
            continue
        if mode=="date_prefix_max":
            value=value[:10]
        values.append(value)
    return max(values) if values else ""


def _schema_warning_counts(schema_report:Mapping[str,Any],contract:Mapping[str,Any])->Dict[str,int]:
    domain_by_contract=dict(contract.get("schema_contract_domain_map") or {})
    counts={name:0 for name in contract["domains"]}
    for audit in schema_report.get("audits") or []:
        if _s(audit.get("status"))!="WARN":
            continue
        domain=domain_by_contract.get(_s(audit.get("contract")))
        if domain in counts:
            counts[domain]+=1
    return counts


def _source_version(staging_dir:Path)->str:
    pieces={}
    for name in ("staging_qa_report.json","schema_drift_report.json"):
        p=staging_dir/name
        if p.exists():
            pieces[name]=sha256_file(p)
    return sha256_json(pieces)


def _business_build_fingerprint(
    *,
    contract_version:str,
    shop_id:str,
    shop_key:str,
    period:str,
    files:List[Mapping[str,Any]],
)->str:
    payload={
        "contract_version":contract_version,
        "shop_id":shop_id,
        "shop_key":shop_key,
        "period":period,
        "files":[{
            "domain":x["domain"],
            "target":x["target"],
            "sha256":x["sha256"],
            "row_count":x["row_count"],
        } for x in sorted(files,key=lambda x:(x["domain"],x["target"]))],
    }
    return sha256_json(payload)


def _copy_domain_files(
    *,
    staging_dir:Path,
    build_dir:Path,
    expected_shop_id:str,
    contract:Mapping[str,Any],
)->Tuple[List[Dict[str,Any]],Dict[str,Dict[str,Any]]]:
    manifest_files=[]
    domain_info={}
    for domain,spec in contract["domains"].items():
        files=list(spec.get("files") or [])
        required=bool(spec.get("required",False))
        domain_rows=0
        missing=[]
        verified=""
        for file_spec in files:
            source=staging_dir/_s(file_spec.get("source"))
            target_rel=_s(file_spec.get("target"))
            if not source.exists():
                missing.append(source.name)
                continue
            target=build_dir/target_rel
            write_meta=_write_processed_jsonl(
                source,target,
                expected_shop_id=expected_shop_id,
                drop_fields=file_spec.get("drop_fields") or (),
            )
            domain_rows+=write_meta["row_count"]
            manifest_files.append({
                "domain":domain,
                "source":source.name,
                "target":target_rel,
                "source_sha256":write_meta["source_sha256"],
                "sha256":write_meta["sha256"],
                "row_count":write_meta["row_count"],
                "bytes":target.stat().st_size,
                "transform":{"drop_fields":write_meta["drop_fields"]},
            })

        if missing and required:
            raise FileNotFoundError(f"{domain}: required staging files missing: {missing}")

        v_spec=spec.get("verified_through") or {}
        v_source=_s(v_spec.get("source"))
        if v_source:
            p=staging_dir/v_source
            if p.exists():
                verified=_verified_through(p,v_spec)

        domain_info[domain]={
            "required":required,
            "missing_files":missing,
            "row_count":domain_rows,
            "verified_through":verified,
            "file_count":sum(1 for x in manifest_files if x["domain"]==domain),
        }
    return manifest_files,domain_info


def build_processed_partition(
    *,
    staging_dir:str|Path,
    output_root:str|Path,
    shop_key:str,
    period:str,
    run_id:str,
    contract_path:str|Path="",
    pipeline_version:str="processed-layer-v1",
    generated_at:str="",
)->Dict[str,Any]:
    """Build and atomically replace one shop/month processed candidate partition."""
    staging_dir=Path(staging_dir)
    output_root=Path(output_root)
    contract=load_processed_contract(contract_path)

    qa_path=staging_dir/"staging_qa_report.json"
    if not qa_path.exists():
        raise FileNotFoundError(f"{staging_dir}: staging_qa_report.json not found")
    staging_qa=json.loads(qa_path.read_text(encoding="utf-8"))
    if staging_qa.get("status")!="PASS" or not bool(staging_qa.get("production_write_allowed")):
        raise ValueError(f"{shop_key}/{period}: staging QA is not PASS")

    expected_period=_s(staging_qa.get("target_month"))
    if expected_period and expected_period!=period:
        raise ValueError(f"{shop_key}: staging period {expected_period} != requested {period}")
    shop_id=_s(staging_qa.get("shop_id"))
    if not shop_id:
        raise ValueError(f"{shop_key}/{period}: staging QA missing shop_id")

    schema_path=staging_dir/"schema_drift_report.json"
    schema_report=json.loads(schema_path.read_text(encoding="utf-8")) if schema_path.exists() else {}
    schema_summary=(schema_report.get("summary") or staging_qa.get("schema_guard") or {})
    if schema_summary.get("status")=="FAIL":
        raise ValueError(f"{shop_key}/{period}: schema guard is FAIL")

    shop_root=output_root/shop_key
    shop_root.mkdir(parents=True,exist_ok=True)
    build_dir=shop_root/f".tmp_{period}_{uuid.uuid4().hex}"
    build_dir.mkdir(parents=False,exist_ok=False)

    try:
        manifest_files,domain_info=_copy_domain_files(
            staging_dir=staging_dir,
            build_dir=build_dir,
            expected_shop_id=shop_id,
            contract=contract,
        )
        staging_artifact_version=_source_version(staging_dir)
        fingerprint=_business_build_fingerprint(
            contract_version=_s(contract.get("version")),
            shop_id=shop_id,
            shop_key=shop_key,
            period=period,
            files=manifest_files,
        )
        source_version=fingerprint
        warning_counts=_schema_warning_counts(schema_report,contract)

        states=[]
        for domain,spec in contract["domains"].items():
            info=domain_info[domain]
            if info["missing_files"] and not bool(spec.get("required",False)):
                state="SKIPPED"
            else:
                state="READY"
            states.append(PipelineState(
                shop_id=shop_id,
                source_domain=domain,
                period=period,
                state=state,
                run_id=run_id,
                pipeline_version=pipeline_version,
                source_version=source_version,
                verified_through=info["verified_through"],
                dq_error=0,
                dq_warning=int(warning_counts.get(domain,0)),
                production_updated=False,
                output_location=f"{shop_key}/{period}/{domain}",
                started_at=generated_at,
                finished_at=generated_at,
            ).to_dict())

        state_qa=validate_state_rows(states)
        readiness=aggregate_shop_readiness(states,contract.get("required_ready_domains") or [])
        ready_scope=next((x for x in readiness if x["shop_id"]==shop_id and x["period"]==period),None)
        checks=[
            {"name":"input_staging_qa","status":"PASS","detail":{
                "staging_status":staging_qa.get("status"),
                "production_write_allowed":staging_qa.get("production_write_allowed"),
            }},
            {"name":"source_schema_guard","status":"PASS" if schema_summary.get("status")!="FAIL" else "FAIL",
             "detail":schema_summary},
            {"name":"processed_transform_integrity","status":"PASS","detail":{
                "files":len(manifest_files),
                "transformed_files":sum(1 for x in manifest_files if (x.get("transform") or {}).get("drop_fields")),
            }},
            {"name":"processed_shop_isolation","status":"PASS","detail":{"shop_id":shop_id}},
            {"name":"control_state_unique_valid","status":state_qa["status"],"detail":state_qa},
            {"name":"required_domains_ready",
             "status":"PASS" if ready_scope and ready_scope["status"]=="READY" else "FAIL",
             "detail":ready_scope or {}},
        ]
        failed=[x for x in checks if x["status"]=="FAIL"]

        control_dir=build_dir/"control"
        control_dir.mkdir(parents=True,exist_ok=True)
        with (control_dir/"pipeline_state.jsonl").open("w",encoding="utf-8") as f:
            for row in states:
                f.write(json.dumps(row,ensure_ascii=False,sort_keys=True)+"\n")

        manifest={
            "layer":contract.get("layer_name"),
            "contract_version":contract.get("version"),
            "shop_key":shop_key,
            "shop_id":shop_id,
            "period":period,
            "run_id":run_id,
            "source_version":source_version,
            "staging_artifact_version":staging_artifact_version,
            "build_fingerprint":fingerprint,
            "generated_at":generated_at,
            "files":manifest_files,
            "domains":domain_info,
            "safety":{
                "legacy_processed_written":False,
                "production_data_mart_written":False,
                "ui_modified":False,
            },
        }
        (build_dir/"manifest.json").write_text(
            json.dumps(manifest,ensure_ascii=False,indent=2,sort_keys=True),
            encoding="utf-8",
        )
        processed_qa={
            "status":"PASS" if not failed else "FAIL",
            "shop_key":shop_key,
            "shop_id":shop_id,
            "period":period,
            "build_fingerprint":fingerprint,
            "checks":checks,
            "processed_partition_ready":not failed,
            "semantic_mart_promotion_performed":False,
            "safety":manifest["safety"],
        }
        (build_dir/"processed_qa_report.json").write_text(
            json.dumps(processed_qa,ensure_ascii=False,indent=2,sort_keys=True),
            encoding="utf-8",
        )
        if failed:
            raise ValueError(f"{shop_key}/{period}: processed candidate QA failed: {failed}")

        target=shop_root/period
        backup=shop_root/f".backup_{period}_{uuid.uuid4().hex}"
        if target.exists():
            target.rename(backup)
        try:
            build_dir.rename(target)
        except Exception:
            if backup.exists() and not target.exists():
                backup.rename(target)
            raise
        if backup.exists():
            shutil.rmtree(backup)

        return {
            "shop_key":shop_key,
            "shop_id":shop_id,
            "period":period,
            "status":"PASS",
            "processed_partition_ready":True,
            "build_fingerprint":fingerprint,
            "file_count":len(manifest_files),
            "control_state_count":len(states),
            "output_location":str(target),
            "schema_status":schema_summary.get("status",""),
        }
    except Exception:
        if build_dir.exists():
            shutil.rmtree(build_dir,ignore_errors=True)
        raise


def inspect_partition_fingerprint(path:str|Path)->str:
    manifest=Path(path)/"manifest.json"
    if not manifest.exists():
        return ""
    return _s(json.loads(manifest.read_text(encoding="utf-8")).get("build_fingerprint"))
