"""Pre-production multi-shop UI payload adapter sourced only from Semantic v2."""
from __future__ import annotations

import hashlib
import itertools
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple


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


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    out = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError(f"{path}: line {line_no} is not an object")
            out.append(row)
    return out


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _sha256_json(value: Any) -> str:
    raw = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _load_contract(path: str | Path) -> Dict[str, Any]:
    data = _read_json(Path(path))
    if s(data.get("layer_name")) != "multi_shop_ui_payload_v1":
        raise ValueError("unexpected UI payload layer_name")
    if s(data.get("status")) != "PREPRODUCTION":
        raise ValueError("UI payload contract must remain PREPRODUCTION")
    safety = data.get("safety") or {}
    if any(bool(safety.get(x)) for x in (
        "write_production_data_mart", "modify_production_ui", "publish_legacy_payload"
    )):
        raise ValueError("unsafe UI payload contract")
    portfolio_semantics = (data.get("scope_semantics") or {}).get("portfolio") or {}
    if s(portfolio_semantics.get("alignment")) != "ALL_ENABLED_SHOPS_COMMON_RELIABLE_INTERSECTION":
        raise ValueError("portfolio semantic alignment contract is missing")
    if s(portfolio_semantics.get("daily_shop_requirement")) != "ALL_ENABLED_SHOPS_PRESENT_EACH_DAY":
        raise ValueError("portfolio daily shop requirement contract is missing")
    if s(portfolio_semantics.get("comparison_window_policy")) != "REQUIRE_COMPLETE_CURRENT_AND_PREVIOUS_WINDOWS":
        raise ValueError("portfolio comparison window policy is missing")
    if not list(portfolio_semantics.get("forbidden_total_fields") or []):
        raise ValueError("portfolio non-additive metric policy is missing")
    shop_semantics = (data.get("scope_semantics") or {}).get("shop") or {}
    if s(shop_semantics.get("alignment")) != "SHOP_COMMON_RELIABLE_WINDOW":
        raise ValueError("shop semantic alignment contract is missing")
    if s(shop_semantics.get("multi_day_unique_policy")) != "DAILY_ONLY_DO_NOT_SUM":
        raise ValueError("shop daily-unique policy is missing")
    if s(shop_semantics.get("headline_unique_policy")) != "OMIT":
        raise ValueError("shop headline unique policy is missing")
    if s(shop_semantics.get("comparison_window_policy")) != "REQUIRE_COMPLETE_CURRENT_AND_PREVIOUS_WINDOWS":
        raise ValueError("shop comparison window policy is missing")
    product_semantics = shop_semantics.get("product") or {}
    if s(product_semantics.get("alignment")) != "SOURCE_MTD_SHOP_SCOPE_ONLY":
        raise ValueError("shop product semantic alignment contract is missing")
    if bool(product_semantics.get("day_7d_derivation")):
        raise ValueError("shop product day/7d derivation must remain disabled")
    shadow=data.get("production_cutover_shadow_mode_v1") or {}
    if shadow:
        if s(shadow.get("mode"))!="PREPRODUCTION_OBSERVE_ONLY":
            raise ValueError("UI shadow-mode contract must remain observe-only")
        if not bool(shadow.get("cutover_requires_explicit_human_approval")):
            raise ValueError("UI shadow-mode contract requires human cutover approval")
        if any(bool(shadow.get(k)) for k in (
            "automatic_cutover_enabled","production_activation_enabled",
            "production_writes_enabled","platform_mutation_allowed",
        )):
            raise ValueError("UI shadow-mode contract is not fail-closed")
    return data


def _require(path: Path) -> Path:
    if not path.exists():
        raise FileNotFoundError(path)
    return path


def _date(value: Any) -> str:
    return s(value)[:10]


ADDITIVE_FIELDS = (
    "placed_gmv", "placed_orders", "product_clicks",
    "confirmed_gmv", "confirmed_orders", "paid_gmv", "paid_orders",
    "cancelled_orders", "cancelled_sales",
    "returned_refunded_orders", "returned_refunded_sales",
    "net_sales_after_cancel",
    "ads_impressions", "ads_clicks", "ads_conversions",
    "ads_attributed_sales", "ads_spend",
    "fixed_fee", "service_fee", "transaction_fee", "order_fees",
)

INTEGER_FIELDS = {
    "placed_orders", "product_clicks", "confirmed_orders", "paid_orders",
    "cancelled_orders", "returned_refunded_orders",
    "ads_impressions", "ads_clicks", "ads_conversions",
}


def _headline(rows: Sequence[Mapping[str, Any]], start: str, end: str) -> Dict[str, Any]:
    selected = [r for r in rows if start <= _date(r.get("data_date")) <= end]
    totals = defaultdict(float)
    for row in selected:
        for field in ADDITIVE_FIELDS:
            totals[field] += n(row.get(field))

    out: Dict[str, Any] = {
        "windowStart": start,
        "windowEnd": end,
        "daysCovered": len({_date(r.get("data_date")) for r in selected}),
    }
    mapping = {
        "placed_gmv": "placedGmv",
        "placed_orders": "placedOrders",
        "product_clicks": "productClicks",
        "confirmed_gmv": "confirmedGmv",
        "confirmed_orders": "confirmedOrders",
        "paid_gmv": "paidGmv",
        "paid_orders": "paidOrders",
        "cancelled_orders": "cancelledOrders",
        "cancelled_sales": "cancelledSales",
        "returned_refunded_orders": "returnedRefundedOrders",
        "returned_refunded_sales": "returnedRefundedSales",
        "net_sales_after_cancel": "netSalesAfterCancel",
        "ads_impressions": "adsImpressions",
        "ads_clicks": "adsClicks",
        "ads_conversions": "adsConversions",
        "ads_attributed_sales": "adsAttributedSales",
        "ads_spend": "adsSpend",
        "fixed_fee": "fixedFee",
        "service_fee": "serviceFee",
        "transaction_fee": "transactionFee",
        "order_fees": "orderFees",
    }
    for src, target in mapping.items():
        out[target] = i(totals[src]) if src in INTEGER_FIELDS else totals[src]

    out.update({
        "placedAov": ratio(totals["placed_gmv"], totals["placed_orders"]),
        "placedCvr": ratio(totals["placed_orders"], totals["product_clicks"]),
        "confirmedAov": ratio(totals["confirmed_gmv"], totals["confirmed_orders"]),
        "adsCtr": ratio(totals["ads_clicks"], totals["ads_impressions"]),
        "adsCvr": ratio(totals["ads_conversions"], totals["ads_clicks"]),
        "roas": ratio(totals["ads_attributed_sales"], totals["ads_spend"]),
        "cancelledSalesRate": ratio(totals["cancelled_sales"], totals["placed_gmv"]),
        "returnedRefundedSalesRate": ratio(
            totals["returned_refunded_sales"], totals["placed_gmv"]
        ),
        "orderFeeRatio": ratio(totals["order_fees"], totals["net_sales_after_cancel"]),
        "adsSpendToNetSales": ratio(totals["ads_spend"], totals["net_sales_after_cancel"]),
        "adsAttributedShareOfPlacedGmv": ratio(
            totals["ads_attributed_sales"], totals["placed_gmv"]
        ),
        "totalPlatformCostRatio": ratio(
            totals["order_fees"] + totals["ads_spend"],
            totals["net_sales_after_cancel"],
        ),
    })
    return out


def _shop_daily_rows(
    rows: Sequence[Mapping[str, Any]], start: str, end: str
) -> List[Dict[str, Any]]:
    out = []
    for r in rows:
        d = _date(r.get("data_date"))
        if not (start <= d <= end):
            continue
        out.append({
            "date": d,
            "placedGmv": n(r.get("placed_gmv")),
            "placedOrders": i(r.get("placed_orders")),
            "productClicks": i(r.get("product_clicks")),
            "placedAov": ratio(r.get("placed_gmv"), r.get("placed_orders")),
            "placedCvr": ratio(r.get("placed_orders"), r.get("product_clicks")),
            "visits": i(r.get("visits")),
            "buyers": i(r.get("buyers")),
            "newBuyers": i(r.get("new_buyers")),
            "existingBuyers": i(r.get("existing_buyers")),
            "potentialBuyers": i(r.get("potential_buyers")),
            "adsSpend": n(r.get("ads_spend")),
            "adsAttributedSales": n(r.get("ads_attributed_sales")),
            "roas": ratio(r.get("ads_attributed_sales"), r.get("ads_spend")),
            "cancelledSales": n(r.get("cancelled_sales")),
            "netSalesAfterCancel": n(r.get("net_sales_after_cancel")),
            "orderFees": n(r.get("order_fees")),
            "totalPlatformCostRatio": ratio(
                n(r.get("order_fees")) + n(r.get("ads_spend")),
                r.get("net_sales_after_cancel"),
            ),
        })
    return sorted(out, key=lambda x: x["date"])


