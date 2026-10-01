"""Unipalm GitHub Actions v2 production publisher."""
from __future__ import annotations

import base64
import datetime as dt
import calendar
import gzip
import hashlib
import json
import math
import os
import random
import re
import time
import subprocess
import sys
from collections import defaultdict
from itertools import permutations
from pathlib import Path
from statistics import mean, median
from typing import Any, Dict, List

import gspread
from gspread.exceptions import APIError
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from google.oauth2.service_account import Credentials
from gspread.utils import ValueRenderOption

from modules.product_ranking import build_priority, rank_signals
from modules.ui_artifact import build_dual_ui_wrapper

STATE_SHEET_ID = os.environ["UNIPALM_STATE_SHEET_ID"]
MART_SHEET_ID = os.environ["UNIPALM_DATA_MART_SHEET_ID"]
SKU_MASTER_ID = os.getenv("UNIPALM_SKU_MASTER_SHEET_ID", "PUBLIC_RESOURCE_LIVE_003")
PROD_URL = os.environ["UNIPALM_PRODUCTION_URL"]
ACCESS_KEY = os.environ["UNIPALM_DASHBOARD_ACCESS_KEY"]
FORCE_FULL = os.getenv("FORCE_FULL_REBUILD", "false").lower() == "true"
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"
EVENT = os.getenv("GITHUB_EVENT_NAME", "")
ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "index.html"
STATE_JSON = ROOT / "automation" / "pipeline_state.json"
PROC_RESULT = ROOT / "automation" / "source_processor_result.json"
FROZEN_TEMPLATE = ROOT / "automation" / "frozen_v14_template.html"
V2_TEMPLATE = ROOT / "automation" / "command_center_v2_template.html"
SCOPES = ["https://www.googleapis.com/auth/drive.readonly", "https://www.googleapis.com/auth/spreadsheets"]
CREDS = Credentials.from_service_account_info(json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]), scopes=SCOPES)
GC = gspread.authorize(CREDS)


TRANSIENT_GOOGLE_STATUSES = {429, 500, 502, 503, 504}


def _api_status(exc: Exception):
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
    """Retry transient Google Sheets failures.

    For HTTP 429 we wait for the per-minute per-user Sheets quota window
    to reset.  Short retries are ineffective after source_processor has just
    materialized several production-mart tables.
    """
    delay = 5.0
    for attempt in range(1, retries + 1):
        try:
            return fn()
        except APIError as exc:
            status = _api_status(exc)
            if status not in TRANSIENT_GOOGLE_STATUSES or attempt >= retries:
                raise
            if status == 429:
                wait = 65.0 + random.uniform(0.5, 2.0)
            else:
                wait = min(delay, 45.0) + random.uniform(0.25, 1.25)
                delay = min(delay * 2, 45.0)
            print(
                f"[google-retry] {label}: HTTP {status}; "
                f"attempt {attempt}/{retries}; sleeping {wait:.1f}s"
            )
            time.sleep(wait)


def open_sheet(file_id: str, label: str):
    return google_retry(lambda: GC.open_by_key(file_id), f"open {label}")


def get_ws(spreadsheet, title: str):
    return google_retry(
        lambda: spreadsheet.worksheet(title),
        f"open worksheet {title}",
    )


def now_iso(): return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()

def n(v, default=0.0):
    if v in (None, ""): return default
    if isinstance(v, bool): return float(v)
    if isinstance(v,(int,float)):
        try: return float(v) if math.isfinite(float(v)) else default
        except Exception: return default
    s=str(v).strip().replace("₫","").replace("đ","").replace("VND","").replace(" ","")
    pct=s.endswith("%"); s=s.rstrip("%")
    if "," in s and "." in s: s=s.replace(".","").replace(",",".")
    elif "," in s: s=s.replace(",",".")
    try: x=float(s); return x/100 if pct else x
    except Exception: return default

def i(v): return int(round(n(v,0)))

def b(v): return v if isinstance(v,bool) else str(v).lower() in {"true","1","yes"}

def records(ws):
    vals=google_retry(
        lambda: ws.get_all_values(value_render_option=ValueRenderOption.unformatted),
        f"read worksheet {getattr(ws, 'title', '?')}",
    )
    if not vals: return []
    headers=[str(x).strip() for x in vals[0]]; out=[]
    for row in vals[1:]:
        if not any(x not in (None,"") for x in row): continue
        row=list(row)+[""]*max(0,len(headers)-len(row))
        out.append({h:row[j] if j<len(row) else "" for j,h in enumerate(headers) if h})
    return out


def assert_single_shop_payload_sources(*sources):
    """Legacy publisher guard.

    The current production UI contract is still one-shop-per-run. It may publish
    any shop identity, but it must never silently merge multiple shops.
    """
    ids=set(); missing=[]
    for label, rows in sources:
        for idx,row in enumerate(rows):
            sid=str(row.get("shop_id","") or "").strip()
            if not sid:
                missing.append(f"{label}[{idx}]")
            else:
                ids.add(sid)
    if missing:
        raise RuntimeError(f"legacy publisher source rows missing shop_id: {missing[:20]}")
    if len(ids)!=1:
        raise RuntimeError(f"legacy publisher requires exactly one shop per run; found {sorted(ids)}")
    return next(iter(ids))

def open_state():
    sh=open_sheet(STATE_SHEET_ID, "state workbook")
    return sh, get_ws(sh, "STATE"), get_ws(sh, "RUN_LOG"), get_ws(sh, "CONTROL")

def kv_map(ws):
    vals=google_retry(lambda: ws.get_all_values(), f"read KV worksheet {getattr(ws, 'title', '?')}")
    return {r[0]:r[1] for r in vals[1:] if len(r)>=2 and r[0]}

def append_run(ws, run_id, trigger, status, qa="", qa_summary="", reliable_end="", commit="", deployment="", note=""):
    row=[run_id,now_iso(),trigger,status,"","",status,qa,qa_summary,reliable_end,commit,deployment,PROD_URL,note]
    google_retry(
        lambda: ws.append_row(row,value_input_option="RAW"),
        f"append RUN_LOG {status}",
    )

def set_output(key,value):
    path=os.getenv("GITHUB_OUTPUT")
    if path:
        with open(path,"a",encoding="utf-8") as f: f.write(f"{key}={value}\n")

def percentile(xs,p):
    xs=sorted(float(x) for x in xs if x not in (None,""))
    if not xs: return 0
    k=(len(xs)-1)*p; a=math.floor(k); c=math.ceil(k)
    if a==c: return xs[a]
    return xs[a]*(c-k)+xs[c]*(k-a)

def load_sku_groups():
    out={}
    try:
        ss=open_sheet(SKU_MASTER_ID, "SKU master")
        for r in records(get_ws(ss, "dim_sku")):
            code=str(r.get("internal_sku_code","") or "")
            base=code.split("-")[0]
            name=str(r.get("internal_sku_name","") or "")
            import re
            m=re.search(r"\b(Cool\s+S\d+|Air\s+[SF]\d+)\b",name,flags=re.I)
            if base and m and base not in out:
                g=m.group(1)
                out[base]=g[:1].upper()+g[1:]
    except Exception as exc:
        print(f"SKU group map warning: {exc}")
    return out

def customer_item(r):
    region=str(r.get("region_latest","") or "").replace("Miền ","")
    return {"username":str(r.get("buyer_username","") or ""),"segment":str(r.get("segment","") or ""),
            "orders":i(r.get("lifetime_orders")),"activeMonths":i(r.get("active_months")),"ltv":n(r.get("lifetime_gmv")),
            "aov":n(r.get("avg_order_value")),"first":str(r.get("first_order_date","") or ""),"last":str(r.get("last_order_date","") or ""),
            "recency":i(r.get("days_since_last_order")),"repeatInterval":n(r.get("avg_days_between_orders")),
            "province":str(r.get("province_latest","") or ""),"region":region}


def _sum_rows(rows, field):
    return sum(n(r.get(field)) for r in rows)

def _pct_delta(cur, prev):
    if prev in (None, 0, 0.0):
        return None
    return cur / prev - 1.0

def _period_metrics(placed_rows, ads_rows, start: dt.date, end: dt.date):
    def in_range(value):
        try:
            d = dt.date.fromisoformat(str(value)[:10])
        except Exception:
            return False
        return start <= d <= end

    p = [r for r in placed_rows if in_range(r.get("date"))]
    a = [r for r in ads_rows if in_range(r.get("date"))]
    gmv = _sum_rows(p, "gmv")
    orders = sum(i(r.get("orders")) for r in p)
    visits = sum(i(r.get("visits")) for r in p)
    clicks = sum(i(r.get("clicks")) for r in p)
    spend = _sum_rows(a, "spend")
    ad_sales = _sum_rows(a, "sales")
    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "days": (end - start).days + 1,
        "gmv": gmv,
        "orders": orders,
        "visits": visits,
        "productClicks": clicks,
        "productClickRate": (clicks / visits if visits else 0),
        "cvr": (orders / clicks if clicks else 0),
        "aov": (gmv / orders if orders else 0),
        "adsSpend": spend,
        "adsSales": ad_sales,
        "roas": (ad_sales / spend if spend else 0),
    }

def _metric_comparison(current, previous):
    keys = ("gmv","orders","visits","productClicks","productClickRate","cvr","aov","adsSpend","adsSales","roas")
    return {k: _pct_delta(n(current.get(k)), n(previous.get(k))) for k in keys}


def _date_context(d: dt.date):
    return {
        "doubleDay": (d.month == d.day and 1 <= d.month <= 12),
        "doubleDayLabel": f"{d.month}.{d.day}" if d.month == d.day and 1 <= d.month <= 12 else "",
        "payday": d.day >= 25,
        "monthStart": d.day <= 3,
        "weekend": d.weekday() >= 5,
    }

def _window_context(start: dt.date, end: dt.date):
    double_days=[]; payday=0; month_start=0; weekend=0
    d=start
    while d<=end:
        ctx=_date_context(d)
        if ctx["doubleDay"]: double_days.append({"date":d.isoformat(),"label":ctx["doubleDayLabel"]})
        payday += 1 if ctx["payday"] else 0
        month_start += 1 if ctx["monthStart"] else 0
        weekend += 1 if ctx["weekend"] else 0
        d += dt.timedelta(days=1)
    return {
        "doubleDayDates":double_days,
        "doubleDayCount":len(double_days),
        "paydayDays":payday,
        "monthStartDays":month_start,
        "weekendDays":weekend,
    }

