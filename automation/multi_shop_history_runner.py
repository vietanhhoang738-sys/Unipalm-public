#!/usr/bin/env python3
"""Inventory real history and build fail-closed historical baselines."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

from googleapiclient.discovery import build

from modules.drive_auth import resolve_drive_credentials
from modules.historical_intelligence import build_historical_intelligence
from modules.shop_registry import enabled_shops, load_shop_registry
from multi_shop_staging_runner import children, download_bytes, resolve_shop_raw_root


FOLDER_MIME="application/vnd.google-apps.folder"


def _s(v:Any)->str:
    return "" if v is None else str(v).strip()


def _read_json(path:str|Path)->Dict[str,Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _child_folder(items:Sequence[Mapping[str,Any]],name:str)->Mapping[str,Any]|None:
    matches=[x for x in items if x.get("mimeType")==FOLDER_MIME and _s(x.get("name"))==name]
    if len(matches)>1:
        raise ValueError(f"duplicate child folder {name!r}")
    return matches[0] if matches else None


def _file(items:Sequence[Mapping[str,Any]],name:str)->Mapping[str,Any]|None:
    matches=[x for x in items if x.get("mimeType")!=FOLDER_MIME and _s(x.get("name"))==name]
    if len(matches)>1:
        raise ValueError(f"duplicate file {name!r}")
    return matches[0] if matches else None


def _json_file(drive,item:Mapping[str,Any])->Dict[str,Any]:
    return json.loads(download_bytes(drive,_s(item.get("id"))).decode("utf-8"))


def _jsonl_file(drive,item:Mapping[str,Any])->List[Dict[str,Any]]:
    raw=download_bytes(drive,_s(item.get("id"))).decode("utf-8")
    out=[]
    for line_no,line in enumerate(raw.splitlines(),1):
        if not line.strip():
            continue
        row=json.loads(line)
        if not isinstance(row,dict):
            raise ValueError(f"{item.get('name')} line {line_no} is not an object")
        out.append(row)
    return out


def _load_business_context(
    context_dir:str|Path,
    as_of_period:str,
)->tuple[List[Dict[str,Any]],str]:
    root=Path(context_dir)
    manifest=_read_json(root/"context_manifest.json")
    qa=_read_json(root/"context_qa_report.json")
    events=_read_json(root/"context_events.json")
    if _s(manifest.get("layer"))!="multi_shop_business_context_v1":
        raise ValueError("unexpected business context layer")
    if _s(manifest.get("asOfPeriod"))!=as_of_period:
        raise ValueError("business context period mismatch")
    if qa.get("status")!="PASS":
        raise ValueError("business context QA is not PASS")
    fingerprint=_s(manifest.get("contextBuildFingerprint"))
    if not fingerprint or fingerprint!=_s(qa.get("contextBuildFingerprint")):
        raise ValueError("business context fingerprint mismatch")
    if _s((events.get("meta") or {}).get("contextBuildFingerprint"))!=fingerprint:
        raise ValueError("business context event lineage mismatch")
    rows=[]
    with (root/"context_days.jsonl").open("r",encoding="utf-8") as fh:
        for line_no,line in enumerate(fh,1):
            if not line.strip():
                continue
            row=json.loads(line)
            if not isinstance(row,dict):
                raise ValueError(f"context_days.jsonl line {line_no} is not an object")
            rows.append(row)
    return rows,fingerprint


def _month_folders(drive,root_id:str,domain:str,as_of_period:str)->Dict[str,Mapping[str,Any]]:
    domain_folder=_child_folder(children(drive,root_id),domain)
    if not domain_folder:
        return {}
    out={}
    for year in children(drive,_s(domain_folder.get("id"))):
        if year.get("mimeType")!=FOLDER_MIME or not re.fullmatch(r"\d{4}",_s(year.get("name"))):
            continue
        for month in children(drive,_s(year.get("id"))):
            name=_s(month.get("name"))
            if (
                month.get("mimeType")==FOLDER_MIME
                and re.fullmatch(r"\d{4}-\d{2}",name)
                and name<=as_of_period
            ):
                out[name]=month
    return dict(sorted(out.items()))


def _source_presence(drive,month_folder:Mapping[str,Any],domain:str)->Dict[str,Any]:
    month=_s(month_folder.get("name"))
    items=children(drive,_s(month_folder.get("id")))
    source_items=items
    layout="MONTH_DIRECT"

    if domain=="orders":
        snapshots=[
            x for x in items
            if x.get("mimeType")==FOLDER_MIME
            and _s(x.get("name")).startswith("snapshot_")
        ]
        final=_child_folder(items,"final")
        if snapshots:
            selected=sorted(snapshots,key=lambda x:_s(x.get("name")))[-1]
            source_items=children(drive,_s(selected.get("id")))
            layout="LATEST_SNAPSHOT"
        elif final:
            source_items=children(drive,_s(final.get("id")))
            layout="FINAL"
        files=[x for x in source_items if _s(x.get("name")).lower().endswith(".xlsx")]
        valid=bool(files)
    elif domain=="ads":
        files=[x for x in items if _s(x.get("name")).lower().endswith(".csv")]
        valid=bool(files)
    elif domain in {"business_insights","product_performance"}:
        final=_child_folder(items,"final")
        source_items=children(drive,_s(final.get("id"))) if final else []
        layout="FINAL"
        files=[x for x in source_items if _s(x.get("name")).lower().endswith(".xlsx")]
        valid=len(files)==1
    else:
        files=[]
        valid=False

    return {
        "month":month,
        "status":"SOURCE_PRESENT_UNVALIDATED" if valid else "SOURCE_NOT_READY",
        "layout":layout,
        "fileCount":len(files),
        "fileNames":sorted(_s(x.get("name")) for x in files),
        "note":"Presence only; schema/business QA is required before historical use.",
    }


def _scan_raw(drive,shops:Sequence[Mapping[str,Any]],as_of_period:str)->Dict[str,Any]:
    result={}
    domains=("orders","ads","business_insights","product_performance")
    for shop in shops:
        sk=_s(shop.get("shop_key"))
        sid=_s(shop.get("shop_id"))
        root_id,resolution=resolve_shop_raw_root(drive,shop)
        domain_info={}
        ready_sets={}
        for domain in domains:
            months=_month_folders(drive,root_id,domain,as_of_period)
            states=[_source_presence(drive,item,domain) for item in months.values()]
            domain_info[domain]=states
            ready_sets[domain]={
                x["month"] for x in states
                if x["status"]=="SOURCE_PRESENT_UNVALIDATED"
            }
        core=set.intersection(
            ready_sets["orders"],
            ready_sets["ads"],
            ready_sets["business_insights"],
        ) if all(ready_sets[x] for x in ("orders","ads","business_insights")) else set()
        result[sid]={
            "shopKey":sk,
            "rawRootId":root_id,
            "rootResolution":resolution,
            "domains":domain_info,
            "coreDailyBackfillCandidateMonths":sorted(core),
            "productBackfillCandidateMonths":sorted(ready_sets["product_performance"]),
            "trustedForHistoricalBaseline":False,
        }
    return result


def _scan_processed(
    drive,
    shops:Sequence[Mapping[str,Any]],
    storage:Mapping[str,Any],
    as_of_period:str,
)->Dict[str,Any]:
    root_id=_s((storage.get("processed_v2") or {}).get("drive_root_id"))
    root_items=children(drive,root_id)
    out={}
    for shop in shops:
        sk=_s(shop.get("shop_key"))
        sid=_s(shop.get("shop_id"))
        shop_folder=_child_folder(root_items,sk)
        months=[]
        if shop_folder:
            for item in children(drive,_s(shop_folder.get("id"))):
                month=_s(item.get("name"))
                if (
                    item.get("mimeType")!=FOLDER_MIME
                    or not re.fullmatch(r"\d{4}-\d{2}",month)
                    or month>as_of_period
                ):
                    continue
                files=children(drive,_s(item.get("id")))
                manifest_item=_file(files,"manifest.json")
                qa_item=_file(files,"processed_qa_report.json")
                ready=False
                fingerprint=""
                if manifest_item and qa_item:
                    manifest=_json_file(drive,manifest_item)
                    qa=_json_file(drive,qa_item)
                    fingerprint=_s(manifest.get("build_fingerprint"))
                    ready=qa.get("status")=="PASS" and bool(fingerprint)
                months.append({
                    "month":month,
                    "status":"READY" if ready else "NOT_READY",
                    "buildFingerprint":fingerprint,
                })
        out[sid]={
            "shopKey":sk,
            "months":sorted(months,key=lambda x:x["month"]),
            "readyMonths":sorted(x["month"] for x in months if x["status"]=="READY"),
        }
    return out


def _scan_semantic(
    drive,
    shops:Sequence[Mapping[str,Any]],
    storage:Mapping[str,Any],
    as_of_period:str,
):
    root_id=_s((storage.get("semantic_v2") or {}).get("drive_root_id"))
    expected=[_s(x.get("shop_id")) for x in shops]
    partitions=[]
    daily=[]
    trusted=[]
    for item in children(drive,root_id):
        month=_s(item.get("name"))
        if (
            item.get("mimeType")!=FOLDER_MIME
            or not re.fullmatch(r"\d{4}-\d{2}",month)
            or month>as_of_period
        ):
            continue
        files=children(drive,_s(item.get("id")))
        manifest_item=_file(files,"manifest.json")
        qa_item=_file(files,"semantic_qa_report.json")
        daily_item=_file(files,"dm_shop_daily.jsonl")
        is_trusted=False
        fingerprint=""
        selected=[]
        if manifest_item and qa_item and daily_item:
            manifest=_json_file(drive,manifest_item)
            qa=_json_file(drive,qa_item)
            fingerprint=_s(manifest.get("semantic_build_fingerprint"))
            selected=[_s(x) for x in qa.get("selected_shop_ids") or []]
            is_trusted=(
                qa.get("status")=="PASS"
                and bool(qa.get("semantic_mart_ready"))
                and bool(fingerprint)
                and fingerprint==_s(qa.get("semantic_build_fingerprint"))
                and set(selected)==set(expected)
            )
            if is_trusted:
                daily.extend(_jsonl_file(drive,daily_item))
                trusted.append((month,fingerprint))
        partitions.append({
            "month":month,
            "status":"TRUSTED" if is_trusted else "NOT_TRUSTED",
            "semanticFingerprint":fingerprint,
            "selectedShopIds":selected,
        })
    trusted=sorted(trusted)
    return {
        "partitions":sorted(partitions,key=lambda x:x["month"]),
        "trustedMonths":[x[0] for x in trusted],
        "trustedFingerprints":[x[1] for x in trusted],
        "trustedMonthCount":len(trusted),
        "policy":"ONLY_QA_PASS_ALL_ENABLED_SHOPS_PARTITIONS_ARE_TRUSTED",
    },daily


def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--month",required=True)
    ap.add_argument("--registry",default="config/shop_registry.json")
    ap.add_argument("--storage-registry",default="config/storage_registry.json")
    ap.add_argument("--contract",default="config/historical_intelligence_contract.json")
    ap.add_argument("--context-dir",default="")
    ap.add_argument("--output-dir",default="history_artifacts")
    ap.add_argument("--refresh-id",default="")
    ap.add_argument("--previous-shadow-state",default="")
    args=ap.parse_args()

    if not re.fullmatch(r"\d{4}-\d{2}",args.month):
        raise ValueError("--month must be YYYY-MM")

    registry=load_shop_registry(args.registry)
    shops=enabled_shops(registry)
    storage=_read_json(args.storage_registry)
    creds,auth_mode=resolve_drive_credentials(auth_mode="user_oauth")
    drive=build("drive","v3",credentials=creds,cache_discovery=False)

    raw=_scan_raw(drive,shops,args.month)
    processed=_scan_processed(drive,shops,storage,args.month)
    semantic,semantic_daily=_scan_semantic(drive,shops,storage,args.month)
    inventory={
        "asOfPeriod":args.month,
        "authMode":auth_mode,
        "policy":{
            "rawPresenceIsTrustedHistory":False,
            "trustedHistorySource":"PUBLISHED_SEMANTIC_QA_PASS",
        },
        "raw":raw,
        "processed":processed,
        "semantic":semantic,
    }

    context_rows=[]
    context_fingerprint=""
    if args.context_dir:
        context_rows,context_fingerprint=_load_business_context(
            args.context_dir,args.month
        )

    previous_shadow_state={}
    if args.previous_shadow_state:
        previous_path=Path(args.previous_shadow_state)
        if previous_path.exists():
            previous_shadow_state=_read_json(previous_path)

    out=Path(args.output_dir)/args.month
    out.mkdir(parents=True,exist_ok=True)
    (out/"history_inventory.json").write_text(
        json.dumps(inventory,ensure_ascii=False,indent=2,sort_keys=True),
        encoding="utf-8",
    )
    result=build_historical_intelligence(
        semantic_daily_rows=semantic_daily,
        inventory=inventory,
        shops=shops,
        as_of_period=args.month,
        contract_path=args.contract,
        output_dir=out,
        context_rows=context_rows,
        context_fingerprint=context_fingerprint,
        refresh_id=args.refresh_id,
        previous_shadow_state=previous_shadow_state,
    )
    summary={
        **result,
        "selectedShopCount":len(shops),
        "rawCoreBackfillCandidates":{
            _s(shop.get("shop_id")):raw[_s(shop.get("shop_id"))]["coreDailyBackfillCandidateMonths"]
            for shop in shops
        },
        "rawProductBackfillCandidates":{
            _s(shop.get("shop_id")):raw[_s(shop.get("shop_id"))]["productBackfillCandidateMonths"]
            for shop in shops
        },
        "processedReadyMonths":{
            _s(shop.get("shop_id")):processed[_s(shop.get("shop_id"))]["readyMonths"]
            for shop in shops
        },
    }
    root=Path(args.output_dir)
    (root/f"multi_shop_history_summary_{args.month}.json").write_text(
        json.dumps(summary,ensure_ascii=False,indent=2,sort_keys=True),
        encoding="utf-8",
    )
    print(json.dumps(summary,ensure_ascii=False))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