def _portfolio_daily(
    shop_daily: Mapping[str, Sequence[Mapping[str, Any]]],
    start: str,
    end: str,
) -> List[Dict[str, Any]]:
    by_date = defaultdict(list)
    for rows in shop_daily.values():
        for r in rows:
            d = _date(r.get("data_date"))
            if start <= d <= end:
                by_date[d].append(r)

    expected_shop_count = len(shop_daily)
    out = []
    for d in sorted(by_date):
        rows = by_date[d]
        if len(rows) != expected_shop_count:
            raise ValueError(
                f"portfolio day {d}: expected {expected_shop_count} shops, got {len(rows)}"
            )
        h = _headline(rows, d, d)
        out.append({
            "date": d,
            "shopCountIncluded": expected_shop_count,
            "placedGmv": h["placedGmv"],
            "placedOrders": h["placedOrders"],
            "productClicks": h["productClicks"],
            "placedAov": h["placedAov"],
            "placedCvr": h["placedCvr"],
            "adsSpend": h["adsSpend"],
            "adsAttributedSales": h["adsAttributedSales"],
            "roas": h["roas"],
            "cancelledSales": h["cancelledSales"],
            "netSalesAfterCancel": h["netSalesAfterCancel"],
            "orderFees": h["orderFees"],
            "totalPlatformCostRatio": h["totalPlatformCostRatio"],
        })
    return out


def _traffic_window(
    rows: Sequence[Mapping[str, Any]], start: str, end: str
) -> List[Dict[str, Any]]:
    agg = defaultdict(lambda: defaultdict(float))
    for r in rows:
        if s(r.get("order_stage")) != "placed":
            continue
        d = _date(r.get("data_date"))
        if not (start <= d <= end):
            continue
        key = (s(r.get("channel_group")), s(r.get("traffic_source")))
        a = agg[key]
        for field in (
            "sales", "impressions", "clicks", "attributed_orders", "attributed_units"
        ):
            a[field] += n(r.get(field))

    group_totals = {}
    for (group, source), a in agg.items():
        if source == group:
            group_totals[group] = a["sales"]

    out = []
    for (group, source), a in sorted(agg.items()):
        out.append({
            "channelGroup": group,
            "trafficSource": source,
            "rowType": "GROUP_TOTAL" if source == group else "SOURCE",
            "sales": a["sales"],
            "salesShareOfGroup": ratio(a["sales"], group_totals.get(group, 0.0)),
            "impressions": i(a["impressions"]),
            "clicks": i(a["clicks"]),
            "attributedOrders": a["attributed_orders"],
            "attributedUnits": a["attributed_units"],
            "ctr": ratio(a["clicks"], a["impressions"]),
            "conversionRate": ratio(a["attributed_orders"], a["clicks"]),
            "salesPerOrder": ratio(a["sales"], a["attributed_orders"]),
        })
    return out