def _comparison_context(current, previous):
    c=_window_context(dt.date.fromisoformat(current["start"]),dt.date.fromisoformat(current["end"]))
    p=_window_context(dt.date.fromisoformat(previous["start"]),dt.date.fromisoformat(previous["end"]))
    reasons=[]
    if c["doubleDayCount"] != p["doubleDayCount"]:
        reasons.append("DOUBLE_DAY_IMBALANCE")
    if c["paydayDays"] != p["paydayDays"]:
        reasons.append("PAYDAY_IMBALANCE")
    if c["monthStartDays"] != p["monthStartDays"]:
        reasons.append("MONTH_START_IMBALANCE")
    signature={
        "doubleDayDelta": c["doubleDayCount"]-p["doubleDayCount"],
        "paydayDelta": c["paydayDays"]-p["paydayDays"],
        "monthStartDelta": c["monthStartDays"]-p["monthStartDays"],
    }
    return {
        "current":c,
        "previous":p,
        "signature":signature,
        "distorted":bool(reasons),
        "reasonCodes":reasons,
        "note":(
            "Hai kỳ có bối cảnh campaign/calendar khác nhau; raw delta cần được diễn giải thận trọng."
            if reasons else
            "Hai kỳ có bối cảnh calendar chính tương đối tương đồng."
        ),
    }

def _gmv_driver_decomposition(current, previous):
    """Exact top-level GMV bridge using Shopee-native Product Clicks.

    User-facing decomposition:
      GMV = Product Clicks × CVR × AOV

    Visits and the derived click-through-to-product rate are kept only as an
    upstream bridge explaining why Product Clicks changed:
      Product Clicks = Visits × (Product Clicks / Visits)
    """
    labels={
        "productClicks":"Lượt nhấp vào sản phẩm",
        "cvr":"Tỷ lệ chuyển đổi",
        "aov":"AOV",
    }
    keys=list(labels)
    cur={k:n(current.get(k)) for k in keys}
    prev={k:n(previous.get(k)) for k in keys}
    if any(cur[k] <= 0 or prev[k] <= 0 for k in keys):
        return {
            "status":"INSUFFICIENT_POSITIVE_FACTORS",
            "drivers":[],
            "residual":n(current.get("gmv"))-n(previous.get("gmv")),
            "clickBridge":{},
        }

    def product(values):
        out=1.0
        for k in keys: out*=values[k]
        return out

    contributions={k:0.0 for k in keys}
    perms=list(permutations(keys))
    for perm in perms:
        state=dict(prev)
        before=product(state)
        for k in perm:
            state[k]=cur[k]
            after=product(state)
            contributions[k]+=after-before
            before=after
    for k in keys:
        contributions[k]/=len(perms)

    gmv_delta=n(current.get("gmv"))-n(previous.get("gmv"))
    explained=sum(contributions.values())
    residual=gmv_delta-explained
    abs_total=sum(abs(v) for v in contributions.values()) or 1.0
    drivers=[]
    for k in keys:
        effect=contributions[k]
        drivers.append({
            "key":k,
            "label":labels[k],
            "current":cur[k],
            "previous":prev[k],
            "deltaPct":_pct_delta(cur[k],prev[k]),
            "effectValue":effect,
            "shareOfAbsoluteEffects":abs(effect)/abs_total,
            "shareOfNetChange":(effect/gmv_delta if gmv_delta else 0),
            "direction":"positive" if effect>0 else ("negative" if effect<0 else "neutral"),
        })
    drivers.sort(key=lambda x:abs(x["effectValue"]),reverse=True)
    for rank,row in enumerate(drivers,1): row["rank"]=rank

    cur_visits=n(current.get("visits")); prev_visits=n(previous.get("visits"))
    cur_clicks=n(current.get("productClicks")); prev_clicks=n(previous.get("productClicks"))
    cur_rate=(cur_clicks/cur_visits) if cur_visits else 0.0
    prev_rate=(prev_clicks/prev_visits) if prev_visits else 0.0
    click_bridge={
        "identity":"Product Clicks = Visits × Derived Click Rate",
        "visits":{
            "current":cur_visits,
            "previous":prev_visits,
            "deltaPct":_pct_delta(cur_visits,prev_visits),
        },
        "derivedClickRate":{
            "current":cur_rate,
            "previous":prev_rate,
            "deltaPct":_pct_delta(cur_rate,prev_rate),
            "userFacing":False,
        },
        "productClicks":{
            "current":cur_clicks,
            "previous":prev_clicks,
            "deltaPct":_pct_delta(cur_clicks,prev_clicks),
        },
    }

    return {
        "status":"READY",
        "method":"SHAPLEY_3_FACTOR",
        "identity":"GMV = Product Clicks × CVR × AOV",
        "gmvDelta":gmv_delta,
        "explained":explained,
        "residual":residual,
        "drivers":drivers,
        "mainDriver":drivers[0]["key"] if drivers else "",
        "clickBridge":click_bridge,
    }

def _month_shift(d: dt.date, months_back: int):
    y=d.year; m=d.month-months_back
    while m<=0:
        y-=1; m+=12
    day=min(d.day,calendar.monthrange(y,m)[1])
    return dt.date(y,m,day)

def _historical_pairs(horizon, placed, ads_daily, latest, limit=12):
    pairs=[]
    min_date=min((dt.date.fromisoformat(str(r.get("date"))[:10]) for r in placed if r.get("date")), default=latest)
    if horizon=="yesterday":
        for k in range(1,limit+1):
            cur_end=latest-dt.timedelta(days=7*k)
            prev_end=cur_end-dt.timedelta(days=1)
            if prev_end < min_date: break
            cur=_period_metrics(placed,ads_daily,cur_end,cur_end)
            prev=_period_metrics(placed,ads_daily,prev_end,prev_end)
            pairs.append({"current":cur,"previous":prev,"context":_comparison_context(cur,prev),"anchor":cur_end.isoformat()})
    elif horizon=="last7":
        for k in range(1,limit+1):
            cur_end=latest-dt.timedelta(days=7*k)
            cur_start=cur_end-dt.timedelta(days=6)
            prev_end=cur_start-dt.timedelta(days=1)
            prev_start=prev_end-dt.timedelta(days=6)
            if prev_start < min_date: break
            cur=_period_metrics(placed,ads_daily,cur_start,cur_end)
            prev=_period_metrics(placed,ads_daily,prev_start,prev_end)
            pairs.append({"current":cur,"previous":prev,"context":_comparison_context(cur,prev),"anchor":cur_end.isoformat()})
    elif horizon=="mtd":
        for k in range(1,limit+1):
            cur_anchor=_month_shift(latest,k)
            if calendar.monthrange(cur_anchor.year,cur_anchor.month)[1] < latest.day:
                continue
            cur_start=cur_anchor.replace(day=1); cur_end=cur_anchor.replace(day=latest.day)
            prev_anchor=_month_shift(cur_anchor,1)
            if calendar.monthrange(prev_anchor.year,prev_anchor.month)[1] < latest.day:
                continue
            prev_start=prev_anchor.replace(day=1); prev_end=prev_anchor.replace(day=latest.day)
            if prev_start < min_date: break
            cur=_period_metrics(placed,ads_daily,cur_start,cur_end)
            prev=_period_metrics(placed,ads_daily,prev_start,prev_end)
            pairs.append({"current":cur,"previous":prev,"context":_comparison_context(cur,prev),"anchor":cur_end.isoformat()})
    return pairs

def _same_context_signature(a,b):
    sa=a.get("signature",{}); sb=b.get("signature",{})
    return (
        i(sa.get("doubleDayDelta"))==i(sb.get("doubleDayDelta"))
        and i(sa.get("paydayDelta"))==i(sb.get("paydayDelta"))
        and i(sa.get("monthStartDelta"))==i(sb.get("monthStartDelta"))
    )

def _baseline_stats(current_delta, values, context_matched, current_context):
    vals=[float(v) for v in values if v is not None and math.isfinite(float(v))]
    if len(vals)<4 or current_delta is None:
        return {
            "status":"INSUFFICIENT_HISTORY","sampleSize":len(vals),"confidence":0.0,
            "contextMatched":context_matched,"alertEligible":False,
        }
    med=median(vals)
    p10=percentile(vals,.10); p25=percentile(vals,.25); p75=percentile(vals,.75); p90=percentile(vals,.90)
    deviations=[abs(x-med) for x in vals]
    mad=median(deviations) if deviations else 0.0
    robust_z=(0.6745*(current_delta-med)/mad) if mad>1e-12 else 0.0
    status="NORMAL"
    if current_delta < p10: status="LOW"
    elif current_delta > p90: status="HIGH"
    confidence=min(.95,.55+.04*len(vals))
    if not context_matched: confidence*=.78
    suppressed=bool(current_context.get("distorted")) and not context_matched
    return {
        "status":status,
        "sampleSize":len(vals),
        "medianDelta":med,
        "p10Delta":p10,"p25Delta":p25,"p75Delta":p75,"p90Delta":p90,
        "mad":mad,"robustZ":robust_z,
        "confidence":confidence,
        "contextMatched":context_matched,
        "suppressedByContext":suppressed,
        "alertEligible":(status!="NORMAL" and confidence>=.72 and not suppressed),
    }

def _build_historical_baseline(horizon, period, placed, ads_daily, latest):
    metrics=("gmv","orders","visits","productClicks","productClickRate","cvr","aov","adsSpend","roas")
    current_context=period["context"]
    pairs=_historical_pairs(horizon,placed,ads_daily,latest,12)
    matched=[x for x in pairs if _same_context_signature(x["context"],current_context)]
    use_matched=len(matched)>=4
    selected=matched if use_matched else pairs
    baselines={}
    for metric in metrics:
        vals=[]
        for x in selected:
            delta=_pct_delta(n(x["current"].get(metric)),n(x["previous"].get(metric)))
            if delta is not None and math.isfinite(delta): vals.append(delta)
        baselines[metric]=_baseline_stats(
            period["delta"].get(metric),vals,use_matched,current_context
        )
    return {
        "method":"ROBUST_HISTORICAL_CHANGE_BASELINE",
        "horizon":horizon,
        "candidateComparisons":len(pairs),
        "contextMatchedComparisons":len(matched),
        "usingContextMatchedHistory":use_matched,
        "metrics":baselines,
    }


