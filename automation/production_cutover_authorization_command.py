#!/usr/bin/env python3
"""Prepare/apply append-only production cutover authorization events.

This command never deploys or mutates production. APPROVE_CUTOVER_PLAN only records
human approval for a future explicit execution milestone.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from modules.production_cutover_control import (
    apply_cutover_authorization_event_command,
    build_cutover_authorization_event_command,
)


def _read(path: str | Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--control", required=True)
    ap.add_argument("--ledger", default="ops/production_cutover_authorization_events.json")
    ap.add_argument("--action", required=True, choices=["APPROVE_CUTOVER_PLAN", "REJECT_CUTOVER_PLAN", "REVOKE_CUTOVER_PLAN"])
    ap.add_argument("--authorized-by", required=True)
    ap.add_argument("--authorized-at", required=True)
    ap.add_argument("--note", default="")
    ap.add_argument("--expected-ledger-fingerprint", required=True)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    control = _read(args.control)
    ledger_path = Path(args.ledger)
    ledger = _read(ledger_path)
    command = build_cutover_authorization_event_command(
        control,
        action=args.action,
        authorized_by=args.authorized_by,
        authorized_at=args.authorized_at,
        note=args.note,
    )
    result = apply_cutover_authorization_event_command(
        ledger,
        command=command,
        expected_ledger_fingerprint=args.expected_ledger_fingerprint,
        apply=args.apply,
    )
    if args.apply:
        ledger_path.write_text(
            json.dumps(result["ledger"], ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
        )
    printable = dict(result)
    printable.pop("ledger", None)
    print(json.dumps(printable, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
