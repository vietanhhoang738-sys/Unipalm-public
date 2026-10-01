#!/usr/bin/env python3
"""Build multi-shop semantic marts from PASSed processed v2 candidates."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path

from modules.semantic_mart import build_semantic_marts
from modules.shop_registry import load_shop_registry, select_shops


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--month",required=True)
    ap.add_argument("--processed-dir",default="processed_artifacts")
    ap.add_argument("--output-dir",default="semantic_artifacts")
    ap.add_argument("--registry",default="config/shop_registry.json")
    ap.add_argument("--contract",default="config/semantic_mart_contract.json")
    ap.add_argument("--shop-key",action="append",default=[])
    args=ap.parse_args()

    if not re.fullmatch(r"\d{4}-\d{2}",args.month):
        raise ValueError("--month must be YYYY-MM")

    registry=load_shop_registry(args.registry)
    selected=select_shops(registry,args.shop_key or ["all"])

    summary_path=Path(args.processed_dir)/f"multi_shop_processed_summary_{args.month}.json"
    if not summary_path.exists():
        raise FileNotFoundError(f"processed summary not found: {summary_path}")
    processed_summary=json.loads(summary_path.read_text(encoding="utf-8"))
    if processed_summary.get("status")!="PASS":
        raise ValueError("processed summary is not PASS")

    by_key={str(x.get("shop_key")):x for x in processed_summary.get("results") or []}
    for shop in selected:
        row=by_key.get(str(shop["shop_key"]))
        if not row or row.get("status")!="PASS" or not row.get("processed_partition_ready"):
            raise ValueError(f"{shop['shop_key']}: processed partition is not ready")

    out=Path(args.output_dir)/args.month
    result=build_semantic_marts(
        processed_root=args.processed_dir,
        output_dir=out,
        period=args.month,
        shops=selected,
        contract_path=args.contract,
        generated_at=dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
    )

    root=Path(args.output_dir)
    root.mkdir(parents=True,exist_ok=True)
    summary={
        "status":"PASS",
        "period":args.month,
        "semantic_mart_ready":True,
        "semantic_build_fingerprint":result["semantic_build_fingerprint"],
        "selected_shop_count":result["selected_shop_count"],
        "freshness":result["freshness"],
        "output_location":result["output_location"],
        "safety":{
            "legacy_data_mart_written":False,
            "production_data_mart_written":False,
            "ui_modified":False,
        },
    }
    (root/f"multi_shop_semantic_summary_{args.month}.json").write_text(
        json.dumps(summary,ensure_ascii=False,indent=2,sort_keys=True),
        encoding="utf-8",
    )
    print(json.dumps(summary,ensure_ascii=False))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
