"""Pure helpers for product-level Ads mart aggregation and validation.

This module intentionally has no Google Sheets, Drive, UI, or diagnosis dependency.
Input: processed Ads rows.
Output: one row per (data_date, product_id), aggregating ALL campaigns for that product.
"""
from __future__ import annotations

import math
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Tuple

PRODUCT_ADS_COLUMNS = [
    "shop_id","data_date","product_id","product_sku","product_name","category",
    "impressions","clicks","ctr","add_to_cart","conversions","cvr","units_sold",
    "attributed_sales","ad_spend","spend_share","roas","cpc","cpm","cpa","acos",
]

ADDITIVE_FIELDS = (
    "impressions","clicks","add_to_cart","conversions","units_sold",
    "attributed_sales","ad_spend",
)


def n(v: Any, default: float = 0.0) -> float:
    if v in (None, ""):
        return default
    if isinstance(v, bool):
        return float(v)
    if isinstance(v, (int, float)):
        x = float(v)
        return x if math.isfinite(x) else default
    s = str(v).strip().replace("₫","").replace("đ","").replace("VND","").replace(" ","")
    pct = s.endswith("%")
    s = s.rstrip("%")
    if "," in s and "." in s:
        s = s.replace(".","").replace(",",".")
    elif "," in s:
        s = s.replace(",",".")
    try:
        x = float(s)
        return x / 100.0 if pct else x
    except Exception:
        return default


def i(v: Any) -> int:
    return int(round(n(v, 0.0)))


def aggregate_product_ads_rows(
    processed_rows: Iterable[Dict[str, Any]],
    metadata_by_product: Dict[Any, Dict[str, Any]] | None = None,
    expected_shop_id: str | None = None,
) -> List[Dict[str, Any]]:
    """Aggregate every product-scope campaign row by (date, product_id).

    Campaign identity is deliberately ignored. If campaign A is stopped and
    campaign B is launched for the same product, both contribute to the same
    product-day history.
    """
    metadata_by_product = metadata_by_product or {}
    agg: Dict[Tuple[str, str, str], Dict[str, float]] = defaultdict(lambda: defaultdict(float))
    source_meta: Dict[Tuple[str, str], Dict[str, Any]] = {}

    for r in processed_rows:
        if str(r.get("ad_scope","")).strip().lower() != "product":
            continue
        sid = str(r.get("shop_id","") or expected_shop_id or "").strip()
        if not sid:
            raise ValueError("product Ads row missing shop_id")
        if expected_shop_id and sid != expected_shop_id:
            raise ValueError(f"product Ads row shop_id mismatch: {sid} != {expected_shop_id}")
        pid = str(r.get("product_id","") or "").strip()
        d = str(r.get("data_date","") or "")[:10]
        if not pid or not d:
            continue
        key = (sid, d, pid)
        for f in ADDITIVE_FIELDS:
            agg[key][f] += n(r.get(f))
        source_meta[(sid,pid)] = {
            "product_sku": str(r.get("product_sku","") or ""),
            "product_name": str(r.get("product_name","") or ""),
        }

    daily_total_spend: Dict[Tuple[str, str], float] = defaultdict(float)
    for (sid,d,_), a in agg.items():
        daily_total_spend[(sid,d)] += a["ad_spend"]

    out: List[Dict[str, Any]] = []
    for (sid,d,pid), a in sorted(agg.items()):
        meta = dict(source_meta.get((sid,pid), {}))
        supplied = metadata_by_product.get((sid,pid), {})
        if not supplied and expected_shop_id:
            supplied = metadata_by_product.get(pid, {})
        meta.update({k:v for k,v in supplied.items() if v not in (None,"")})
        sku = str(meta.get("product_sku","") or "")
        name = str(meta.get("product_name","") or pid)
        category = str(meta.get("category","") or "")
        impr = a["impressions"]; clicks = a["clicks"]; conv = a["conversions"]
        spend = a["ad_spend"]; sales = a["attributed_sales"]
        out.append({
            "shop_id": sid,
            "data_date": d,
            "product_id": pid,
            "product_sku": sku,
            "product_name": name,
            "category": category,
            "impressions": i(impr),
            "clicks": i(clicks),
            "ctr": (clicks/impr if impr else 0.0),
            "add_to_cart": i(a["add_to_cart"]),
            "conversions": i(conv),
            "cvr": (conv/clicks if clicks else 0.0),
            "units_sold": i(a["units_sold"]),
            "attributed_sales": sales,
            "ad_spend": spend,
            "spend_share": (spend/daily_total_spend[(sid,d)] if daily_total_spend[(sid,d)] else 0.0),
            "roas": (sales/spend if spend else 0.0),
            "cpc": (spend/clicks if clicks else 0.0),
            "cpm": (spend*1000/impr if impr else 0.0),
            "cpa": (spend/conv if conv else 0.0),
            "acos": (spend/sales if sales else 0.0),
        })
    return out