SMART_ISSUE_METRICS = {
    "productClicks": {"label":"Lượt nhấp vào sản phẩm","unit":"count","direction":"low"},
    "cvr": {"label":"Tỷ lệ chuyển đổi","unit":"rate","direction":"low"},
    "aov": {"label":"AOV","unit":"currency","direction":"low"},
}

def _daily_metric_rows(placed, ads_daily):
    ads_by_date={str(r.get("date","")):r for r in ads_daily}
    rows=[]
    for r in placed:
        d=str(r.get("date",""))
        if not d:
            continue
        visits=n(r.get("visits")); clicks=n(r.get("clicks")); orders=n(r.get("orders")); gmv=n(r.get("gmv"))
        ad=ads_by_date.get(d,{})
        rows.append({
            "date":d,
            "gmv":gmv,
            "orders":orders,
            "visits":visits,
            "productClicks":clicks,
            "productClickRate":(clicks/visits if visits else 0),
            "cvr":(orders/clicks if clicks else 0),
            "aov":(gmv/orders if orders else 0),
            "adsSpend":n(ad.get("spend")),
            "roas":n(ad.get("roas")),
        })
    rows.sort(key=lambda x:x["date"])
    return rows

def _raw_daily_expected(metric, target_date: dt.date, daily_rows, lookback_weeks=12):
    current=next((r for r in daily_rows if r["date"]==target_date.isoformat()),None)
    if not current:
        return {"status":"NO_DATA","date":target_date.isoformat()}

    target_ctx=_date_context(target_date)
    candidates=[]
    for r in daily_rows:
        try:
            d=dt.date.fromisoformat(r["date"])
        except Exception:
            continue
        if d>=target_date or d.weekday()!=target_date.weekday():
            continue
        if (target_date-d).days > lookback_weeks*7:
            continue
        candidates.append((d,r))

    # Prefer history with the same simple day context when enough samples exist.
    matched=[]
    for d,r in candidates:
        ctx=_date_context(d)
        if (
            bool(ctx["doubleDay"])==bool(target_ctx["doubleDay"])
            and bool(ctx["payday"])==bool(target_ctx["payday"])
            and bool(ctx["monthStart"])==bool(target_ctx["monthStart"])
        ):
            matched.append((d,r))
    use_matched=len(matched)>=4
    selected=matched if use_matched else candidates

    vals=[n(r.get(metric)) for _,r in selected if r.get(metric) not in (None,"")]
    vals=[v for v in vals if math.isfinite(v)]
    if len(vals)<4:
        return {
            "status":"INSUFFICIENT_HISTORY","date":target_date.isoformat(),
            "sampleSize":len(vals),"contextMatched":use_matched,
        }

    med=median(vals); p10=percentile(vals,.10); p90=percentile(vals,.90)
    mad=median([abs(x-med) for x in vals]) if vals else 0.0
    actual=n(current.get(metric))
    robust_z=(0.6745*(actual-med)/mad) if mad>1e-12 else 0.0
    status="NORMAL"
    if actual < p10: status="LOW"
    elif actual > p90: status="HIGH"
    confidence=min(.95,.55+.04*len(vals))
    if not use_matched:
        confidence*=.88
    special=bool(target_ctx["doubleDay"] or target_ctx["payday"] or target_ctx["monthStart"])
    if special and not use_matched:
        confidence*=.80

    return {
        "status":status,"date":target_date.isoformat(),"actual":actual,
        "median":med,"p10":p10,"p90":p90,"mad":mad,"robustZ":robust_z,
        "sampleSize":len(vals),"confidence":confidence,"contextMatched":use_matched,
        "specialContext":special,
    }

def _persistence_evidence(metric, horizon, period, placed, ads_daily, latest):
    daily=_daily_metric_rows(placed,ads_daily)
    start=dt.date.fromisoformat(period["current"]["start"])
    end=dt.date.fromisoformat(period["current"]["end"])
    checks=[]
    d=start
    while d<=end:
        ev=_raw_daily_expected(metric,d,daily)
        if ev.get("status") not in {"NO_DATA","INSUFFICIENT_HISTORY"}:
            checks.append(ev)
        d+=dt.timedelta(days=1)

    low_days=[x for x in checks if x.get("status")=="LOW" and n(x.get("confidence"))>=.60]
    low_dates={x["date"] for x in low_days}
    tail=0; cursor=end
    while cursor>=start and cursor.isoformat() in low_dates:
        tail+=1; cursor-=dt.timedelta(days=1)

    if horizon=="yesterday":
        # Look backwards beyond the one-day UI period so a 3-day issue can persist.
        tail=0; scan=latest
        checks=[]
        for _ in range(7):
            ev=_raw_daily_expected(metric,scan,daily)
            checks.append(ev)
            if ev.get("status")=="LOW" and n(ev.get("confidence"))>=.60:
                tail+=1; scan-=dt.timedelta(days=1)
            else:
                break
        low_days=[x for x in checks if x.get("status")=="LOW" and n(x.get("confidence"))>=.60]

    low_count=len(low_days)
    if horizon=="yesterday":
        strength=min(1.0,tail/3.0)
    elif horizon=="last7":
        strength=min(1.0,max(tail/3.0,low_count/4.0))
    else:
        denom=max(3.0,period["current"].get("days",1)*.35)
        strength=min(1.0,max(tail/3.0,low_count/denom))

    dates=sorted(x["date"] for x in low_days)
    return {
        "metric":metric,
        "horizon":horizon,
        "lowDays":low_count,
        "consecutiveTailDays":tail,
        "strength":strength,
        "firstObserved":dates[0] if dates else "",
        "lastObserved":dates[-1] if dates else "",
        "dailyEvidence":low_days[-7:],
    }

def _impact_component(effect_value, previous_gmv):
    # 15% of prior-period GMV is treated as full-scale material impact.
    denom=max(abs(n(previous_gmv))*.15,1.0)
    return min(1.0,abs(n(effect_value))/denom)

def _deviation_component(baseline):
    if baseline.get("status")!="LOW":
        return 0.0
    rz=abs(n(baseline.get("robustZ")))
    # Crossing P10 is meaningful even when MAD is wide.
    return min(1.0,max(.35,rz/3.0))

def _context_component(period, baseline):
    ctx=period.get("context",{})
    if baseline.get("suppressedByContext"):
        return 0.0
    if ctx.get("distorted"):
        return .90 if baseline.get("contextMatched") else .55
    return 1.0

def _smart_issue_score(impact, deviation, persistence, confidence, context):
    components=[impact,deviation,persistence,confidence,context]
    if any(x<=0 for x in components):
        return 0.0
    # Weighted geometric mean: every dimension gates the result while preserving
    # business emphasis on impact/deviation.
    return 100.0 * (
        impact**.30 *
        deviation**.25 *
        persistence**.20 *
        confidence**.15 *
        context**.10
    )

def _format_issue_evidence(metric, baseline, persistence):
    if metric in {"cvr","productClicks"}:
        return f"Biến động thấp hơn expected band; {persistence.get('lowDays',0)} ngày gần đây dưới daily baseline."
    if metric=="aov":
        return f"AOV thấp hơn historical pattern; {persistence.get('lowDays',0)} ngày dưới expected band."
    return "Tín hiệu lệch khỏi historical baseline."


def _shop_issue_diagnostic(metric, period, placed, ads_daily, latest):
    daily=_daily_metric_rows(placed,ads_daily)
    series=[]
    start=latest-dt.timedelta(days=29)
    cursor=start
    while cursor<=latest:
        ev=_raw_daily_expected(metric,cursor,daily)
        actual_row=next((r for r in daily if r["date"]==cursor.isoformat()),None)
        if actual_row and actual_row.get(metric) not in (None,""):
            series.append({
                "date":cursor.isoformat(),
                "actual":n(actual_row.get(metric)),
                "expected":n(ev.get("median")) if ev.get("median") not in (None,"") else None,
                "p10":n(ev.get("p10")) if ev.get("p10") not in (None,"") else None,
                "p90":n(ev.get("p90")) if ev.get("p90") not in (None,"") else None,
                "status":ev.get("status","NO_BASELINE"),
                "confidence":n(ev.get("confidence")),
            })
        cursor+=dt.timedelta(days=1)

    next_checks={
        "productClicks":[
            "Kiểm tra biến động Lượt truy cập theo nguồn và tỷ trọng nguồn traffic.",
            "Kiểm tra PDP / listing / ảnh / title / voucher nếu traffic ổn nhưng clicks giảm.",
            "Đối chiếu Ads product traffic để xem Paid traffic có thay đổi cấu trúc hay không.",
        ],
        "cvr":[
            "Kiểm tra giá bán thực tế, voucher và mức giảm giá so với giai đoạn baseline.",
            "Kiểm tra PDP image, review/rating, variation mix và trạng thái tồn hàng.",
            "Đối chiếu traffic source để loại trừ thay đổi chất lượng traffic.",
        ],
        "aov":[
            "Kiểm tra product mix / variation mix và tỷ trọng combo.",
            "Kiểm tra voucher / discount làm thay đổi giá trị đơn.",
            "Đối chiếu số units mỗi đơn và cơ cấu sản phẩm bán ra.",
        ],
    }
    return {
        "kind":"shop_issue",
        "chartType":"daily_expected_band",
        "chartTitle":"Diễn biến 30 ngày",
        "series":series,
        "nextChecks":next_checks.get(metric,["Đối chiếu các driver liên quan trước khi thay đổi vận hành."]),
        "contextNote":period.get("context",{}).get("note",""),
    }

def _product_signal_diagnostic(signal, by_month):
    months=signal.get("historyMonths",[])
    series=[]
    for m in months:
        r=by_month.get(m)
        if not r:
            continue
        clicks=i(r.get("clicks")); orders=i(r.get("placedOrders")); gmv=n(r.get("placedGmv"))
        series.append({
            "month":m,
            "gmv":gmv,
            "orders":orders,
            "clicks":clicks,
            "cvr":(orders/clicks if clicks else 0.0),
            "aov":(gmv/orders if orders else 0.0),
        })
    checks=[
        "Kiểm tra thay đổi listing/PDP, giá/voucher và variation mix giữa hai cửa sổ 3 tháng.",
        "Kiểm tra Product Clicks và CVR theo tháng để xác định tầng funnel suy yếu hay cải thiện.",
        "Đối chiếu Ads product performance để phân biệt thay đổi paid demand và organic demand.",
    ]
    return {
        "kind":"product_signal",
        "chartType":"monthly_product_history",
        "chartTitle":"Diễn biến 6 tháng",
        "series":series,
        "nextChecks":checks,
    }


