from __future__ import annotations

import datetime as dt
import json
import os
import random
import re
import time
from pathlib import Path

import gspread
import requests
from google.oauth2.service_account import Credentials
from gspread.exceptions import APIError

ROOT = Path(__file__).resolve().parents[1]
meta = json.loads((ROOT / "automation" / "pipeline_state.json").read_text(encoding="utf-8"))

url = os.environ["UNIPALM_PRODUCTION_URL"]
state_id = os.environ["UNIPALM_STATE_SHEET_ID"]
commit = os.getenv("PUBLISHED_COMMIT", "")
build = meta["build_id"]
candidate = meta["candidate_reliable_end"]
run_id = meta["run_id"]

needle = f'<meta name="unipalm-build" content="{build}">'

# ---------------------------------------------------------------------------
# 1) Verify Vercel fixed URL exposes the exact build marker.
# ---------------------------------------------------------------------------
last = ""
for attempt in range(30):
    try:
        check_url = url.rstrip("/") + f"/?build_check={build}"
        r = requests.get(
            check_url,
            timeout=20,
            headers={"Cache-Control": "no-cache", "Pragma": "no-cache"},
        )
        last = f"HTTP {r.status_code} len={len(r.text)}"
        if r.ok and needle in r.text:
            print(f"Vercel build marker verified: {build}")
            break
    except Exception as exc:
        last = str(exc)
    time.sleep(10)
else:
    raise RuntimeError(
        f"Vercel fixed URL did not expose build {build} within 5 minutes. Last={last}"
    )

# ---------------------------------------------------------------------------
# 2) Finalize STATE / RUN_LOG.
#
# Production refresh can consume the Sheets per-user read quota immediately
# before this process starts.  The old finalizer called open_by_key() once and
# failed instantly on HTTP 429.  Retry every transient Sheets failure here.
# For 429, wait long enough for the per-minute quota window to roll over.
# ---------------------------------------------------------------------------
TRANSIENT = {429, 500, 502, 503, 504}


def api_status(exc: Exception):
    response = getattr(exc, "response", None)
    code = getattr(response, "status_code", None)
    if code:
        try:
            return int(code)
        except Exception:
            pass
    m = re.search(r"\[(429|500|502|503|504)\]", str(exc))
    return int(m.group(1)) if m else None


def google_retry(fn, label: str, retries: int = 8):
    delay = 5.0
    for attempt in range(1, retries + 1):
        try:
            return fn()
        except APIError as exc:
            status = api_status(exc)
            if status not in TRANSIENT or attempt >= retries:
                raise

            if status == 429:
                # Sheets quota is measured per minute per user.  A full minute
                # cooldown is more deterministic than short exponential retries.
                wait = 65.0 + random.uniform(0.5, 2.0)
            else:
                wait = min(delay, 45.0) + random.uniform(0.25, 1.25)
                delay = min(delay * 2, 45.0)

            print(
                f"[google-retry] {label}: HTTP {status}; "
                f"attempt {attempt}/{retries}; sleeping {wait:.1f}s"
            )
            time.sleep(wait)


scopes = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_info(
    json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]),
    scopes=scopes,
)
gc = gspread.authorize(creds)

sh = google_retry(
    lambda: gc.open_by_key(state_id),
    f"open state workbook {state_id}",
)
state = google_retry(lambda: sh.worksheet("STATE"), "open STATE worksheet")
run = google_retry(lambda: sh.worksheet("RUN_LOG"), "open RUN_LOG worksheet")

vals = google_retry(lambda: state.get_all_values(), "read STATE")

now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
updates = {
    "last_successful_publish_at": now,
    "common_reliable_end": candidate,
    "last_qa_status": "PASS",
    "latest_github_commit": commit,
    "latest_production_build": build,
}

# Build one batch update for existing keys; only append genuinely missing keys.
key_to_row = {}
for idx, row in enumerate(vals[1:], start=2):
    if row:
        key_to_row[str(row[0])] = idx

batch = []
missing = []
for key, value in updates.items():
    row_idx = key_to_row.get(key)
    if row_idx:
        batch.append({"range": f"B{row_idx}", "values": [[str(value)]]})
    else:
        missing.append([key, str(value), "", now])

if batch:
    google_retry(
        lambda: state.batch_update(batch, value_input_option="RAW"),
        "batch update STATE",
    )
if missing:
    google_retry(
        lambda: state.append_rows(
            missing,
            value_input_option="RAW",
            insert_data_option="INSERT_ROWS",
        ),
        "append missing STATE keys",
    )

# Avoid duplicate PUBLISH audit rows if finalization is retried for the same run.
run_vals = google_retry(lambda: run.get_all_values(), "read RUN_LOG")
already_logged = any(
    len(row) >= 7
    and str(row[0]) == str(run_id)
    and str(row[2]).upper() == "PUBLISH"
    and str(row[3]).upper() == "SUCCESS"
    for row in run_vals[1:]
)

if not already_logged:
    audit_row = [
        run_id,
        now,
        "PUBLISH",
        "SUCCESS",
        "",
        "",
        "PUBLISHED",
        "PASS",
        "Fixed URL build marker verified",
        candidate,
        commit,
        build,
        url,
        f"Verified {needle}",
    ]
    google_retry(
        lambda: run.append_row(audit_row, value_input_option="RAW"),
        "append PUBLISH audit row",
    )

print(
    f"Verified production build {build} at {url}; "
    f"reliable_end={candidate}; commit={commit}; state finalized"
)
