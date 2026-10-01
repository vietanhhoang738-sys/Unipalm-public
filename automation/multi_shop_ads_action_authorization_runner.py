#!/usr/bin/env python3
"""Build PREPRODUCTION Recommendation / Action Authorization v1 sidecar."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from modules.ads_action_authorization import bind_ads_action_authorization_artifact


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--month", required=True)
    ap.add_argument("--ads-intelligence-dir", default="ads_intelligence_artifacts")
    ap.add_argument("--contract", default="config/ads_action_authorization_contract.json")
    ap.add_argument("--authorization-events", default="ops/ads_action_authorization_events.json")
    args = ap.parse_args()
    if not re.fullmatch(r"\d{4}-\d{2}", args.month):
        raise ValueError("--month must be YYYY-MM")

    out = Path(args.ads_intelligence_dir) / args.month
    result = bind_ads_action_authorization_artifact(
        ads_output_dir=out,
        contract_path=args.contract,
        authorization_events_path=args.authorization_events,
    )
    summary = {
        "status": result["status"],
        "period": args.month,
        "ads_intelligence_fingerprint": result["adsIntelligenceFingerprint"],
        "ads_smart_issue_registry_fingerprint": result["adsSmartIssueRegistryFingerprint"],
        "ads_action_authorization_fingerprint": result["adsActionAuthorizationFingerprint"],
        "authorization_ledger_fingerprint": result["authorizationLedgerFingerprint"],
        "action_authorization_status": result["actionAuthorizationStatus"],
        "proposal_count": result["proposalCount"],
        "suppressed_issue_count": result["suppressedIssueCount"],
        "authenticated_executor_bound": result["authenticatedExecutorBound"],
        "execution_enabled": result["executionEnabled"],
        "platform_mutation_allowed": result["platformMutationAllowed"],
        "action_authorization_file": str(out / "ads_action_authorization.json"),
    }
    root = Path(args.ads_intelligence_dir)
    root.mkdir(parents=True, exist_ok=True)
    (root / f"multi_shop_ads_action_authorization_summary_{args.month}.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