def _build_smart_issues(horizon, period, placed, ads_daily, latest):
    driver_rows={r.get("key"):r for r in period.get("drivers",{}).get("drivers",[])}
    metric_baselines=period.get("baseline",{}).get("metrics",{})
    issues=[]
    for metric,cfg in SMART_ISSUE_METRICS.items():
        driver=driver_rows.get(metric)
        baseline=metric_baselines.get(metric,{})
        if not driver or n(driver.get("effectValue"))>=0:
            continue
        if baseline.get("status")!="LOW" or not baseline.get("alertEligible"):
            continue

        persistence=_persistence_evidence(metric,horizon,period,placed,ads_daily,latest)
        impact=_impact_component(driver.get("effectValue"),period["previous"].get("gmv"))
        deviation=_deviation_component(baseline)
        persistence_score=n(persistence.get("strength"))
        confidence=n(baseline.get("confidence"))
        context=_context_component(period,baseline)

        # Actionability gate:
        # - If total GMV is itself historically LOW, a material driver can surface quickly.
        # - If GMV is still within historical range, require stronger persistence.
        # - A one-day signal is allowed only when deviation is extreme.
        gmv_baseline=metric_baselines.get("gmv",{})
        gmv_is_low=gmv_baseline.get("status")=="LOW" and bool(gmv_baseline.get("alertEligible"))
        extreme_deviation=abs(n(baseline.get("robustZ")))>=2.5
        min_persistence=.33 if gmv_is_low else .50
        if persistence_score < min_persistence and not extreme_deviation:
            continue

        score=_smart_issue_score(impact,deviation,persistence_score,confidence,context)
        if score < 50.0:
            continue

        severity="High" if score>=70 else "Med"
        if not gmv_is_low and severity=="High":
            severity="Med"
        start_date=persistence.get("firstObserved") or period["current"]["start"]
        issue_id=f"SHOP-{metric.upper()}-LOW-{start_date.replace('-','')}"
        issues.append({
            "anomalyId":issue_id,
            "scope":"shop",
            "metric":metric,
            "label":cfg["label"],
            "direction":"LOW",
            "severity":severity,
            "score":score,
            "impactScore":impact,
            "deviationScore":deviation,
            "persistenceScore":persistence_score,
            "confidenceScore":confidence,
            "contextScore":context,
            "impactValue":abs(n(driver.get("effectValue"))),
            "driverRank":i(driver.get("rank")),
            "metricDelta":period.get("delta",{}).get(metric),
            "gmvDelta":period.get("drivers",{}).get("gmvDelta"),
            "gmvBaselineStatus":gmv_baseline.get("status"),
            "gmvBaselineAlertEligible":bool(gmv_baseline.get("alertEligible")),
            "baselineStatus":baseline.get("status"),
            "baselineRobustZ":baseline.get("robustZ"),
            "baselineP10":baseline.get("p10Delta"),
            "baselineMedian":baseline.get("medianDelta"),
            "historicalSampleSize":baseline.get("sampleSize"),
            "persistence":persistence,
            "context":period.get("context",{}),
            "diagnostic":_shop_issue_diagnostic(metric,period,placed,ads_daily,latest),
            "summary":f"{cfg['label']} thấp hơn expected pattern và đang kéo GMV xuống.",
            "evidence":_format_issue_evidence(metric,baseline,persistence),
            "recommendedAction":"Mở chẩn đoán",
            "status":"OPEN",
        })

    issues.sort(key=lambda x:(-x["score"],-x["impactValue"]))
    return {
        "status":"ISSUES_FOUND" if issues else "NO_ACTIONABLE_ISSUES",
        "count":len(issues),
        "issues":issues[:5],
        "scoringMethod":"WEIGHTED_GEOMETRIC_IMPACT_DEVIATION_PERSISTENCE_CONFIDENCE_CONTEXT",
        "minimumScore":50,
    }


def _period_diagnosis(period):
    drivers=period.get("drivers",{}).get("drivers",[])
    gmv_base=period.get("baseline",{}).get("metrics",{}).get("gmv",{})
    main=drivers[0] if drivers else {}
    return {
        "gmvDirection":"up" if n(period["delta"].get("gmv"))>0 else ("down" if n(period["delta"].get("gmv"))<0 else "flat"),
        "mainDriverKey":main.get("key",""),
        "mainDriverLabel":main.get("label",""),
        "mainDriverEffect":main.get("effectValue",0),
        "gmvBaselineStatus":gmv_base.get("status","INSUFFICIENT_HISTORY"),
        "gmvAlertEligible":bool(gmv_base.get("alertEligible")),
        "confidence":n(gmv_base.get("confidence")),
        "contextDistorted":bool(period.get("context",{}).get("distorted")),
        "contextReasons":period.get("context",{}).get("reasonCodes",[]),
    }


def build_command_center_history(shop_daily, ads_daily, loaded_end):
    placed = [r for r in shop_daily if str(r.get("stage")) == "placed"]
    if not placed:
        return {"status":"NO_PLACED_DATA"}

    latest = dt.date.fromisoformat(str(loaded_end)[:10])
    available = {dt.date.fromisoformat(str(r.get("date"))[:10]) for r in placed if r.get("date")}
    if latest not in available:
        latest = max(available)

    prev_day = latest - dt.timedelta(days=1)
    last7_start = latest - dt.timedelta(days=6)
    prev7_end = last7_start - dt.timedelta(days=1)
    prev7_start = prev7_end - dt.timedelta(days=6)

    month_start = latest.replace(day=1)
    if latest.month == 1:
        pm_y, pm_m = latest.year - 1, 12
    else:
        pm_y, pm_m = latest.year, latest.month - 1
    prev_month_last_day = calendar.monthrange(pm_y, pm_m)[1]
    prev_mtd_end = dt.date(pm_y, pm_m, min(latest.day, prev_month_last_day))
    prev_mtd_start = dt.date(pm_y, pm_m, 1)

    periods = {
        "yesterday": {
            "current": _period_metrics(placed, ads_daily, latest, latest),
            "previous": _period_metrics(placed, ads_daily, prev_day, prev_day),
        },
        "last7": {
            "current": _period_metrics(placed, ads_daily, last7_start, latest),
            "previous": _period_metrics(placed, ads_daily, prev7_start, prev7_end),
        },
        "mtd": {
            "current": _period_metrics(placed, ads_daily, month_start, latest),
            "previous": _period_metrics(placed, ads_daily, prev_mtd_start, prev_mtd_end),
        },
    }
    for key,p in periods.items():
        p["delta"] = _metric_comparison(p["current"], p["previous"])
        p["context"] = _comparison_context(p["current"],p["previous"])
        p["drivers"] = _gmv_driver_decomposition(p["current"],p["previous"])
        p["baseline"] = _build_historical_baseline(key,p,placed,ads_daily,latest)
        p["diagnosis"] = _period_diagnosis(p)
        p["smartIssues"] = _build_smart_issues(key,p,placed,ads_daily,latest)

    return {
        "status":"READY",
        "commercialStage":"placed",
        "latestCompleteDate":latest.isoformat(),
        "periods":periods,
        "smartIssues":periods["yesterday"].get("smartIssues",{}),
        "labels":{
            "yesterday":f"Hôm qua · {latest.strftime('%d/%m')}",
            "last7":f"7 ngày gần nhất · {last7_start.strftime('%d/%m')}–{latest.strftime('%d/%m')}",
            "mtd":f"Tháng này · 01–{latest.strftime('%d/%m')}",
        },
    }



def _month_key_shift(month_key: str, delta: int) -> str:
    y,m=[int(x) for x in month_key.split("-")]
    m += delta
    while m<=0:
        y-=1; m+=12
    while m>12:
        y+=1; m-=12
    return f"{y:04d}-{m:02d}"

def _month_days(month_key: str) -> int:
    y,m=[int(x) for x in month_key.split("-")]
    return calendar.monthrange(y,m)[1]

def _aggregate_product_rows(rows):
    gmv=sum(n(r.get("placedGmv")) for r in rows)
    orders=sum(i(r.get("placedOrders")) for r in rows)
    clicks=sum(i(r.get("clicks")) for r in rows)
    views=sum(i(r.get("views")) for r in rows)
    visits=sum(i(r.get("visits")) for r in rows)
    page_views=sum(i(r.get("pageViews")) for r in rows)
    bounces=sum(i(r.get("bounces")) for r in rows)
    atc_visits=sum(i(r.get("atcVisits")) for r in rows)
    atc_units=sum(i(r.get("atcUnits")) for r in rows)
    units=sum(i(r.get("placedUnits")) for r in rows)
    return {
        "gmv":gmv,
        "orders":orders,
        "clicks":clicks,
        "views":views,
        "visits":visits,
        "pageViews":page_views,
        "bounces":bounces,
        "atcVisits":atc_visits,
        "atcUnits":atc_units,
        "units":units,
        "ctr":(clicks/views if views else 0.0),
        "bounceRate":(bounces/visits if visits else 0.0),
        "visitToAtcRate":(atc_visits/visits if visits else 0.0),
        "cvr":(orders/clicks if clicks else 0.0),
        "aov":(gmv/orders if orders else 0.0),
        "unitsPerOrder":(units/orders if orders else 0.0),
    }

def _tail_direction(values, direction):
    if len(values)<2:
        return 0
    tail=0
    for j in range(len(values)-1,0,-1):
        cur=n(values[j]); prev=n(values[j-1])
        ok=(cur>prev) if direction=="up" else (cur<prev)
        if ok:
            tail+=1
        else:
            break
    return tail

