#!/usr/bin/env python3
"""Build PREPRODUCTION explicit-source business context calendar."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from modules.business_context_calendar import build_business_context


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--month",required=True)
    ap.add_argument("--contract",default="config/business_context_contract.json")
    ap.add_argument("--calendar",default="config/business_context_calendar.json")
    ap.add_argument("--output-dir",default="context_artifacts")
    args=ap.parse_args()

    if not re.fullmatch(r"\d{4}-\d{2}",args.month):
        raise ValueError("--month must be YYYY-MM")

    out=Path(args.output_dir)/args.month
    result=build_business_context(
        contract_path=args.contract,
        calendar_path=args.calendar,
        as_of_period=args.month,
        output_dir=out,
    )
    root=Path(args.output_dir)
    root.mkdir(parents=True,exist_ok=True)
    summary={
        "status":"PASS",
        "period":args.month,
        "context_build_fingerprint":result["contextBuildFingerprint"],
        "selected_event_count":result["selectedEventCount"],
        "context_day_row_count":result["contextDayRowCount"],
        "matching_eligible_event_count":result["matchingEligibleEventCount"],
        "output_location":result["outputLocation"],
        "safety":result["safety"],
    }
    (root/f"business_context_summary_{args.month}.json").write_text(
        json.dumps(summary,ensure_ascii=False,indent=2,sort_keys=True),
        encoding="utf-8",
    )
    print(json.dumps(summary,ensure_ascii=False))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
