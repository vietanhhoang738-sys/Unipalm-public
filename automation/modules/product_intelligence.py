"""Shop-scoped Product Intelligence V2 foundation.

Trusted Product history is semantic-only. Canonical QA-passed Semantic v2 is
preferred; historical gaps may be filled only by the deterministic Product
history semantic adapter built from durable Processed v2 QA-PASS partitions.

Product Performance is monthly-grain, so the destination exposes monthly-family
horizons only. Supporting daily Ads data is rolled into product-month facts and
may never upgrade Product to a synthetic day/week view.
"""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from itertools import permutations
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

from .product_ranking import build_priority, rank_signals


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


def load_contract(path: str | Path) -> Dict[str, Any]:
    data = _read_json(path)
    if s(data.get("layer_name")) != "multi_shop_product_intelligence_v1":
        raise ValueError("unexpected Product Intelligence layer")
    if s(data.get("status")) != "PREPRODUCTION":
        raise ValueError("Product Intelligence contract must remain PREPRODUCTION")
    source = data.get("source_policy") or {}
    sources = list(source.get("trusted_history_sources") or [])
    if not sources and s(source.get("trusted_history_source")):
        sources = [s(source.get("trusted_history_source"))]
    required_sources = {"PUBLISHED_SEMANTIC_QA_PASS"}
    if not required_sources.issubset(set(sources)):
        raise ValueError("Product history must include QA-passed canonical Semantic")
    if s(source.get("canonical_mart")) != "dm_product_monthly":
        raise ValueError("Product canonical mart must remain dm_product_monthly")
    if not bool(source.get("daily_or_weekly_product_scope_forbidden")):
        raise ValueError("Product day/week scope must remain forbidden")
    scope = data.get("scope_policy") or {}
    if not bool(scope.get("single_shop_only")) or bool(scope.get("cross_shop_compare_allowed")):
        raise ValueError("Product destination must remain single-shop and non-compare")
    intelligence = data.get("intelligence_policy") or {}
    if int(intelligence.get("minimum_complete_months_for_structural_signal") or 0) < 6:
        raise ValueError("Product structural intelligence requires at least six complete months")
    if s(intelligence.get("current_partial_month_role")) not in {"", "CORROBORATING_ONLY"}:
        raise ValueError("current Product partial month must remain corroborating-only")
    safety = data.get("safety") or {}
    if any(bool(safety.get(k)) for k in (
        "write_production_data_mart", "modify_production_ui", "publish_legacy_payload",
        "platform_mutation_allowed", "production_activation_enabled",
    )):
        raise ValueError("unsafe Product Intelligence contract")
    return data


ADDITIVE_FIELDS = (
    "placed_gmv", "placed_orders", "confirmed_gmv", "confirmed_orders",
    "product_views", "product_clicks", "product_visits", "product_page_views",
    "page_bounces", "add_to_cart_visits", "add_to_cart_units", "confirmed_units",
    "ads_impressions", "ads_clicks", "ads_conversions", "ads_units_sold",
    "ads_attributed_sales", "ads_spend",
)

INTEGER_FIELDS = {
    "placed_orders", "confirmed_orders", "product_views", "product_clicks",
    "product_visits", "product_page_views", "page_bounces", "add_to_cart_visits",
    "add_to_cart_units", "confirmed_units", "ads_impressions", "ads_clicks",
    "ads_conversions", "ads_units_sold",
}


def _month_add(month: str, delta: int) -> str:
    year, mon = map(int, month.split("-"))
    idx = year * 12 + (mon - 1) + delta
    return f"{idx // 12:04d}-{idx % 12 + 1:02d}"


def _month_range(start: str, end: str) -> List[str]:
    if not start or not end or start > end:
        return []
    out = []
    cur = start
    while cur <= end:
        out.append(cur)
        cur = _month_add(cur, 1)
    return out


def _last_n_months(as_of: str, count: int) -> List[str]:
    return [_month_add(as_of, -(count - 1 - idx)) for idx in range(count)]