def validate_product_ads_rows(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    keys = [(str(r.get("shop_id","")), str(r.get("data_date","")), str(r.get("product_id",""))) for r in rows]
    duplicates = len(keys) - len(set(keys))
    negative_spend = sum(1 for r in rows if n(r.get("ad_spend")) < 0)
    bad_roas = 0
    bad_spend_share = 0
    by_date_share: Dict[Tuple[str, str], float] = defaultdict(float)
    missing_shop_id = 0

    for r in rows:
        sid = str(r.get("shop_id","") or "")
        if not sid:
            missing_shop_id += 1
        spend = n(r.get("ad_spend")); sales = n(r.get("attributed_sales")); roas = n(r.get("roas"))
        expected = sales/spend if spend else 0.0
        if abs(roas-expected) > 1e-7:
            bad_roas += 1
        by_date_share[(sid,str(r.get("data_date","")))] += n(r.get("spend_share"))

    for total in by_date_share.values():
        if total and abs(total-1.0) > 1e-6:
            bad_spend_share += 1

    errors = []
    if missing_shop_id:
        errors.append(f"missing shop_id rows={missing_shop_id}")
    if duplicates:
        errors.append(f"duplicate shop+date+product keys={duplicates}")
    if negative_spend:
        errors.append(f"negative ad_spend rows={negative_spend}")
    if bad_roas:
        errors.append(f"ROAS formula mismatches={bad_roas}")
    if bad_spend_share:
        errors.append(f"daily spend_share sum mismatches={bad_spend_share}")

    return {
        "status":"PASS" if not errors else "FAIL",
        "rows":len(rows),
        "uniqueKeys":len(set(keys)),
        "duplicateKeys":duplicates,
        "missingShopId":missing_shop_id,
        "negativeSpend":negative_spend,
        "roasMismatches":bad_roas,
        "spendShareDateMismatches":bad_spend_share,
        "errors":errors,
    }


def audit_existing_product_ads_rows(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Audit a materialized mart without treating undefined ratio cells as missing.

    ad_spend must be present for every row. ROAS/CPC/CPA/ACOS can be blank when
    their denominator is zero in older materializations.
    """
    by_month: Dict[str, Dict[str, Any]] = {}
    keys = set()
    duplicates = 0
    negative_spend = 0
    missing_spend = 0
    for r in rows:
        d = str(r.get("data_date","") or "")[:10]
        if not d:
            continue
        m = d[:7]
        rec = by_month.setdefault(m, {"rows":0,"spendPresent":0,"negativeSpend":0,"duplicates":0})
        rec["rows"] += 1
        if r.get("ad_spend") not in (None,""):
            rec["spendPresent"] += 1
        else:
            missing_spend += 1
        if n(r.get("ad_spend")) < 0:
            negative_spend += 1
            rec["negativeSpend"] += 1
        key=(str(r.get("shop_id","") or ""),d,str(r.get("product_id","") or ""))
        if key in keys:
            duplicates += 1
            rec["duplicates"] += 1
        keys.add(key)

    for rec in by_month.values():
        rec["spendCoverage"] = rec["spendPresent"]/rec["rows"] if rec["rows"] else 0.0

    status = "PASS" if not duplicates and not negative_spend and not missing_spend else "FAIL"
    return {
        "status":status,
        "rows":sum(x["rows"] for x in by_month.values()),
        "duplicateKeys":duplicates,
        "negativeSpend":negative_spend,
        "missingSpend":missing_spend,
        "months":dict(sorted(by_month.items())),
    }