def _product_ads_support(product_id, ads_product_daily, recent_months, previous_months, loaded_end):
    """Aggregate ALL product campaigns by product_id before comparing periods.

    Primary Ads comparison is horizon-aligned with the structural product signal:
    recent 3 complete months vs prior 3 complete months.
    A trailing 28d comparison is kept only as secondary recency context.
    """
    def aggregate_months(months):
        rows=[
            r for r in ads_product_daily
            if str(r.get("productId"))==str(product_id)
            and str(r.get("date",""))[:7] in set(months)
        ]
        return _aggregate_ads_product_rows(rows)

    structural_current=aggregate_months(recent_months)
    structural_previous=aggregate_months(previous_months)

    try:
        end=dt.date.fromisoformat(str(loaded_end)[:10])
    except Exception:
        end=None

    recent28={"status":"NO_RECENCY_CONTEXT"}
    if end:
        current_start=end-dt.timedelta(days=27)
        previous_end=current_start-dt.timedelta(days=1)
        previous_start=previous_end-dt.timedelta(days=27)
        cur_rows=[r for r in ads_product_daily if str(r.get("productId"))==str(product_id) and current_start.isoformat()<=str(r.get("date"))<=end.isoformat()]
        prev_rows=[r for r in ads_product_daily if str(r.get("productId"))==str(product_id) and previous_start.isoformat()<=str(r.get("date"))<=previous_end.isoformat()]
        a=_aggregate_ads_product_rows(cur_rows); b=_aggregate_ads_product_rows(prev_rows)
        recent28={
            "status":"READY" if _ads_has_activity(a,b) else "NO_ADS_ACTIVITY",
            "currentWindow":{"start":current_start.isoformat(),"end":end.isoformat()},
            "previousWindow":{"start":previous_start.isoformat(),"end":previous_end.isoformat()},
            "current":a,"previous":b,
            **_ads_delta_fields(a,b),
        }

    return {
        "status":"READY" if _ads_has_activity(structural_current,structural_previous) else "NO_ADS_ACTIVITY",
        "grain":"product_all_campaigns_aggregated",
        "aggregationKey":"product_id",
        "campaignPolicy":"SUM_ALL_CAMPAIGNS_FOR_PRODUCT",
        "structuralWindow":{
            "currentMonths":list(recent_months),
            "previousMonths":list(previous_months),
        },
        "current":structural_current,
        "previous":structural_previous,
        **_ads_delta_fields(structural_current,structural_previous),
        "recent28d":recent28,
    }

def _aggregate_ads_product_rows(rows):
    impressions=sum(i(r.get("impressions")) for r in rows)
    clicks=sum(i(r.get("clicks")) for r in rows)
    conv=sum(i(r.get("conversions")) for r in rows)
    sales=sum(n(r.get("sales")) for r in rows)
    spend=sum(n(r.get("spend")) for r in rows)
    return {
        "impressions":impressions,"clicks":clicks,"conversions":conv,"sales":sales,"spend":spend,
        "ctr":(clicks/impressions if impressions else 0.0),
        "cvr":(conv/clicks if clicks else 0.0),
        "roas":(sales/spend if spend else 0.0),
        "cpc":(spend/clicks if clicks else 0.0),
        "cpa":(spend/conv if conv else 0.0),
        "acos":(spend/sales if sales else 0.0),
    }

def _ads_has_activity(a,b):
    return any([
        n(a.get("impressions")),n(a.get("clicks")),n(a.get("sales")),n(a.get("spend")),
        n(b.get("impressions")),n(b.get("clicks")),n(b.get("sales")),n(b.get("spend")),
    ])

def _ads_delta_fields(a,b):
    def delta(k):
        return _pct_delta(n(a.get(k)),n(b.get(k))) if n(b.get(k)) else None
    return {
        "impressionsDelta":delta("impressions"),"clicksDelta":delta("clicks"),
        "conversionsDelta":delta("conversions"),"salesDelta":delta("sales"),
        "spendDelta":delta("spend"),"ctrDelta":delta("ctr"),"cvrDelta":delta("cvr"),
        "roasDelta":delta("roas"),"cpcDelta":delta("cpc"),"cpaDelta":delta("cpa"),"acosDelta":delta("acos"),
        "spendAvailable":bool(n(a.get("spend")) or n(b.get("spend"))),
        "roasAvailable":bool(n(a.get("spend")) or n(b.get("spend"))),
    }


def _product_root_cause_layers(signal_type, recent, prev, deltas, ads_ctx):
    observed=[]
    hypotheses=[]

    # 1) Discovery / exposure layer
    if n(deltas.get("views")) <= -.20 and n(deltas.get("clicks")) <= -.20:
        if n(deltas.get("ctr")) >= -.05:
            observed.append({
                "title":"Độ phủ sản phẩm giảm rõ, nhưng khả năng kéo click không xấu đi",
                "confidence":"Cao",
                "evidence":(
                    f"Lượt xem sản phẩm {n(deltas.get('views'))*100:+.1f}%; "
                    f"Lượt nhấp {n(deltas.get('clicks'))*100:+.1f}%; "
                    f"CTR {n(deltas.get('ctr'))*100:+.1f}%."
                ),
                "meaning":"Nút thắt nằm nhiều hơn ở số cơ hội được nhìn thấy/phân phối, không phải ở tỷ lệ click trên mỗi lượt hiển thị."
            })
            hypotheses.append({
                "rank":1,
                "level":"Khả năng cao",
                "title":"Sản phẩm đang mất độ phủ / khả năng được phân phối trên sàn",
                "basis":"Lượt xem và lượt nhấp cùng giảm mạnh trong khi CTR không giảm.",
                "check":"Đối chiếu nguồn hiển thị, thứ hạng tìm kiếm/đề xuất, campaign enrollment và mức hỗ trợ quảng cáo theo thời gian."
            })
        else:
            observed.append({
                "title":"Cả độ phủ và khả năng kéo click đều suy yếu",
                "confidence":"Cao",
                "evidence":(
                    f"Lượt xem {n(deltas.get('views'))*100:+.1f}%; "
                    f"Lượt nhấp {n(deltas.get('clicks'))*100:+.1f}%; CTR {n(deltas.get('ctr'))*100:+.1f}%."
                ),
                "meaning":"Tầng đầu phễu đang yếu ở cả lượng hiển thị và sức hút click."
            })

    # 2) PDP / offer / traffic quality layer
    if n(deltas.get("bounceRate")) >= .25 and n(deltas.get("visitToAtcRate")) <= -.15 and n(deltas.get("cvr")) <= -.10:
        observed.append({
            "title":"Sau khi khách vào trang, chất lượng phiên giảm",
            "confidence":"Cao",
            "evidence":(
                f"Tỷ lệ thoát {n(deltas.get('bounceRate'))*100:+.1f}%; "
                f"tỷ lệ truy cập → thêm vào giỏ {n(deltas.get('visitToAtcRate'))*100:+.1f}%; "
                f"CVR {n(deltas.get('cvr'))*100:+.1f}%."
            ),
            "meaning":"Không chỉ thiếu traffic; hiệu quả từ trang sản phẩm đến giỏ hàng/đơn hàng cũng yếu hơn."
        })
        hypotheses.append({
            "rank":2,
            "level":"Khả năng vừa–cao",
            "title":"Đề nghị bán hàng/PDP hoặc chất lượng traffic sau click kém phù hợp hơn",
            "basis":"Tỷ lệ thoát tăng, thêm vào giỏ giảm và CVR giảm đồng thời.",
            "check":"Kiểm tra giá/voucher, ảnh & nội dung PDP, review/rating, nguồn traffic, variation và tình trạng còn hàng."
        })

    # 3) Paid exposure / efficiency corroboration from Ads.
    if ads_ctx.get("status")=="READY":
        imp=n(ads_ctx.get("impressionsDelta")); clk=n(ads_ctx.get("clicksDelta"))
        spend=n(ads_ctx.get("spendDelta")); roas=n(ads_ctx.get("roasDelta"))
        sales=n(ads_ctx.get("salesDelta"))
        if imp <= -.30 and clk <= -.30:
            observed.append({
                "title":"Quảng cáo 3 tháng cũng giảm mạnh về quy mô phân phối",
                "confidence":"Cao" if ads_ctx.get("spendAvailable") else "Khá",
                "evidence":(
                    f"3 tháng gần nhất vs 3 tháng trước: hiển thị Ads {imp*100:+.1f}%; click Ads {clk*100:+.1f}%; "
                    + (f"Ads Spend {spend*100:+.1f}%; ROAS {roas*100:+.1f}%; " if ads_ctx.get("spendAvailable") else "")
                    + f"doanh số quy đổi {sales*100:+.1f}%."
                ),
                "meaning":(
                    "Độ phủ trả phí co lại mạnh. Nếu ROAS chỉ biến động nhẹ, vấn đề chính nằm ở quy mô phân phối/chi tiêu chứ không phải hiệu suất Ads suy sụp."
                    if ads_ctx.get("spendAvailable") and abs(roas)<=.15 else
                    "Độ phủ trả phí co lại mạnh và đang củng cố tín hiệu mất volume."
                )
            })
            hypotheses.append({
                "rank":3,
                "level":"Khả năng cao" if ads_ctx.get("spendAvailable") and spend<=-.30 else "Khả năng vừa",
                "title":"Khối lượng hỗ trợ quảng cáo thấp hơn đang góp phần làm giảm độ phủ",
                "basis":(
                    "Ads Spend, impressions và clicks cùng giảm mạnh trên cùng cửa sổ 3 tháng."
                    if ads_ctx.get("spendAvailable") else
                    "Hiển thị và lượt nhấp quảng cáo cấp sản phẩm giảm mạnh."
                ),
                "check":"Đối chiếu target ROAS, lịch sử phân phối, ngân sách/chi tiêu thực tế và thời điểm chiến dịch bị giới hạn trong Seller Center."
            })

    # 4) AOV / basket value is a ruling-out observation, not proof about price competitiveness.
    if n(deltas.get("aov")) >= -.05:
        observed.append({
            "title":"Giá trị đơn hàng không phải driver chính của mức giảm doanh số",
            "confidence":"Cao",
            "evidence":f"Doanh số trên mỗi đơn (AOV) {n(deltas.get('aov'))*100:+.1f}%.",
            "meaning":"Mức giảm chủ yếu đến từ số đơn/funnel. Tuy nhiên AOV ổn không loại trừ khả năng giá/voucher đang làm CVR kém đi."
        })

    # Always keep unobserved operational hypotheses explicit.
    hypotheses.append({
        "rank":len(hypotheses)+1,
        "level":"Cần loại trừ",
        "title":"Thiếu hàng / variation kém sẵn có hoặc thay đổi cấu trúc lựa chọn",
        "basis":"Data Mart hiện chưa có lịch sử tồn kho/availability theo variation đủ để xác nhận.",
        "check":"Kiểm tra out-of-stock, variation bị ẩn/hết hàng, thay đổi Seller SKU và tỷ trọng variation bán ra."
    })
    hypotheses.append({
        "rank":len(hypotheses)+1,
        "level":"Cần thêm benchmark",
        "title":"Nhu cầu ngành hàng/cạnh tranh thị trường thay đổi",
        "basis":"Dữ liệu nội bộ chưa đủ để tách biến động riêng của sản phẩm khỏi xu hướng chung của ngành hàng.",
        "check":"So với các sản phẩm cùng nhóm trong shop và benchmark thị trường/cạnh tranh nếu có."
    })

    # Re-rank deterministic order.
    for idx,h in enumerate(hypotheses,1):
        h["rank"]=idx

    return {
        "observedFindings":observed,
        "hypotheses":hypotheses,
        "quickConclusion":(
            "Doanh số giảm đến từ cả hai tầng: sản phẩm được nhìn thấy/nhấp ít hơn và hiệu quả sau khi khách vào trang cũng yếu đi."
            if any("Độ phủ" in x["title"] for x in observed) and any("chất lượng phiên" in x["title"] for x in observed)
            else "Doanh số giảm có nhiều tín hiệu đồng thời; cần ưu tiên kiểm tra các giả thuyết có bằng chứng trực tiếp trước."
        ),
    }


