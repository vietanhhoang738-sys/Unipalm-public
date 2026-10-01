#!/usr/bin/env python3
"""Publish all-shop semantic v2 portfolio partition to PREPRODUCTION Drive."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
from pathlib import Path

from googleapiclient.discovery import build

from modules.drive_auth import resolve_drive_credentials
from modules.drive_partition_writer import retry_idempotent_drive_operation, upload_control_file
from modules.semantic_drive_writer import (
    load_semantic_storage_registry,
    publish_semantic_partition_atomic,
    validate_local_semantic_partition,
)
from modules.shop_registry import enabled_shops, load_shop_registry


def _s(v):
    return "" if v is None else str(v).strip()


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--month",required=True)
    ap.add_argument("--semantic-dir",default="semantic_artifacts")
    ap.add_argument("--storage-registry",default="config/storage_registry.json")
    ap.add_argument("--shop-registry",default="config/shop_registry.json")
    ap.add_argument("--run-id",default="")
    args=ap.parse_args()

    if not re.fullmatch(r"\d{4}-\d{2}",args.month):
        raise ValueError("--month must be YYYY-MM")

    storage=load_semantic_storage_registry(args.storage_registry)
    cfg=storage["semantic_v2"]
    shops=enabled_shops(load_shop_registry(args.shop_registry))
    expected_shop_ids={_s(x.get("shop_id")) for x in shops}

    semantic_root=Path(args.semantic_dir)
    summary_path=semantic_root/f"multi_shop_semantic_summary_{args.month}.json"
    part=semantic_root/args.month
    if not summary_path.exists():
        raise FileNotFoundError(f"semantic summary not found: {summary_path}")
    summary=json.loads(summary_path.read_text(encoding="utf-8"))
    if summary.get("status")!="PASS" or not summary.get("semantic_mart_ready"):
        raise ValueError("semantic summary is not PASS/ready")
    if int(summary.get("selected_shop_count") or 0)!=len(shops):
        raise ValueError("canonical semantic persistence requires all enabled shops")

    local=validate_local_semantic_partition(
        part,expected_period=args.month,expected_shop_ids=expected_shop_ids)
    if _s(summary.get("semantic_build_fingerprint"))!=local["semantic_build_fingerprint"]:
        raise ValueError("semantic summary fingerprint mismatch")

    run_id=_s(args.run_id) or _s(os.environ.get("GITHUB_RUN_ID")) or "local-run"
    auth_mode=_s((cfg.get("writer_policy") or {}).get("auth_mode"))
    creds,resolved_mode=resolve_drive_credentials(auth_mode=auth_mode)
    drive=build("drive","v3",credentials=creds,cache_discovery=False)

    try:
        result=retry_idempotent_drive_operation(
            lambda: publish_semantic_partition_atomic(
                drive,
                storage_cfg=storage,
                semantic_dir=part,
                period=args.month,
                expected_shop_ids=expected_shop_ids,
                run_id=run_id,
            ),
            attempts=3,
            base_delay_seconds=1.0,
        )
        overall="PASS"
        error=""
    except Exception as exc:
        result={
            "status":"ERROR","period":args.month,
            "semantic_build_fingerprint":local["semantic_build_fingerprint"],
            "error":str(exc),
        }
        overall="FAIL"
        error=str(exc)

    publish_summary={
        "status":overall,
        "layer":"semantic_v2",
        "storage_status":cfg.get("status"),
        "auth_mode":resolved_mode,
        "run_id":run_id,
        "period":args.month,
        "generated_at":dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "selected_shop_count":len(shops),
        "selected_shop_ids":sorted(expected_shop_ids),
        "result":result,
        "error":error,
        "safety":{
            "legacy_data_mart_written":False,
            "production_data_mart_written":False,
            "ui_modified":False,
        },
    }
    out=semantic_root/f"semantic_drive_publish_summary_{args.month}.json"
    out.write_text(
        json.dumps(publish_summary,ensure_ascii=False,indent=2,sort_keys=True),
        encoding="utf-8",
    )

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
            publish_summary["drive_control_audit_file_id"]=remote.get("id","")
            out.write_text(
                json.dumps(publish_summary,ensure_ascii=False,indent=2,sort_keys=True),
                encoding="utf-8",
            )
        except Exception as exc:
            publish_summary["drive_control_audit_error"]=str(exc)
            publish_summary["status"]="FAIL"
            overall="FAIL"
            out.write_text(
                json.dumps(publish_summary,ensure_ascii=False,indent=2,sort_keys=True),
                encoding="utf-8",
            )

    print(json.dumps(publish_summary,ensure_ascii=False))
    return 0 if overall=="PASS" else 2


if __name__=="__main__":
    raise SystemExit(main())
