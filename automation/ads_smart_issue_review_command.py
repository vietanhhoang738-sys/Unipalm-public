#!/usr/bin/env python3
"""Build or explicitly apply one human Smart Issue review ledger event."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from modules.ads_smart_issue_review_workflow import append_review_event, build_review_event_command


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workflow", required=True, help="Path to ads_smart_issue_review_workflow.json")
    ap.add_argument("--ledger", default="ops/ads_smart_issue_review_events.json")
    ap.add_argument("--action", required=True)
    target = ap.add_mutually_exclusive_group(required=True)
    target.add_argument("--candidate-key", default="")
    target.add_argument("--issue-id", default="")
    ap.add_argument("--reviewed-by", required=True)
    ap.add_argument("--reviewed-at", required=True, help="ISO-8601 timestamp with explicit timezone")
    ap.add_argument("--note", default="")
    ap.add_argument("--apply", action="store_true", help="Explicitly append the validated event to the ledger file")
    args = ap.parse_args()

    workflow = json.loads(Path(args.workflow).read_text(encoding="utf-8"))
    command = build_review_event_command(
        workflow,
        action=args.action,
        reviewed_by=args.reviewed_by,
        reviewed_at=args.reviewed_at,
        note=args.note,
        candidate_key=args.candidate_key,
        issue_id=args.issue_id,
    )
    result = append_review_event(
        review_ledger_path=args.ledger,
        command=command,
        apply=bool(args.apply),
    )
    output = {
        "command": command,
        "ledgerResult": {k: v for k, v in result.items() if k != "proposedLedger"},
        "safety": {
            "explicitApplyRequired": True,
            "automaticPromotionEnabled": False,
            "automaticStateTransitionEnabled": False,
            "automaticAlertsEnabled": False,
            "automaticActionsEnabled": False,
        },
    }
    print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