def build_product_signals(product_monthly, ads_product_daily, loaded_end):
    """High-confidence structural Product Opportunity / Problem Engine v1.

    Uses six COMPLETE historical months: recent 3 vs prior 3.
    Current MTD is only corroborating evidence, never the primary baseline.
    """
    if not product_monthly:
        return {"status":"NO_PRODUCT_DATA","signals":[],"count":0}

    current_month=str(loaded_end)[:7]
    completed=[_month_key_shift(current_month,-k) for k in range(1,7)]
    completed=list(reversed(completed))  # oldest -> newest
    prior3=completed[:3]; recent3=completed[3:]
    prior3_days=sum(_month_days(m) for m in prior3) or 1
    recent3_days=sum(_month_days(m) for m in recent3) or 1

    grouped=defaultdict(list)
    for r in product_monthly:
        pid=str(r.get("productId","") or "")
        if pid:
            grouped[pid].append(r)

    # Shop materiality denominator over the same recent 3 complete months.
    recent_shop_gmv=sum(
        n(r.get("placedGmv")) for r in product_monthly
        if str(r.get("month")) in recent3
    ) or 1.0

    signals=[]
    for pid,rows in grouped.items():
        by_month={str(r.get("month")):r for r in rows}
        latest_row=by_month.get(current_month) or by_month.get(recent3[-1])
        if not latest_row:
            continue
        name=str(latest_row.get("name","") or "")
        sku=str(latest_row.get("sku","") or "")
        category=str(latest_row.get("category","") or "")
        status=str(latest_row.get("status","") or "")
        if status and status!="Đang hoạt động":
            continue
        if category=="Quà tặng" or name.startswith("[Quà tặng]") or sku in {"CT001","PK001","SO001"}:
            continue

        hist=[by_month.get(m) for m in completed]
        positive=[r for r in hist if r and (n(r.get("placedGmv"))>0 or i(r.get("placedOrders"))>0)]
        coverage=len(positive)/6.0
        if coverage < .83:
            continue

        prev_rows=[by_month.get(m) for m in prior3 if by_month.get(m)]
        recent_rows=[by_month.get(m) for m in recent3 if by_month.get(m)]
        if len(prev_rows)<3 or len(recent_rows)<3:
            continue
        prev=_aggregate_product_rows(prev_rows)
        recent=_aggregate_product_rows(recent_rows)
        if prev["gmv"]<=0 or recent["gmv"]<=0:
            continue

        deltas={
            "gmv":_pct_delta(recent["gmv"],prev["gmv"]),
            "orders":_pct_delta(recent["orders"],prev["orders"]),
            "views":_pct_delta(recent["views"],prev["views"]),
            "clicks":_pct_delta(recent["clicks"],prev["clicks"]),
            "ctr":_pct_delta(recent["ctr"],prev["ctr"]),
            "visits":_pct_delta(recent["visits"],prev["visits"]),
            "pageViews":_pct_delta(recent["pageViews"],prev["pageViews"]),
            "bounceRate":_pct_delta(recent["bounceRate"],prev["bounceRate"]),
            "atcVisits":_pct_delta(recent["atcVisits"],prev["atcVisits"]),
            "visitToAtcRate":_pct_delta(recent["visitToAtcRate"],prev["visitToAtcRate"]),
            "cvr":_pct_delta(recent["cvr"],prev["cvr"]),
            "aov":_pct_delta(recent["aov"],prev["aov"]),
            "unitsPerOrder":_pct_delta(recent["unitsPerOrder"],prev["unitsPerOrder"]),
        }
        materiality=recent["gmv"]/recent_shop_gmv
        if materiality < .02:
            continue

        monthly_gmv=[n(by_month[m].get("placedGmv")) for m in completed if by_month.get(m)]
        down_tail=_tail_direction(monthly_gmv,"down")
        up_tail=_tail_direction(monthly_gmv,"up")

        current=by_month.get(current_month)
        pace_delta=None
        if current and int(str(loaded_end)[8:10])>=10:
            elapsed=max(int(str(loaded_end)[8:10]),1)
            current_daily=n(current.get("placedGmv"))/elapsed
            hist_days=recent3_days
            recent_daily=recent["gmv"]/hist_days if hist_days else 0.0
            pace_delta=_pct_delta(current_daily,recent_daily) if recent_daily else None

        support_negative=sum(1 for k in ("orders","clicks","cvr","aov") if deltas.get(k) is not None and deltas[k]<0)
        support_positive=sum(1 for k in ("orders","clicks","cvr","aov") if deltas.get(k) is not None and deltas[k]>0)

        signal_type=None
        direction=None
        support_count=0
        tail=0
        pace_support=.5
        if deltas["gmv"] is not None and deltas["gmv"]<=-.35 and support_negative>=2:
            signal_type="Vấn đề"; direction="down"; support_count=support_negative; tail=down_tail
            if pace_delta is not None: pace_support=1.0 if pace_delta<=-.10 else (.25 if pace_delta>.10 else .6)
        elif deltas["gmv"] is not None and deltas["gmv"]>=.35 and support_positive>=2:
            signal_type="Cơ hội"; direction="up"; support_count=support_positive; tail=up_tail
            if pace_delta is not None: pace_support=1.0 if pace_delta>=.10 else (.25 if pace_delta<-.10 else .6)
        if not signal_type:
            continue

        # Require either multi-month persistence or current-MTD corroboration.
        if tail<1 and pace_support<1.0:
            continue

        trend=min(1.0,abs(n(deltas["gmv"]))/.80)
        material=min(1.0,materiality/.08)
        support=min(1.0,support_count/4.0)
        persistence=min(1.0,max(tail/2.0,.50))
        score=100.0*(.28*trend+.24*material+.18*support+.15*persistence+.15*pace_support)
        if score<70:
            continue

        driver_candidates={
            "Lượt nhấp vào sản phẩm":deltas.get("clicks"),
            "Tỷ lệ chuyển đổi":deltas.get("cvr"),
            "AOV":deltas.get("aov"),
        }
        if direction=="down":
            driver_label,driver_delta=min(driver_candidates.items(),key=lambda kv:n(kv[1],0))
        else:
            driver_label,driver_delta=max(driver_candidates.items(),key=lambda kv:n(kv[1],0))

        ads_ctx=_product_ads_support(pid,ads_product_daily,recent3,prior3,loaded_end)
        confidence=min(.95,.70+.04*max(0,len(positive)-5)+.05*(1 if tail>=1 else 0)+.05*(1 if pace_support>=.6 else 0))
        severity="High" if score>=85 and confidence>=.85 else "Med"

        priority=build_priority(
            recent_gmv=recent["gmv"],
            previous_gmv=prev["gmv"],
            recent_days=recent3_days,
            previous_days=prior3_days,
            recent_shop_gmv=recent_shop_gmv,
            gmv_delta=deltas["gmv"],
            persistence_months=tail,
            pace_delta=pace_delta,
            pace_support=pace_support,
            confidence=confidence,
        )
        structural_impact_value=priority["structuralImpactValue"]
        structural_impact_share=priority["structuralImpactShare"]
        priority_score=priority["priorityScore"]

        summary=(
            f"GMV 3 tháng gần nhất giảm {abs(n(deltas['gmv']))*100:.1f}% so với 3 tháng trước."
            if direction=="down" else
            f"GMV 3 tháng gần nhất tăng {abs(n(deltas['gmv']))*100:.1f}% so với 3 tháng trước."
        )
        evidence=(
            f"{driver_label} là tín hiệu hỗ trợ mạnh nhất ({n(driver_delta)*100:+.1f}%); "
            f"product share {materiality*100:.1f}% trong 3 tháng gần nhất."
        )
        if pace_delta is not None:
            evidence += f" MTD daily pace {n(pace_delta)*100:+.1f}% so với daily pace 3 tháng hoàn chỉnh gần nhất."

        signal={
            "signalId":f"PROD-{'PROBLEM' if direction=='down' else 'OPPORTUNITY'}-{pid}",
            "type":signal_type,
            "severity":severity,
            "score":score,
            "confidence":confidence,
            "productId":pid,
            "sellerSku":sku,
            "productName":name,
            "category":category,
            "historyMonths":completed,
            "recentWindow":recent3,
            "previousWindow":prior3,
            "recent":recent,
            "previous":prev,
            "deltas":deltas,
            "materialityShare":materiality,
            "structuralImpactValue":structural_impact_value,
            "structuralImpactShare":structural_impact_share,
            "priorityScore":priority_score,
            "priorityComponents":priority["priorityComponents"],
            "persistenceMonths":tail,
            "currentMtd":{
                "month":current_month,
                "placedGmv":n(current.get("placedGmv")) if current else None,
                "orders":i(current.get("placedOrders")) if current else None,
                "paceDelta":pace_delta,
                "corroborationScore":pace_support,
            },
            "adsSupport":ads_ctx,
            "mainDriver":driver_label,
            "mainDriverDelta":driver_delta,
            "summary":summary,
            "evidence":evidence,
            "action":"Xem chẩn đoán sản phẩm",
        }
        signal["rootCause"]=_product_root_cause_layers(signal_type,recent,prev,deltas,ads_ctx)
        signal["diagnostic"]=_product_signal_diagnostic(signal,by_month)
        signal["diagnostic"]["quickConclusion"]=signal["rootCause"].get("quickConclusion","")
        signal["diagnostic"]["observedFindings"]=signal["rootCause"].get("observedFindings",[])
        signal["diagnostic"]["hypotheses"]=signal["rootCause"].get("hypotheses",[])
        signals.append(signal)

    ranking_result=rank_signals(signals)
    ranked=ranking_result["ranked"]
    problems=ranking_result["problems"]
    opportunities=ranking_result["opportunities"]

    selected=[]
    if problems: selected.append(problems[0])
    if opportunities: selected.append(opportunities[0])

    def rank_summary(x):
        return {
            "signalId":x.get("signalId"),
            "type":x.get("type"),
            "productId":x.get("productId"),
            "sellerSku":x.get("sellerSku"),
            "productName":x.get("productName"),
            "priorityScore":x.get("priorityScore"),
            "globalRank":x.get("globalRank"),
            "rankWithinType":x.get("rankWithinType"),
            "structuralImpactValue":x.get("structuralImpactValue"),
            "structuralImpactShare":x.get("structuralImpactShare"),
            "gmvDelta":x.get("deltas",{}).get("gmv"),
            "persistenceMonths":x.get("persistenceMonths"),
            "confidence":x.get("confidence"),
            "priorityComponents":x.get("priorityComponents"),
        }

    return {
        "status":"SIGNALS_FOUND" if selected else "NO_HIGH_CONFIDENCE_SIGNALS",
        "count":len(selected),
        "candidateCount":len(ranked),
        "problemCount":len(problems),
        "opportunityCount":len(opportunities),
        "signals":selected,
        "ranking":{
            "method":"GEOMETRIC_4_FACTOR",
            "formula":"100 × (Impact × Deviation × Persistence × Confidence)^(1/4)",
            "problems":[rank_summary(x) for x in problems[:10]],
            "opportunities":[rank_summary(x) for x in opportunities[:10]],
            "all":[rank_summary(x) for x in ranked[:20]],
        },
        "engine":"STRUCTURAL_6M_3V3_WITH_MTD_CORROBORATION",
        "latestCompleteMonths":completed,
        "currentMtdMonth":current_month,
        "minimumScore":70,
    }


