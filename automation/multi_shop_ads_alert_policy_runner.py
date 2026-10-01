#!/usr/bin/env python3
"""Build PREPRODUCTION Smart Issue Alert Policy sidecar from locked Ads artifacts."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from modules.ads_alert_policy import bind_ads_alert_policy_artifact


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--month", required=True)
    ap.add_argument("--ads-intelligence-dir", default="ads_intelligence_artifacts")
    ap.add_argument("--contract", default="config/ads_alert_policy_contract.json")
    ap.add_argument("--delivery-events", default="ops/ads_alert_delivery_events.json")
    ap.add_argument("--evaluation-at", default="")
    args = ap.parse_args()
    if not re.fullmatch(r"\d{4}-\d{2}", args.month):
        raise ValueError("--month must be YYYY-MM")

    root = Path(args.ads_intelligence_dir)
    ads_dir = root / args.month
    result = bind_ads_alert_policy_artifact(
        ads_output_dir=ads_dir,
        contract_path=args.contract,
        delivery_events_path=args.delivery_events,
        evaluation_at=args.evaluation_at,
    )
    summary = {
        "status": result["status"],
        "period": args.month,
        "adsIntelligenceFingerprint": result["adsIntelligenceFingerprint"],
        "adsSmartIssueRegistryFingerprint": result["adsSmartIssueRegistryFingerprint"],
        "adsSmartIssueAlertPolicyFingerprint": result["adsSmartIssueAlertPolicyFingerprint"],
        "smartIssueAlertPolicyStatus": result["smartIssueAlertPolicyStatus"],
        "eligibleAlertCount": result["eligibleAlertCount"],
        "suppressedIssueCount": result["suppressedIssueCount"],
        "deliveryEnabled": result["deliveryEnabled"],
        "automaticDeliveryEnabled": result["automaticDeliveryEnabled"],
        "doesNotModifyAdsIntelligenceFingerprint": True,
        "alertPolicyFile": str(ads_dir / "ads_alert_policy.json"),
    }
    root.mkdir(parents=True, exist_ok=True)
    (root / f"multi_shop_ads_alert_policy_summary_{args.month}.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
