"""Unipalm processed-ready -> cumulative dashboard production mart refresher.

This controller intentionally uses the Control Center as the upstream readiness gate.
It does not fake or infer missing source partitions. Current-month daily data is
accepted only through the common source cutoff already validated by upstream DQ.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import random
import re
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import gspread
from google.oauth2.service_account import Credentials
from gspread.utils import ValueRenderOption
from gspread.exceptions import APIError

from modules.ads_product_mart import PRODUCT_ADS_COLUMNS, aggregate_product_ads_rows, validate_product_ads_rows

CONTROL_CENTER_ID = os.getenv("UNIPALM_CONTROL_CENTER_SHEET_ID", "PUBLIC_RESOURCE_LIVE_004")
PROD_MART_ID = os.environ["UNIPALM_DATA_MART_SHEET_ID"]
SKU_MASTER_ID = os.getenv("UNIPALM_SKU_MASTER_SHEET_ID", "PUBLIC_RESOURCE_LIVE_003")
ROOT = Path(__file__).resolve().parents[1]
RESULT_PATH = ROOT / "automation" / "source_processor_result.json"

SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
]
CREDS = Credentials.from_service_account_info(
    json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]), scopes=SCOPES
)
GC = gspread.authorize(CREDS)

REQUIRED_READY = [
    "Orders", "Returns & Refunds", "Ads", "Product Performance", "Business Insights", "Data Mart"
]


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def n(v: Any, default: float = 0.0) -> float:
    if v in (None, ""):
        return default
    if isinstance(v, bool):
        return float(v)
    if isinstance(v, (int, float)):
        return float(v) if math.isfinite(float(v)) else default
    s = str(v).strip().replace("₫", "").replace("đ", "").replace("VND", "").replace(" ", "")
    if not s:
        return default
    pct = s.endswith("%")
    s = s.rstrip("%")
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    elif s.count(".") > 1:
        s = s.replace(".", "")
    try:
        x = float(s)
        return x / 100.0 if pct else x
    except Exception:
        return default


def i(v: Any) -> int:
    return int(round(n(v, 0.0)))


def b(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in {"true", "1", "yes", "y"}


def require_shop_id(row: Dict[str, Any], context: str) -> str:
    sid = str(row.get("shop_id", "") or "").strip()
    if not sid:
        raise RuntimeError(f"{context}: missing shop_id")
    return sid


def assert_single_shop_sources(*sources: Tuple[str, List[Dict[str, Any]]]) -> str:
    ids = set()
    missing = []
    for label, rows in sources:
        for idx, row in enumerate(rows):
            sid = str(row.get("shop_id", "") or "").strip()
            if not sid:
                missing.append(f"{label}[{idx}]")
            else:
                ids.add(sid)
    if missing:
        raise RuntimeError(f"source rows missing shop_id: {missing[:20]}")
    if len(ids) != 1:
        raise RuntimeError(f"legacy production adapter requires exactly one shop per run; found {sorted(ids)}")
    return next(iter(ids))


def sheet_date(v: Any) -> dt.date | None:
    if v in (None, ""):
        return None
    if isinstance(v, (int, float)):
        return dt.date(1899, 12, 30) + dt.timedelta(days=int(math.floor(float(v))))
    s = str(v).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return dt.datetime.strptime(s[:10], fmt).date()
        except Exception:
            pass
    return None


def sheet_datetime(v: Any) -> dt.datetime | None:
    if v in (None, ""):
        return None
    if isinstance(v, (int, float)):
        base = dt.datetime(1899, 12, 30)
        return base + dt.timedelta(days=float(v))
    s = str(v).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return dt.datetime.strptime(s, fmt)
        except Exception:
            pass
    return None


def month_text(v: Any) -> str:
    d = sheet_date(v)
    if d:
        return d.strftime("%Y-%m")
    s = str(v or "").strip()
    m = re.match(r"^(\d{4})-(\d{2})", s)
    return f"{m.group(1)}-{m.group(2)}" if m else s[:7]



def _api_status(exc: Exception) -> int | None:
    response = getattr(exc, "response", None)
    code = getattr(response, "status_code", None)
    if code:
        try:
            return int(code)
        except Exception:
            pass
    m = re.search(r"\[(429|500|502|503|504)\]", str(exc))
    return int(m.group(1)) if m else None


def google_retry(fn, *, label: str = "Google Sheets call", retries: int = 8):
    """Retry transient Google Sheets API failures with exponential backoff + jitter.

    Retries:
      429 quota/rate-limit
      500/502/503/504 transient server/service errors

    Non-transient API errors fail immediately.
    """
    delay = 2.0
    last = None
    for attempt in range(1, retries + 1):
        try:
            return fn()
        except APIError as exc:
            last = exc
            status = _api_status(exc)
            transient = status in {429, 500, 502, 503, 504}
            if not transient or attempt >= retries:
                raise
            wait = min(delay, 45.0) + random.uniform(0.25, 1.25)
            print(
                f"[google-retry] {label}: HTTP {status}; "
                f"attempt {attempt}/{retries}, sleeping {wait:.1f}s"
            )
            time.sleep(wait)
            delay = min(delay * 2, 45.0)
    if last:
        raise last


def open_spreadsheet(file_id: str, *, label: str = "spreadsheet"):
    file_id = str(file_id or "").strip()
    if not file_id:
        raise RuntimeError(f"{label}: spreadsheet id is blank")
    return google_retry(
        lambda: GC.open_by_key(file_id),
        label=f"open {label} ({file_id})",
    )


def get_worksheet(spreadsheet, title: str):
    return google_retry(
        lambda: spreadsheet.worksheet(title),
        label=f"open worksheet {spreadsheet.id}/{title}",
    )


def sheet_values(ws, *, unformatted: bool = True, retries: int = 8):
    def _read():
        if unformatted:
            return ws.get_all_values(value_render_option=ValueRenderOption.unformatted)
        return ws.get_all_values()
    return google_retry(
        _read,
        label=f"read worksheet {getattr(ws, 'title', '?')}",
        retries=retries,
    )


def sheet_write(fn, *, label: str):
    return google_retry(fn, label=label, retries=8)


def records(ws) -> List[Dict[str, Any]]:
    values = sheet_values(ws, unformatted=True)
    if not values:
        return []
    headers = [str(x).strip() for x in values[0]]
    out = []
    for row in values[1:]:
        if not any(x not in (None, "") for x in row):
            continue
        padded = list(row) + [""] * max(0, len(headers) - len(row))
        out.append({h: padded[j] if j < len(padded) else "" for j, h in enumerate(headers) if h})
    return out


def row_matrix(rows: List[Dict[str, Any]], headers: List[str]) -> List[List[Any]]:
    return [[r.get(h, "") for h in headers] for r in rows]


def ensure_columns(ws, required: List[str]) -> List[str]:
    """Append missing columns to an existing mart sheet without touching data."""
    vals = sheet_values(ws, unformatted=False)
    if not vals:
        raise RuntimeError(f"{ws.title}: empty worksheet")
    headers = [str(x).strip() for x in vals[0]]
    missing = [x for x in required if x not in headers]
    if not missing:
        return headers
    new_headers = headers + missing
    end_col = gspread.utils.rowcol_to_a1(1, len(new_headers)).replace("1","")
    sheet_write(
        lambda: ws.update(f"A1:{end_col}1", [new_headers], value_input_option="RAW"),
        label=f"extend {ws.title} headers",
    )
    return new_headers


def replace_partition(ws, key_col: str, prefix: str, rows: List[Dict[str, Any]]) -> int:
    # One read per worksheet. V2.0.1 used three reads (header + full table + post-write count),
    # which could exhaust the per-user Google Sheets read quota during a production refresh.
    vals = sheet_values(ws, unformatted=True)
    if not vals:
        raise RuntimeError(f"{ws.title}: empty worksheet")
    headers = [str(x).strip() for x in vals[0]]
    if key_col not in headers:
        raise RuntimeError(f"{ws.title}: missing partition key column {key_col}")
    key_idx = headers.index(key_col)

    matching_rows = []
    for rnum, row in enumerate(vals[1:], start=2):
        value = row[key_idx] if key_idx < len(row) else ""
        if str(value).startswith(prefix):
            matching_rows.append(rnum)

    # Delete only the target partition range, never "target -> end of sheet".
    # This keeps historical republish safe even when later months already exist.
    if matching_rows:
        first, last = min(matching_rows), max(matching_rows)
        expected = list(range(first, last + 1))
        if matching_rows != expected:
            raise RuntimeError(
                f"{ws.title}: target partition {prefix} is non-contiguous; "
                f"refusing destructive rewrite"
            )
        sheet_write(lambda: ws.delete_rows(first, last), label=f"delete {ws.title} partition {prefix}")

    matrix = row_matrix(rows, headers)
    if matrix:
        # Partitions are materialized chronologically; target month is expected at the tail
        # during normal forward operation. For a same-month rerun, deleting then appending
        # replaces that partition idempotently.
        sheet_write(lambda: ws.append_rows(matrix, value_input_option="RAW", insert_data_option="INSERT_ROWS"), label=f"append {ws.title} partition {prefix}")

    current_count = max(0, len(vals) - 1)
    return current_count - len(matching_rows) + len(matrix)


def replace_all_data(ws, rows: List[Dict[str, Any]]) -> int:
    vals = sheet_values(ws, unformatted=False)
    if not vals:
        raise RuntimeError(f"{ws.title}: empty worksheet")
    headers = [str(x).strip() for x in vals[0]]
    if len(vals) > 1:
        sheet_write(lambda: ws.delete_rows(2, len(vals)), label=f"clear {ws.title} data")
    matrix = row_matrix(rows, headers)
    if matrix:
        sheet_write(lambda: ws.append_rows(matrix, value_input_option="RAW", insert_data_option="INSERT_ROWS"), label=f"append {ws.title} full data")
    return len(matrix)


def set_kv(ws, key: str, value: Any) -> None:
    vals = sheet_values(ws, unformatted=False)
    for idx, row in enumerate(vals[1:], start=2):
        if row and str(row[0]).strip() == key:
            sheet_write(lambda: ws.update_cell(idx, 2, value), label=f"update {ws.title} {key}")
            return
    sheet_write(lambda: ws.append_row([key, value], value_input_option="RAW"), label=f"append {ws.title} {key}")


def status_rows() -> Dict[str, Dict[str, Any]]:
    cc = open_spreadsheet(CONTROL_CENTER_ID, label="Control Center")
    rs = records(get_worksheet(cc, "PIPELINE_STATUS"))
    return {str(r.get("pipeline", "")).strip(): r for r in rs}


def require_ready(status: Dict[str, Dict[str, Any]]) -> None:
    problems = []
    for name in REQUIRED_READY:
        r = status.get(name)
        if not r:
            problems.append(f"{name}: missing PIPELINE_STATUS row")
            continue
        if str(r.get("state", "")).upper() != "READY" or str(r.get("last_run_status", "")).upper() != "SUCCESS":
            problems.append(f"{name}: state={r.get('state')} last_run={r.get('last_run_status')}")
    if problems:
        raise RuntimeError("Upstream Control Center is not publish-ready: " + " | ".join(problems))


def open_source(file_id: str):
    if not file_id:
        raise RuntimeError("Control Center output_spreadsheet_id is blank")
    return open_spreadsheet(str(file_id).strip(), label="upstream source")


def expected_dates(month: str, cutoff: dt.date) -> List[dt.date]:
    y, m = map(int, month.split("-"))
    cur = dt.date(y, m, 1)
    out = []
    while cur <= cutoff:
        out.append(cur)
        cur += dt.timedelta(days=1)
    return out


def validate_bi_coverage(bi_shop: List[Dict[str, Any]], target: str) -> dt.date:
    stage_dates: Dict[str, set] = defaultdict(set)
    for r in bi_shop:
        d = sheet_date(r.get("data_date"))
        if d and d.strftime("%Y-%m") == target:
            stage_dates[str(r.get("order_stage", ""))].add(d)
    for stage in ("placed", "confirmed", "paid"):
        if not stage_dates.get(stage):
            raise RuntimeError(f"Business Insights missing {stage} daily rows for {target}")
    maxes = {stage: max(stage_dates[stage]) for stage in ("placed", "confirmed", "paid")}
    if len(set(maxes.values())) != 1:
        raise RuntimeError(f"Business Insights stage cutoffs mismatch: {maxes}")
    cutoff = next(iter(maxes.values()))
    exp = set(expected_dates(target, cutoff))
    for stage in ("placed", "confirmed", "paid"):
        if stage_dates[stage] != exp:
            miss = sorted(exp - stage_dates[stage])
            extra = sorted(stage_dates[stage] - exp)
            raise RuntimeError(f"Business Insights {stage} date coverage invalid. missing={miss[:5]} extra={extra[:5]}")
    return cutoff


def source_cutoff(rows: List[Dict[str, Any]], field: str, target: str) -> dt.date | None:
    dates = [sheet_date(r.get(field)) for r in rows]
    dates = [d for d in dates if d and d.strftime("%Y-%m") == target]
    return max(dates) if dates else None


def product_canonical_maps(prod_mart) -> Tuple[Dict[str, Dict[str, str]], Dict[str, Dict[str, str]]]:
    current = records(prod_mart.worksheet("dm_product_monthly"))
    by_id, by_sku = {}, {}
    for r in current:
        data = {
            "name": str(r.get("product_name", "") or ""),
            "category": str(r.get("category", "") or ""),
            "sku": str(r.get("product_sku", "") or ""),
        }
        pid = str(r.get("product_id", "") or "")
        sku = data["sku"]
        if pid: by_id[pid] = data
        if sku: by_sku[sku] = data
    return by_id, by_sku


def fallback_category(sku: str, name: str) -> str:
    s = (sku or "").upper()
    text = (name or "").lower()
    if s.startswith("CB") or "cặp đôi" in text or "combo" in text: return "Combo & Cặp Đôi"
    if s.startswith("MS") or "khẩu trang" in text: return "Khẩu trang"
    if s.startswith("GL") or "găng tay" in text or "ống tay" in text: return "Găng tay"
    if s.startswith(("PK", "SO", "CT")) or "quà tặng" in text: return "Quà tặng"
    return "Khác"


def build_shop_hourly(
    target: str,
    common_cutoff: dt.date,
    order_cutoff: dt.date,
    orders_all: List[Dict[str, Any]],
    order_items_all: List[Dict[str, Any]],
    bi_shop_all: List[Dict[str, Any]],
    orders_version: str,
    orders_run_id: str,
    expected_shop_id: str,
) -> List[Dict[str, Any]]:
    """Build Orders-timestamp hourly operational mart.

    This table is intentionally a proxy layer, not the canonical BI confirmed-GMV
    authority. It preserves minute-level order timing for matched-hour operations
    and records end-of-day reconciliation against BI placed gross sales.
    """
    orders = [
        r for r in orders_all
        if (sheet_date(r.get("order_created_at")) or dt.date.min).strftime("%Y-%m") == target
        and (sheet_date(r.get("order_created_at")) or dt.date.min) <= order_cutoff
    ]
    order_meta: Dict[str, Dict[str, Any]] = {}
    snapshot_dates: List[dt.date] = []
    for r in orders:
        created = sheet_datetime(r.get("order_created_at"))
        if not created:
            continue
        oid = str(r.get("order_id", "") or "")
        if not oid:
            continue
        order_meta[oid] = {
            "created": created,
            "shop_id": require_shop_id(r, "Orders"),
            "order_total_value": n(r.get("order_total_value")),
            "buyer_total_payment": n(r.get("buyer_total_payment")),
            "shop_voucher": n(r.get("shop_voucher")),
            "shopee_voucher": n(r.get("shopee_voucher")),
        }
        ld = sheet_date(r.get("loaded_at"))
        if ld:
            snapshot_dates.append(ld)

    item_sales_by_order: Dict[str, float] = defaultdict(float)
    for r in order_items_all:
        oid = str(r.get("order_id", "") or "")
        if oid in order_meta:
            item_sales_by_order[oid] += n(r.get("item_buyer_payment"))

    hourly: Dict[Tuple[str, int], Dict[str, Any]] = {}
    for oid, meta in order_meta.items():
        created = meta["created"]
        d = created.date().isoformat()
        h = int(created.hour)
        key = (d, h)
        if key not in hourly:
            hourly[key] = {
                "shop_id": meta["shop_id"],
                "data_date": d,
                "hour_local": h,
                "orders_created_count": 0,
                "order_total_value": 0.0,
                "buyer_total_payment": 0.0,
                "shop_voucher": 0.0,
                "shopee_voucher": 0.0,
                "item_sales_base": 0.0,
            }
        rec = hourly[key]
        rec["orders_created_count"] += 1
        rec["order_total_value"] += meta["order_total_value"]
        rec["buyer_total_payment"] += meta["buyer_total_payment"]
        rec["shop_voucher"] += meta["shop_voucher"]
        rec["shopee_voucher"] += meta["shopee_voucher"]
        rec["item_sales_base"] += item_sales_by_order.get(oid, 0.0)

    daily_proxy = defaultdict(lambda: {"item_sales_base": 0.0, "shop_voucher": 0.0})
    for rec in hourly.values():
        d = rec["data_date"]
        daily_proxy[d]["item_sales_base"] += n(rec.get("item_sales_base"))
        daily_proxy[d]["shop_voucher"] += n(rec.get("shop_voucher"))

    bi_placed = {}
    for r in bi_shop_all:
        d = sheet_date(r.get("data_date"))
        if d and d.strftime("%Y-%m") == target and d <= common_cutoff and str(r.get("order_stage", "")) == "placed":
            bi_placed[d.isoformat()] = n(r.get("gross_sales"))

    snapshot_date = max(snapshot_dates) if snapshot_dates else order_cutoff
    rows = []
    for (d, h), rec in sorted(hourly.items()):
        day_proxy = daily_proxy[d]["item_sales_base"] - daily_proxy[d]["shop_voucher"]
        authority = bi_placed.get(d)
        diff: Any = ""
        diff_pct: Any = ""
        reconciliation = "NO_BI_YET"
        reliable = False
        if authority is not None:
            diff = day_proxy - authority
            diff_pct = (diff / authority) if authority else 0.0
            if abs(diff) <= 1.0:
                reconciliation = "EXACT"
                reliable = True
            elif abs(diff_pct) <= 0.005:
                reconciliation = "CLOSE_LE_0_5PCT"
                reliable = True
            else:
                reconciliation = "REVIEW_GT_0_5PCT"

        placed_proxy = n(rec.get("item_sales_base")) - n(rec.get("shop_voucher"))
        count = i(rec.get("orders_created_count"))
        rows.append({
            "shop_id": rec["shop_id"],
            "data_date": d,
            "hour_local": h,
            "hour_end_at": f"{d} {h:02d}:59:59",
            "orders_created_count": count,
            "order_total_value": n(rec.get("order_total_value")),
            "buyer_total_payment": n(rec.get("buyer_total_payment")),
            "shop_voucher": n(rec.get("shop_voucher")),
            "shopee_voucher": n(rec.get("shopee_voucher")),
            "item_sales_base": n(rec.get("item_sales_base")),
            "placed_gmv_proxy": placed_proxy,
            "aov_proxy": (placed_proxy / count if count else ""),
            "bi_placed_gmv_daily": authority if authority is not None else "",
            "proxy_daily_diff": diff,
            "proxy_daily_diff_pct": diff_pct,
            "reconciliation_status": reconciliation,
            "reliable_flag": reliable,
            "data_status": "PARTIAL_SOURCE_DAY" if d == snapshot_date.isoformat() else "COMPLETE_ORDERS_DAY",
            "source_snapshot_date": snapshot_date.isoformat(),
            "source_period": target,
            "source_version": orders_version,
            "source_run_id": orders_run_id,
        })
    return rows


def build_rows(target: str, cutoff: dt.date, order_cutoff: dt.date, status: Dict[str, Dict[str, Any]], prod_mart) -> Dict[str, List[Dict[str, Any]]]:
    orders_ss = open_source(status["Orders"].get("output_spreadsheet_id"))
    ads_ss = open_source(status["Ads"].get("output_spreadsheet_id"))
    product_ss = open_source(status["Product Performance"].get("output_spreadsheet_id"))
    bi_ss = open_source(status["Business Insights"].get("output_spreadsheet_id"))

    bi_shop_all = records(get_worksheet(bi_ss, "fact_shop_performance_daily"))
    bi_traffic_daily_all = records(bi_ss.worksheet("fact_traffic_source_daily"))
    bi_traffic_monthly_all = records(bi_ss.worksheet("fact_traffic_source_monthly"))
    ads_all = records(get_worksheet(ads_ss, "fact_ads_performance_daily"))
    products_all = records(product_ss.worksheet("fact_product_performance_monthly"))
    orders_all = records(get_worksheet(orders_ss, "fact_orders"))
    order_items_all = records(get_worksheet(orders_ss, "fact_order_items"))

    source_shop_id = assert_single_shop_sources(
        ("Business Insights", bi_shop_all),
        ("Ads", ads_all),
        ("Product Performance", products_all),
        ("Orders", orders_all),
        ("Order Items", order_items_all),
    )

    bi_shop = [r for r in bi_shop_all if (sheet_date(r.get("data_date")) or dt.date.min).strftime("%Y-%m") == target and sheet_date(r.get("data_date")) <= cutoff]
    traffic_daily = [r for r in bi_traffic_daily_all if (sheet_date(r.get("data_date")) or dt.date.min).strftime("%Y-%m") == target and sheet_date(r.get("data_date")) <= cutoff]
    traffic_monthly = [r for r in bi_traffic_monthly_all if month_text(r.get("data_month")) == target]
    ads = [r for r in ads_all if (sheet_date(r.get("data_date")) or dt.date.min).strftime("%Y-%m") == target and sheet_date(r.get("data_date")) <= cutoff]
    products = [r for r in products_all if month_text(r.get("data_month")) == target]
    orders = [r for r in orders_all if (sheet_date(r.get("order_created_at")) or dt.date.min).strftime("%Y-%m") == target and sheet_date(r.get("order_created_at")) <= cutoff]
    shop_hourly = build_shop_hourly(
        target, cutoff, order_cutoff, orders_all, order_items_all, bi_shop_all,
        str(status["Orders"].get("version", "") or ""),
        str(status["Orders"].get("latest_run_id", "") or ""),
        source_shop_id,
    )

    by_stage_date = {}
    for r in bi_shop:
        d = sheet_date(r.get("data_date")).isoformat()
        by_stage_date[(d, str(r.get("order_stage")))] = r

    # Ads aggregates: all service rows contribute to shop-level totals. Product rows only to product-level mart.
    ads_day = defaultdict(lambda: defaultdict(float))
    for r in ads:
        d = sheet_date(r.get("data_date")).isoformat()
        for f in ("impressions", "clicks", "add_to_cart", "conversions", "units_sold", "attributed_sales", "ad_spend"):
            ads_day[d][f] += n(r.get(f))

    # Orders aggregates by creation day. Cancelled orders must have zero platform fees.
    order_day = defaultdict(lambda: {"orders": 0, "fixed": 0.0, "service": 0.0, "transaction": 0.0, "fulfill": []})
    bad_cancel_fees = []
    for r in orders:
        d0 = sheet_date(r.get("order_created_at"))
        if not d0: continue
        d = d0.isoformat()
        rec = order_day[d]
        rec["orders"] += 1
        fixed, service, tx = n(r.get("fixed_fee")), n(r.get("service_fee")), n(r.get("transaction_fee"))
        cancelled = str(r.get("order_status", "")).strip() == "Đã hủy" or r.get("cancelled_at") not in (None, "")
        if cancelled and abs(fixed) + abs(service) + abs(tx) > 1e-9:
            bad_cancel_fees.append(str(r.get("order_id", "")))
        rec["fixed"] += fixed; rec["service"] += service; rec["transaction"] += tx
        created = sheet_datetime(r.get("order_created_at")); shipped = sheet_datetime(r.get("ship_date"))
        if created and shipped and shipped >= created:
            rec["fulfill"].append((shipped-created).total_seconds()/3600.0)
    if bad_cancel_fees:
        raise RuntimeError(f"Cancelled orders with non-zero fees: {bad_cancel_fees[:10]}")

    commercial = []
    shop = []
    quality = []
    for d0 in expected_dates(target, cutoff):
        d = d0.isoformat()
        for stage in ("placed", "confirmed", "paid"):
            r = by_stage_date.get((d, stage))
            if not r:
                raise RuntimeError(f"Missing Business Insights {stage} row for {d}")
            orders_n = i(r.get("order_count")); cancelled_n = i(r.get("cancelled_orders")); rr_n = i(r.get("returned_refunded_orders"))
            commercial.append({
                "shop_id": require_shop_id(r, "source row"), "data_date": d, "order_stage": stage,
                "gmv": n(r.get("gross_sales")), "orders": orders_n,
                "aov": n(r.get("sales_per_order")) if orders_n else "", "product_clicks": i(r.get("product_clicks")),
                "visits": i(r.get("visits")), "cvr": n(r.get("order_conversion_rate")),
                "cancelled_orders": cancelled_n, "cancelled_sales": n(r.get("cancelled_sales")),
                "cancel_rate": (cancelled_n/orders_n if orders_n else ""), "rr_orders": rr_n,
                "rr_sales": n(r.get("returned_refunded_sales")), "rr_rate": (rr_n/orders_n if orders_n else ""),
                "buyers": i(r.get("buyers")), "new_buyers": i(r.get("new_buyers")),
                "existing_buyers": i(r.get("existing_buyers")), "potential_buyers": i(r.get("potential_buyers")),
            })
        placed = by_stage_date[(d, "placed")]; confirmed = by_stage_date[(d, "confirmed")]; paid = by_stage_date[(d, "paid")]
        od = order_day[d]; ad = ads_day[d]
        fees = od["fixed"] + od["service"] + od["transaction"]
        placed_gmv = n(placed.get("gross_sales")); cancelled_sales = n(placed.get("cancelled_sales")); net = placed_gmv - cancelled_sales
        spend = ad["ad_spend"]
        shop.append({
            "shop_id": require_shop_id(placed, "Business Insights placed"), "data_date": d,
            "visits": i(placed.get("visits")), "product_clicks": i(placed.get("product_clicks")), "buyers": i(placed.get("buyers")),
            "new_buyers": i(placed.get("new_buyers")), "existing_buyers": i(placed.get("existing_buyers")), "potential_buyers": i(placed.get("potential_buyers")),
            "placed_gmv": placed_gmv, "placed_orders": i(placed.get("order_count")),
            "confirmed_gmv": n(confirmed.get("gross_sales")), "confirmed_orders": i(confirmed.get("order_count")),
            "paid_gmv": n(paid.get("gross_sales")), "paid_orders": i(paid.get("order_count")),
            "cancelled_sales": cancelled_sales, "net_sales_after_cancel": net,
            "ads_spend": spend, "order_fees": fees,
            "total_platform_cost_ratio": ((fees + spend)/net if net > 0 else ""),
            "reliable_flag": True, "data_status": "CURRENT_MTD" if cutoff < (dt.date(d0.year, d0.month % 12 + 1, 1) - dt.timedelta(days=1) if d0.month < 12 else dt.date(d0.year,12,31)) else "OK",
        })
        pr = by_stage_date[(d, "placed")]
        fulfill = od["fulfill"]
        quality.append({
            "shop_id": prequire_shop_id(r, "source row"), "data_date": d,
            "total_orders": od["orders"], "cancelled_orders": i(pr.get("cancelled_orders")),
            "cancel_rate": (i(pr.get("cancelled_orders"))/od["orders"] if od["orders"] else ""),
            "rr_orders": i(pr.get("returned_refunded_orders")),
            "rr_rate": (i(pr.get("returned_refunded_orders"))/od["orders"] if od["orders"] else ""),
            "avg_fulfill_hours": (sum(fulfill)/len(fulfill) if fulfill else ""), "on_time_ship_rate": "", "late_ship_orders": "",
            "fixed_fee": od["fixed"], "service_fee": od["service"], "transaction_fee": od["transaction"], "order_fees": fees,
            "data_status": "OK",
        })

    td = []
    for r in traffic_daily:
        td.append({
            "shop_id": require_shop_id(r, "source row"), "data_date": sheet_date(r.get("data_date")).isoformat(),
            "order_stage": r.get("order_stage"), "channel_group": r.get("channel_group"), "traffic_source": r.get("traffic_source"),
            "is_group_total": b(r.get("is_group_total")), "sales_share": n(r.get("sales_share")), "sales": n(r.get("sales")),
            "impressions": i(r.get("impressions")), "clicks": i(r.get("clicks")), "attributed_orders": n(r.get("attributed_orders")),
            "attributed_units": n(r.get("attributed_units")), "ctr": n(r.get("ctr")), "conversion_rate": n(r.get("conversion_rate")),
            "sales_per_order": n(r.get("sales_per_order")), "buyers": i(r.get("buyers")),
            "unique_impressions": i(r.get("unique_impressions")), "unique_clicks": i(r.get("unique_clicks")),
            "ad_spend": n(r.get("ad_spend")), "roas": n(r.get("roas")),
        })
    tm = []
    for r in traffic_monthly:
        x = dict(r)
        tm.append({
            "shop_id": require_shop_id(x, "traffic monthly"), "data_month": target,
            "order_stage": x.get("order_stage"), "channel_group": x.get("channel_group"), "traffic_source": x.get("traffic_source"),
            "is_group_total": b(x.get("is_group_total")), "sales_share": n(x.get("sales_share")), "sales": n(x.get("sales")),
            "impressions": i(x.get("impressions")), "clicks": i(x.get("clicks")), "attributed_orders": n(x.get("attributed_orders")),
            "attributed_units": n(x.get("attributed_units")), "ctr": n(x.get("ctr")), "conversion_rate": n(x.get("conversion_rate")),
            "sales_per_order": n(x.get("sales_per_order")), "buyers": i(x.get("buyers")),
            "unique_impressions": i(x.get("unique_impressions")), "unique_clicks": i(x.get("unique_clicks")),
            "ad_spend": n(x.get("ad_spend")), "roas": n(x.get("roas")),
        })

    ads_daily = []
    for d in sorted(ads_day):
        a = ads_day[d]; clicks=a["clicks"]; impr=a["impressions"]; conv=a["conversions"]; spend=a["ad_spend"]; sales=a["attributed_sales"]
        ads_daily.append({
            "shop_id":source_shop_id, "data_date":d, "impressions":i(impr), "clicks":i(clicks),
            "ctr":(clicks/impr if impr else 0), "add_to_cart":i(a["add_to_cart"]), "conversions":i(conv),
            "cvr":(conv/clicks if clicks else 0), "units_sold":i(a["units_sold"]), "attributed_sales":sales,
            "ad_spend":spend, "roas":(sales/spend if spend else 0), "cpc":(spend/clicks if clicks else 0),
            "cpm":(spend*1000/impr if impr else 0), "cpa":(spend/conv if conv else 0), "acos":(spend/sales if sales else 0),
        })

    by_id, by_sku = product_canonical_maps(prod_mart)
    src_product_by_id = {str(r.get("product_id")): r for r in products if str(r.get("product_id", ""))}
    feature_health: Dict[str, Dict[str, Any]] = {}
    try:
        metadata_by_product: Dict[str, Dict[str, Any]] = {}
        for r in ads:
            if str(r.get("ad_scope","")).strip().lower()!="product":
                continue
            pid=str(r.get("product_id","") or "")
            if not pid:
                continue
            src=src_product_by_id.get(pid,{})
            sku=str(src.get("product_sku","") or r.get("product_sku","") or "")
            can=by_id.get(pid) or by_sku.get(sku) or {}
            name=can.get("name") or str(src.get("product_name","") or r.get("product_name","") or pid)
            metadata_by_product[pid]={
                "product_sku":sku,
                "product_name":name,
                "category":can.get("category") or fallback_category(sku,name),
            }
        ads_product_daily=aggregate_product_ads_rows(ads,metadata_by_product,expected_shop_id=source_shop_id)
        product_ads_qa=validate_product_ads_rows(ads_product_daily)
        if product_ads_qa.get("status")!="PASS":
            raise RuntimeError("product Ads candidate QA failed: "+" | ".join(product_ads_qa.get("errors",[])))
        feature_health["product_ads_mart"]={"status":"READY","qa":product_ads_qa}
    except Exception as exc:
        # Optional feature: failure degrades Product Intelligence only.
        ads_product_daily=[]
        feature_health["product_ads_mart"]={"status":"DEGRADED","error":str(exc)}
        print(f"[feature-degraded] product_ads_mart: {exc}")

    total_confirmed = sum(n(r.get("confirmed_gmv_vnd")) for r in products)
    product_monthly = []
    for r in products:
        pid = str(r.get("product_id", "") or ""); sku = str(r.get("product_sku", "") or "")
        can = by_id.get(pid) or by_sku.get(sku) or {}
        raw_name = str(r.get("product_name", "") or "")
        name = can.get("name") or raw_name
        category = can.get("category") or fallback_category(sku,name)
        confirmed_gmv = n(r.get("confirmed_gmv_vnd"))
        product_monthly.append({
            "shop_id":require_shop_id(r, "source row"), "data_month":target, "product_id":pid,
            "product_sku":sku, "product_name":name, "category":category, "product_status":r.get("product_status"),
            "placed_gmv":n(r.get("placed_gmv_vnd")), "confirmed_gmv":confirmed_gmv,
            "confirmed_gmv_share":(confirmed_gmv/total_confirmed if total_confirmed else 0),
            "product_views":i(r.get("product_views")), "product_clicks":i(r.get("product_clicks")), "ctr":n(r.get("ctr")),
            "unique_impressions":i(r.get("unique_product_impressions")), "unique_clicks":i(r.get("unique_product_clicks")),
            "product_visits":i(r.get("product_visits")), "product_page_views":i(r.get("product_page_views")),
            "page_bounces":i(r.get("product_page_bounces")), "bounce_rate":n(r.get("product_page_bounce_rate")),
            "add_to_cart_visits":i(r.get("add_to_cart_visits")), "add_to_cart_units":i(r.get("add_to_cart_units")),
            "atc_rate":n(r.get("add_to_cart_conversion_rate")), "placed_orders":i(r.get("placed_orders")),
            "confirmed_orders":i(r.get("confirmed_orders")), "placed_units":i(r.get("placed_units")),
            "confirmed_units":i(r.get("confirmed_units")), "placed_buyers":i(r.get("placed_buyers")),
            "confirmed_buyers":i(r.get("confirmed_buyers")),
            "confirmed_cvr":n(r.get("confirmed_order_conversion_rate")), "confirmed_aov":n(r.get("confirmed_aov_vnd")),
            "repeat_order_rate":n(r.get("confirmed_repeat_order_rate")), "avg_days_to_repeat":n(r.get("confirmed_avg_days_to_repeat_order")),
        })

    return {
        "dm_shop_daily": shop, "dm_commercial_stage_daily": commercial, "dm_product_monthly": product_monthly,
        "dm_traffic_source_daily": td, "dm_traffic_source_monthly": tm, "dm_ads_daily": ads_daily,
        "dm_ads_product_daily": ads_product_daily, "dm_order_quality_daily": quality,
        "dm_shop_hourly": shop_hourly,
        "__feature_health__": feature_health,
    }


def validate_candidate(rows: Dict[str, List[Dict[str, Any]]], target: str, cutoff: dt.date) -> None:
    exp_days = len(expected_dates(target, cutoff))
    if len(rows["dm_shop_daily"]) != exp_days:
        raise RuntimeError(f"Candidate dm_shop_daily rows={len(rows['dm_shop_daily'])}, expected={exp_days}")
    if len(rows["dm_commercial_stage_daily"]) != exp_days * 3:
        raise RuntimeError("Candidate commercial stage daily row count mismatch")
    keys = [(r["data_date"], r["order_stage"]) for r in rows["dm_commercial_stage_daily"]]
    if len(keys) != len(set(keys)):
        raise RuntimeError("Candidate commercial stage duplicate keys")
    tkeys = [(r["data_date"],r["order_stage"],r["channel_group"],r["traffic_source"]) for r in rows["dm_traffic_source_daily"]]
    if len(tkeys) != len(set(tkeys)):
        raise RuntimeError("Candidate traffic daily duplicate keys")
    if any(n(r.get("ad_spend")) < 0 for r in rows["dm_ads_daily"]):
        raise RuntimeError("Candidate negative ad spend")
    if any("placed_buyers" not in r for r in rows["dm_product_monthly"]):
        raise RuntimeError("Candidate product contract missing placed_buyers")
    hkeys = [(r.get("data_date"), i(r.get("hour_local"))) for r in rows.get("dm_shop_hourly", [])]
    if len(hkeys) != len(set(hkeys)):
        raise RuntimeError("Candidate dm_shop_hourly duplicate date/hour keys")
    if any(h < 0 or h > 23 for _, h in hkeys):
        raise RuntimeError("Candidate dm_shop_hourly contains invalid hour")


def health_rows(target: str, cutoff: dt.date, counts: Dict[str,int], previous: List[Dict[str,Any]], feature_health: Dict[str,Dict[str,Any]] | None = None) -> List[Dict[str,Any]]:
    prev = {str(r.get("source_domain")): r for r in previous}
    feature_health = feature_health or {}
    ads_product_degraded = feature_health.get("product_ads_mart",{}).get("status")=="DEGRADED"
    def row(domain, window, files, count, warn, err, status, impact, pages, remediation):
        return {"as_of_date": cutoff.isoformat() if domain != "Customer Identity" else prev.get(domain,{}).get("as_of_date", "2026-07-31"),
                "source_domain":domain,"production_window":window,"source_files":files,"row_count":count,
                "dq_warning_count":warn,"dq_error_count":err,"status":status,"metric_impact":impact,
                "affected_pages":pages,"remediation":remediation}
    return [
        row("Business Insights",f"2025-11-01 → {cutoff.isoformat()}",10,counts.get("dm_commercial_stage_daily",0)+counts.get("dm_traffic_source_daily",0),1,0,"READY_WITH_CAVEAT","Current-month MTD commercial funnel / traffic authority","Tổng quan; Phễu; Traffic",f"MTD source cutoff {cutoff.isoformat()}; không yêu cầu đủ ngày cuối tháng."),
        row("Orders",f"2025-11-09 → {cutoff.isoformat()}",10,counts.get("dm_order_quality_daily",0)+counts.get("dm_shop_hourly",0),0,0,"READY","Fees, order quality, and Orders-timestamp hourly operational proxy; customer identity remains separately versioned","Tổng quan; Chất lượng; Command Center V2","Cancelled fee = 0 blocking QA. Hourly sales remains a proxy until BI reconciliation is exact."),
        row(
            "Ads",f"2025-11-01 → {cutoff.isoformat()}",10,
            counts.get("dm_ads_product_daily", i(prev.get("Ads",{}).get("row_count"))),
            1 if ads_product_degraded else 0,0,
            "READY_WITH_CAVEAT" if ads_product_degraded else "READY",
            "Shop Ads READY; Product Ads intelligence degraded" if ads_product_degraded else "Ads metrics materialized",
            "Tổng quan; Quảng cáo; Command Center Product Intelligence",
            feature_health.get("product_ads_mart",{}).get("error","Không cần."),
        ),
        row("Product Performance",f"2025-11 → {target}",10,counts.get("dm_product_monthly",0),0,0,"READY","Product grain tháng, current month is MTD","Sản phẩm; Top 3 Tổng quan","Không suy diễn daily."),
        row("Customer Identity",str(prev.get("Customer Identity",{}).get("production_window") or "2025-11-09 → 2026-07-31"),prev.get("Customer Identity",{}).get("source_files",9),prev.get("Customer Identity",{}).get("row_count",7851),prev.get("Customer Identity",{}).get("dq_warning_count",5),0,"READY_WITH_CAVEAT","Customer lifetime remains at last identity materialization","Khách hàng","Commercial August can publish; Customer page remains observed through its own as_of_date."),
        row("COGS","",0,0,0,0,"DISABLED_BY_DESIGN","Profitability chưa phát hành","Lợi nhuận","Không coi là lỗi cho tới khi COGS được bật."),
    ]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--full", action="store_true")
    args = ap.parse_args()

    status = status_rows(); require_ready(status)
    # Control Center PIPELINE_STATUS is read with UNFORMATTED_VALUE.
    # Google Sheets may therefore return a YYYY-MM cell formatted as a date
    # using its serial number (e.g. 46235 == 2026-08-01). Normalize both
    # formatted text and numeric serials into the canonical YYYY-MM contract.
    target_raw = status["Data Mart"].get("verified_through", "")
    target = month_text(target_raw)
    if not re.match(r"^\d{4}-\d{2}$", target):
        raise RuntimeError(
            f"Data Mart verified_through cannot be normalized to YYYY-MM: "
            f"raw={target_raw!r}, normalized={target!r}"
        )

    bi_ss = open_source(status["Business Insights"].get("output_spreadsheet_id"))
    ads_ss = open_source(status["Ads"].get("output_spreadsheet_id"))
    orders_ss = open_source(status["Orders"].get("output_spreadsheet_id"))
    bi_shop = records(get_worksheet(bi_ss, "fact_shop_performance_daily"))
    ads_rows = records(get_worksheet(ads_ss, "fact_ads_performance_daily"))
    order_rows = records(get_worksheet(orders_ss, "fact_orders"))
    bi_cut = validate_bi_coverage(bi_shop, target)
    ads_cut = source_cutoff(ads_rows, "data_date", target)
    order_cut = source_cutoff(order_rows, "order_created_at", target)
    if not ads_cut or not order_cut:
        raise RuntimeError(f"Missing target-month daily coverage: BI={bi_cut}, Ads={ads_cut}, Orders={order_cut}")
    cutoff = min(bi_cut, ads_cut, order_cut)
    if cutoff.strftime("%Y-%m") != target:
        raise RuntimeError(f"Common reliable cutoff {cutoff} is outside target {target}")

    prod = open_spreadsheet(PROD_MART_ID, label="production mart")
    candidate = build_rows(target, cutoff, order_cut, status, prod)
    feature_health = candidate.pop("__feature_health__", {})
    validate_candidate(candidate, target, cutoff)

    result = {
        "run_at": now_iso(), "target_period": target, "reliable_end": cutoff.isoformat(),
        "dry_run": args.dry_run, "full": args.full,
        "source_ids": {k: str(status[k].get("output_spreadsheet_id", "")) for k in REQUIRED_READY},
        "candidate_row_counts": {k: len(v) for k,v in candidate.items()},
        "changed": False, "qa": "PASS", "feature_health": feature_health,
    }

    current_shop = records(get_worksheet(prod, "dm_shop_daily"))
    current_target_dates = [sheet_date(r.get("data_date")) for r in current_shop if str(r.get("data_date","")).startswith(target)]
    current_target_dates = [d for d in current_target_dates if d]
    current_cut = max(current_target_dates) if current_target_dates else None
    result["current_mart_target_end"] = current_cut.isoformat() if current_cut else ""
    current_hourly = records(get_worksheet(prod, "dm_shop_hourly"))
    current_hourly_run_ids = [str(r.get("source_run_id", "") or "") for r in current_hourly if str(r.get("data_date", "")).startswith(target)]
    current_hourly_run_id = current_hourly_run_ids[-1] if current_hourly_run_ids else ""
    upstream_orders_run_id = str(status["Orders"].get("latest_run_id", "") or "")
    result["current_hourly_orders_run_id"] = current_hourly_run_id
    result["upstream_orders_run_id"] = upstream_orders_run_id
    result["orders_hourly_end"] = order_cut.isoformat()
    needs_write = args.full or current_cut != cutoff or current_hourly_run_id != upstream_orders_run_id
    result["changed"] = bool(needs_write)

    if not args.dry_run and needs_write:
        counts = {}
        counts["dm_shop_daily"] = replace_partition(get_worksheet(prod, "dm_shop_daily"), "data_date", target, candidate["dm_shop_daily"])
        counts["dm_commercial_stage_daily"] = replace_partition(get_worksheet(prod, "dm_commercial_stage_daily"), "data_date", target, candidate["dm_commercial_stage_daily"])
        counts["dm_product_monthly"] = replace_partition(get_worksheet(prod, "dm_product_monthly"), "data_month", target, candidate["dm_product_monthly"])
        counts["dm_traffic_source_daily"] = replace_partition(get_worksheet(prod, "dm_traffic_source_daily"), "data_date", target, candidate["dm_traffic_source_daily"])
        counts["dm_traffic_source_monthly"] = replace_partition(get_worksheet(prod, "dm_traffic_source_monthly"), "data_month", target, candidate["dm_traffic_source_monthly"])
        counts["dm_ads_daily"] = replace_partition(get_worksheet(prod, "dm_ads_daily"), "data_date", target, candidate["dm_ads_daily"])
        if feature_health.get("product_ads_mart",{}).get("status")=="READY":
            try:
                ads_product_ws = get_worksheet(prod, "dm_ads_product_daily")
                ensure_columns(ads_product_ws, PRODUCT_ADS_COLUMNS)
                counts["dm_ads_product_daily"] = replace_partition(
                    ads_product_ws, "data_date", target, candidate["dm_ads_product_daily"]
                )
            except Exception as exc:
                feature_health["product_ads_mart"]={"status":"DEGRADED","error":f"write failed: {exc}"}
                result["feature_health"]=feature_health
                print(f"[feature-degraded] product_ads_mart write: {exc}")
        counts["dm_order_quality_daily"] = replace_partition(get_worksheet(prod, "dm_order_quality_daily"), "data_date", target, candidate["dm_order_quality_daily"])
        counts["dm_shop_hourly"] = replace_partition(get_worksheet(prod, "dm_shop_hourly"), "data_date", target, candidate["dm_shop_hourly"])

        old_health = records(get_worksheet(prod, "dm_data_health"))
        hrows = health_rows(target, cutoff, counts, old_health, feature_health)
        counts["dm_data_health"] = replace_all_data(get_worksheet(prod, "dm_data_health"), hrows)

        # README is recomputed from materialized mart, avoiding double-counting on reruns.
        commercial_all = records(get_worksheet(prod, "dm_commercial_stage_daily"))
        placed_all = [r for r in commercial_all if str(r.get("order_stage")) == "placed" and (sheet_date(r.get("data_date")) or dt.date.min) <= cutoff]
        placed_gross = sum(n(r.get("gmv")) for r in placed_all)
        placed_cancelled = sum(n(r.get("cancelled_sales")) for r in placed_all)
        readme = get_worksheet(prod, "00_README")
        set_kv(readme, "Production window", f"Common cross-source window: 09/11/2025 → {cutoff.strftime('%d/%m/%Y')}; current month is source-window MTD.")
        set_kv(readme, "BI placed gross GMV", placed_gross)
        set_kv(readme, "BI placed cancelled sales", placed_cancelled)
        set_kv(readme, "BI placed net after cancellation", placed_gross - placed_cancelled)
        set_kv(readme, "Status", f"REFRESHED + RECONCILED; dashboard mart current through {cutoff.isoformat()} (MTD).")

        reg = get_worksheet(prod, "01_SOURCE_REGISTRY")
        reg_vals = sheet_values(reg, unformatted=False)
        headers = reg_vals[0]; dom_i=headers.index("domain"); end_i=headers.index("coverage_end")
        for ridx,row in enumerate(reg_vals[1:],start=2):
            domain = row[dom_i] if dom_i < len(row) else ""
            if domain in {"Orders","RAW Orders","Business Insights","Business Insights Traffic","Ads"}:
                sheet_write(lambda ridx=ridx: reg.update_cell(ridx,end_i+1,cutoff.isoformat()), label=f"update source registry row {ridx}")
            elif domain == "Product Performance":
                sheet_write(lambda ridx=ridx: reg.update_cell(ridx,end_i+1,target), label=f"update source registry row {ridx}")

        runlog = get_worksheet(prod, "05_RUN_LOG")
        run_id = "GHA_MART_" + dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        for table, count in counts.items():
            sheet_write(lambda table=table, count=count: runlog.append_row([run_id, dt.date.today().isoformat(), table, "CURRENT_MONTH_REFRESH", count, 1, "PASS", f"{target} materialized through {cutoff.isoformat()}"], value_input_option="RAW"), label=f"append mart runlog {table}")
        result["production_row_counts"] = counts

    RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