def build_payload(mart, loaded_end, build_id, state):
    feature_health={}
    stage=records(get_ws(mart, "dm_commercial_stage_daily")); shop=records(get_ws(mart, "dm_shop_daily"))
    quality=records(get_ws(mart, "dm_order_quality_daily")); traffic=records(get_ws(mart, "dm_traffic_source_daily"))
    ads=records(get_ws(mart, "dm_ads_daily"))
    try:
        adsprod_ws=get_ws(mart, "dm_ads_product_daily")
        adsprod_headers=[str(x).strip() for x in adsprod_ws.row_values(1)]
        adsprod=records(adsprod_ws)
        required_adsprod={"shop_id","data_date","product_id","impressions","clicks","conversions","attributed_sales","ad_spend","roas"}
        missing=sorted(required_adsprod-set(adsprod_headers))
        if missing:
            feature_health["productAdsMart"]={"status":"DEGRADED","reason":"missing columns: "+", ".join(missing)}
        else:
            feature_health["productAdsMart"]={"status":"READY","rows":len(adsprod)}
    except Exception as exc:
        adsprod=[]
        feature_health["productAdsMart"]={"status":"DEGRADED","reason":str(exc)}
    prod=records(get_ws(mart, "dm_product_monthly"))
    source_shop_id=assert_single_shop_payload_sources(
        ("commercial_stage",stage),
        ("shop_daily",shop),
        ("order_quality",quality),
        ("traffic",traffic),
        ("ads",ads),
        ("ads_product",adsprod),
        ("product_monthly",prod),
    )
    cust=records(get_ws(mart, "dm_customer_lifetime")); geo=records(get_ws(mart, "dm_customer_geo_monthly")); health=records(get_ws(mart, "dm_data_health")); readme=kv_map(get_ws(mart, "00_README"))
    loaded_start=str(state.get("common_reliable_start") or "2025-11-09")
    def in_window(d): return bool(d) and loaded_start <= str(d) <= loaded_end
    months=sorted({str(r.get("data_date"))[:7] for r in stage if in_window(r.get("data_date"))})
    shop_by_date={str(r.get("data_date")):r for r in shop if in_window(r.get("data_date"))}
    q_by_date={str(r.get("data_date")):r for r in quality if in_window(r.get("data_date"))}

    shop_daily=[]
    for r in stage:
        d=str(r.get("data_date",""))
        if not in_window(d): continue
        shop_daily.append({"shopId":source_shop_id,"date":d,"stage":str(r.get("order_stage","")),"gmv":n(r.get("gmv")),"orders":i(r.get("orders")),
            "aov":n(r.get("aov")),"clicks":i(r.get("product_clicks")),"visits":i(r.get("visits")),"cvr":n(r.get("cvr")),
            "cancelOrders":i(r.get("cancelled_orders")),"cancelSales":n(r.get("cancelled_sales")),"rrOrders":i(r.get("rr_orders")),
            "rrSales":n(r.get("rr_sales")),"buyers":i(r.get("buyers")),"newBuyers":i(r.get("new_buyers")),
            "existingBuyers":i(r.get("existing_buyers")),"returnRate":n(r.get("rr_rate"))})

    order_daily=[]
    for d in sorted(q_by_date):
        q=q_by_date[d]; s=shop_by_date.get(d,{})
        order_daily.append({"shopId":source_shop_id,"date":d,"orders":i(q.get("total_orders")),"placedGmv":n(s.get("placed_gmv")),"cancelOrders":i(q.get("cancelled_orders")),
            "cancelSales":n(s.get("cancelled_sales")),"netGmv":n(s.get("net_sales_after_cancel")),"fixed":n(q.get("fixed_fee")),
            "service":n(q.get("service_fee")),"transaction":n(q.get("transaction_fee")),"fees":n(q.get("order_fees"))})

    traffic_daily=[]
    for r in traffic:
        d=str(r.get("data_date",""))
        if str(r.get("order_stage"))!="placed" or not in_window(d): continue
        traffic_daily.append({"shopId":source_shop_id,"date":d,"group":str(r.get("channel_group","")),"source":str(r.get("traffic_source","")),
            "isTotal":b(r.get("is_group_total")),"sales":n(r.get("sales")),"impressions":i(r.get("impressions")),"clicks":i(r.get("clicks")),
            "orders":n(r.get("attributed_orders")),"units":n(r.get("attributed_units")),"cvr":n(r.get("conversion_rate")),"buyers":i(r.get("buyers")),
            "uniqueImpressions":i(r.get("unique_impressions")),"uniqueClicks":i(r.get("unique_clicks")),"adSpend":n(r.get("ad_spend")),"roas":n(r.get("roas"))})

    ads_daily=[{"shopId":source_shop_id,"date":str(r.get("data_date")),"impressions":i(r.get("impressions")),"clicks":i(r.get("clicks")),"atc":i(r.get("add_to_cart")),
        "conversions":i(r.get("conversions")),"units":i(r.get("units_sold")),"sales":n(r.get("attributed_sales")),"spend":n(r.get("ad_spend")),
        "ctr":n(r.get("ctr")),"cvr":n(r.get("cvr")),"cpc":n(r.get("cpc")),"cpm":n(r.get("cpm")),"cpa":n(r.get("cpa")),"roas":n(r.get("roas"))}
        for r in ads if in_window(r.get("data_date"))]
    ads_product_daily=[{"shopId":source_shop_id,"date":str(r.get("data_date")),"productId":str(r.get("product_id","")),"name":str(r.get("product_name","")),
        "spend":n(r.get("ad_spend")),"sales":n(r.get("attributed_sales")),"clicks":i(r.get("clicks")),"impressions":i(r.get("impressions")),
        "conversions":i(r.get("conversions")),"roas":n(r.get("roas")),"cvr":n(r.get("cvr")),"cpa":n(r.get("cpa"))}
        for r in adsprod if in_window(r.get("data_date"))]

    sku_groups=load_sku_groups()
    def group_name(name,sku):
        import re
        m=re.search(r"\b(Cool\s+S\d+|Air\s+[SF]\d+)\b",str(name),flags=re.I)
        if m:
            g=m.group(1)
            return re.sub(r"^cool", "Cool", re.sub(r"^air", "Air", g, flags=re.I), flags=re.I)
        base=str(sku or "").split("-")[0]
        return sku_groups.get(base,base or "Khác")
    product_monthly=[]
    for r in prod:
        m=str(r.get("data_month", ""))[:7]
        if m < loaded_start[:7] or m > loaded_end[:7]: continue
        name=str(r.get("product_name","") or ""); sku=str(r.get("product_sku","") or "")
        product_monthly.append({"shopId":source_shop_id,"month":m,"productId":str(r.get("product_id","")),"sku":sku,"name":name,"rawName":name,
            "category":str(r.get("category","") or ""),"status":str(r.get("product_status","") or ""),"group":group_name(name,sku),
            "placedGmv":n(r.get("placed_gmv")),"confirmedGmv":n(r.get("confirmed_gmv")),
            "views":i(r.get("product_views")),"clicks":i(r.get("product_clicks")),"ctr":n(r.get("ctr")),
            "placedOrders":i(r.get("placed_orders")),"confirmedOrders":i(r.get("confirmed_orders")),
            "placedUnits":i(r.get("placed_units")),"confirmedUnits":i(r.get("confirmed_units")),"placedBuyers":i(r.get("placed_buyers")),"confirmedBuyers":i(r.get("confirmed_buyers")),
            "uniqueImpressions":i(r.get("unique_impressions")),"uniqueClicks":i(r.get("unique_clicks")),"visits":i(r.get("product_visits")),
            "pageViews":i(r.get("product_page_views")),"bounces":i(r.get("page_bounces")),"atcVisits":i(r.get("add_to_cart_visits")),"atcUnits":i(r.get("add_to_cart_units"))})

    try:
        product_signals=build_product_signals(product_monthly,ads_product_daily,loaded_end)
        feature_health["productIntelligence"]={
            "status":"READY",
            "candidateCount":i(product_signals.get("candidateCount")),
            "problemCount":i(product_signals.get("problemCount")),
            "opportunityCount":i(product_signals.get("opportunityCount")),
        }
    except Exception as exc:
        product_signals={
            "status":"DEGRADED",
            "count":0,
            "signals":[],
            "ranking":{"problems":[],"opportunities":[],"all":[]},
            "reason":"Product Intelligence unavailable; core dashboard remains usable.",
        }
        feature_health["productIntelligence"]={"status":"DEGRADED","reason":str(exc)}

    username_coverage=n(readme.get("Customer identity GMV coverage"), n(state.get("username_coverage"),0))
    observed_ltv=sum(n(r.get("lifetime_gmv")) for r in cust); repeat=[r for r in cust if i(r.get("lifetime_orders"))>=2]
    intervals=[n(r.get("avg_days_between_orders")) for r in repeat if r.get("avg_days_between_orders") not in (None,"")]
    asof=max([str(r.get("as_of_date","")) for r in cust if r.get("as_of_date")], default=loaded_end)
    segs=[]
    byseg=defaultdict(list)
    for r in cust: byseg[str(r.get("segment","") or "Khác")].append(r)
    for name,rows in sorted(byseg.items()):
        customers=len(rows); ltv=sum(n(x.get("lifetime_gmv")) for x in rows); orders=sum(i(x.get("lifetime_orders")) for x in rows)
        segs.append({"name":name,"customers":customers,"ltv":ltv,"avgLtv":ltv/customers if customers else 0,
            "avgAov":mean([n(x.get("avg_order_value")) for x in rows]) if rows else 0,"avgOrders":orders/customers if customers else 0,
            "avgRecency":mean([i(x.get("days_since_last_order")) for x in rows]) if rows else 0})
    react=sorted([customer_item(r) for r in cust if str(r.get("segment")) in {"Nguy cơ rời bỏ","Khách rời bỏ"}],key=lambda x:x["ltv"],reverse=True)[:30]
    loyal=sorted([customer_item(r) for r in cust if str(r.get("segment"))=="Khách trung thành"],key=lambda x:x["ltv"],reverse=True)[:20]
    monthagg=defaultdict(lambda:{"buyers":0,"new":0,"gmv":0.0,"orders":0})
    geo_monthly=[]; regagg=defaultdict(lambda:{"gmv":0.0,"orders":0,"buyers":0})
    for r in geo:
        m=str(r.get("data_month",""))[:7]; region=str(r.get("region","") or "").replace("Miền ",""); province=str(r.get("province","") or "")
        monthagg[m]["buyers"]+=i(r.get("buyers")); monthagg[m]["new"]+=i(r.get("new_buyers")); monthagg[m]["gmv"]+=n(r.get("gmv")); monthagg[m]["orders"]+=i(r.get("orders"))
        regagg[(m,region)]["gmv"]+=n(r.get("gmv")); regagg[(m,region)]["orders"]+=i(r.get("orders")); regagg[(m,region)]["buyers"]+=i(r.get("buyers"))
        geo_monthly.append({"month":m,"level":"province","name":province,"gmv":n(r.get("gmv")),"orders":i(r.get("orders")),"buyers":i(r.get("buyers"))})
    for (m,region),a in regagg.items(): geo_monthly.append({"month":m,"level":"region","name":region,**a})
    monthly=[{"month":m,"buyers":a["buyers"],"newBuyers":a["new"],"repeatBuyers":max(a["buyers"]-a["new"],0),"gmv":a["gmv"],"orders":a["orders"]} for m,a in sorted(monthagg.items())]
    customer={"summary":{"identifiedUsers":len(cust),"usernameCoverage":username_coverage,"observedLtv":observed_ltv,
        "repeatUsers":len(repeat),"repeatRate":len(repeat)/len(cust) if cust else 0,
        "repeatStats":{"n":len(intervals),"median":median(intervals) if intervals else 0,"p25":percentile(intervals,.25),"p75":percentile(intervals,.75),"p90":percentile(intervals,.90),"mean":mean(intervals) if intervals else 0},
        "windowStart":loaded_start,"windowEnd":asof},"segments":segs,"reactivation":react,"loyalTop":loyal,"monthly":monthly,"geoMonthly":sorted(geo_monthly,key=lambda x:(x["month"],x["level"],x["name"]))}

    sources=[]; known=[]
    status_map={"READY":"ready","READY_WITH_CAVEAT":"warning","DISABLED_BY_DESIGN":"disabled"}
    for r in health:
        domain=str(r.get("source_domain","")); sources.append({"name":domain,"range":str(r.get("production_window","") or "nan"),
            "months":i(r.get("source_files")),"status":status_map.get(str(r.get("status","")),"warning"),"note":str(r.get("metric_impact","") or "")})
        rem=str(r.get("remediation","") or "")
        if rem and str(r.get("status")) not in {"READY"}: known.append(f"{domain}: {rem}")
    known.append(f"Common cross-source production window hiện khóa tới {loaded_end}.")
    health_obj={"sources":sources,"knownIssues":known}
    command_center=build_command_center_history(shop_daily, ads_daily, loaded_end)
    command_center["productSignals"]=product_signals
    command_center["featureHealth"]=feature_health

    return {"meta":{"shopId":source_shop_id,"loadedStart":loaded_start,"loadedEnd":loaded_end,"months":months,"timezone":"Asia/Ho_Chi_Minh","currency":"VND",
        "generatedAt":dt.date.today().isoformat(),"ordersCount":sum(i(r.get("total_orders")) for r in quality if in_window(r.get("data_date"))),
        "usernameCoverage":username_coverage,"dataSource":"unipalm_dashboard_data_mart_v1_PROD","dataSourceId":MART_SHEET_ID,"dataBuild":build_id},
        "shopDaily":shop_daily,"orderDaily":order_daily,"trafficDaily":traffic_daily,"adsDaily":ads_daily,"adsProductDaily":ads_product_daily,
        "productMonthly":product_monthly,"customer":customer,"health":health_obj,"commandCenter":command_center}

