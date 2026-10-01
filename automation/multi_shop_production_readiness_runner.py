#!/usr/bin/env python3
"""Build PREPRODUCTION Production Readiness Hardening v1 evidence package."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from modules.production_readiness_hardening import bind_production_readiness_artifact


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--month", required=True)
    ap.add_argument("--source-run-id", required=True)
    ap.add_argument("--source-head-sha", required=True)
    ap.add_argument("--native-v2-dir", required=True)
    ap.add_argument("--production-baseline", required=True)
    ap.add_argument("--external-probe", required=True)
    ap.add_argument("--contract", default="config/production_readiness_hardening_contract.json")
    ap.add_argument("--output-dir", default="production_readiness_artifacts")
    args = ap.parse_args()
    if not re.fullmatch(r"\d{4}-\d{2}", args.month):
        raise ValueError("--month must be YYYY-MM")
    if not args.source_run_id.strip() or not args.source_head_sha.strip():
        raise ValueError("source run/head lineage is required")

    native_root = Path(args.native_v2_dir)
    summary = native_root / f"multi_shop_native_v2_summary_{args.month}.json"
    html = native_root / args.month / "command_center_v2_multi_shop_native_template.html"
    result = bind_production_readiness_artifact(
        native_summary_path=summary,
        native_html_path=html,
        production_baseline_path=args.production_baseline,
        external_probe_path=args.external_probe,
        contract_path=args.contract,
        output_dir=args.output_dir,
        period=args.month,
        source_run_id=args.source_run_id,
        source_head_sha=args.source_head_sha,
    )
    artifact = result["artifact"]
    qa = result["qa"]
    summary_out = {
        "status": result["status"],
        "period": args.month,
        "source_staging_run_id": artifact["sourceStagingRunId"],
        "source_head_sha": artifact["sourceHeadSha"],
        "production_readiness_hardening_status": artifact["status"],
        "production_readiness_hardening_fingerprint": artifact["productionReadinessHardeningFingerprint"],
        "release_candidate_fingerprint": artifact["releaseCandidateFingerprint"],
        "release_candidate_sha256": artifact["releaseCandidateSha256"],
        "production_baseline_sha256": artifact["productionBaselineSha256"],
        "pass_count": artifact["passCount"],
        "blocked_count": artifact["blockedCount"],
        "blocked_gates": [x["name"] for x in artifact["checks"] if x["status"] != "PASS"],
        "qa_status": qa["status"],
        "qa_failed_check_count": qa["failedCheckCount"],
        "production_write_performed": artifact["safety"]["productionWritePerformed"],
        "repository_write_performed": artifact["safety"]["repositoryWritePerformed"],
        "execution_enabled": artifact["safety"]["executionEnabled"],
        "execution_permit_issued": artifact["safety"]["executionPermitIssued"],
        "production_activation_enabled": artifact["safety"]["productionActivationEnabled"],
    }
    root = Path(args.output_dir)
    (root / f"multi_shop_production_readiness_summary_{args.month}.json").write_text(
        json.dumps(summary_out, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(json.dumps(summary_out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
