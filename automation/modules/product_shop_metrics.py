"""BI-authoritative shop metrics supporting Product destination summaries.

Product Performance order counts are product-order occurrences, not unique shop
orders. Summing them across products double-counts multi-product orders and can
be further distorted by free-gift / zero-GMV products. Shop-level order count
and AOV therefore come only from Business Insights placed-stage facts.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, Mapping, Sequence


def s(v: Any) -> str:
    return "" if v is None else str(v).strip()


def n(v: Any) -> float:
    if v in (None, ""):
        return 0.0
    try:
        return float(v)
    except Exception:
        return 0.0


def i(v: Any) -> int:
    return int(round(n(v)))


def ratio(num: Any, den: Any) -> float:
    d = n(den)
    return n(num) / d if d else 0.0


def monthly_from_bi_stage(rows: Sequence[Mapping[str, Any]], *, shop_id: str, period: str) -> Dict[str, Any]:
    scoped = [r for r in rows if s(r.get("shop_id")) == shop_id and s(r.get("data_date"))[:7] == period]
    foreign = sorted({s(r.get("shop_id")) for r in rows if s(r.get("shop_id")) and s(r.get("shop_id")) != shop_id})
    if foreign:
        raise ValueError(f"{shop_id}/{period}: foreign BI shop ids {foreign}")
    wrong_months = sorted({s(r.get("data_date"))[:7] for r in rows if s(r.get("data_date")) and s(r.get("data_date"))[:7] != period})
    if wrong_months:
        raise ValueError(f"{shop_id}/{period}: BI rows outside target month {wrong_months}")
    if not scoped:
        raise ValueError(f"{shop_id}/{period}: no BI shop rows")

    by_stage = defaultdict(list)
    seen = set()
    duplicates = []
    for row in scoped:
        stage = s(row.get("order_stage"))
        date = s(row.get("data_date"))[:10]
        key = (date, stage)
        if key in seen:
            duplicates.append(key)
        seen.add(key)
        by_stage[stage].append(row)
    if duplicates:
        raise ValueError(f"{shop_id}/{period}: duplicate BI date/stage rows {duplicates[:10]}")
    if not by_stage.get("placed"):
        raise ValueError(f"{shop_id}/{period}: placed BI stage missing")

    def stage_totals(stage: str):
        rs = by_stage.get(stage) or []
        return sum(n(r.get("gross_sales")) for r in rs), sum(i(r.get("order_count")) for r in rs)

    placed_gmv, placed_orders = stage_totals("placed")
    confirmed_gmv, confirmed_orders = stage_totals("confirmed")
    paid_gmv, paid_orders = stage_totals("paid")
    dates = sorted({s(r.get("data_date"))[:10] for r in by_stage["placed"]})
    return {
        "shop_id": shop_id,
        "data_month": period,
        "placed_gmv": placed_gmv,
        "placed_orders": placed_orders,
        "placed_aov": ratio(placed_gmv, placed_orders),
        "confirmed_gmv": confirmed_gmv,
        "confirmed_orders": confirmed_orders,
        "confirmed_aov": ratio(confirmed_gmv, confirmed_orders),
        "paid_gmv": paid_gmv,
        "paid_orders": paid_orders,
        "coverage_start": dates[0] if dates else "",
        "coverage_end": dates[-1] if dates else "",
        "source": "BUSINESS_INSIGHTS_SHOP_LEVEL",
        "order_semantics": "UNIQUE_SHOP_ORDERS",
    }


def monthly_from_semantic_shop_daily(rows: Sequence[Mapping[str, Any]], *, month: str, expected_shop_ids: Sequence[str]) -> list[Dict[str, Any]]:
    expected = set(expected_shop_ids)
    foreign = sorted({s(r.get("shop_id")) for r in rows if s(r.get("shop_id")) not in expected})
    if foreign:
        raise ValueError(f"{month}: foreign semantic shop ids {foreign}")
    wrong = sorted({s(r.get("data_date"))[:7] for r in rows if s(r.get("data_date")) and s(r.get("data_date"))[:7] != month})
    if wrong:
        raise ValueError(f"{month}: semantic shop rows outside month {wrong}")

    out = []
    for sid in expected_shop_ids:
        scoped = [r for r in rows if s(r.get("shop_id")) == sid]
        if not scoped:
            continue
        dates = sorted({s(r.get("data_date"))[:10] for r in scoped})
        placed_gmv = sum(n(r.get("placed_gmv")) for r in scoped)
        placed_orders = sum(i(r.get("placed_orders")) for r in scoped)
        confirmed_gmv = sum(n(r.get("confirmed_gmv")) for r in scoped)
        confirmed_orders = sum(i(r.get("confirmed_orders")) for r in scoped)
        paid_gmv = sum(n(r.get("paid_gmv")) for r in scoped)
        paid_orders = sum(i(r.get("paid_orders")) for r in scoped)
        out.append({
            "shop_id": sid,
            "data_month": month,
            "placed_gmv": placed_gmv,
            "placed_orders": placed_orders,
            "placed_aov": ratio(placed_gmv, placed_orders),
            "confirmed_gmv": confirmed_gmv,
            "confirmed_orders": confirmed_orders,
            "confirmed_aov": ratio(confirmed_gmv, confirmed_orders),
            "paid_gmv": paid_gmv,
            "paid_orders": paid_orders,
            "coverage_start": dates[0] if dates else "",
            "coverage_end": dates[-1] if dates else "",
            "source": "CANONICAL_SEMANTIC_V2_BUSINESS_INSIGHTS",
            "order_semantics": "UNIQUE_SHOP_ORDERS",
        })
    return out


def summarize(rows: Sequence[Mapping[str, Any]], *, shop_id: str, months: Sequence[str]) -> Dict[str, Any]:
    by_month = {s(r.get("data_month")): r for r in rows if s(r.get("shop_id")) == shop_id and s(r.get("data_month")) in set(months)}
    missing = [m for m in months if m not in by_month]
    if missing:
        return {
            "status": "INSUFFICIENT_HISTORY",
            "missingMonths": missing,
            "requiredMonths": list(months),
            "source": "BUSINESS_INSIGHTS_SHOP_LEVEL",
        }
    selected = [by_month[m] for m in months]
    placed_gmv = sum(n(r.get("placed_gmv")) for r in selected)
    placed_orders = sum(i(r.get("placed_orders")) for r in selected)
    confirmed_gmv = sum(n(r.get("confirmed_gmv")) for r in selected)
    confirmed_orders = sum(i(r.get("confirmed_orders")) for r in selected)
    sources = sorted({s(r.get("source")) for r in selected if s(r.get("source"))})
    return {
        "status": "READY",
        "missingMonths": [],
        "requiredMonths": list(months),
        "placedGmv": placed_gmv,
        "placedOrders": placed_orders,
        "placedAov": ratio(placed_gmv, placed_orders),
        "confirmedGmv": confirmed_gmv,
        "confirmedOrders": confirmed_orders,
        "confirmedAov": ratio(confirmed_gmv, confirmed_orders),
        "source": "BUSINESS_INSIGHTS_SHOP_LEVEL",
        "sourceLayers": sources,
        "orderSemantics": "UNIQUE_SHOP_ORDERS",
    }
