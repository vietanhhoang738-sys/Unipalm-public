#!/usr/bin/env python3
"""Build/apply an explicit Action Authorization ledger decision.

This command changes only the append-only PREPRODUCTION authorization ledger.
It never executes a platform/business mutation.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from modules.ads_action_authorization import (
    apply_authorization_event_command,
    build_authorization_event_command,
)


def read_json(path: str | Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--authorization-artifact", required=True)
    ap.add_argument("--ledger", default="ops/ads_action_authorization_events.json")
    ap.add_argument("--proposal-id", required=True)
    ap.add_argument("--action", required=True, choices=["APPROVE", "REJECT", "REVOKE"])
    ap.add_argument("--authorized-by", required=True)
    ap.add_argument("--authorized-at", required=True)
    ap.add_argument("--note", default="")
    ap.add_argument("--expected-ledger-fingerprint", required=True)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    artifact = read_json(args.authorization_artifact)
    ledger = read_json(args.ledger)
    command = build_authorization_event_command(
        artifact,
        action=args.action,
        proposal_id=args.proposal_id,
        authorized_by=args.authorized_by,
        authorized_at=args.authorized_at,
        note=args.note,
    )
    result = apply_authorization_event_command(
        ledger,
        command=command,
        expected_ledger_fingerprint=args.expected_ledger_fingerprint,
        apply=args.apply,
    )
    if args.apply:
        Path(args.ledger).write_text(
            json.dumps(result["proposedLedger"], ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    public = {k: v for k, v in result.items() if k != "proposedLedger"}
    public["authorizationArtifactFingerprint"] = artifact.get("actionAuthorizationFingerprint")
    print(json.dumps(public, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
