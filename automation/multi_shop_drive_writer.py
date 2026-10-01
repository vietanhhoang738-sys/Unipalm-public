#!/usr/bin/env python3
"""Publish PASSed processed v2 candidates into the PREPRODUCTION Drive namespace."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
from pathlib import Path

from googleapiclient.discovery import build

from modules.drive_auth import resolve_drive_credentials

from modules.drive_partition_writer import (
    load_storage_registry,
    publish_partition_atomic,
    retry_idempotent_drive_operation,
    upload_control_file,
    validate_local_partition,
)


def _s(v):
    return "" if v is None else str(v).strip()


def drive_write_client(*,auth_mode:str):
    creds,resolved_mode=resolve_drive_credentials(auth_mode=auth_mode)
    return build("drive","v3",credentials=creds,cache_discovery=False),resolved_mode


def _selected(processed_root:Path,month:str,requested:list[str])->list[dict]:
    summary_path=processed_root/f"multi_shop_processed_summary_{month}.json"
    if not summary_path.exists():
        raise FileNotFoundError(f"processed summary not found: {summary_path}")
    summary=json.loads(summary_path.read_text(encoding="utf-8"))
    if summary.get("status")!="PASS":
        raise ValueError("processed summary is not PASS")
    rows=[
        x for x in summary.get("results") or []
        if _s(x.get("shop_key")) and x.get("status")=="PASS"
        and bool(x.get("processed_partition_ready"))
    ]
    if requested and "all" not in requested:
        wanted=set(requested)
        rows=[x for x in rows if _s(x.get("shop_key")) in wanted]
        found={_s(x.get("shop_key")) for x in rows}
        missing=sorted(wanted-found)
        if missing:
            raise KeyError(f"requested shops are not PASSed processed partitions: {missing}")
    if not rows:
        raise ValueError("no PASSed processed partitions selected")
    return rows


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--month",required=True)
    ap.add_argument("--processed-dir",default="processed_artifacts")
    ap.add_argument("--storage-registry",default="config/storage_registry.json")
    ap.add_argument("--shop-key",action="append",default=[])
    ap.add_argument("--run-id",default="")
    args=ap.parse_args()

    if not re.fullmatch(r"\d{4}-\d{2}",args.month):
        raise ValueError("--month must be YYYY-MM")

    run_id=_s(args.run_id) or _s(os.environ.get("GITHUB_RUN_ID")) or "local-run"
    processed_root=Path(args.processed_dir)
    storage=load_storage_registry(args.storage_registry)
    cfg=storage["processed_v2"]
    selected=_selected(processed_root,args.month,args.shop_key)

    # Preflight every selected shop before Drive mutation.
    preflight=[]
    for row in selected:
        shop_key=_s(row.get("shop_key"))
        part=processed_root/shop_key/args.month
        local=validate_local_partition(
            part,expected_shop_key=shop_key,expected_period=args.month)
        expected_fp=_s(row.get("build_fingerprint"))
        if expected_fp and local["build_fingerprint"]!=expected_fp:
            raise ValueError(
                f"{shop_key}/{args.month}: processed summary fingerprint mismatch")
        preflight.append({
            "shop_key":shop_key,
            "shop_id":local["shop_id"],
            "period":args.month,
            "build_fingerprint":local["build_fingerprint"],
            "file_count":len(local["files"]),
            "partition_dir":str(part),
        })

    drive,auth_mode=drive_write_client(auth_mode=_s((cfg.get("writer_policy") or {}).get("auth_mode")))
    results=[]
    for item in preflight:
        shop_key=item["shop_key"]
        try:
            result=retry_idempotent_drive_operation(
                lambda: publish_partition_atomic(
                    drive,
                    storage_cfg=storage,
                    partition_dir=Path(item["partition_dir"]),
                    shop_key=shop_key,
                    period=args.month,
                    run_id=run_id,
                ),
                attempts=3,
                base_delay_seconds=1.0,
            )
            results.append({**result,"error":""})
        except Exception as exc:
            results.append({
                "status":"ERROR",
                "shop_key":shop_key,
                "shop_id":item["shop_id"],
                "period":args.month,
                "build_fingerprint":item["build_fingerprint"],
                "error":str(exc),
            })

    overall="PASS" if all(x.get("status") in {"PUBLISHED","NOOP"} for x in results) else "FAIL"
    summary={
        "status":overall,
        "layer":"processed_v2",
        "storage_status":cfg.get("status"),
        "auth_mode":auth_mode,
        "run_id":run_id,
        "period":args.month,
        "generated_at":dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "selected_shop_count":len(preflight),
        "preflight":preflight,
        "results":results,
        "safety":{
            "legacy_processed_written":False,
            "production_data_mart_written":False,
            "ui_modified":False,
        },
    }
    out=processed_root/f"drive_publish_summary_{args.month}.json"
    out.write_text(
        json.dumps(summary,ensure_ascii=False,indent=2,sort_keys=True),
        encoding="utf-8",
    )

    # Audit the writer run even when a shop publish failed.
    control_id=_s(cfg.get("control_folder_id"))
    if control_id:
        try:
            remote=upload_control_file(
                drive,
                control_root_id=control_id,
                run_id=run_id,
                local_path=out,
                file_name=out.name,
            )
            summary["drive_control_audit_file_id"]=remote.get("id","")
            out.write_text(
                json.dumps(summary,ensure_ascii=False,indent=2,sort_keys=True),
                encoding="utf-8",
            )
        except Exception as exc:
            summary["drive_control_audit_error"]=str(exc)
            out.write_text(
                json.dumps(summary,ensure_ascii=False,indent=2,sort_keys=True),
                encoding="utf-8",
            )
            if overall=="PASS":
                overall="FAIL"
                summary["status"]="FAIL"

    print(json.dumps(summary,ensure_ascii=False))
    return 0 if overall=="PASS" else 2


if __name__=="__main__":
    raise SystemExit(main())
