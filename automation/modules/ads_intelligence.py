"""Shop-scoped Ads Intelligence V2 foundation.

Trusted Ads history is Semantic-v2-only in this foundation. The engine is daily
at source grain, exposes day/week/month/year scopes, recomputes every ratio from
additive facts and keeps driver attribution explicitly non-causal.
"""
from __future__ import annotations

import calendar
import datetime as dt
import hashlib
import json
from collections import defaultdict
from itertools import permutations
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence


ADDITIVE_FIELDS = (
    "impressions", "clicks", "add_to_cart", "conversions", "units_sold",
    "attributed_sales", "ad_spend",
)


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


def _read_json(path: str | Path) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _sha(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _parse_date(value: str) -> dt.date:
    return dt.datetime.strptime(value[:10], "%Y-%m-%d").date()


def _date_str(value: dt.date) -> str:
    return value.isoformat()


def _date_range(start: dt.date, end: dt.date) -> List[str]:
    if end < start:
        return []
    return [_date_str(start + dt.timedelta(days=x)) for x in range((end - start).days + 1)]


def _prev_month(year: int, month: int) -> tuple[int, int]:
    return (year - 1, 12) if month == 1 else (year, month - 1)


def load_contract(path: str | Path) -> Dict[str, Any]:
    data = _read_json(path)
    if s(data.get("layer_name")) != "multi_shop_ads_intelligence_v1":
        raise ValueError("unexpected Ads Intelligence layer")
    if s(data.get("status")) != "PREPRODUCTION":
        raise ValueError("Ads Intelligence contract must remain PREPRODUCTION")
    source = data.get("source_policy") or {}
    if s(source.get("trusted_history_source")) != "PUBLISHED_SEMANTIC_QA_PASS":
        raise ValueError("Ads history must remain Semantic QA PASS only")
    if s(source.get("canonical_grain")) != "DAILY":
        raise ValueError("Ads canonical grain must remain DAILY")
    scope = data.get("scope_policy") or {}
    if not bool(scope.get("single_shop_only")) or bool(scope.get("cross_shop_compare_allowed")):
        raise ValueError("Ads destination must remain single-shop and non-compare")
    if list(scope.get("allowed_time_scopes") or []) != ["day", "week", "month", "year"]:
        raise ValueError("Ads time-scope contract mismatch")
    safety = data.get("safety") or {}
    if any(bool(safety.get(k)) for k in (
        "write_production_data_mart", "modify_production_ui", "publish_legacy_payload",
        "platform_mutation_allowed", "production_activation_enabled",
    )):
        raise ValueError("unsafe Ads Intelligence contract")
    return data


def _summary(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    totals = defaultdict(float)
    for row in rows:
        for field in ADDITIVE_FIELDS:
            totals[field] += n(row.get(field))
    spend = totals["ad_spend"]
    sales = totals["attributed_sales"]
    clicks = totals["clicks"]
    conv = totals["conversions"]
    impr = totals["impressions"]
    return {
        "impressions": i(impr),
        "clicks": i(clicks),
        "addToCart": i(totals["add_to_cart"]),
        "conversions": i(conv),
        "unitsSold": i(totals["units_sold"]),
        "attributedSales": sales,
        "adSpend": spend,
        "ctr": ratio(clicks, impr),
        "cvr": ratio(conv, clicks),
        "roas": ratio(sales, spend),
        "cpc": ratio(spend, clicks),
        "cpm": ratio(spend * 1000, impr),
        "cpa": ratio(spend, conv),
        "acos": ratio(spend, sales),
        "adsAov": ratio(sales, conv),
    }


def _delta(cur: Any, prev: Any) -> float | None:
    p = n(prev)
    if p <= 0:
        return None
    return n(cur) / p - 1.0


def _summary_deltas(cur: Mapping[str, Any], prev: Mapping[str, Any]) -> Dict[str, Any]:
    keys = ("impressions", "clicks", "conversions", "attributedSales", "adSpend", "ctr", "cvr", "roas", "cpc", "cpa", "acos", "adsAov")
    return {key: _delta(cur.get(key), prev.get(key)) for key in keys}


def _roas_driver_attribution(previous: Mapping[str, Any], current: Mapping[str, Any]) -> Dict[str, Any]:
    prev = {
        "cvr": n(previous.get("cvr")),
        "adsAov": n(previous.get("adsAov")),
        "cpc": n(previous.get("cpc")),
    }
    cur = {
        "cvr": n(current.get("cvr")),
        "adsAov": n(current.get("adsAov")),
        "cpc": n(current.get("cpc")),
    }
    keys = ["cvr", "adsAov", "cpc"]
    if any(prev[k] <= 0 or cur[k] <= 0 for k in keys):
        return {
            "status": "NOT_ATTRIBUTED",
            "reason": "NON_POSITIVE_IDENTITY_FACTOR",
            "identity": "ROAS = Ads CVR × Ads AOV / CPC",
            "causalClaim": False,
            "driverContributions": [],
        }

    def model(v: Mapping[str, float]) -> float:
        return v["cvr"] * v["adsAov"] / v["cpc"] if v["cpc"] else 0.0

    contributions = {k: 0.0 for k in keys}
    perms = list(permutations(keys))
    for perm in perms:
        state = dict(prev)
        before = model(state)
        for key in perm:
            state[key] = cur[key]
            after = model(state)
            contributions[key] += after - before
            before = after
    for key in keys:
        contributions[key] /= len(perms)

    modeled_gap = model(cur) - model(prev)
    rows = []
    for key in keys:
        rows.append({
            "driverMetric": key,
            "contributionValue": contributions[key],
            "contributionShareOfModeledGap": contributions[key] / modeled_gap if modeled_gap else None,
            "driverPrevious": prev[key],
            "driverCurrent": cur[key],
            "driverDirection": "UP" if cur[key] > prev[key] else ("DOWN" if cur[key] < prev[key] else "FLAT"),
            "relationType": "IDENTITY_CONTRIBUTION",
            "causalClaim": False,
        })
    rows.sort(key=lambda x: abs(n(x.get("contributionValue"))), reverse=True)
    return {
        "status": "ATTRIBUTED",
        "identity": "ROAS = Ads CVR × Ads AOV / CPC",
        "method": "EXACT_SHAPLEY_ON_BUSINESS_IDENTITY",
        "previousModelValue": model(prev),
        "currentModelValue": model(cur),
        "modeledDifference": modeled_gap,
        "topDriverMetric": s((rows[0] if rows else {}).get("driverMetric")),
        "driverContributions": rows,
        "causalClaim": False,
    }


def _aggregate_products(rows: Sequence[Mapping[str, Any]], dates: Sequence[str]) -> List[Dict[str, Any]]:
    wanted = set(dates)
    grouped: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        d = s(row.get("data_date"))[:10]
        pid = s(row.get("product_id"))
        if d in wanted and pid:
            grouped[pid].append(row)
    out = []
    for pid, prows in grouped.items():
        totals = defaultdict(float)
        for row in prows:
            for field in ADDITIVE_FIELDS:
                totals[field] += n(row.get(field))
        latest = max(prows, key=lambda r: s(r.get("data_date")))
        summary = _summary([{field: totals[field] for field in ADDITIVE_FIELDS}])
        out.append({
            "productId": pid,
            "productName": s(latest.get("product_name")),
            "productSku": s(latest.get("product_sku")),
            "category": s(latest.get("category")),
            **summary,
        })
    return sorted(out, key=lambda x: (-n(x.get("adSpend")), s(x.get("productId"))))


def _product_signals(
    current: Sequence[Mapping[str, Any]],
    previous: Sequence[Mapping[str, Any]],
    *,
    min_spend_share: float,
    min_abs_roas_delta: float,
    max_count: int,
) -> Dict[str, Any]:
    prev = {s(x.get("productId")): x for x in previous}
    total_spend = sum(n(x.get("adSpend")) for x in current)
    signals = []
    for row in current:
        pid = s(row.get("productId"))
        prior = prev.get(pid)
        if not prior:
            continue
        share = ratio(row.get("adSpend"), total_spend)
        if share < min_spend_share:
            continue
        roas_delta = _delta(row.get("roas"), prior.get("roas"))
        if roas_delta is None or abs(roas_delta) < min_abs_roas_delta:
            continue
        sales_delta = _delta(row.get("attributedSales"), prior.get("attributedSales"))
        spend_delta = _delta(row.get("adSpend"), prior.get("adSpend"))
        confidence = 0.9 if n(prior.get("adSpend")) > 0 and n(prior.get("clicks")) > 0 else 0.72
        priority = min(100.0, share * 100 * 0.5 + min(abs(roas_delta), 2.0) * 25 + confidence * 25)
        signals.append({
            "type": "Cơ hội" if roas_delta > 0 else "Vấn đề",
            "productId": pid,
            "productName": s(row.get("productName")),
            "productSku": s(row.get("productSku")),
            "currentSpend": n(row.get("adSpend")),
            "currentAttributedSales": n(row.get("attributedSales")),
            "currentRoas": n(row.get("roas")),
            "currentCpa": n(row.get("cpa")),
            "currentCvr": n(row.get("cvr")),
            "spendShare": share,
            "roasDelta": roas_delta,
            "salesDelta": sales_delta,
            "spendDelta": spend_delta,
            "priorityScore": priority,
            "confidence": confidence,
            "relationType": "PERIOD_OVER_PERIOD_EVIDENCE",
            "causalClaim": False,
        })
    signals.sort(key=lambda x: (-n(x.get("priorityScore")), -n(x.get("spendShare")), s(x.get("productId"))))
    signals = signals[:max_count]
    return {
        "signals": signals,
        "problemCount": sum(1 for x in signals if x.get("type") == "Vấn đề"),
        "opportunityCount": sum(1 for x in signals if x.get("type") == "Cơ hội"),
    }


def _daily_series(rows: Sequence[Mapping[str, Any]], dates: Sequence[str]) -> List[Dict[str, Any]]:
    wanted = set(dates)
    by_date: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        d = s(row.get("data_date"))[:10]
        if d in wanted:
            by_date[d].append(row)
    return [{"dataDate": d, **_summary(by_date[d])} for d in sorted(wanted) if d in by_date]


def _snapshot(
    *,
    scope_key: str,
    option_key: str,
    current_dates: Sequence[str],
    previous_dates: Sequence[str],
    shop_rows: Sequence[Mapping[str, Any]],
    product_rows: Sequence[Mapping[str, Any]],
    trusted_dates: set[str],
    contract: Mapping[str, Any],
    is_partial: bool = False,
) -> Dict[str, Any]:
    current_missing = [d for d in current_dates if d not in trusted_dates]
    if current_missing or not current_dates:
        return {
            "status": "INSUFFICIENT_HISTORY",
            "scope": scope_key,
            "optionKey": option_key,
            "requiredDates": list(current_dates),
            "missingDates": current_missing,
            "summary": {}, "products": [], "signals": [],
        }
    current_shop = [r for r in shop_rows if s(r.get("data_date"))[:10] in set(current_dates)]
    current_products = _aggregate_products(product_rows, current_dates)
    summary = _summary(current_shop)
    top3 = sum(n(x.get("adSpend")) for x in current_products[:3])
    summary["top3SpendShare"] = ratio(top3, summary.get("adSpend"))

    comparison_ready = bool(previous_dates) and all(d in trusted_dates for d in previous_dates)
    previous_summary: Dict[str, Any] = {}
    deltas: Dict[str, Any] = {}
    driver = {"status": "INSUFFICIENT_COMPARISON_HISTORY", "causalClaim": False, "driverContributions": []}
    signal_state = {"signals": [], "problemCount": 0, "opportunityCount": 0}
    previous_products: List[Dict[str, Any]] = []
    if comparison_ready:
        previous_shop = [r for r in shop_rows if s(r.get("data_date"))[:10] in set(previous_dates)]
        previous_summary = _summary(previous_shop)
        deltas = _summary_deltas(summary, previous_summary)
        driver = _roas_driver_attribution(previous_summary, summary)
        previous_products = _aggregate_products(product_rows, previous_dates)
        policy = contract.get("intelligence_policy") or {}
        signal_state = _product_signals(
            current_products, previous_products,
            min_spend_share=float(policy.get("product_signal_min_spend_share") or 0.03),
            min_abs_roas_delta=float(policy.get("product_signal_min_abs_roas_delta") or 0.15),
            max_count=int(policy.get("product_signal_max_count") or 8),
        )

    return {
        "status": "READY",
        "scope": scope_key,
        "optionKey": option_key,
        "coverageStart": current_dates[0],
        "coverageEnd": current_dates[-1],
        "dayCount": len(current_dates),
        "isPartial": bool(is_partial),
        "comparisonStatus": "READY" if comparison_ready else "INSUFFICIENT_COMPARISON_HISTORY",
        "comparisonStart": previous_dates[0] if comparison_ready else "",
        "comparisonEnd": previous_dates[-1] if comparison_ready else "",
        "summary": summary,
        "previousSummary": previous_summary,
        "deltas": deltas,
        "driverAttribution": driver,
        "signals": signal_state["signals"],
        "problemCount": signal_state["problemCount"],
        "opportunityCount": signal_state["opportunityCount"],
        "products": current_products,
        "dailySeries": _daily_series(shop_rows, current_dates),
        "causalClaim": False,
    }


def _build_scope_snapshots(
    *,
    shop_rows: Sequence[Mapping[str, Any]],
    product_rows: Sequence[Mapping[str, Any]],
    lifecycle: Mapping[str, Any],
    contract: Mapping[str, Any],
) -> Dict[str, Any]:
    trusted_dates = sorted({s(r.get("data_date"))[:10] for r in shop_rows if s(r.get("data_date"))})
    trusted = set(trusted_dates)
    if not trusted_dates:
        return {
            "asOfDate": "", "trustedDateStart": "", "trustedDateEnd": "",
            "day": {"options": [], "snapshots": {}},
            "week": {"options": [], "snapshots": {}},
            "month": {"options": [], "snapshots": {}},
            "year": {"options": [], "snapshots": {}},
        }

    day_snapshots = {}
    for d in trusted_dates:
        date = _parse_date(d)
        prev = [_date_str(date - dt.timedelta(days=1))]
        day_snapshots[d] = _snapshot(
            scope_key="day", option_key=d, current_dates=[d], previous_dates=prev,
            shop_rows=shop_rows, product_rows=product_rows, trusted_dates=trusted, contract=contract,
        )

    week_snapshots = {}
    week_options = []
    for d in trusted_dates:
        end = _parse_date(d); start = end - dt.timedelta(days=6)
        current = _date_range(start, end)
        if all(x in trusted for x in current):
            previous = _date_range(start - dt.timedelta(days=7), start - dt.timedelta(days=1))
            week_snapshots[d] = _snapshot(
                scope_key="week", option_key=d, current_dates=current, previous_dates=previous,
                shop_rows=shop_rows, product_rows=product_rows, trusted_dates=trusted, contract=contract,
            )
            week_options.append(d)

    month_groups: Dict[str, List[str]] = defaultdict(list)
    for d in trusted_dates:
        month_groups[d[:7]].append(d)
    month_snapshots = {}
    for month, dates in sorted(month_groups.items()):
        dates = sorted(dates)
        anchor = _parse_date(dates[-1])
        month_start = dt.date(anchor.year, anchor.month, 1)
        current = _date_range(month_start, anchor)
        py, pm = _prev_month(anchor.year, anchor.month)
        prev_start = dt.date(py, pm, 1)
        prev_last = calendar.monthrange(py, pm)[1]
        elapsed = len(current)
        prev_end_day = min(elapsed, prev_last)
        previous = _date_range(prev_start, dt.date(py, pm, prev_end_day))
        full_month_end = calendar.monthrange(anchor.year, anchor.month)[1]
        month_snapshots[month] = _snapshot(
            scope_key="month", option_key=month, current_dates=current, previous_dates=previous,
            shop_rows=shop_rows, product_rows=product_rows, trusted_dates=trusted, contract=contract,
            is_partial=anchor.day < full_month_end,
        )

    year_groups: Dict[str, List[str]] = defaultdict(list)
    for d in trusted_dates:
        year_groups[d[:4]].append(d)
    year_snapshots = {}
    year_options = []
    for year, dates in sorted(year_groups.items()):
        dates = sorted(dates); anchor = _parse_date(dates[-1])
        if s(lifecycle.get("origin")) == "SHOP_LAUNCH" and s(lifecycle.get("start_policy")) == "FIRST_TRUSTED_SEMANTIC_DATE":
            year_start = _parse_date(dates[0])
        else:
            year_start = dt.date(anchor.year, 1, 1)
        current = _date_range(year_start, anchor)
        elapsed = len(current)
        prev_end = year_start - dt.timedelta(days=1)
        prev_start = prev_end - dt.timedelta(days=elapsed - 1)
        previous = _date_range(prev_start, prev_end)
        snap = _snapshot(
            scope_key="year", option_key=year, current_dates=current, previous_dates=previous,
            shop_rows=shop_rows, product_rows=product_rows, trusted_dates=trusted, contract=contract,
            is_partial=anchor < dt.date(anchor.year, 12, 31),
        )
        year_snapshots[year] = snap
        if snap.get("status") == "READY":
            year_options.append(year)

    return {
        "asOfDate": trusted_dates[-1],
        "trustedDateStart": trusted_dates[0],
        "trustedDateEnd": trusted_dates[-1],
        "trustedDateCount": len(trusted_dates),
        "day": {"options": trusted_dates, "snapshots": day_snapshots},
        "week": {"options": week_options, "snapshots": week_snapshots},
        "month": {"options": sorted(month_snapshots), "snapshots": month_snapshots},
        "year": {"options": sorted(year_snapshots), "readyOptions": year_options, "snapshots": year_snapshots},
    }


def validate_ads_intelligence(payload: Mapping[str, Any], expected_shop_ids: Sequence[str], contract: Mapping[str, Any]) -> Dict[str, Any]:
    checks = []
    def ck(name: str, ok: bool, detail: Any = None) -> None:
        checks.append({"name": name, "status": "PASS" if ok else "FAIL", "detail": detail or {}})

    shops = payload.get("shops") or {}
    ck("all_expected_shops_present", set(shops) == set(expected_shop_ids), {"shops": sorted(shops)})
    scope = payload.get("scopePolicy") or {}
    ck("single_shop_only", bool(scope.get("singleShopOnly")) and not bool(scope.get("compareAllowed")))
    ck("daily_source_grain", s(scope.get("canonicalSourceGrain")) == "DAILY")
    ck("time_scope_order", list(scope.get("allowedTimeScopes") or []) == ["day", "week", "month", "year"])

    for sid, shop in shops.items():
        ck(f"{sid}_scope_shop", s((shop.get("scope") or {}).get("type")) == "shop" and s((shop.get("scope") or {}).get("shopId")) == sid)
        ck(f"{sid}_compare_disabled", shop.get("compareAllowed") is False)
        periods = shop.get("periods") or {}
        for scope_key in ("day", "week", "month", "year"):
            block = periods.get(scope_key) or {}
            for option_key, snap in (block.get("snapshots") or {}).items():
                status = s(snap.get("status"))
                ck(f"{sid}_{scope_key}_{option_key}_status", status in {"READY", "INSUFFICIENT_HISTORY"}, {"status": status})
                if status != "READY":
                    continue
                sm = snap.get("summary") or {}
                ck(f"{sid}_{scope_key}_{option_key}_roas", abs(n(sm.get("roas")) - ratio(sm.get("attributedSales"), sm.get("adSpend"))) <= 1e-9)
                ck(f"{sid}_{scope_key}_{option_key}_ctr", abs(n(sm.get("ctr")) - ratio(sm.get("clicks"), sm.get("impressions"))) <= 1e-9)
                ck(f"{sid}_{scope_key}_{option_key}_cvr", abs(n(sm.get("cvr")) - ratio(sm.get("conversions"), sm.get("clicks"))) <= 1e-9)
                ck(f"{sid}_{scope_key}_{option_key}_cpc", abs(n(sm.get("cpc")) - ratio(sm.get("adSpend"), sm.get("clicks"))) <= 1e-9)
                ck(f"{sid}_{scope_key}_{option_key}_cpa", abs(n(sm.get("cpa")) - ratio(sm.get("adSpend"), sm.get("conversions"))) <= 1e-9)
                causal = [x.get("productId") for x in snap.get("signals") or [] if bool(x.get("causalClaim"))]
                ck(f"{sid}_{scope_key}_{option_key}_non_causal", not causal, {"badProducts": causal})
                attr = snap.get("driverAttribution") or {}
                ck(f"{sid}_{scope_key}_{option_key}_driver_non_causal", not bool(attr.get("causalClaim")))
    safety = payload.get("safety") or {}
    ck("production_safety", not any(bool(safety.get(k)) for k in (
        "productionDataMartWritten", "productionUiModified", "productionActivationEnabled", "platformMutationAllowed"
    )))
    failed = [x for x in checks if x["status"] == "FAIL"]
    return {"status": "PASS" if not failed else "FAIL", "failedCheckCount": len(failed), "checks": checks}


def build_ads_intelligence(
    *,
    ads_rows: Sequence[Mapping[str, Any]],
    ads_product_rows: Sequence[Mapping[str, Any]],
    shops: Sequence[Mapping[str, Any]],
    trusted_months: Sequence[str],
    trusted_fingerprints: Sequence[str],
    as_of_period: str,
    contract_path: str | Path,
    output_dir: str | Path,
    history_lineage: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    contract = load_contract(contract_path)
    expected = [s(shop.get("shop_id")) for shop in shops]
    allowed = set(expected)
    foreign = sorted({s(r.get("shop_id")) for r in list(ads_rows) + list(ads_product_rows) if s(r.get("shop_id")) not in allowed})
    if foreign:
        raise ValueError(f"foreign shop ids in Ads history: {foreign}")

    lineage = dict(history_lineage or {})
    shop_payloads = {}
    for shop in shops:
        sid = s(shop.get("shop_id")); sk = s(shop.get("shop_key"))
        srows = [dict(r) for r in ads_rows if s(r.get("shop_id")) == sid and s(r.get("data_date"))[:7] <= as_of_period]
        prows = [dict(r) for r in ads_product_rows if s(r.get("shop_id")) == sid and s(r.get("data_date"))[:7] <= as_of_period]
        periods = _build_scope_snapshots(
            shop_rows=srows, product_rows=prows,
            lifecycle=shop.get("history_lifecycle") or {}, contract=contract,
        )
        shop_payloads[sid] = {
            "scope": {"type": "shop", "shopId": sid},
            "shopKey": sk,
            "displayName": s(shop.get("display_name")),
            "sourceGrain": "DAILY",
            "compareAllowed": False,
            "timeScopeOrder": ["day", "week", "month", "year"],
            "historyLineage": dict((lineage.get("shops") or {}).get(sid) or {}),
            "periods": periods,
        }

    payload: Dict[str, Any] = {
        "meta": {
            "layer": s(contract.get("layer_name")),
            "contractVersion": s(contract.get("version")),
            "status": "PREPRODUCTION",
            "asOfPeriod": as_of_period,
            "trustedSemanticMonths": list(trusted_months),
            "trustedSemanticFingerprints": list(trusted_fingerprints),
            "historyLineageFingerprint": _sha(lineage) if lineage else "",
        },
        "scopePolicy": {
            "singleShopOnly": True,
            "compareAllowed": False,
            "canonicalSourceGrain": "DAILY",
            "allowedTimeScopes": ["day", "week", "month", "year"],
        },
        "shops": shop_payloads,
        "capabilities": {
            "adsDestinationV2": True,
            "adsDailyScopes": True,
            "adsPeriodComparison": True,
            "adsRoasDriverAttribution": True,
            "adsProductSignals": True,
        },
        "safety": {
            "productionDataMartWritten": False,
            "productionUiModified": False,
            "productionActivationEnabled": False,
            "platformMutationAllowed": False,
            "automaticAlertsEnabled": False,
            "automaticActionsEnabled": False,
            "causalClaimsEnabled": False,
        },
    }
    qa = validate_ads_intelligence(payload, expected, contract)
    if qa["status"] != "PASS":
        failed = [x["name"] for x in qa["checks"] if x["status"] == "FAIL"]
        raise ValueError(f"Ads Intelligence QA failed: {failed}")

    fingerprint = _sha({
        "contractVersion": contract.get("version"),
        "asOfPeriod": as_of_period,
        "trustedMonths": list(trusted_months),
        "trustedFingerprints": list(trusted_fingerprints),
        "lineage": lineage,
        "payload": payload,
    })
    payload["meta"]["adsIntelligenceFingerprint"] = fingerprint
    qa.update({
        "adsIntelligenceFingerprint": fingerprint,
        "asOfPeriod": as_of_period,
        "selectedShopIds": expected,
        "selectedShopCount": len(expected),
    })
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    _write_json(out / "ads_intelligence.json", payload)
    _write_json(out / "ads_intelligence_qa_report.json", qa)
    manifest = {
        "layer": s(contract.get("layer_name")),
        "contractVersion": s(contract.get("version")),
        "asOfPeriod": as_of_period,
        "adsIntelligenceFingerprint": fingerprint,
        "trustedSemanticMonths": list(trusted_months),
        "trustedSemanticFingerprints": list(trusted_fingerprints),
        "selectedShopIds": expected,
        "files": ["ads_intelligence.json", "ads_intelligence_qa_report.json"],
        "safety": payload["safety"],
    }
    _write_json(out / "ads_intelligence_manifest.json", manifest)
    return {
        "status": "PASS",
        "adsIntelligenceReady": True,
        "adsIntelligenceFingerprint": fingerprint,
        "asOfPeriod": as_of_period,
        "selectedShopCount": len(expected),
        "shopCoverage": {
            sid: {
                "trustedDateStart": (scope.get("periods") or {}).get("trustedDateStart", ""),
                "trustedDateEnd": (scope.get("periods") or {}).get("trustedDateEnd", ""),
                "yearReadyOptions": (((scope.get("periods") or {}).get("year") or {}).get("readyOptions") or []),
            }
            for sid, scope in shop_payloads.items()
        },
        "safety": payload["safety"],
    }
