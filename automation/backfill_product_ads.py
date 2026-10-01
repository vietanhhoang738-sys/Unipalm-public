"""Legacy single-shop product Ads mart audit/backfill.

This recovery tool exists only for the current production mart. It is NOT the
multi-shop ingestion path. Default mode is audit-only; --apply is allowed only
when source rows resolve to exactly one shop and the legacy destination mart
contains no different shop.

Product Ads aggregation grain is (shop_id, data_date, product_id).
Retire this tool after the registry-driven multi-shop mart is promoted.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List

import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from modules.ads_product_mart import (
    PRODUCT_ADS_COLUMNS,
    aggregate_product_ads_rows,
    audit_existing_product_ads_rows,
    validate_product_ads_rows,
)

ROOT = Path(__file__).resolve().parents[1]
RESULT_PATH = ROOT / "automation" / "product_ads_backfill_result.json"
MART_ID = os.environ["UNIPALM_DATA_MART_SHEET_ID"]
ADS_FOLDER_ID = os.environ["UNIPALM_PROCESSED_ADS_FOLDER_ID"]
SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
]
CREDS = Credentials.from_service_account_info(json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]), scopes=SCOPES)
GC = gspread.authorize(CREDS)
DRIVE = build("drive","v3",credentials=CREDS,cache_discovery=False)


def records(ws) -> List[Dict[str, Any]]:
    vals=ws.get_all_values()
    if not vals:
        return []
    headers=[str(x).strip() for x in vals[0]]
    out=[]
    for row in vals[1:]:
        if not any(x not in (None,"") for x in row):
            continue
        row=list(row)+[""]*max(0,len(headers)-len(row))
        out.append({h:row[j] if j<len(row) else "" for j,h in enumerate(headers) if h})
    return out


def single_shop_id(rows: List[Dict[str, Any]], *, label: str, allow_empty: bool = False) -> str:
    ids={str(r.get("shop_id","") or "").strip() for r in rows if str(r.get("shop_id","") or "").strip()}
    missing=sum(1 for r in rows if not str(r.get("shop_id","") or "").strip())
    if missing:
        raise RuntimeError(f"{label}: {missing} rows missing shop_id")
    if not ids and allow_empty:
        return ""
    if len(ids)!=1:
        raise RuntimeError(f"{label}: expected exactly one shop_id, found {sorted(ids)}")
    return next(iter(ids))


def discover_processed_ads() -> Dict[str,str]:
    q=f"'{ADS_FOLDER_ID}' in parents and trashed=false and mimeType='application/vnd.google-apps.spreadsheet'"
    page=None; out={}
    while True:
        resp=DRIVE.files().list(q=q,fields="nextPageToken,files(id,name)",pageToken=page,pageSize=1000).execute()
        for f in resp.get("files",[]):
            m=re.fullmatch(r"ads_processed_(\d{4})_(\d{2})",str(f.get("name","")))
            if m:
                out[f"{m.group(1)}-{m.group(2)}"]=f["id"]
        page=resp.get("nextPageToken")
        if not page:
            break
    return dict(sorted(out.items()))


def ensure_headers(ws) -> List[str]:
    headers=[str(x).strip() for x in ws.row_values(1)]
    missing=[x for x in PRODUCT_ADS_COLUMNS if x not in headers]
    if missing:
        headers=headers+missing
        ws.update(f"A1:{gspread.utils.rowcol_to_a1(1,len(headers)).replace('1','')}1",[headers],value_input_option="RAW")
    return headers


def replace_month(ws, month: str, rows: List[Dict[str,Any]]) -> int:
    vals=ws.get_all_values()
    headers=[str(x).strip() for x in vals[0]]
    di=headers.index("data_date")
    matching=[]
    for rnum,row in enumerate(vals[1:],start=2):
        d=row[di] if di<len(row) else ""
        if str(d).startswith(month):
            matching.append(rnum)
    if matching:
        if matching != list(range(min(matching),max(matching)+1)):
            raise RuntimeError(f"{month}: existing partition is non-contiguous")
        ws.delete_rows(min(matching),max(matching))
    matrix=[[r.get(h,"") for h in headers] for r in rows]
    if matrix:
        ws.append_rows(matrix,value_input_option="RAW",insert_data_option="INSERT_ROWS")
    return len(matrix)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--start-month",default="2025-11")
    ap.add_argument("--end-month",default="")
    ap.add_argument("--apply",action="store_true")
    args=ap.parse_args()

    mart=GC.open_by_key(MART_ID)
    ws=mart.worksheet("dm_ads_product_daily")
    existing=records(ws)
    existing_shop_id=single_shop_id(existing,label="existing dm_ads_product_daily",allow_empty=True)
    existing_audit=audit_existing_product_ads_rows(existing)

    sources=discover_processed_ads()
    months=[m for m in sources if m>=args.start_month and (not args.end_month or m<=args.end_month)]
    result={
        "mode":"APPLY" if args.apply else "AUDIT_ONLY",
        "existingAudit":existing_audit,
        "sourceMonths":months,
        "action":"NONE",
        "months":{},
    }

    # Healthy mart -> no destructive rewrite unless explicitly requested by a failing audit.
    if existing_audit["status"]=="PASS":
        result["action"]="NO_BACKFILL_REQUIRED"
        RESULT_PATH.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return

    if not months:
        raise RuntimeError("No processed Ads monthly sources discovered")

    ensure_headers(ws)
    for month in months:
        ss=GC.open_by_key(sources[month])
        raw=records(ss.worksheet("fact_ads_performance_daily"))
        source_shop_id=single_shop_id(raw,label=f"{month} processed Ads")
        if existing_shop_id and source_shop_id != existing_shop_id:
            raise RuntimeError(
                f"{month}: legacy destination belongs to {existing_shop_id}, "
                f"but source belongs to {source_shop_id}"
            )
        candidate=aggregate_product_ads_rows(raw,expected_shop_id=source_shop_id)
        qa=validate_product_ads_rows(candidate)
        result["months"][month]={"sourceId":sources[month],"shopId":source_shop_id,"rows":len(candidate),"qa":qa}
        if qa["status"]!="PASS":
            raise RuntimeError(f"{month}: candidate QA failed: {qa['errors']}")
        if args.apply:
            replace_month(ws,month,candidate)

    result["action"]="BACKFILLED" if args.apply else "BACKFILL_AVAILABLE"
    RESULT_PATH.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
