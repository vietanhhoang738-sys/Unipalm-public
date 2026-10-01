#!/usr/bin/env python3
"""Build PREPRODUCTION Production Cutover Preparation & Execution-Control sidecar."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from modules.production_cutover_control import bind_production_cutover_control_artifact


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--month", required=True)
    ap.add_argument("--ads-intelligence-dir", default="ads_intelligence_artifacts")
    ap.add_argument("--native-v2-dir", default="native_v2_artifacts")
    ap.add_argument("--output-dir", default="production_cutover_artifacts")
    ap.add_argument("--contract", default="config/production_cutover_control_contract.json")
    ap.add_argument("--readiness-evidence", default="ops/production_cutover_evidence.json")
    ap.add_argument("--authorization-events", default="ops/production_cutover_authorization_events.json")
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--head-sha", required=True)
    ap.add_argument("--staging-run-id", required=True)
    args = ap.parse_args()
    if not re.fullmatch(r"\d{4}-\d{2}", args.month):
        raise ValueError("--month must be YYYY-MM")
    if not args.head_sha.strip() or not args.staging_run_id.strip():
        raise ValueError("--head-sha and --staging-run-id are required")

    out = Path(args.output_dir) / args.month
    result = bind_production_cutover_control_artifact(
        ads_output_dir=Path(args.ads_intelligence_dir) / args.month,
        native_output_dir=Path(args.native_v2_dir) / args.month,
        output_dir=out,
        contract_path=args.contract,
        readiness_evidence_path=args.readiness_evidence,
        authorization_events_path=args.authorization_events,
        repo_root=args.repo_root,
        period=args.month,
        head_sha=args.head_sha,
        staging_run_id=args.staging_run_id,
    )
    summary = {
        "status": result["status"],
        "period": args.month,
        "production_cutover_control_status": result["productionCutoverControlStatus"],
        "production_cutover_control_fingerprint": result["productionCutoverControlFingerprint"],
        "cutover_plan_fingerprint": result["cutoverPlanFingerprint"],
        "readiness_evidence_fingerprint": result["readinessEvidenceFingerprint"],
        "cutover_authorization_ledger_fingerprint": result["cutoverAuthorizationLedgerFingerprint"],
        "blocker_count": result["blockerCount"],
        "blockers": result["blockers"],
        "rollback_drill_status": result["rollbackDrillStatus"],
        "authenticated_executor_bound": result["authenticatedExecutorBound"],
        "execution_enabled": result["executionEnabled"],
        "execution_permit_issued": result["executionPermitIssued"],
        "platform_mutation_allowed": result["platformMutationAllowed"],
        "production_activation_enabled": result["productionActivationEnabled"],
        "qa_status": result["qaStatus"],
        "qa_check_count": result["qaCheckCount"],
        "qa_failed_check_count": result["qaFailedCheckCount"],
        "control_file": str(out / "production_cutover_control.json"),
        "qa_file": str(out / "production_cutover_control_qa.json"),
        "rollback_drill_file": str(out / "production_cutover_rollback_drill.json"),
    }
    root = Path(args.output_dir)
    root.mkdir(parents=True, exist_ok=True)
    (root / f"multi_shop_production_cutover_control_summary_{args.month}.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