def _product_rows(rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for r in rows:
        out.append({
            "productId": s(r.get("product_id")),
            "productName": s(r.get("product_name")),
            "productStatus": s(r.get("product_status")),
            "productSkuObserved": s(r.get("product_sku_observed")),
            "resolvedParentSku": s(r.get("resolved_parent_sku")),
            "catalogJoinStatus": s(r.get("catalog_join_status")),
            "catalogStatus": s(r.get("catalog_status")),
            "currentListingPresent": bool(r.get("current_listing_present")),
            "placedGmv": n(r.get("placed_gmv")),
            "placedOrders": i(r.get("placed_orders")),
            "confirmedGmv": n(r.get("confirmed_gmv")),
            "confirmedOrders": i(r.get("confirmed_orders")),
            "productViews": i(r.get("product_views")),
            "productClicks": i(r.get("product_clicks")),
            "ctr": n(r.get("ctr")),
            "productVisits": i(r.get("product_visits")),
            "bounceRate": n(r.get("bounce_rate")),
            "addToCartVisits": i(r.get("add_to_cart_visits")),
            "atcRate": n(r.get("atc_rate")),
            "adsSpend": n(r.get("ads_spend")),
            "adsAttributedSales": n(r.get("ads_attributed_sales")),
            "roas": n(r.get("roas")),
        })
    return sorted(out, key=lambda x: (-x["placedGmv"], x["productId"]))



def _shift_date(date_text: str, days: int) -> str:
    import datetime as dt
    return (dt.date.fromisoformat(date_text) + dt.timedelta(days=days)).isoformat()


def _compare_windows(start: str, end: str) -> Dict[str, Dict[str, str]]:
    last7_start=max(start,_shift_date(end,-6))
    return {
        "latestDay":{
            "key":"latestDay","label":"Ngày gần nhất",
            "windowStart":end,"windowEnd":end,
        },
        "last7":{
            "key":"last7","label":"7 ngày",
            "windowStart":last7_start,"windowEnd":end,
        },
        "mtd":{
            "key":"mtd","label":"Tháng này",
            "windowStart":start,"windowEnd":end,
        },
    }


def _traffic_group_window(
    rows: Sequence[Mapping[str, Any]], start: str, end: str
) -> List[Dict[str, Any]]:
    window=_traffic_window(rows,start,end)
    groups=[dict(x) for x in window if s(x.get("rowType"))=="GROUP_TOTAL"]
    total_sales=sum(n(x.get("sales")) for x in groups)
    for row in groups:
        row["salesShareOfTraffic"]=ratio(row.get("sales"),total_sales)
    return sorted(groups,key=lambda x:(-n(x.get("sales")),s(x.get("channelGroup"))))


def _ads_product_window(
    rows: Sequence[Mapping[str, Any]], start: str, end: str
) -> Dict[str, Any]:
    agg=defaultdict(lambda:defaultdict(float))
    meta={}
    for r in rows:
        d=_date(r.get("data_date"))
        if not (start<=d<=end):
            continue
        pid=s(r.get("product_id"))
        if not pid:
            continue
        meta[pid]=r
        for f in (
            "impressions","clicks","conversions","units_sold",
            "attributed_sales","ad_spend",
        ):
            agg[pid][f]+=n(r.get(f))
    products=[]
    total_sales=sum(a["attributed_sales"] for a in agg.values())
    total_spend=sum(a["ad_spend"] for a in agg.values())
    for pid,a in agg.items():
        m=meta[pid]
        products.append({
            "productId":pid,
            "productName":s(m.get("product_name")) or pid,
            "resolvedParentSku":s(m.get("resolved_parent_sku")),
            "adsAttributedSales":a["attributed_sales"],
            "adsSpend":a["ad_spend"],
            "adsSalesShare":ratio(a["attributed_sales"],total_sales),
            "adsSpendShare":ratio(a["ad_spend"],total_spend),
            "roas":ratio(a["attributed_sales"],a["ad_spend"]),
            "impressions":i(a["impressions"]),
            "clicks":i(a["clicks"]),
            "conversions":i(a["conversions"]),
            "adsCtr":ratio(a["clicks"],a["impressions"]),
            "adsCvr":ratio(a["conversions"],a["clicks"]),
        })
    products.sort(key=lambda x:(-n(x.get("adsAttributedSales")),s(x.get("productId"))))
    def share(k: int) -> float:
        return sum(n(x.get("adsAttributedSales")) for x in products[:k]) / total_sales if total_sales else 0.0
    return {
        "productCount":len(products),
        "adsAttributedSales":total_sales,
        "adsSpend":total_spend,
        "top1AdsSalesShare":share(1),
        "top3AdsSalesShare":share(3),
        "top5AdsSalesShare":share(5),
        "topProducts":products[:5],
    }


def _product_mtd_concentration(
    rows: Sequence[Mapping[str, Any]], period: str
) -> Dict[str, Any]:
    products=[dict(r) for r in rows if s(r.get("data_month"))==period]
    products.sort(key=lambda x:(-n(x.get("confirmed_gmv")),-n(x.get("placed_gmv")),s(x.get("product_id"))))
    total=sum(n(x.get("confirmed_gmv")) for x in products)
    def share(k: int) -> float:
        return sum(n(x.get("confirmed_gmv")) for x in products[:k]) / total if total else 0.0
    top=[]
    for r in products[:5]:
        top.append({
            "productId":s(r.get("product_id")),
            "productName":s(r.get("product_name")),
            "resolvedParentSku":s(r.get("resolved_parent_sku")),
            "confirmedGmv":n(r.get("confirmed_gmv")),
            "confirmedGmvShare":ratio(r.get("confirmed_gmv"),total),
            "placedGmv":n(r.get("placed_gmv")),
            "placedOrders":i(r.get("placed_orders")),
            "roas":n(r.get("roas")),
        })
    return {
        "alignment":"SOURCE_MTD_NOT_HORIZON_ALIGNED",
        "dataMonth":period,
        "metric":"confirmedGmv",
        "productCount":len(products),
        "confirmedGmv":total,
        "top1GmvShare":share(1),
        "top3GmvShare":share(3),
        "top5GmvShare":share(5),
        "topProducts":top,
    }


def _gap_decomposition(
    left: Mapping[str, Any], right: Mapping[str, Any]
) -> Dict[str, Any]:
    keys=("productClicks","placedCvr","placedAov")
    labels={
        "productClicks":"Product Clicks",
        "placedCvr":"CVR",
        "placedAov":"AOV",
    }
    lv={k:n(left.get(k)) for k in keys}
    rv={k:n(right.get(k)) for k in keys}
    if any(lv[k]<=0 or rv[k]<=0 for k in keys):
        return {
            "status":"INSUFFICIENT_POSITIVE_FACTORS",
            "identity":"GMV = Product Clicks × CVR × AOV",
            "drivers":[],
        }
    def product(values: Mapping[str,float]) -> float:
        out=1.0
        for key in keys:
            out*=values[key]
        return out
    effects={k:0.0 for k in keys}
    perms=list(itertools.permutations(keys))
    for perm in perms:
        state=dict(lv)
        before=product(state)
        for key in perm:
            state[key]=rv[key]
            after=product(state)
            effects[key]+=after-before
            before=after
    for key in keys:
        effects[key]/=len(perms)
    gap=n(right.get("placedGmv"))-n(left.get("placedGmv"))
    drivers=[]
    for key in keys:
        effect=effects[key]
        drivers.append({
            "key":key,
            "label":labels[key],
            "leftValue":lv[key],
            "rightValue":rv[key],
            "effectValueRightVsLeft":effect,
            "shareOfAbsoluteEffects":0.0,
            "shareOfNetGap":effect/gap if gap else 0.0,
            "direction":"positive" if effect>0 else ("negative" if effect<0 else "neutral"),
        })
    abs_total=sum(abs(x["effectValueRightVsLeft"]) for x in drivers) or 1.0
    for row in drivers:
        row["shareOfAbsoluteEffects"]=abs(row["effectValueRightVsLeft"])/abs_total
    drivers.sort(key=lambda x:abs(x["effectValueRightVsLeft"]),reverse=True)
    return {
        "status":"READY",
        "identity":"GMV = Product Clicks × CVR × AOV",
        "gmvGapRightVsLeft":gap,
        "reconciledEffectTotal":sum(x["effectValueRightVsLeft"] for x in drivers),
        "drivers":drivers,
    }


def _compare_horizon(
    *,
    key: str,
    window: Mapping[str, str],
    left_daily: Sequence[Mapping[str, Any]],
    right_daily: Sequence[Mapping[str, Any]],
    left_traffic: Sequence[Mapping[str, Any]],
    right_traffic: Sequence[Mapping[str, Any]],
    left_ads_products: Sequence[Mapping[str, Any]],
    right_ads_products: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    start=s(window.get("windowStart")); end=s(window.get("windowEnd"))
    left_h=_headline(left_daily,start,end)
    right_h=_headline(right_daily,start,end)
    metrics={
        metric:_compare_metric(left_h,right_h,metric)
        for metric in COMPARE_METRICS
    }
    return {
        "key":key,
        "label":s(window.get("label")),
        "coverage":{"windowStart":start,"windowEnd":end,"alignedShopCount":2},
        "leftHeadline":left_h,
        "rightHeadline":right_h,
        "metrics":metrics,
        "driverDecomposition":_gap_decomposition(left_h,right_h),
        "traffic":{
            "left":_traffic_group_window(left_traffic,start,end),
            "right":_traffic_group_window(right_traffic,start,end),
        },
        "adsProducts":{
            "left":_ads_product_window(left_ads_products,start,end),
            "right":_ads_product_window(right_ads_products,start,end),
        },
    }


COMPARE_METRICS = (
    "placedGmv", "placedOrders", "productClicks", "placedAov", "placedCvr",
    "confirmedGmv", "confirmedOrders", "paidGmv", "paidOrders",
    "cancelledSales", "cancelledSalesRate",
    "returnedRefundedSales", "returnedRefundedSalesRate",
    "netSalesAfterCancel",
    "adsImpressions", "adsClicks", "adsConversions",
    "adsSpend", "adsAttributedSales", "adsCtr", "adsCvr", "roas",
    "fixedFee", "serviceFee", "transactionFee", "orderFees",
    "orderFeeRatio", "adsSpendToNetSales", "adsAttributedShareOfPlacedGmv",
    "totalPlatformCostRatio",
)


def _compare_metric(
    left: Mapping[str, Any], right: Mapping[str, Any], metric: str
) -> Dict[str, Any]:
    lv = n(left.get(metric))
    rv = n(right.get(metric))
    return {
        "leftValue": lv,
        "rightValue": rv,
        "differenceRightVsLeft": rv - lv,
        "differencePctRightVsLeft": (rv / lv - 1.0) if lv else None,
    }


def _aligned_window(
    freshness_rows: Sequence[Mapping[str, Any]]
) -> Tuple[str, str]:
    starts = [s(x.get("common_reliable_start")) for x in freshness_rows]
    ends = [s(x.get("common_reliable_end")) for x in freshness_rows]
    if not starts or any(not x for x in starts + ends):
        raise ValueError("missing common reliable window")
    start = max(starts)
    end = min(ends)
    if start > end:
        raise ValueError(f"no aligned window: {start}>{end}")
    return start, end


def validate_payload(
    payload: Mapping[str, Any],
    expected_shop_ids: Sequence[str],
    contract: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    checks = []

    def ck(name: str, ok: bool, detail: Mapping[str, Any] | None = None) -> None:
        checks.append({
            "name": name,
            "status": "PASS" if ok else "FAIL",
            "detail": dict(detail or {}),
        })

    expected = list(expected_shop_ids)
    selector_ids = [
        s(x.get("shopId")) for x in payload.get("selector", {}).get("shops", [])
    ]
    ck(
        "selector_matches_semantic_shops",
        selector_ids == expected,
        {"selector": selector_ids, "expected": expected},
    )

    shop_map = payload.get("shops", {})
    ck(
        "shop_scopes_complete",
        set(shop_map) == set(expected),
        {"shopScopes": sorted(shop_map)},
    )

    portfolio = payload.get("portfolio", {})
    ph = portfolio.get("headline", {})
    contributions = portfolio.get("shopContributions", [])
    portfolio_daily = list(portfolio.get("daily") or [])
    portfolio_policy = ((contract or {}).get("scope_semantics") or {}).get("portfolio") or {}
    forbidden_total_fields = list(
        portfolio_policy.get("forbidden_total_fields")
        or ["visits", "buyers", "newBuyers", "existingBuyers", "potentialBuyers",
            "uniqueImpressions", "uniqueClicks"]
    )
    forbidden_hits = sorted({
        field
        for field in forbidden_total_fields
        if field in ph or any(field in row for row in portfolio_daily)
    })
    ck(
        "portfolio_non_additive_totals_omitted",
        not forbidden_hits,
        {"forbiddenFieldsPresent": forbidden_hits},
    )
    ck(
        "portfolio_daily_all_enabled_shops_aligned",
        bool(portfolio_daily) and all(
            i(row.get("shopCountIncluded")) == len(expected)
            for row in portfolio_daily
        ),
        {
            "expectedShopCount": len(expected),
            "observedShopCounts": sorted({
                i(row.get("shopCountIncluded")) for row in portfolio_daily
            }),
        },
    )
    gmv_sum = sum(n(x.get("headline", {}).get("placedGmv")) for x in contributions)
    orders_sum = sum(n(x.get("headline", {}).get("placedOrders")) for x in contributions)
    ck(
        "portfolio_gmv_reconciles",
        abs(n(ph.get("placedGmv")) - gmv_sum) <= 1e-6,
        {"portfolio": ph.get("placedGmv"), "shops": gmv_sum},
    )
    ck(
        "portfolio_orders_reconcile",
        abs(n(ph.get("placedOrders")) - orders_sum) <= 1e-6,
        {"portfolio": ph.get("placedOrders"), "shops": orders_sum},
    )
    ck(
        "portfolio_aov_recomputed",
        abs(n(ph.get("placedAov")) - ratio(ph.get("placedGmv"), ph.get("placedOrders"))) <= 1e-9,
    )
    ck(
        "portfolio_cvr_recomputed",
        abs(n(ph.get("placedCvr")) - ratio(ph.get("placedOrders"), ph.get("productClicks"))) <= 1e-9,
    )
    ck(
        "portfolio_roas_recomputed",
        abs(n(ph.get("roas")) - ratio(ph.get("adsAttributedSales"), ph.get("adsSpend"))) <= 1e-9,
    )
    ck(
        "portfolio_platform_cost_ratio_recomputed",
        abs(
            n(ph.get("totalPlatformCostRatio"))
            - ratio(
                n(ph.get("orderFees")) + n(ph.get("adsSpend")),
                ph.get("netSalesAfterCancel"),
            )
        ) <= 1e-9,
    )
    daily_ratio_errors = []
    for row in portfolio_daily:
        expectations = {
            "placedAov": ratio(row.get("placedGmv"), row.get("placedOrders")),
            "placedCvr": ratio(row.get("placedOrders"), row.get("productClicks")),
            "roas": ratio(row.get("adsAttributedSales"), row.get("adsSpend")),
            "totalPlatformCostRatio": ratio(
                n(row.get("orderFees")) + n(row.get("adsSpend")),
                row.get("netSalesAfterCancel"),
            ),
        }
        for field, expected_value in expectations.items():
            if abs(n(row.get(field)) - expected_value) > 1e-9:
                daily_ratio_errors.append(
                    (row.get("date"), field, row.get(field), expected_value)
                )
    ck(
        "portfolio_daily_ratios_recomputed",
        not daily_ratio_errors,
        {"errors": daily_ratio_errors[:20]},
    )

    shop_semantics = ((contract or {}).get("scope_semantics") or {}).get("shop") or {}
    daily_unique_fields = list(
        shop_semantics.get("daily_unique_fields")
        or ["visits", "buyers", "newBuyers", "existingBuyers", "potentialBuyers"]
    )
    shop_headline_unique_hits = []
    shop_daily_ratio_errors = []
    shop_daily_date_errors = []
    shop_traffic_unique_hits = []
    shop_product_scope_errors = []
    for sid, scope in shop_map.items():
        headline = scope.get("headline") or {}
        for field in daily_unique_fields:
            if field in headline:
                shop_headline_unique_hits.append((sid, field))
        daily = list(scope.get("daily") or [])
        dates = [s(row.get("date")) for row in daily]
        if len(dates) != len(set(dates)):
            shop_daily_date_errors.append((sid, "duplicate_date"))
        for row in daily:
            expectations = {
                "placedAov": ratio(row.get("placedGmv"), row.get("placedOrders")),
                "placedCvr": ratio(row.get("placedOrders"), row.get("productClicks")),
                "roas": ratio(row.get("adsAttributedSales"), row.get("adsSpend")),
                "totalPlatformCostRatio": ratio(
                    n(row.get("orderFees")) + n(row.get("adsSpend")),
                    row.get("netSalesAfterCancel"),
                ),
            }
            for field, expected_value in expectations.items():
                if abs(n(row.get(field)) - expected_value) > 1e-9:
                    shop_daily_ratio_errors.append(
                        (sid, row.get("date"), field, row.get(field), expected_value)
                    )
        traffic_forbidden = set(
            ((shop_semantics.get("traffic") or {}).get("forbidden_multi_day_unique_fields"))
            or ["buyers", "uniqueImpressions", "uniqueClicks"]
        )
        for row in scope.get("traffic") or []:
            for field in traffic_forbidden:
                if field in row:
                    shop_traffic_unique_hits.append((sid, field))
        product_coverage = scope.get("productCoverage") or {}
        if (
            s(product_coverage.get("alignment")) != "SOURCE_MTD_SHOP_SCOPE_ONLY"
            or bool(product_coverage.get("crossShopAggregationAllowed"))
        ):
            shop_product_scope_errors.append((sid, dict(product_coverage)))

    ck(
        "shop_headline_daily_uniques_omitted",
        not shop_headline_unique_hits,
        {"hits": shop_headline_unique_hits[:20]},
    )
    ck(
        "shop_daily_grain_unique",
        not shop_daily_date_errors,
        {"errors": shop_daily_date_errors[:20]},
    )
    ck(
        "shop_daily_ratios_recomputed",
        not shop_daily_ratio_errors,
        {"errors": shop_daily_ratio_errors[:20]},
    )
    ck(
        "shop_traffic_multi_day_uniques_omitted",
        not shop_traffic_unique_hits,
        {"hits": shop_traffic_unique_hits[:20]},
    )
    ck(
        "shop_product_scope_mtd_only",
        not shop_product_scope_errors,
        {"errors": shop_product_scope_errors[:20]},
    )

    pairs = payload.get("compare", {}).get("pairs", [])
    expected_pairs = len(expected) * (len(expected) - 1) // 2
    ck(
        "compare_pair_count",
        len(pairs) == expected_pairs,
        {"pairs": len(pairs), "expected": expected_pairs},
    )
    pair_ids = [s(x.get("compareId")) for x in pairs]
    ck(
        "compare_pair_ids_unique",
        len(pair_ids) == len(set(pair_ids)),
        {"compareIds": pair_ids},
    )

    horizon_errors=[]
    decomposition_errors=[]
    for pair in pairs:
        horizons=pair.get("horizons") or {}
        if list(pair.get("horizonOrder") or [])!=["latestDay","last7","mtd"]:
            horizon_errors.append((pair.get("compareId"),"order"))
        if set(horizons)!={"latestDay","last7","mtd"}:
            horizon_errors.append((pair.get("compareId"),"keys"))
        for key,h in horizons.items():
            cov=h.get("coverage") or {}
            if s(cov.get("windowStart"))>s(cov.get("windowEnd")):
                horizon_errors.append((pair.get("compareId"),key,"window"))
            d=h.get("driverDecomposition") or {}
            if d.get("status")=="READY":
                if abs(n(d.get("gmvGapRightVsLeft"))-n(d.get("reconciledEffectTotal")))>1e-6:
                    decomposition_errors.append((pair.get("compareId"),key))
    ck("compare_horizons_complete",not horizon_errors,{"errors":horizon_errors[:20]})
    ck("compare_gap_decomposition_reconciles",not decomposition_errors,{"errors":decomposition_errors[:20]})

    product_owners = defaultdict(int)
    for sid, scope in shop_map.items():
        for product in scope.get("products", []):
            product_owners[(sid, s(product.get("productId")))] += 1
    dup_product_keys = [key for key, count in product_owners.items() if count > 1]
    ck(
        "product_identity_is_shop_scoped",
        not dup_product_keys,
        {"duplicates": dup_product_keys[:20]},
    )

    hist_enabled=bool((payload.get("capabilities") or {}).get("historicalComparatorContext"))
    if hist_enabled:
        contexts=[(payload.get("portfolio") or {}).get("historicalContext") or {}]
        contexts.extend(
            ((payload.get("shops") or {}).get(sid) or {}).get("historicalContext") or {}
            for sid in expected_shop_ids
        )
        ck("historical_context_all_scopes_bound",all(bool(x.get("sourceHistoricalFingerprint")) for x in contexts))
        ck("historical_context_fail_closed",all(
            not bool(x.get("alertEligible")) and not bool(x.get("diagnosisEligible"))
            for x in contexts
        ))
        ck("historical_context_factual_only",all(
            all(not bool((c or {}).get("alertEligible")) and not bool((c or {}).get("diagnosisEligible"))
                for c in (x.get("comparators") or {}).values())
            for x in contexts
        ))

        context_enabled=bool((payload.get("capabilities") or {}).get("businessContextCalendar"))
        if context_enabled:
            ck("business_context_lineage_all_scopes",all(
                s((x.get("businessContext") or {}).get("status"))=="CONTEXT_AVAILABLE"
                and bool(s((x.get("businessContext") or {}).get("sourceFingerprint")))
                for x in contexts
            ))
            ck("context_matched_baseline_safety",all(
                not bool((x.get("businessContext") or {}).get("alertEligible"))
                and not bool((x.get("businessContext") or {}).get("diagnosisEligible"))
                for x in contexts
            ))
            allowed_context_eval={"CONTEXT_COMPATIBLE","CONTEXT_DIFFERENT","CONTEXT_UNKNOWN"}
            qualification_errors=[]
            for scope_ctx in contexts:
                for key,comp in (scope_ctx.get("comparators") or {}).items():
                    bc=(comp or {}).get("businessContext") or {}
                    evaluation=s(bc.get("matchEvaluation"))
                    if evaluation not in allowed_context_eval:
                        qualification_errors.append((key,evaluation))
                    q=bc.get("qualification") or {}
                    if any(bool(q.get(flag)) for flag in (
                        "alertEligible","diagnosisEligible","causalClaimEligible"
                    )):
                        qualification_errors.append((key,"unsafe"))
            ck("context_comparator_qualification_factual_only",not qualification_errors,{
                "errors":qualification_errors[:20]
            })
            matched_errors=[]
            any_ready=False
            for scope_ctx in contexts:
                scope_ready=False
                for key in ("sameWeekday","sameDayOfMonth"):
                    comp=(scope_ctx.get("comparators") or {}).get(key) or {}
                    matched=comp.get("contextMatchedBaseline") or {}
                    status=s(matched.get("status"))
                    if status not in {"READY","INSUFFICIENT_CONTEXT_MATCHED_HISTORY"}:
                        matched_errors.append((key,status))
                        continue
                    required=int(matched.get("requiredSampleCount") or 0)
                    count=int(matched.get("sampleCount") or 0)
                    has_stats=bool(matched.get("baseline"))
                    if status=="READY":
                        any_ready=True
                        scope_ready=True
                        if required<=0 or count<required or not has_stats:
                            matched_errors.append((key,"ready_contract"))
                    else:
                        if has_stats:
                            matched_errors.append((key,"stats_leak"))
                    if bool(matched.get("silentFallbackUsed")):
                        matched_errors.append((key,"silent_fallback"))
                if bool((scope_ctx.get("businessContext") or {}).get("contextMatchedBaselineEnabled"))!=scope_ready:
                    matched_errors.append(("scope","capability_mismatch"))
            ck("context_matched_baseline_contract",not matched_errors,{
                "errors":matched_errors[:30]
            })
            ck(
                "context_matched_baseline_capability_consistent",
                bool((payload.get("capabilities") or {}).get("contextMatchedBaseline"))==any_ready,
                {"anyReady":any_ready},
            )
            if bool((payload.get("capabilities") or {}).get("anomalyEligibilityGuardrails")):
                eligibility_errors=[]
                allowed_elig={"ANOMALY_ELIGIBLE","ANOMALY_BLOCKED"}
                for scope_ctx in contexts:
                    summary=scope_ctx.get("anomalyEligibility") or {}
                    if s(summary.get("status")) not in allowed_elig:
                        eligibility_errors.append(("scope",summary.get("status")))
                    if any(bool(summary.get(k)) for k in (
                        "anomalyDetectionEnabled","severityEnabled","alertsEnabled",
                        "diagnosisEnabled","causalClaimsEnabled"
                    )):
                        eligibility_errors.append(("scope","unsafe"))
                    for key,comp in (scope_ctx.get("comparators") or {}).items():
                        elig=(comp or {}).get("anomalyEligibility") or {}
                        if s(elig.get("status")) not in allowed_elig:
                            eligibility_errors.append((key,elig.get("status")))
                        if any(bool(elig.get(k)) for k in (
                            "anomalyDetectionEnabled","severityEnabled","alertEligible",
                            "diagnosisEligible","causalClaimEligible"
                        )):
                            eligibility_errors.append((key,"unsafe"))
                ck("anomaly_eligibility_guardrails_bound_fail_closed",not eligibility_errors,{
                    "errors":eligibility_errors[:30]
                })
            ck(
                "anomaly_detection_capability_off",
                not bool((payload.get("capabilities") or {}).get("anomalyDetection"))
            )
            if bool((payload.get("capabilities") or {}).get("anomalyDetectionFoundation")):
                detection_errors=[]
                allowed_detection={"NORMAL","DEVIATION_CANDIDATE","NOT_EVALUATED"}
                for scope_ctx in contexts:
                    summary=scope_ctx.get("anomalyDetectionFoundation") or {}
                    if s(summary.get("status")) not in allowed_detection:
                        detection_errors.append(("scope",summary.get("status")))
                    if any(bool(summary.get(k)) for k in (
                        "operationalAnomalyDetectionEnabled","severityEnabled","alertsEnabled",
                        "diagnosisEnabled","causalClaimsEnabled"
                    )):
                        detection_errors.append(("scope","unsafe"))
                    for key,comp in (scope_ctx.get("comparators") or {}).items():
                        det=(comp or {}).get("anomalyDetectionFoundation") or {}
                        if s(det.get("status")) not in allowed_detection:
                            detection_errors.append((key,det.get("status")))
                        for metric,result in (det.get("metricResults") or {}).items():
                            status=s(result.get("status"))
                            if status not in allowed_detection:
                                detection_errors.append((key,metric,status))
                            if status=="NOT_EVALUATED":
                                if bool(result.get("scorePublished")) or "modifiedZScore" in result:
                                    detection_errors.append((key,metric,"score_leak"))
                            elif not bool(result.get("scorePublished")):
                                detection_errors.append((key,metric,"missing_score"))
                            if any(bool(result.get(k)) for k in (
                                "severityEligible","alertEligible","diagnosisEligible","causalClaimEligible"
                            )):
                                detection_errors.append((key,metric,"unsafe_metric"))
                ck("anomaly_detection_foundation_bound_fail_closed",not detection_errors,{
                    "errors":detection_errors[:40]
                })
            if bool((payload.get("capabilities") or {}).get("anomalySeverityConfidence")):
                severity_errors=[]
                allowed_levels={"LOW","MEDIUM","HIGH"}
                for scope_ctx in contexts:
                    summary=scope_ctx.get("anomalySeverityConfidence") or {}
                    if s(summary.get("status")) not in {"ASSESSED","NOT_ASSESSED"}:
                        severity_errors.append(("scope",summary.get("status")))
                    if any(bool(summary.get(k)) for k in (
                        "businessImpactClaim","automaticAlertsEnabled",
                        "diagnosisEnabled","causalClaimsEnabled"
                    )):
                        severity_errors.append(("scope","unsafe"))
                    for key,comp in (scope_ctx.get("comparators") or {}).items():
                        det=(comp or {}).get("anomalyDetectionFoundation") or {}
                        comp_summary=(comp or {}).get("anomalySeverityConfidence") or {}
                        if s(comp_summary.get("status")) not in {"ASSESSED","NOT_ASSESSED"}:
                            severity_errors.append((key,"comp_status"))
                        for metric,result in (det.get("metricResults") or {}).items():
                            assessment=result.get("severityConfidence") or {}
                            if s(result.get("status"))=="DEVIATION_CANDIDATE":
                                if s(assessment.get("status"))!="ASSESSED":
                                    severity_errors.append((key,metric,"candidate_not_assessed"))
                                if s(assessment.get("severityLevel")) not in allowed_levels:
                                    severity_errors.append((key,metric,"severity_level"))
                                if s(assessment.get("confidenceLevel")) not in allowed_levels:
                                    severity_errors.append((key,metric,"confidence_level"))
                            else:
                                if s(assessment.get("status"))!="NOT_ASSESSED":
                                    severity_errors.append((key,metric,"non_candidate_assessed"))
                                if "severityScore" in assessment or "confidenceScore" in assessment:
                                    severity_errors.append((key,metric,"non_candidate_score_leak"))
                            if any(bool(assessment.get(k)) for k in (
                                "businessImpactClaim","alertEligible",
                                "diagnosisEligible","causalClaimEligible"
                            )):
                                severity_errors.append((key,metric,"unsafe_metric"))
                ck("anomaly_severity_confidence_bound_candidate_only",not severity_errors,{
                    "errors":severity_errors[:40]
                })
            ck(
                "operational_anomaly_severity_off",
                not bool((payload.get("capabilities") or {}).get("anomalySeverity"))
            )
            if bool((payload.get("capabilities") or {}).get("driverAttributionFoundation")):
                attribution_errors=[]
                allowed_attr={"ATTRIBUTED","ASSOCIATION_ONLY","NOT_DIAGNOSED"}
                for scope_ctx in contexts:
                    summary=scope_ctx.get("driverAttributionFoundation") or {}
                    if s(summary.get("status")) not in allowed_attr:
                        attribution_errors.append(("scope",summary.get("status")))
                    if any(bool(summary.get(k)) for k in (
                        "operationalDiagnosisEnabled","automaticAlertsEnabled","causalClaimsEnabled"
                    )):
                        attribution_errors.append(("scope","unsafe"))
                    for key,comp in (scope_ctx.get("comparators") or {}).items():
                        comp_summary=(comp or {}).get("driverAttributionFoundation") or {}
                        if s(comp_summary.get("status")) not in allowed_attr:
                            attribution_errors.append((key,"comp_status"))
                        det=(comp or {}).get("anomalyDetectionFoundation") or {}
                        for metric,result in (det.get("metricResults") or {}).items():
                            attr=result.get("driverAttribution") or {}
                            status=s(attr.get("status"))
                            if status not in allowed_attr:
                                attribution_errors.append((key,metric,status))
                                continue
                            if s(result.get("status"))!="DEVIATION_CANDIDATE" and status!="NOT_DIAGNOSED":
                                attribution_errors.append((key,metric,"non_candidate_diagnosed"))
                            if status=="ATTRIBUTED":
                                if not (attr.get("driverContributions") or []) or not s(attr.get("identity")):
                                    attribution_errors.append((key,metric,"missing_contributions"))
                                if bool(attr.get("identityContributionIsCausalClaim")):
                                    attribution_errors.append((key,metric,"causal_claim"))
                            if any(bool(attr.get(k)) for k in (
                                "operationalDiagnosisEnabled","alertEligible",
                                "diagnosisEligible","causalClaimEligible"
                            )):
                                attribution_errors.append((key,metric,"unsafe"))
                ck("driver_attribution_foundation_bound_noncausal",not attribution_errors,{
                    "errors":attribution_errors[:40]
                })
            ck(
                "operational_diagnosis_off",
                not bool((payload.get("capabilities") or {}).get("diagnosis"))
            )
            if bool((payload.get("capabilities") or {}).get("smartIssuesFoundation")):
                smart_issue_errors=[]
                for scope_ctx in contexts:
                    summary=scope_ctx.get("smartIssuesFoundation") or {}
                    issues=list(summary.get("issues") or [])
                    status=s(summary.get("status"))
                    if status not in {"ISSUE_READY","NO_ISSUE"}:
                        smart_issue_errors.append(("scope",status))
                    if int(summary.get("issueCount") or 0)!=len(issues):
                        smart_issue_errors.append(("scope","count"))
                    if len({s(x.get("affectedMetric")) for x in issues})!=len(issues):
                        smart_issue_errors.append(("scope","dedupe"))
                    if status=="NO_ISSUE" and issues:
                        smart_issue_errors.append(("scope","no_issue_has_items"))
                    if any(bool(summary.get(k)) for k in (
                        "automaticAlertsEnabled","actionRecommendationsEnabled",
                        "operationalDiagnosisEnabled","causalClaimsEnabled"
                    )):
                        smart_issue_errors.append(("scope","unsafe"))
                    for issue in issues:
                        if s(issue.get("status"))!="ISSUE_READY":
                            smart_issue_errors.append(("issue","status"))
                        if s(issue.get("detectorStatus"))!="DEVIATION_CANDIDATE":
                            smart_issue_errors.append(("issue","detector"))
                        if any(bool(issue.get(k)) for k in (
                            "automaticAlertEligible","actionRecommendationEligible",
                            "operationalDiagnosisEnabled","causalClaimEligible"
                        )):
                            smart_issue_errors.append(("issue","unsafe"))
                        if not (issue.get("unresolvedUncertainty") or []):
                            smart_issue_errors.append(("issue","uncertainty"))
                ck("smart_issues_foundation_bound_evidence_only",not smart_issue_errors,{
                    "errors":smart_issue_errors[:40]
                })
            ck(
                "operational_smart_issues_off",
                not bool((payload.get("capabilities") or {}).get("smartIssues"))
            )
            if bool((payload.get("capabilities") or {}).get("operatorActionPolicyFoundation")):
                action_errors=[]
                for scope_ctx in contexts:
                    smart=scope_ctx.get("smartIssuesFoundation") or {}
                    summary=scope_ctx.get("operatorActionPolicyFoundation") or {}
                    actions=list(summary.get("actionOptions") or [])
                    status=s(summary.get("status"))
                    if status not in {"ACTION_OPTIONS_READY","NO_ACTION_OPTIONS"}:
                        action_errors.append(("scope",status))
                    if int(summary.get("actionOptionCount") or 0)!=len(actions):
                        action_errors.append(("scope","count"))
                    if status=="NO_ACTION_OPTIONS" and actions:
                        action_errors.append(("scope","no_options_has_items"))
                    issue_ids={s(x.get("issueId")) for x in smart.get("issues") or []}
                    for option in actions:
                        if s(option.get("sourceIssueId")) not in issue_ids:
                            action_errors.append(("option","unknown_issue"))
                        if s(option.get("status"))!="REVIEW_OPTION":
                            action_errors.append(("option","status"))
                        if not bool(option.get("requiresHumanReview")):
                            action_errors.append(("option","human_review_missing"))
                        if s(option.get("executionMode"))!="HUMAN_REVIEW_ONLY":
                            action_errors.append(("option","execution_mode"))
                        if any(bool(option.get(k)) for k in (
                            "platformMutationAllowed","automaticExecutionEligible",
                            "automaticAlertEligible","causalClaimEligible",
                            "prescriptiveRecommendation"
                        )):
                            action_errors.append(("option","unsafe"))
                        if not (option.get("verificationChecks") or []):
                            action_errors.append(("option","verification_missing"))
                        if not (option.get("stopOrReversalChecks") or []):
                            action_errors.append(("option","stop_missing"))
                ck("operator_action_policy_bound_review_only",not action_errors,{
                    "errors":action_errors[:40]
                })
            ck(
                "operational_actions_off",
                not bool((payload.get("capabilities") or {}).get("operatorActions"))
            )

    if bool((payload.get("capabilities") or {}).get("productionCutoverShadowMode")):
        shadow=payload.get("shadowModeV1") or {}
        activation=shadow.get("activationControls") or {}
        rollback=shadow.get("rollbackControls") or {}
        shadow_ok=(
            s(shadow.get("mode"))=="PREPRODUCTION_OBSERVE_ONLY"
            and s(shadow.get("status")) in {
                "SHADOW_OBSERVING","READY_FOR_HUMAN_CUTOVER_REVIEW","CUTOVER_BLOCKED"
            }
            and bool(shadow.get("readinessGates"))
            and bool(activation.get("requiresExplicitHumanApproval"))
            and not bool(activation.get("productionActivationAllowed"))
            and not bool(activation.get("automaticCutoverEnabled"))
            and not bool(activation.get("cutoverAuthorized"))
            and bool(rollback.get("required"))
            and bool(rollback.get("legacyProductionPathRetained"))
            and not bool(rollback.get("automaticRollbackEnabled"))
            and not bool(shadow.get("productionWritesEnabled"))
            and not bool(shadow.get("platformMutationAllowed"))
        )
        ck("production_cutover_shadow_mode_bound_observe_only",shadow_ok,{
            "status":s(shadow.get("status")),
        })
    ck(
        "production_cutover_off",
        not bool((payload.get("capabilities") or {}).get("productionCutover"))
        and not bool((payload.get("safety") or {}).get("productionCutoverAuthorized"))
        and not bool((payload.get("safety") or {}).get("productionActivationEnabled")),
    )

    failed = [x for x in checks if x["status"] == "FAIL"]
    return {
        "status": "PASS" if not failed else "FAIL",
        "failedCheckCount": len(failed),
        "checks": checks,
    }


def _load_historical_binding(
    path: str | Path | None,
    *,
    period: str,
    expected_shop_ids: Sequence[str],
) -> Dict[str,Any] | None:
    if not path:
        return None
    p=Path(path)
    data=_read_json(_require(p))
    meta=data.get("meta") or {}
    if s(meta.get("layer"))!="multi_shop_historical_intelligence_v1":
        raise ValueError("unexpected historical intelligence layer")
    if s(meta.get("asOfPeriod"))!=period:
        raise ValueError("historical intelligence period mismatch")
    fp=s(meta.get("historicalBuildFingerprint"))
    if not fp:
        raise ValueError("historical intelligence fingerprint missing")
    shop_map=data.get("shops") or {}
    if set(shop_map)!=set(expected_shop_ids):
        raise ValueError("historical shop scope differs from UI payload scope")
    safety=data.get("safety") or {}
    if any(bool(safety.get(k)) for k in (
        "productionDataMartWritten","productionUiModified","legacyPayloadPublished",
        "historicalAlertsEnabled","diagnosisEnabled","productionCutoverAuthorized",
        "productionActivationEnabled",
    )):
        raise ValueError("historical intelligence safety boundary violated")
    shadow=data.get("shadowModeV1") or {}
    activation=shadow.get("activationControls") or {}
    if shadow:
        if (
            s(shadow.get("mode"))!="PREPRODUCTION_OBSERVE_ONLY"
            or bool(activation.get("productionActivationAllowed"))
            or bool(activation.get("automaticCutoverEnabled"))
            or bool(activation.get("cutoverAuthorized"))
        ):
            raise ValueError("historical shadow-mode boundary violated")
    return data


def _historical_scope_context(
    scope: Mapping[str,Any],
    *,
    fingerprint: str,
) -> Dict[str,Any]:
    coverage=scope.get("coverage") or {}
    comparators=scope.get("comparators") or {}
    allowed=("previousDay","previous7d","previousMonthMtd","sameWeekday","sameDayOfMonth")
    out_comparators={k:dict(comparators.get(k) or {}) for k in allowed}
    context=scope.get("context") or {}
    return {
        "sourceHistoricalFingerprint":fingerprint,
        "status":s(scope.get("status")) or "INSUFFICIENT_HISTORY",
        "historyDepthReason":s(scope.get("historyDepthReason")),
        "latestTrustedDate":s(scope.get("latestTrustedDate")),
        "coverage":{
            "start":s(coverage.get("start")),
            "end":s(coverage.get("end")),
            "dayCount":int(coverage.get("dayCount") or 0),
            "historySpanDays":int(coverage.get("historySpanDays") or 0),
            "availableMonthCount":int(coverage.get("availableMonthCount") or 0),
            "calendarCompleteMonthCount":int(
                coverage.get("calendarCompleteMonthCount")
                if coverage.get("calendarCompleteMonthCount") is not None
                else coverage.get("completeMonthCount") or 0
            ),
            "coverageOrigin":s(coverage.get("coverageOrigin")),
            "startPolicy":s(coverage.get("startPolicy")),
            "lifecycleStartDate":s(coverage.get("lifecycleStartDate")),
            "preStartDatesAreMissing":coverage.get("preStartDatesAreMissing"),
            "coverageInterpretation":s(coverage.get("coverageInterpretation")),
        },
        "comparators":out_comparators,
        "contextStatus":s(context.get("status")),
        "businessContext":{
            "status":s(context.get("status")),
            "sourceLayer":s(context.get("sourceLayer")),
            "sourceFingerprint":s(context.get("sourceFingerprint")),
            "availableDimensions":list(context.get("availableDimensions") or []),
            "coverage":dict(context.get("coverage") or {}),
            "contextMatchedBaselineEnabled":bool(context.get("contextMatchedBaselineEnabled")),
            "alertEligible":False,
            "diagnosisEligible":False,
        },
        "anomalyEligibility":dict(scope.get("anomalyEligibility") or {}),
        "anomalyDetectionFoundation":dict(scope.get("anomalyDetectionFoundation") or {}),
        "anomalySeverityConfidence":dict(scope.get("anomalySeverityConfidence") or {}),
        "driverAttributionFoundation":dict(scope.get("driverAttributionFoundation") or {}),
        "smartIssuesFoundation":dict(scope.get("smartIssuesFoundation") or {}),
        "operatorActionPolicyFoundation":dict(scope.get("operatorActionPolicyFoundation") or {}),
        "alertEligible":False,
        "diagnosisEligible":False,
    }


def build_ui_payload(
    *,
    semantic_dir: str | Path,
    output_dir: str | Path,
    contract_path: str | Path,
    historical_path: str | Path | None = None,
) -> Dict[str, Any]:
    semantic_dir = Path(semantic_dir)
    output_dir = Path(output_dir)
    contract = _load_contract(contract_path)

    manifest = _read_json(_require(semantic_dir / "manifest.json"))
    semantic_qa = _read_json(_require(semantic_dir / "semantic_qa_report.json"))
    if semantic_qa.get("status") != "PASS" or not semantic_qa.get("semantic_mart_ready"):
        raise ValueError("semantic QA is not PASS/ready")
    semantic_fp = s(manifest.get("semantic_build_fingerprint"))
    if not semantic_fp or semantic_fp != s(semantic_qa.get("semantic_build_fingerprint")):
        raise ValueError("semantic fingerprint mismatch")

    period = s(manifest.get("period"))
    dim_shop = _read_jsonl(_require(semantic_dir / "dim_shop.jsonl"))
    shop_daily_all = _read_jsonl(_require(semantic_dir / "dm_shop_daily.jsonl"))
    traffic_daily_all = _read_jsonl(
        _require(semantic_dir / "dm_traffic_source_daily.jsonl")
    )
    products_all = _read_jsonl(_require(semantic_dir / "dm_product_monthly.jsonl"))
    ads_products_all = _read_jsonl(
        _require(semantic_dir / "dm_ads_product_daily.jsonl")
    )

    freshness = manifest.get("freshness") or {}
    # dim_shop is emitted in Shop Registry order. Preserve that order so the
    # selector remains registry-controlled rather than code/alphabet controlled.
    shops = list(dim_shop)
    shop_ids = [s(x.get("shop_id")) for x in shops]
    qa_shop_ids = {s(x) for x in semantic_qa.get("selected_shop_ids") or []}
    if set(shop_ids) != qa_shop_ids:
        raise ValueError("dim_shop scope differs from semantic QA")

    historical=_load_historical_binding(
        historical_path,
        period=period,
        expected_shop_ids=shop_ids,
    )
    historical_fp=s(((historical or {}).get("meta") or {}).get("historicalBuildFingerprint"))
    business_context_fp=s(
        ((historical or {}).get("historySources") or {}).get("businessContextFingerprint")
    )

    daily_by_shop = defaultdict(list)
    traffic_by_shop = defaultdict(list)
    products_by_shop = defaultdict(list)
    ads_products_by_shop = defaultdict(list)
    for row in shop_daily_all:
        daily_by_shop[s(row.get("shop_id"))].append(row)
    for row in traffic_daily_all:
        traffic_by_shop[s(row.get("shop_id"))].append(row)
    for row in products_all:
        products_by_shop[s(row.get("shop_id"))].append(row)
    for row in ads_products_all:
        ads_products_by_shop[s(row.get("shop_id"))].append(row)

    freshness_rows = [freshness.get(sid) or {} for sid in shop_ids]
    portfolio_start, portfolio_end = _aligned_window(freshness_rows)

    selector_shops = []
    shop_payloads = {}
    for shop in shops:
        sid = s(shop.get("shop_id"))
        fr = freshness.get(sid) or {}
        start, end = _aligned_window([fr])
        selector_shops.append({
            "shopId": sid,
            "shopKey": s(shop.get("shop_key")),
            "displayName": s(shop.get("display_name")),
            "platform": s(shop.get("platform")),
            "shopBadge": {
                "kind": s(shop.get("shop_badge_kind")),
                "label": s(shop.get("shop_badge_label")),
            },
            "freshness": {
                "commonReliableStart": start,
                "commonReliableEnd": end,
                "sourceVerifiedThrough": fr.get("source_verified_through") or {},
            },
        })
        shop_payloads[sid] = {
            "scope": {"type": "shop", "shopId": sid},
            "coverage": {
                "windowStart": start,
                "windowEnd": end,
                "alignedShopCount": 1,
            },
            "headline": _headline(daily_by_shop[sid], start, end),
            "daily": _shop_daily_rows(daily_by_shop[sid], start, end),
            "traffic": _traffic_window(traffic_by_shop[sid], start, end),
            "products": _product_rows(products_by_shop[sid]),
            "productCoverage": {
                "dataMonth": period,
                "alignment": "SOURCE_MTD_SHOP_SCOPE_ONLY",
                "crossShopAggregationAllowed": False,
            },
            "semanticPolicy": {
                "alignment": s(
                    ((contract.get("scope_semantics") or {}).get("shop") or {}).get("alignment")
                ),
                "dailyUniqueFields": list(
                    ((contract.get("scope_semantics") or {}).get("shop") or {}).get("daily_unique_fields")
                    or []
                ),
                "multiDayUniquePolicy": s(
                    ((contract.get("scope_semantics") or {}).get("shop") or {}).get("multi_day_unique_policy")
                ),
                "headlineUniquePolicy": s(
                    ((contract.get("scope_semantics") or {}).get("shop") or {}).get("headline_unique_policy")
                ),
                "ratioPolicy": "RECOMPUTE_FROM_ADDITIVE_COMPONENTS",
                "funnel": dict(
                    ((contract.get("scope_semantics") or {}).get("shop") or {}).get("funnel")
                    or {}
                ),
                "traffic": dict(
                    ((contract.get("scope_semantics") or {}).get("shop") or {}).get("traffic")
                    or {}
                ),
                "product": dict(
                    ((contract.get("scope_semantics") or {}).get("shop") or {}).get("product")
                    or {}
                ),
                "latestCompleteDayVisibleLabel": s(
                    ((contract.get("scope_semantics") or {}).get("shop") or {}).get("latest_complete_day_visible_label")
                ),
                "partialWindowVisiblePolicy": s(
                    ((contract.get("scope_semantics") or {}).get("shop") or {}).get("partial_window_visible_policy")
                ),
                "comparisonWindowPolicy": s(
                    ((contract.get("scope_semantics") or {}).get("shop") or {}).get("comparison_window_policy")
                ),
            },
        }

    aligned_rows = [
        r
        for sid in shop_ids
        for r in daily_by_shop[sid]
        if portfolio_start <= _date(r.get("data_date")) <= portfolio_end
    ]
    portfolio_headline = _headline(aligned_rows, portfolio_start, portfolio_end)
    contributions = []
    for sid in shop_ids:
        h = _headline(daily_by_shop[sid], portfolio_start, portfolio_end)
        contributions.append({
            "shopId": sid,
            "headline": h,
            "placedGmvShare": ratio(
                h.get("placedGmv"), portfolio_headline.get("placedGmv")
            ),
            "placedOrdersShare": ratio(
                h.get("placedOrders"), portfolio_headline.get("placedOrders")
            ),
            "adsSpendShare": ratio(
                h.get("adsSpend"), portfolio_headline.get("adsSpend")
            ),
            "adsSalesShare": ratio(
                h.get("adsAttributedSales"),
                portfolio_headline.get("adsAttributedSales"),
            ),
        })

    portfolio_traffic_rows = [
        r
        for sid in shop_ids
        for r in traffic_by_shop[sid]
        if portfolio_start <= _date(r.get("data_date")) <= portfolio_end
    ]
    if historical:
        for sid in shop_ids:
            shop_payloads[sid]["historicalContext"]=_historical_scope_context(
                (historical.get("shops") or {}).get(sid) or {},
                fingerprint=historical_fp,
            )

    portfolio = {
        "scope": {"type": "portfolio", "shopIds": shop_ids},
        "coverage": {
            "windowStart": portfolio_start,
            "windowEnd": portfolio_end,
            "alignedShopCount": len(shop_ids),
            "policy": "INTERSECTION_OF_SHOP_COMMON_RELIABLE_WINDOWS",
        },
        "headline": portfolio_headline,
        "daily": _portfolio_daily(
            daily_by_shop, portfolio_start, portfolio_end
        ),
        "traffic": _traffic_window(
            portfolio_traffic_rows, portfolio_start, portfolio_end
        ),
        "shopContributions": contributions,
        "semanticPolicy": {
            "alignment": s(
                ((contract.get("scope_semantics") or {}).get("portfolio") or {}).get("alignment")
            ),
            "dailyShopRequirement": s(
                ((contract.get("scope_semantics") or {}).get("portfolio") or {}).get("daily_shop_requirement")
            ),
            "ratioPolicy": "RECOMPUTE_FROM_ADDITIVE_COMPONENTS",
            "forbiddenTotalFields": list(
                ((contract.get("scope_semantics") or {}).get("portfolio") or {}).get("forbidden_total_fields")
                or []
            ),
            "latestCompleteDayVisibleLabel": s(
                ((contract.get("scope_semantics") or {}).get("portfolio") or {}).get("latest_complete_day_visible_label")
            ),
            "comparisonWindowPolicy": s(
                ((contract.get("scope_semantics") or {}).get("portfolio") or {}).get("comparison_window_policy")
            ),
        },
    }

    if historical:
        portfolio["historicalContext"]=_historical_scope_context(
            historical.get("portfolio") or {},
            fingerprint=historical_fp,
        )

    pairs = []
    for left, right in itertools.combinations(shops, 2):
        left_id = s(left.get("shop_id"))
        right_id = s(right.get("shop_id"))
        start, end = _aligned_window([freshness[left_id], freshness[right_id]])
        windows=_compare_windows(start,end)
        horizons={
            key:_compare_horizon(
                key=key,
                window=window,
                left_daily=daily_by_shop[left_id],
                right_daily=daily_by_shop[right_id],
                left_traffic=traffic_by_shop[left_id],
                right_traffic=traffic_by_shop[right_id],
                left_ads_products=ads_products_by_shop[left_id],
                right_ads_products=ads_products_by_shop[right_id],
            )
            for key,window in windows.items()
        }
        mtd=horizons["mtd"]
        pairs.append({
            "compareId": f"{left_id}__{right_id}",
            "scope": {
                "type": "compare",
                "leftShopId": left_id,
                "rightShopId": right_id,
            },
            "coverage": dict(mtd["coverage"]),
            "defaultHorizon":"mtd",
            "horizonOrder":["latestDay","last7","mtd"],
            "horizons":horizons,
            "productMtd":{
                "alignment":"SOURCE_MTD_NOT_HORIZON_ALIGNED",
                "left":_product_mtd_concentration(products_by_shop[left_id],period),
                "right":_product_mtd_concentration(products_by_shop[right_id],period),
            },
        })

    payload = {
        "meta": {
            "payloadContractVersion": s(contract.get("version")),
            "sourceLayer": s(contract.get("source_layer")),
            "sourceSemanticFingerprint": semantic_fp,
            "sourceHistoricalFingerprint": historical_fp,
            "period": period,
            "timezone": s(contract.get("timezone")),
            "canonicalCommercialStage": "placed",
        },
        "selector": {
            "defaultScope": {"type": "portfolio"},
            "scopeModes": ["portfolio", "shop", "compare"],
            "orderPolicy": "SHOP_REGISTRY_ORDER",
            "shops": selector_shops,
        },
        "portfolio": portfolio,
        "shops": shop_payloads,
        "compare": {
            "policy": "PAIRWISE_ALIGNED_WINDOW_NO_RANKING",
            "pairs": pairs,
        },
        "shadowModeV1":dict((historical or {}).get("shadowModeV1") or {}),
        "capabilities": {
            **dict(contract.get("capability_defaults") or {}),
            "historicalComparatorContext":bool(historical),
            "businessContextCalendar":bool(business_context_fp),
            "contextComparatorQualification":bool(business_context_fp),
            "contextMatchedBaseline":bool(
                ((historical or {}).get("capabilities") or {}).get("contextMatchedBaseline")
            ),
            "anomalyEligibilityGuardrails":bool(
                ((historical or {}).get("capabilities") or {}).get("anomalyEligibilityGuardrails")
            ),
            "anomalyDetectionFoundation":bool(
                ((historical or {}).get("capabilities") or {}).get("anomalyDetectionFoundation")
            ),
            "anomalySeverityConfidence":bool(
                ((historical or {}).get("capabilities") or {}).get("anomalySeverityConfidence")
            ),
            "driverAttributionFoundation":bool(
                ((historical or {}).get("capabilities") or {}).get("driverAttributionFoundation")
            ),
            "smartIssuesFoundation":bool(
                ((historical or {}).get("capabilities") or {}).get("smartIssuesFoundation")
            ),
            "operatorActionPolicyFoundation":bool(
                ((historical or {}).get("capabilities") or {}).get("operatorActionPolicyFoundation")
            ),
            "productionCutoverShadowMode":bool(
                ((historical or {}).get("capabilities") or {}).get("productionCutoverShadowMode")
            ),
            "productionCutover":False,
            "operatorActions":False,
            "smartIssues":False,
            "diagnosis":False,
            "anomalySeverity":False,
            "anomalyDetection":False,
            "historicalAlerts":False,
            "historicalDiagnosis":False,
        },
        "safety": {
            "productionDataMartWritten": False,
            "productionUiModified": False,
            "legacyPayloadPublished": False,
            "productionCutoverAuthorized":False,
            "productionActivationEnabled":False,
        },
    }

    qa = validate_payload(payload, shop_ids, contract)
    if qa["status"] != "PASS":
        failed = [x["name"] for x in qa["checks"] if x["status"] == "FAIL"]
        raise ValueError(f"payload QA failed: {failed}")

    payload_hash = _sha256_json(payload)
    fingerprint = _sha256_json({
        "contractVersion": contract.get("version"),
        "semanticFingerprint": semantic_fp,
        "historicalFingerprint": historical_fp,
        "payloadSha256": payload_hash,
    })

    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "ui_payload.json", payload)
    manifest_out = {
        "layer": s(contract.get("layer_name")),
        "contractVersion": s(contract.get("version")),
        "period": period,
        "sourceSemanticFingerprint": semantic_fp,
        "sourceHistoricalFingerprint": historical_fp,
        "payloadBuildFingerprint": fingerprint,
        "payloadSha256": payload_hash,
        "selectedShopIds": shop_ids,
        "selectedShopCount": len(shop_ids),
        "files": [{"file": "ui_payload.json", "sha256": payload_hash}],
        "safety": payload["safety"],
    }
    _write_json(output_dir / "payload_manifest.json", manifest_out)

    qa.update({
        "period": period,
        "payloadBuildFingerprint": fingerprint,
        "sourceSemanticFingerprint": semantic_fp,
        "sourceHistoricalFingerprint": historical_fp,
        "selectedShopCount": len(shop_ids),
        "selectedShopIds": shop_ids,
        "payloadReady": True,
        "safety": payload["safety"],
    })
    _write_json(output_dir / "payload_qa_report.json", qa)

    return {
        "status": "PASS",
        "period": period,
        "payloadReady": True,
        "payloadBuildFingerprint": fingerprint,
        "sourceSemanticFingerprint": semantic_fp,
        "sourceHistoricalFingerprint": historical_fp,
        "selectedShopCount": len(shop_ids),
        "outputLocation": str(output_dir),
        "portfolioCoverage": payload["portfolio"]["coverage"],
        "comparePairCount": len(pairs),
        "safety": payload["safety"],
    }