def _latest_meta(rows: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
    return max(rows, key=lambda r: (s(r.get("data_month")), s(r.get("product_id"))))


def _aggregate_product_rows(rows: Sequence[Mapping[str, Any]], months: Sequence[str]) -> List[Dict[str, Any]]:
    month_set = set(months)
    selected = [r for r in rows if s(r.get("data_month")) in month_set]
    grouped: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    for row in selected:
        pid = s(row.get("product_id"))
        if pid:
            grouped[pid].append(row)

    out = []
    for pid, prows in grouped.items():
        latest = _latest_meta(prows)
        totals = defaultdict(float)
        for row in prows:
            for field in ADDITIVE_FIELDS:
                totals[field] += n(row.get(field))
        rec: Dict[str, Any] = {
            "productId": pid,
            "productName": s(latest.get("product_name")),
            "productStatus": s(latest.get("product_status")),
            "productSkuObserved": s(latest.get("product_sku_observed")),
            "resolvedParentSku": s(latest.get("resolved_parent_sku")),
            "canonicalFamilyKey": s(latest.get("canonical_family_key")),
            "catalogStatus": s(latest.get("catalog_status")),
            "catalogJoinStatus": s(latest.get("catalog_join_status")),
            "currentListingPresent": bool(latest.get("current_listing_present")),
            "latestMonth": s(latest.get("data_month")),
            "monthsObserved": sorted({s(x.get("data_month")) for x in prows}),
            "latestMonthContext": {
                "confirmedBuyers": i(latest.get("confirmed_buyers")),
                "repeatOrderRate": n(latest.get("repeat_order_rate")),
                "avgDaysToRepeat": n(latest.get("avg_days_to_repeat")),
            },
        }
        for field in ADDITIVE_FIELDS:
            value = totals[field]
            rec[field] = i(value) if field in INTEGER_FIELDS else value
        rec.update({
            "placedAov": ratio(totals["placed_gmv"], totals["placed_orders"]),
            "confirmedAov": ratio(totals["confirmed_gmv"], totals["confirmed_orders"]),
            "ctr": ratio(totals["product_clicks"], totals["product_views"]),
            "bounceRate": ratio(totals["page_bounces"], totals["product_visits"]),
            "atcRate": ratio(totals["add_to_cart_visits"], totals["product_visits"]),
            "adsCtr": ratio(totals["ads_clicks"], totals["ads_impressions"]),
            "adsCvr": ratio(totals["ads_conversions"], totals["ads_clicks"]),
            "roas": ratio(totals["ads_attributed_sales"], totals["ads_spend"]),
        })
        out.append(rec)
    return sorted(out, key=lambda r: (-n(r.get("placed_gmv")), s(r.get("productId"))))


def _summary(products: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    totals = defaultdict(float)
    for row in products:
        for field in ADDITIVE_FIELDS:
            totals[field] += n(row.get(field))
    placed = totals["placed_gmv"]
    sorted_products = sorted(products, key=lambda x: -n(x.get("placed_gmv")))
    def share(k: int) -> float:
        return sum(n(x.get("placed_gmv")) for x in sorted_products[:k]) / placed if placed else 0.0
    return {
        "productCount": len(products),
        "placedGmv": placed,
        "placedOrders": i(totals["placed_orders"]),
        "placedAov": ratio(placed, totals["placed_orders"]),
        "confirmedGmv": totals["confirmed_gmv"],
        "confirmedOrders": i(totals["confirmed_orders"]),
        "productViews": i(totals["product_views"]),
        "productClicks": i(totals["product_clicks"]),
        "ctr": ratio(totals["product_clicks"], totals["product_views"]),
        "productVisits": i(totals["product_visits"]),
        "addToCartVisits": i(totals["add_to_cart_visits"]),
        "atcRate": ratio(totals["add_to_cart_visits"], totals["product_visits"]),
        "adsSpend": totals["ads_spend"],
        "adsAttributedSales": totals["ads_attributed_sales"],
        "roas": ratio(totals["ads_attributed_sales"], totals["ads_spend"]),
        "top1GmvShare": share(1),
        "top3GmvShare": share(3),
        "top5GmvShare": share(5),
    }


def _horizon_status(*, key: str, as_of: str, observed_months: Sequence[str], lifecycle: Mapping[str, Any]) -> Dict[str, Any]:
    observed = set(observed_months)
    if key == "oneMonth":
        required = [as_of]
    elif key == "threeMonths":
        required = _last_n_months(as_of, 3)
    elif key == "sixMonths":
        required = _last_n_months(as_of, 6)
    elif key == "year":
        year_start = f"{as_of[:4]}-01"
        if s(lifecycle.get("origin")) == "SHOP_LAUNCH" and s(lifecycle.get("start_policy")) == "FIRST_TRUSTED_SEMANTIC_DATE":
            candidates = sorted(m for m in observed if m[:4] == as_of[:4] and m <= as_of)
            year_start = candidates[0] if candidates else year_start
        required = _month_range(year_start, as_of)
    else:
        raise ValueError(f"unknown Product horizon {key}")
    missing = [m for m in required if m not in observed]
    return {
        "status": "READY" if required and not missing else "INSUFFICIENT_HISTORY",
        "requiredMonths": required,
        "observedMonths": [m for m in required if m in observed],
        "missingMonths": missing,
        "coverageStart": required[0] if required else "",
        "coverageEnd": required[-1] if required else "",
        "lifecycleAware": key == "year" and s(lifecycle.get("origin")) == "SHOP_LAUNCH",
    }


def _month_product_index(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Dict[str, Mapping[str, Any]]]:
    out: Dict[str, Dict[str, Mapping[str, Any]]] = defaultdict(dict)
    for row in rows:
        month = s(row.get("data_month")); pid = s(row.get("product_id"))
        if not month or not pid:
            continue
        if pid in out[month]:
            raise ValueError(f"duplicate Product monthly grain {month}/{pid}")
        out[month][pid] = row
    return out


def _gmv_identity_attribution(prev_rows: Sequence[Mapping[str, Any]], recent_rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    def factors(rows: Sequence[Mapping[str, Any]]) -> Dict[str, float]:
        clicks = sum(n(r.get("product_clicks")) for r in rows)
        orders = sum(n(r.get("placed_orders")) for r in rows)
        gmv = sum(n(r.get("placed_gmv")) for r in rows)
        return {
            "productClicks": clicks,
            "cvr": ratio(orders, clicks),
            "aov": ratio(gmv, orders),
        }

    prev = factors(prev_rows); cur = factors(recent_rows)
    keys = ["productClicks", "cvr", "aov"]
    if any(prev[k] <= 0 or cur[k] <= 0 for k in keys):
        return {
            "status": "NOT_ATTRIBUTED",
            "reason": "NON_POSITIVE_IDENTITY_FACTOR",
            "identity": "GMV = Product Clicks × CVR × AOV",
            "causalClaim": False,
            "driverContributions": [],
        }

    def product(values: Mapping[str, float]) -> float:
        out = 1.0
        for key in keys:
            out *= n(values.get(key))
        return out

    contributions = {k: 0.0 for k in keys}
    perms = list(permutations(keys))
    for perm in perms:
        state = dict(prev)
        before = product(state)
        for key in perm:
            state[key] = cur[key]
            after = product(state)
            contributions[key] += after - before
            before = after
    for key in keys:
        contributions[key] /= len(perms)

    modeled_gap = product(cur) - product(prev)
    rows = [{
        "driverMetric": key,
        "contributionValue": contributions[key],
        "contributionShareOfModeledGap": contributions[key] / modeled_gap if modeled_gap else None,
        "driverPrevious": prev[key],
        "driverRecent": cur[key],
        "driverDirection": "UP" if cur[key] > prev[key] else ("DOWN" if cur[key] < prev[key] else "FLAT"),
        "relationType": "IDENTITY_CONTRIBUTION",
        "causalClaim": False,
    } for key in keys]
    rows.sort(key=lambda x: abs(n(x.get("contributionValue"))), reverse=True)
    return {
        "status": "ATTRIBUTED",
        "identity": "GMV = Product Clicks × CVR × AOV",
        "method": "EXACT_SHAPLEY_ON_BUSINESS_IDENTITY",
        "previousModelValue": product(prev),
        "recentModelValue": product(cur),
        "modeledDifference": modeled_gap,
        "topDriverMetric": s((rows[0] if rows else {}).get("driverMetric")),
        "driverContributions": rows,
        "causalClaim": False,
    }


def _structural_signals(rows: Sequence[Mapping[str, Any]], as_of: str, lifecycle: Mapping[str, Any]) -> Dict[str, Any]:
    # The as-of month may be MTD. Structural comparison therefore uses the six
    # completed months immediately before it. The current month is corroborating
    # context only and never participates in score/priority.
    baseline_end = _month_add(as_of, -1)
    months = _last_n_months(baseline_end, 6)
    idx = _month_product_index(rows)
    observed = sorted(idx)
    missing = [m for m in months if m not in idx]

    if missing:
        if s(lifecycle.get("origin")) == "SHOP_LAUNCH" and observed:
            launch_month = observed[0]
            prelaunch = [m for m in months if m < launch_month]
            if prelaunch:
                return {
                    "status": "INSUFFICIENT_OPERATING_HISTORY",
                    "reason": "SHOP_NOT_OPERATING_FOR_FULL_SIX_COMPLETE_MONTH_BASELINE",
                    "baselineEndMonth": baseline_end,
                    "requiredMonths": months,
                    "missingMonths": missing,
                    "preLaunchMonths": prelaunch,
                    "currentPartialMonth": as_of,
                    "currentPartialMonthRole": "CORROBORATING_ONLY_NOT_SCORED",
                    "signals": [],
                    "ranking": {"problems": [], "opportunities": [], "all": []},
                }
        return {
            "status": "INSUFFICIENT_HISTORY",
            "reason": "SIX_COMPLETE_MONTH_BASELINE_NOT_AVAILABLE",
            "baselineEndMonth": baseline_end,
            "requiredMonths": months,
            "missingMonths": missing,
            "currentPartialMonth": as_of,
            "currentPartialMonthRole": "CORROBORATING_ONLY_NOT_SCORED",
            "signals": [],
            "ranking": {"problems": [], "opportunities": [], "all": []},
        }

    previous = months[:3]; recent = months[3:]
    pids = sorted(set().union(*(set(idx[m]) for m in months)))
    recent_shop_gmv = sum(n(row.get("placed_gmv")) for m in recent for row in idx[m].values())
    current_idx = idx.get(as_of, {})
    signals = []
    for pid in pids:
        prev_rows = [idx[m].get(pid, {}) for m in previous]
        rec_rows = [idx[m].get(pid, {}) for m in recent]
        prev_gmv = sum(n(r.get("placed_gmv")) for r in prev_rows)
        rec_gmv = sum(n(r.get("placed_gmv")) for r in rec_rows)
        if prev_gmv <= 0 and rec_gmv <= 0:
            continue
        delta = (rec_gmv / prev_gmv - 1.0) if prev_gmv > 0 else 1.0
        if abs(delta) < 0.15:
            continue
        direction = 1 if delta > 0 else -1
        prev_avg = prev_gmv / 3.0
        persistence = sum(
            1 for r in rec_rows
            if ((n(r.get("placed_gmv")) - prev_avg) * direction) > 0
        )
        latest_meta = next((r for r in reversed(rec_rows) if r), None) or next((r for r in reversed(prev_rows) if r), {})
        observed_count = sum(1 for r in prev_rows + rec_rows if r)
        confidence = min(0.95, 0.65 + 0.05 * observed_count)
        attribution = _gmv_identity_attribution(prev_rows, rec_rows)
        priority = build_priority(
            recent_gmv=rec_gmv,
            previous_gmv=prev_gmv,
            recent_days=3,
            previous_days=3,
            recent_shop_gmv=recent_shop_gmv,
            gmv_delta=delta,
            persistence_months=persistence,
            pace_delta=None,
            pace_support=0.0,
            confidence=confidence,
        )
        current_row = current_idx.get(pid, {})
        signals.append({
            "type": "Cơ hội" if delta > 0 else "Vấn đề",
            "productId": pid,
            "productName": s(latest_meta.get("product_name")),
            "resolvedParentSku": s(latest_meta.get("resolved_parent_sku")),
            "recent3mGmv": rec_gmv,
            "prior3mGmv": prev_gmv,
            "gmvDelta": delta,
            "persistenceMonths": persistence,
            "confidence": confidence,
            "historyMonths": months,
            "previousWindow": previous,
            "recentWindow": recent,
            "driverAttribution": attribution,
            "currentMtdEvidence": {
                "month": as_of,
                "available": bool(current_row),
                "placedGmv": n(current_row.get("placed_gmv")),
                "role": "CORROBORATING_ONLY_NOT_SCORED",
            },
            "causalClaim": False,
            **priority,
        })
    ranking = rank_signals(signals)
    return {
        "status": "READY",
        "method": "RECENT_3_COMPLETE_MONTHS_VS_PRIOR_3_COMPLETE_MONTHS",
        "baselineEndMonth": baseline_end,
        "requiredMonths": months,
        "previousWindow": previous,
        "recentWindow": recent,
        "missingMonths": [],
        "currentPartialMonth": as_of,
        "currentPartialMonthRole": "CORROBORATING_ONLY_NOT_SCORED",
        "signalCount": len(signals),
        "problemCount": len(ranking["problems"]),
        "opportunityCount": len(ranking["opportunities"]),
        "signals": ranking["ranked"],
        "ranking": {
            "problems": ranking["problems"],
            "opportunities": ranking["opportunities"],
            "all": ranking["ranked"],
        },
    }


def validate_product_intelligence(payload: Mapping[str, Any], expected_shop_ids: Sequence[str], contract: Mapping[str, Any]) -> Dict[str, Any]:
    checks = []
    def ck(name: str, ok: bool, detail: Any = None) -> None:
        checks.append({"name": name, "status": "PASS" if ok else "FAIL", "detail": detail or {}})

    shops = payload.get("shops") or {}
    ck("all_expected_shops_present", set(shops) == set(expected_shop_ids), {"shops": sorted(shops)})
    horizon_order = list((contract.get("horizons") or {}).get("order") or [])
    ck("monthly_family_horizons_only", horizon_order == ["oneMonth", "threeMonths", "sixMonths", "year"], {"order": horizon_order})
    for sid, scope in shops.items():
        ck(f"{sid}_single_shop_scope", s((scope.get("scope") or {}).get("type")) == "shop" and s((scope.get("scope") or {}).get("shopId")) == sid)
        horizons = scope.get("horizons") or {}
        ck(f"{sid}_all_horizons_explicit", set(horizons) == set(horizon_order), {"keys": sorted(horizons)})
        for key, horizon in horizons.items():
            status = s(horizon.get("status"))
            ck(f"{sid}_{key}_valid_status", status in {"READY", "INSUFFICIENT_HISTORY"}, {"status": status})
            if status == "INSUFFICIENT_HISTORY":
                ck(f"{sid}_{key}_unavailable_has_reason", bool(horizon.get("missingMonths")))
                ck(f"{sid}_{key}_unavailable_has_no_products", not list(horizon.get("products") or []))
            if status == "READY":
                keys = set(); duplicate = []
                for product in horizon.get("products") or []:
                    pid = s(product.get("productId"))
                    if pid in keys:
                        duplicate.append(pid)
                    keys.add(pid)
                ck(f"{sid}_{key}_product_identity_unique", not duplicate, {"duplicates": duplicate[:10]})
                sm = horizon.get("summary") or {}
                ck(f"{sid}_{key}_aov_recomputed", abs(n(sm.get("placedAov")) - ratio(sm.get("placedGmv"), sm.get("placedOrders"))) <= 1e-9)
                ck(f"{sid}_{key}_roas_recomputed", abs(n(sm.get("roas")) - ratio(sm.get("adsAttributedSales"), sm.get("adsSpend"))) <= 1e-9)
        structural = scope.get("structuralIntelligence") or {}
        ck(
            f"{sid}_structural_status_valid",
            s(structural.get("status")) in {"READY", "INSUFFICIENT_HISTORY", "INSUFFICIENT_OPERATING_HISTORY"},
            {"status": structural.get("status")},
        )
        if s(structural.get("status")) == "READY":
            ck(f"{sid}_structural_excludes_current_mtd", s(structural.get("baselineEndMonth")) == _month_add(s((payload.get("meta") or {}).get("asOfPeriod")), -1))
            causal = [x.get("productId") for x in structural.get("signals") or [] if bool(x.get("causalClaim"))]
            ck(f"{sid}_structural_non_causal", not causal, {"badProducts": causal})
    safety = payload.get("safety") or {}
    ck("production_safety", not any(bool(safety.get(k)) for k in (
        "productionDataMartWritten", "productionUiModified", "productionActivationEnabled", "platformMutationAllowed"
    )))
    failed = [x for x in checks if x["status"] == "FAIL"]
    return {"status": "PASS" if not failed else "FAIL", "failedCheckCount": len(failed), "checks": checks}


def build_product_intelligence(
    *,
    product_rows: Sequence[Mapping[str, Any]],
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
    rows = [dict(r) for r in product_rows if s(r.get("shop_id")) in allowed and s(r.get("data_month")) <= as_of_period]
    foreign = sorted({s(r.get("shop_id")) for r in product_rows if s(r.get("shop_id")) not in allowed})
    if foreign:
        raise ValueError(f"foreign shop ids in Product history: {foreign}")

    lineage = dict(history_lineage or {})
    lineage_fp = _sha(lineage) if lineage else ""
    shop_payloads: Dict[str, Any] = {}
    horizon_order = list((contract.get("horizons") or {}).get("order") or [])
    for shop in shops:
        sid = s(shop.get("shop_id")); sk = s(shop.get("shop_key"))
        srows = [r for r in rows if s(r.get("shop_id")) == sid]
        observed_months = sorted({s(r.get("data_month")) for r in srows})
        horizons = {}
        for key in horizon_order:
            state = _horizon_status(
                key=key,
                as_of=as_of_period,
                observed_months=observed_months,
                lifecycle=shop.get("history_lifecycle") or {},
            )
            if state["status"] == "READY":
                products = _aggregate_product_rows(srows, state["requiredMonths"])
                horizons[key] = {
                    **state,
                    "products": products,
                    "summary": _summary(products),
                }
            else:
                horizons[key] = {**state, "products": [], "summary": {}}
        shop_payloads[sid] = {
            "scope": {"type": "shop", "shopId": sid},
            "shopKey": sk,
            "displayName": s(shop.get("display_name")),
            "sourceGrain": "MONTHLY",
            "timeScopeOrder": horizon_order,
            "compareAllowed": False,
            "trustedProductMonths": observed_months,
            "historyLineage": dict((lineage.get("shops") or {}).get(sid) or {}),
            "horizons": horizons,
            "structuralIntelligence": _structural_signals(
                srows, as_of_period, shop.get("history_lifecycle") or {}
            ),
        }

    payload: Dict[str, Any] = {
        "meta": {
            "layer": s(contract.get("layer_name")),
            "contractVersion": s(contract.get("version")),
            "status": "PREPRODUCTION",
            "asOfPeriod": as_of_period,
            "trustedSemanticMonths": list(trusted_months),
            "trustedSemanticFingerprints": list(trusted_fingerprints),
            "productHistoryLineageFingerprint": lineage_fp,
        },
        "scopePolicy": {
            "singleShopOnly": True,
            "compareAllowed": False,
            "canonicalSourceGrain": "MONTHLY",
            "allowedTimeScopes": horizon_order,
            "dayWeekForbidden": True,
        },
        "shops": shop_payloads,
        "capabilities": {
            "productDestinationV2": True,
            "productMultiMonthScopes": True,
            "productHistoricalSemanticBackfill": bool(lineage),
            "productStructuralIntelligence": any(
                s((scope.get("structuralIntelligence") or {}).get("status")) == "READY"
                for scope in shop_payloads.values()
            ),
            "productStructuralDriverAttribution": any(
                any(s((sig.get("driverAttribution") or {}).get("status")) == "ATTRIBUTED" for sig in (scope.get("structuralIntelligence") or {}).get("signals") or [])
                for scope in shop_payloads.values()
            ),
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
    qa = validate_product_intelligence(payload, expected, contract)
    if qa["status"] != "PASS":
        failed = [x["name"] for x in qa["checks"] if x["status"] == "FAIL"]
        raise ValueError(f"Product Intelligence QA failed: {failed}")

    fingerprint = _sha({
        "contractVersion": contract.get("version"),
        "asOfPeriod": as_of_period,
        "trustedMonths": list(trusted_months),
        "trustedFingerprints": list(trusted_fingerprints),
        "historyLineageFingerprint": lineage_fp,
        "payload": payload,
    })
    payload["meta"]["productIntelligenceFingerprint"] = fingerprint
    qa.update({
        "productIntelligenceFingerprint": fingerprint,
        "productHistoryLineageFingerprint": lineage_fp,
        "asOfPeriod": as_of_period,
        "selectedShopIds": expected,
        "selectedShopCount": len(expected),
    })
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    _write_json(out / "product_intelligence.json", payload)
    _write_json(out / "product_intelligence_qa_report.json", qa)
    manifest = {
        "layer": s(contract.get("layer_name")),
        "contractVersion": s(contract.get("version")),
        "asOfPeriod": as_of_period,
        "productIntelligenceFingerprint": fingerprint,
        "productHistoryLineageFingerprint": lineage_fp,
        "trustedSemanticMonths": list(trusted_months),
        "trustedSemanticFingerprints": list(trusted_fingerprints),
        "selectedShopIds": expected,
        "files": ["product_intelligence.json", "product_intelligence_qa_report.json"],
        "safety": payload["safety"],
    }
    _write_json(out / "product_intelligence_manifest.json", manifest)
    return {
        "status": "PASS",
        "productIntelligenceReady": True,
        "productIntelligenceFingerprint": fingerprint,
        "productHistoryLineageFingerprint": lineage_fp,
        "asOfPeriod": as_of_period,
        "selectedShopCount": len(expected),
        "shopHorizonStatus": {
            sid: {k: v["status"] for k, v in scope["horizons"].items()}
            for sid, scope in shop_payloads.items()
        },
        "structuralIntelligenceStatus": {
            sid: s((scope.get("structuralIntelligence") or {}).get("status"))
            for sid, scope in shop_payloads.items()
        },
        "safety": payload["safety"],
    }
