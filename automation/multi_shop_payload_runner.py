#!/usr/bin/env python3
"""Build canonical pre-production multi-shop UI payload from Semantic v2."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from modules.semantic_ads_payload import build_ui_payload


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--month",required=True)
    ap.add_argument("--semantic-dir",default="semantic_artifacts")
    ap.add_argument("--output-dir",default="payload_artifacts")
    ap.add_argument("--contract",default="config/ui_payload_contract.json")
    ap.add_argument("--history-dir",default="")
    ap.add_argument("--product-intelligence-dir",default="")
    ap.add_argument("--ads-intelligence-dir",default="")
    args=ap.parse_args()

    if not re.fullmatch(r"\d{4}-\d{2}",args.month):
        raise ValueError("--month must be YYYY-MM")

    semantic_part=Path(args.semantic_dir)/args.month
    out=Path(args.output_dir)/args.month
    history_path=(Path(args.history_dir)/"historical_intelligence.json") if args.history_dir else None
    product_dir=Path(args.product_intelligence_dir) if args.product_intelligence_dir else None
    ads_dir=Path(args.ads_intelligence_dir) if args.ads_intelligence_dir else None
    result=build_ui_payload(
        semantic_dir=semantic_part,
        output_dir=out,
        contract_path=args.contract,
        historical_path=history_path,
        product_intelligence_dir=product_dir,
        ads_intelligence_dir=ads_dir,
    )

    root=Path(args.output_dir)
    root.mkdir(parents=True,exist_ok=True)
    summary={
        "status":"PASS",
        "period":args.month,
        "payload_ready":True,
        "payload_build_fingerprint":result["payloadBuildFingerprint"],
        "source_semantic_fingerprint":result["sourceSemanticFingerprint"],
        "source_historical_fingerprint":result.get("sourceHistoricalFingerprint",""),
        "source_product_intelligence_fingerprint":result.get("sourceProductIntelligenceFingerprint",""),
        "source_ads_intelligence_fingerprint":result.get("sourceAdsIntelligenceFingerprint",""),
        "product_destination_ready":bool(result.get("productDestinationReady")),
        "ads_destination_ready":bool(result.get("adsDestinationReady")),
        "selected_shop_count":result["selectedShopCount"],
        "portfolio_coverage":result["portfolioCoverage"],
        "compare_pair_count":result["comparePairCount"],
        "output_location":result["outputLocation"],
        "safety":result["safety"],
    }
    (root/f"multi_shop_payload_summary_{args.month}.json").write_text(
        json.dumps(summary,ensure_ascii=False,indent=2,sort_keys=True),
        encoding="utf-8",
    )
    print(json.dumps(summary,ensure_ascii=False))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