def qa_mart(mart, expected_end):
    required=["dm_shop_daily","dm_commercial_stage_daily","dm_product_monthly","dm_traffic_source_daily","dm_ads_daily","dm_ads_product_daily","dm_order_quality_daily","dm_customer_lifetime","dm_customer_geo_monthly","dm_data_health"]
    existing={x.title for x in mart.worksheets()}; missing=[x for x in required if x not in existing]
    if missing: return False,f"Missing mart sheets: {missing}"
    stage=records(get_ws(mart, "dm_commercial_stage_daily")); keys=[(r.get("shop_id"),r.get("data_date"),r.get("order_stage")) for r in stage]
    if len(keys)!=len(set(keys)): return False,"Commercial stage duplicate keys"
    shop_ids=sorted({str(r.get("shop_id","") or "") for r in stage if str(r.get("shop_id","") or "")})
    if len(shop_ids)!=1: return False,f"Legacy publisher multi-shop guard: expected exactly one shop, found {shop_ids}"
    dates=[str(r.get("data_date")) for r in stage if r.get("data_date")]
    if not dates or max(dates)!=expected_end: return False,f"Commercial max date {max(dates) if dates else None} != expected {expected_end}"
    ads=records(get_ws(mart, "dm_ads_daily"))
    if any(n(r.get("ad_spend"))<0 for r in ads): return False,"Negative ad_spend"
    return True,"Blocking production mart QA PASS"

def build_encrypted_index(payload, build_id):
    """Build one encrypted production entrypoint with a runtime UI fallback.

    Default: Command Center V2.
    Immediate fallback: append ?ui=v1 to the same production URL.
    Data payload is identical for both UIs; UI failure cannot mutate the mart.
    """
    meta=build_dual_ui_wrapper(
        payload=payload,
        v2_template_path=V2_TEMPLATE,
        v1_template_path=FROZEN_TEMPLATE,
        output_path=INDEX_PATH,
        access_key=ACCESS_KEY,
        build_id=build_id,
    )
    print("UI artifact:", json.dumps(meta, ensure_ascii=False))


def main():
    _,state_ws,run_ws,control_ws=open_state(); state=kv_map(state_ws); control=kv_map(control_ws)
    run_id="gha2_"+dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    trigger="MANUAL_FULL" if FORCE_FULL else ("MANUAL" if EVENT=="workflow_dispatch" else "AUTO_DAILY")
    if str(control.get("AUTO_ENABLED","TRUE")).upper()=="FALSE" and trigger=="AUTO_DAILY":
        append_run(run_ws,run_id,trigger,"PAUSED",note="CONTROL.AUTO_ENABLED=FALSE"); set_output("publish_required","false"); return
    cmd=[sys.executable,str(ROOT/"automation"/"source_processor.py")]
    if DRY_RUN: cmd.append("--dry-run")
    if FORCE_FULL: cmd.append("--full")
    try: subprocess.run(cmd,check=True)
    except subprocess.CalledProcessError as exc:
        append_run(run_ws,run_id,trigger,"BLOCKED",qa="FAIL",qa_summary=f"source_processor exit={exc.returncode}")
        raise
    proc=json.loads(PROC_RESULT.read_text(encoding="utf-8")); candidate_end=proc["reliable_end"]
    if DRY_RUN:
        append_run(run_ws,run_id,trigger,"DRY_RUN_PASS",qa="PASS",qa_summary="Upstream readiness + candidate mart QA PASS",reliable_end=candidate_end)
        set_output("publish_required","false"); set_output("candidate_reliable_end",candidate_end); set_output("qa_status","PASS"); return
    # source_processor may have just consumed the Sheets per-user quota while
    # replacing the current-month production partitions.  Open/read the mart
    # through the same transient-error policy instead of failing immediately.
    mart=open_sheet(MART_SHEET_ID, "production mart")
    ok,summary=qa_mart(mart,candidate_end)
    if not ok:
        append_run(run_ws,run_id,trigger,"BLOCKED",qa="FAIL",qa_summary=summary,reliable_end=candidate_end); raise RuntimeError(summary)
    published_end=str(state.get("common_reliable_end") or "")
    publish_required=FORCE_FULL or candidate_end>published_end
    if not publish_required:
        append_run(run_ws,run_id,trigger,"NO_CHANGE",qa="PASS",qa_summary=summary,reliable_end=candidate_end); set_output("publish_required","false"); return
    build_id="ccv2-gha2-"+dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    payload=build_payload(mart,candidate_end,build_id,state); build_encrypted_index(payload,build_id)
    STATE_JSON.write_text(json.dumps({"run_id":run_id,"build_id":build_id,"candidate_reliable_end":candidate_end,"qa":"PASS","production_url":PROD_URL,"generated_at":now_iso()},indent=2),encoding="utf-8")
    append_run(run_ws,run_id,trigger,"READY_TO_COMMIT",qa="PASS",qa_summary=summary,reliable_end=candidate_end,note=f"build={build_id}")
    set_output("publish_required","true"); set_output("candidate_reliable_end",candidate_end); set_output("build_id",build_id); set_output("qa_status","PASS")

if __name__=="__main__": main()
