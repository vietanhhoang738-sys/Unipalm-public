#!/usr/bin/env python3
"""Build pre-production shop-scoped processed/control partitions from PASSed staging.

Input:
  staging_artifacts/<shop_key>/<YYYY-MM>/...

Output:
  processed_artifacts/<shop_key>/<YYYY-MM>/...

This runner never writes Google Drive, legacy processed folders, production Data
Mart, or UI. It is intended to prove the processed/control contract before a
storage cutover.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
from pathlib import Path

from modules.processed_layer import build_processed_partition


def _s(v):
    return "" if v is None else str(v).strip()


def _selected_shop_keys(staging_root:Path,month:str,requested:list[str])->list[str]:
    summary_path=staging_root/f"multi_shop_staging_summary_{month}.json"
    if not summary_path.exists():
        raise FileNotFoundError(f"staging summary not found: {summary_path}")
    summary=json.loads(summary_path.read_text(encoding="utf-8"))
    available=[
        _s(x.get("shop_key"))
        for x in summary.get("results") or []
        if _s(x.get("shop_key"))
    ]
    if requested and "all" not in requested:
        missing=[x for x in requested if x not in available]
        if missing:
            raise KeyError(f"requested shops not present in staging summary: {missing}")
        return list(dict.fromkeys(requested))
    return available


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--month",required=True)
    ap.add_argument("--staging-dir",default="staging_artifacts")
    ap.add_argument("--output-dir",default="processed_artifacts")
    ap.add_argument("--contract",default="config/processed_layer_contract.json")
    ap.add_argument("--shop-key",action="append",default=[])
    ap.add_argument("--run-id",default="")
    ap.add_argument("--pipeline-version",default="processed-layer-v1")
    args=ap.parse_args()

    if not re.fullmatch(r"\d{4}-\d{2}",args.month):
        raise ValueError("--month must be YYYY-MM")

    staging_root=Path(args.staging_dir)
    output_root=Path(args.output_dir)
    run_id=_s(args.run_id) or _s(os.environ.get("GITHUB_RUN_ID")) or "local-run"
    generated_at=dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()

    selected=_selected_shop_keys(staging_root,args.month,args.shop_key)
    if not selected:
        raise ValueError("no staged shops selected")

    results=[]
    for shop_key in selected:
        staging_dir=staging_root/shop_key/args.month
        try:
            result=build_processed_partition(
                staging_dir=staging_dir,
                output_root=output_root,
                shop_key=shop_key,
                period=args.month,
                run_id=run_id,
                contract_path=args.contract,
                pipeline_version=args.pipeline_version,
                generated_at=generated_at,
            )
            results.append({**result,"error":""})
        except Exception as exc:
            results.append({
                "shop_key":shop_key,
                "period":args.month,
                "status":"ERROR",
                "processed_partition_ready":False,
                "error":str(exc),
            })

    overall="PASS" if results and all(x.get("status")=="PASS" for x in results) else "FAIL"
    summary={
        "status":overall,
        "period":args.month,
        "selected_shop_count":len(selected),
        "results":results,
        "safety":{
            "legacy_processed_written":False,
            "production_data_mart_written":False,
            "ui_modified":False,
        },
    }
    output_root.mkdir(parents=True,exist_ok=True)
    (output_root/f"multi_shop_processed_summary_{args.month}.json").write_text(
        json.dumps(summary,ensure_ascii=False,indent=2,sort_keys=True),
        encoding="utf-8",
    )
    print(json.dumps(summary,ensure_ascii=False))
    return 0 if overall=="PASS" else 2


if __name__=="__main__":
    raise SystemExit(main())
