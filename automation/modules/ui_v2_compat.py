"""Shared V2 compatibility helpers for the multi-shop native UI.

This module contains only reusable data-to-V2 adaptation and read-only template
compatibility logic. It is not a standalone preview system.
"""
from __future__ import annotations

import itertools
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from .ui_artifact import DATA_MARKER


V2_COMPATIBILITY_PATCH_VERSION="v2-production-shadow-mode-v17"


def _s(v: Any) -> str:
    return "" if v is None else str(v).strip()


def _n(v: Any) -> float:
    if v in (None, ""):
        return 0.0
    try:
        return float(v)
    except Exception:
        return 0.0


def _ratio(num: Any, den: Any) -> float:
    d=_n(den)
    return _n(num)/d if d else 0.0


def _date(v: Any) -> str:
    return _s(v)[:10]


def _pct_delta(cur: float, prev: float) -> float | None:
    return cur/prev-1.0 if prev else None


def _window(
    rows: Sequence[Mapping[str,Any]], start: str, end: str
) -> List[Mapping[str,Any]]:
    return [r for r in rows if start <= _date(r.get("date")) <= end]


def _period_metrics(
    rows: Sequence[Mapping[str,Any]], start: str, end: str
) -> Dict[str,Any]:
    selected=_window(rows,start,end)
    selected_dates=sorted({_date(r.get("date")) for r in selected if _date(r.get("date"))})
    gmv=sum(_n(r.get("placedGmv")) for r in selected)
    orders=sum(_n(r.get("placedOrders")) for r in selected)
    clicks=sum(_n(r.get("productClicks")) for r in selected)
    visits_available=len(selected_dates)==1 and all(
        "visits" in r and r.get("visits") not in (None,"") for r in selected
    )
    visits=(
        sum(_n(r.get("visits")) for r in selected)
        if visits_available else None
    )
    ads_spend=sum(_n(r.get("adsSpend")) for r in selected)
    ads_sales=sum(_n(r.get("adsAttributedSales")) for r in selected)
    return {
        "start":start,
        "end":end,
        "days":len(selected_dates),
        "observedStart":selected_dates[0] if selected_dates else "",
        "observedEnd":selected_dates[-1] if selected_dates else "",
        "gmv":gmv,
        "orders":orders,
        "visits":visits,
        "visitsAvailable":visits_available,
        "productClicks":clicks,
        "productClickRate":_ratio(clicks,visits) if visits_available else None,
        "cvr":_ratio(orders,clicks),
        "aov":_ratio(gmv,orders),
        "adsSpend":ads_spend,
        "adsSales":ads_sales,
        "roas":_ratio(ads_sales,ads_spend),
    }


def _shift_date(date_text: str, days: int) -> str:
    import datetime as dt
    d=dt.date.fromisoformat(date_text)
    return (d+dt.timedelta(days=days)).isoformat()


def _month_start(date_text: str) -> str:
    return date_text[:7]+"-01"


def _previous_month_same_day(date_text: str) -> Tuple[str,str]:
    import calendar
    import datetime as dt
    d=dt.date.fromisoformat(date_text)
    if d.month==1:
        y,m=d.year-1,12
    else:
        y,m=d.year,d.month-1
    day=min(d.day,calendar.monthrange(y,m)[1])
    return f"{y:04d}-{m:02d}-01",f"{y:04d}-{m:02d}-{day:02d}"


def _days_inclusive(start: str, end: str) -> int:
    import datetime as dt
    a=dt.date.fromisoformat(start)
    b=dt.date.fromisoformat(end)
    return max(0,(b-a).days+1)


def _shapley_drivers(
    cur: Mapping[str,Any], prev: Mapping[str,Any]
) -> Dict[str,Any]:
    keys=("productClicks","cvr","aov")
    labels={
        "productClicks":"Lượt nhấp vào sản phẩm",
        "cvr":"Tỷ lệ chuyển đổi",
        "aov":"AOV",
    }
    c={k:_n(cur.get(k)) for k in keys}
    p={k:_n(prev.get(k)) for k in keys}
    if any(c[k]<=0 or p[k]<=0 for k in keys):
        return {
            "status":"INSUFFICIENT_POSITIVE_FACTORS",
            "method":"SHAPLEY_3_FACTOR",
            "identity":"GMV = Product Clicks × CVR × AOV",
            "drivers":[],
        }

    def product(values: Mapping[str,float]) -> float:
        out=1.0
        for k in keys:
            out*=values[k]
        return out

    contribution={k:0.0 for k in keys}
    perms=list(itertools.permutations(keys))
    for perm in perms:
        state=dict(p)
        before=product(state)
        for key in perm:
            state[key]=c[key]
            after=product(state)
            contribution[key]+=after-before
            before=after
    for key in keys:
        contribution[key]/=len(perms)

    abs_total=sum(abs(v) for v in contribution.values()) or 1.0
    gmv_delta=_n(cur.get("gmv"))-_n(prev.get("gmv"))
    drivers=[]
    for key in keys:
        effect=contribution[key]
        drivers.append({
            "key":key,
            "label":labels[key],
            "current":c[key],
            "previous":p[key],
            "deltaPct":_pct_delta(c[key],p[key]),
            "effectValue":effect,
            "shareOfAbsoluteEffects":abs(effect)/abs_total,
            "shareOfNetChange":effect/gmv_delta if gmv_delta else 0.0,
            "direction":"positive" if effect>0 else (
                "negative" if effect<0 else "neutral"
            ),
        })
    drivers.sort(key=lambda x:abs(x["effectValue"]),reverse=True)
    for rank,row in enumerate(drivers,1):
        row["rank"]=rank

    out={
        "status":"READY",
        "method":"SHAPLEY_3_FACTOR",
        "identity":"GMV = Product Clicks × CVR × AOV",
        "drivers":drivers,
    }
    if bool(cur.get("visitsAvailable")) and bool(prev.get("visitsAvailable")):
        cur_visits=_n(cur.get("visits"))
        prev_visits=_n(prev.get("visits"))
        out["clickBridge"]={
            "visits":{
                "current":cur_visits,
                "previous":prev_visits,
                "deltaPct":_pct_delta(cur_visits,prev_visits),
            },
            "derivedClickRate":{
                "current":_ratio(cur.get("productClicks"),cur_visits),
                "previous":_ratio(prev.get("productClicks"),prev_visits),
                "deltaPct":None,
                "userFacing":False,
            },
            "productClicks":{
                "current":_n(cur.get("productClicks")),
                "previous":_n(prev.get("productClicks")),
                "deltaPct":_pct_delta(
                    _n(cur.get("productClicks")),_n(prev.get("productClicks"))
                ),
            },
        }
    return out


def _comparison(
    current: Mapping[str,Any], previous: Mapping[str,Any]
) -> Dict[str,Any]:
    keys=(
        "gmv","orders","visits","productClicks","productClickRate",
        "cvr","aov","adsSpend","roas",
    )
    return {
        k:_pct_delta(_n(current.get(k)),_n(previous.get(k))) for k in keys
    }


def _empty_baseline() -> Dict[str,Any]:
    metrics={}
    for key in (
        "gmv","orders","visits","productClicks","productClickRate",
        "cvr","aov","adsSpend","roas",
    ):
        metrics[key]={
            "status":"INSUFFICIENT_HISTORY",
            "sampleSize":0,
            "confidence":0.0,
            "alertEligible":False,
            "contextMatched":False,
        }
    return {
        "method":"MULTI_SHOP_PAYLOAD_NO_LONG_HISTORY",
        "candidateComparisons":0,
        "contextMatchedComparisons":0,
        "usingContextMatchedHistory":False,
        "metrics":metrics,
    }


HISTORY_METRIC_MAP={
    "placedGmv":"gmv",
    "placedOrders":"orders",
    "productClicks":"productClicks",
    "placedCvr":"cvr",
    "placedAov":"aov",
    "adsSpend":"adsSpend",
    "roas":"roas",
}


def _history_snapshot(
    source: Mapping[str,Any],
    window: Mapping[str,Any],
) -> Dict[str,Any]:
    start=_s(window.get("start"))
    end=_s(window.get("end"))
    out={
        "start":start,
        "end":end,
        "days":_days_inclusive(start,end) if start and end else 0,
        "observedStart":start,
        "observedEnd":end,
        "visits":None,
        "visitsAvailable":False,
        "productClickRate":None,
        "adsSales":_n(source.get("adsAttributedSales")),
    }
    for src,dst in HISTORY_METRIC_MAP.items():
        out[dst]=_n(source.get(src))
    return out


def _history_baseline(
    historical_context: Mapping[str,Any] | None,
) -> Dict[str,Any]:
    if not historical_context:
        return _empty_baseline()
    sw=((historical_context.get("comparators") or {}).get("sameWeekday") or {})
    if _s(sw.get("status"))!="READY":
        return _empty_baseline()
    sample_count=int(sw.get("sampleCount") or 0)
    src=sw.get("baseline") or {}
    metrics={}
    for src_key,dst_key in HISTORY_METRIC_MAP.items():
        stat=src.get(src_key) or {}
        metrics[dst_key]={
            "status":"READY",
            "sampleSize":sample_count,
            "median":_n(stat.get("median")),
            "mean":_n(stat.get("mean")),
            "min":_n(stat.get("min")),
            "max":_n(stat.get("max")),
            "confidence":0.0,
            "alertEligible":False,
            "contextMatched":False,
        }
    for key in ("visits","productClickRate"):
        metrics[key]={
            "status":"NOT_AVAILABLE",
            "sampleSize":0,
            "confidence":0.0,
            "alertEligible":False,
            "contextMatched":False,
        }
    matched=sw.get("contextMatchedBaseline") or {}
    matched_status=_s(matched.get("status")) or "INSUFFICIENT_CONTEXT_MATCHED_HISTORY"
    matched_count=int(matched.get("sampleCount") or 0)
    matched_required=int(matched.get("requiredSampleCount") or 0)
    matched_metrics={}
    if matched_status=="READY":
        matched_src=matched.get("baseline") or {}
        for src_key,dst_key in HISTORY_METRIC_MAP.items():
            stat=matched_src.get(src_key) or {}
            matched_metrics[dst_key]={
                "status":"READY",
                "sampleSize":matched_count,
                "median":_n(stat.get("median")),
                "mean":_n(stat.get("mean")),
                "min":_n(stat.get("min")),
                "max":_n(stat.get("max")),
                "confidence":0.0,
                "alertEligible":False,
                "contextMatched":True,
            }
    return {
        "method":"SAME_WEEKDAY_MEDIAN_FACTUAL",
        "candidateComparisons":sample_count,
        "contextMatchedComparisons":matched_count,
        "usingContextMatchedHistory":False,
        "sampleDates":list(sw.get("sampleDates") or []),
        "metrics":metrics,
        "contextMatchedBaseline":{
            "status":matched_status,
            "requiredSampleCount":matched_required,
            "sampleCount":matched_count,
            "sampleDates":list(matched.get("sampleDates") or []),
            "method":"SAME_WEEKDAY_CONTEXT_MATCHED_MEDIAN_FACTUAL",
            "metrics":matched_metrics,
            "silentFallbackUsed":False,
            "alertEligible":False,
            "diagnosisEligible":False,
            "causalClaimEligible":False,
        },
        "anomalyEligibility":dict(sw.get("anomalyEligibility") or {}),
        "anomalyDetectionFoundation":dict(sw.get("anomalyDetectionFoundation") or {}),
        "anomalySeverityConfidence":dict(sw.get("anomalySeverityConfidence") or {}),
        "driverAttributionFoundation":dict(sw.get("driverAttributionFoundation") or {}),
    }


def _historical_comparator(
    historical_context: Mapping[str,Any] | None,
    key: str,
) -> Mapping[str,Any]:
    if not historical_context:
        return {}
    name={
        "yesterday":"previousDay",
        "last7":"previous7d",
        "mtd":"previousMonthMtd",
    }.get(key,"")
    return ((historical_context.get("comparators") or {}).get(name) or {}) if name else {}


SMART_ISSUE_METRIC_LABELS={
    "placedGmv":"GMV",
    "placedOrders":"Đơn hàng",
    "productClicks":"Lượt nhấp vào sản phẩm",
    "placedAov":"AOV",
    "placedCvr":"CVR",
    "adsSpend":"Ads Spend",
    "adsAttributedSales":"Ads Sales",
    "roas":"ROAS",
    "cancelledSales":"Doanh số hủy",
    "netSalesAfterCancel":"Net Sales",
    "orderFees":"Order Fees",
    "totalPlatformCostRatio":"Tỷ lệ chi phí nền tảng",
}


def _smart_issue_summary(issue: Mapping[str,Any]) -> str:
    metric=_s(issue.get("affectedMetric"))
    label=SMART_ISSUE_METRIC_LABELS.get(metric,metric or "KPI")
    effect=_n(issue.get("effectPct"))
    direction="giảm" if effect<0 else ("tăng" if effect>0 else "thay đổi")
    pct_text=f"{abs(effect)*100:.1f}%"
    attr=_s(issue.get("attributionStatus"))
    driver=_s((issue.get("driverEvidence") or {}).get("topDriverMetric"))
    driver_label=SMART_ISSUE_METRIC_LABELS.get(driver,driver)
    if attr=="ATTRIBUTED" and driver_label:
        return (
            f"{label} {direction} {pct_text} so với baseline cùng bối cảnh; "
            f"{driver_label} là contribution định lượng lớn nhất theo business identity. "
            "Đây chưa phải kết luận nguyên nhân."
        )
    if attr=="ASSOCIATION_ONLY":
        return (
            f"{label} {direction} {pct_text} so với baseline cùng bối cảnh; "
            "hiện chỉ có association, chưa đủ identity attribution hoặc causal evidence."
        )
    return f"{label} {direction} {pct_text} so với baseline cùng bối cảnh."


def _smart_issues_for_period(
    historical_context: Mapping[str,Any] | None,
    key: str,
) -> Dict[str,Any]:
    if key!="yesterday" or not historical_context:
        return {
            "status":"NO_ISSUE","count":0,"issues":[],
            "surface":"LATEST_TRUSTED_OBSERVATION",
        }
    foundation=(historical_context.get("smartIssuesFoundation") or {})
    action_policy=(historical_context.get("operatorActionPolicyFoundation") or {})
    options_by_issue={}
    for option in action_policy.get("actionOptions") or []:
        options_by_issue.setdefault(_s(option.get("sourceIssueId")),[]).append(dict(option))
    issues=[]
    for raw in foundation.get("issues") or []:
        severity=_s(raw.get("severityLevel")) or "MEDIUM"
        issues.append({
            "anomalyId":_s(raw.get("issueId")),
            "issueId":_s(raw.get("issueId")),
            "metric":_s(raw.get("affectedMetric")),
            "label":SMART_ISSUE_METRIC_LABELS.get(
                _s(raw.get("affectedMetric")),
                _s(raw.get("affectedMetric")) or "KPI",
            ),
            "severity":"High" if severity=="HIGH" else "Med",
            "severityLevel":severity,
            "summary":_smart_issue_summary(raw),
            "evidence":"Smart Issue Foundation · evidence only",
            "confidenceScore":_n(raw.get("confidenceScore")),
            "score":round(_n(raw.get("severityScore"))*100),
            "metricDelta":raw.get("effectPct"),
            "baselineRobustZ":raw.get("modifiedZScore"),
            "historicalSampleSize":int(
                ((raw.get("contextEvidence") or {}).get("matchedSampleCount")) or 0
            ),
            "baselineStatus":"CONTEXT_MATCHED",
            "sourceComparator":_s(raw.get("sourceComparator")),
            "attributionStatus":_s(raw.get("attributionStatus")),
            "topDriverMetric":_s((raw.get("driverEvidence") or {}).get("topDriverMetric")),
            "unresolvedUncertainty":list(raw.get("unresolvedUncertainty") or []),
            "context":{
                "distorted":False,
                "matchEvaluation":_s(
                    (raw.get("contextEvidence") or {}).get("matchEvaluation")
                ),
            },
            "persistence":{},
            "reviewOptions":list(options_by_issue.get(_s(raw.get("issueId"))) or []),
            "reviewOptionCount":len(options_by_issue.get(_s(raw.get("issueId"))) or []),
            "operatorActionPolicyStatus":_s(action_policy.get("status")) or "NO_ACTION_OPTIONS",
            "diagnostic":{
                "nextChecks":[
                    _s(x.get("title"))
                    for x in options_by_issue.get(_s(raw.get("issueId"))) or []
                    if _s(x.get("title"))
                ],
                "contextNote":"Review options only; human review required and platform mutation is disabled.",
            },
            "operationalDiagnosisEnabled":False,
            "automaticAlertEligible":False,
            "actionRecommendationEligible":False,
            "causalClaimEligible":False,
            "rawFoundation":dict(raw),
        })
    return {
        "status":_s(foundation.get("status")) or "NO_ISSUE",
        "count":len(issues),
        "issues":issues,
        "surface":"LATEST_TRUSTED_OBSERVATION",
        "automaticAlertsEnabled":False,
        "actionRecommendationsEnabled":False,
        "operationalDiagnosisEnabled":False,
        "causalClaimsEnabled":False,
    }


def _period_model(
    rows: Sequence[Mapping[str,Any]], key: str, latest: str,
    historical_context: Mapping[str,Any] | None = None,
) -> Dict[str,Any]:
    if key=="yesterday":
        cur_start=cur_end=latest
        prev_start=prev_end=_shift_date(latest,-1)
    elif key=="last7":
        cur_end=latest
        cur_start=_shift_date(latest,-6)
        prev_end=_shift_date(cur_start,-1)
        prev_start=_shift_date(prev_end,-6)
    elif key=="mtd":
        cur_start=_month_start(latest)
        cur_end=latest
        prev_start,prev_end=_previous_month_same_day(latest)
    else:
        raise ValueError(key)

    current=_period_metrics(rows,cur_start,cur_end)
    previous=_period_metrics(rows,prev_start,prev_end)
    current_expected_days=_days_inclusive(cur_start,cur_end)
    previous_expected_days=_days_inclusive(prev_start,prev_end)
    current_complete=current["days"]==current_expected_days
    previous_complete=previous["days"]==previous_expected_days
    has_previous=current_complete and previous_complete
    historical_used=False
    hcomp=_historical_comparator(historical_context,key)
    if _s(hcomp.get("status"))=="READY":
        hcur=hcomp.get("currentWindow") or {}
        href=hcomp.get("referenceWindow") or {}
        expected_current_start=_s(hcur.get("start"))
        expected_current_end=_s(hcur.get("end"))
        window_matches=expected_current_start==cur_start and expected_current_end==cur_end
        previous=_history_snapshot(hcomp.get("reference") or {},href)
        current_expected_days=_days_inclusive(cur_start,cur_end)
        previous_expected_days=previous["days"]
        current_missing=list(hcomp.get("currentMissingDates") or [])
        previous_missing=list(hcomp.get("referenceMissingDates") or [])
        current_complete=(
            window_matches
            and current["days"]==current_expected_days
            and not current_missing
        )
        previous_complete=not previous_missing and previous["days"]==previous_expected_days
        has_previous=current_complete and previous_complete
        historical_used=has_previous
    delta=_comparison(current,previous) if has_previous else {
        k:None for k in (
            "gmv","orders","visits","productClicks","productClickRate",
            "cvr","aov","adsSpend","roas",
        )
    }
    drivers=_shapley_drivers(current,previous) if has_previous else {
        "status":"INSUFFICIENT_PREVIOUS_PERIOD",
        "method":"SHAPLEY_3_FACTOR",
        "identity":"GMV = Product Clicks × CVR × AOV",
        "drivers":[],
    }
    coverage=(historical_context or {}).get("coverage") or {}
    lifecycle_note=""
    if _s(coverage.get("coverageOrigin"))=="SHOP_LAUNCH":
        lifecycle_note=" Dữ liệu lịch sử được tính từ thời điểm shop bắt đầu hoạt động."
    elif _s(coverage.get("coverageOrigin"))=="ALL_ENABLED_SHOPS_ACTIVE":
        lifecycle_note=" Dữ liệu toàn hệ thống được tính từ khi tất cả shop hiện tại bắt đầu hoạt động."
    if not current_complete:
        note="Kỳ hiện tại chưa đủ dữ liệu để so sánh."+lifecycle_note
    elif not previous_complete:
        note="Chưa có kỳ trước đủ cùng số ngày để so sánh."+lifecycle_note
    elif historical_used:
        bc=hcomp.get("businessContext") or {}
        evaluation=_s(bc.get("matchEvaluation"))
        if evaluation=="CONTEXT_COMPATIBLE":
            context_note="Hai kỳ có bối cảnh bán hàng tương đồng."
        elif evaluation=="CONTEXT_DIFFERENT":
            context_note="Hai kỳ có bối cảnh bán hàng khác nhau; cần đọc mức chênh lệch thận trọng."
        else:
            context_note="Chưa đủ thông tin để xác nhận hai kỳ có bối cảnh bán hàng tương đồng."
        note=context_note+" So sánh dùng để nhận diện diễn biến; chưa đủ bằng chứng để kết luận nguyên nhân."+lifecycle_note
    else:
        note="Dữ liệu đã được đối soát; cần thêm lịch sử trước khi đánh giá mức độ bất thường."+lifecycle_note
    return {
        "current":current,
        "previous":previous,
        "delta":delta,
        "drivers":drivers,
        "context":{
            "distorted":False,
            "reasonCodes":[],
            "note":note,
        },
        "baseline":_history_baseline(historical_context) if key=="yesterday" else _empty_baseline(),
        "historicalComparator":{
            "status":"READY" if historical_used else _s(hcomp.get("status")) or "NOT_BOUND",
            "source":"historical_intelligence" if historical_used else "",
            "comparatorKey":{
                "yesterday":"previousDay","last7":"previous7d","mtd":"previousMonthMtd"
            }.get(key,""),
            "contextQualification":_s((hcomp.get("businessContext") or {}).get("matchEvaluation")) or "CONTEXT_UNKNOWN",
            "contextQualificationReason":_s(
                ((hcomp.get("businessContext") or {}).get("qualification") or {}).get("reason")
            ),
            "contextMatchedBaselineEligible":bool(
                ((historical_context or {}).get("businessContext") or {}).get("contextMatchedBaselineEnabled")
            ),
            "anomalyEligibilityStatus":_s(
                (hcomp.get("anomalyEligibility") or {}).get("status")
            ) or "ANOMALY_BLOCKED",
            "anomalyEligibilityReasonCodes":list(
                (hcomp.get("anomalyEligibility") or {}).get("reasonCodes") or []
            ),
            "anomalyDetectionFoundationStatus":_s(
                (hcomp.get("anomalyDetectionFoundation") or {}).get("status")
            ) or "NOT_EVALUATED",
            "deviationCandidateMetricCount":int(
                (hcomp.get("anomalyDetectionFoundation") or {}).get("deviationCandidateMetricCount") or 0
            ),
            "severityConfidenceStatus":_s(
                (hcomp.get("anomalySeverityConfidence") or {}).get("status")
            ) or "NOT_ASSESSED",
            "highestSignalSeverity":_s(
                (hcomp.get("anomalySeverityConfidence") or {}).get("highestSignalSeverity")
            ),
            "lowestEvidenceConfidence":_s(
                (hcomp.get("anomalySeverityConfidence") or {}).get("lowestEvidenceConfidence")
            ),
            "driverAttributionStatus":_s(
                (hcomp.get("driverAttributionFoundation") or {}).get("status")
            ) or "NOT_DIAGNOSED",
            "topAttributedTargetMetric":_s(
                (hcomp.get("driverAttributionFoundation") or {}).get("topAttributedTargetMetric")
            ),
            "topDriverMetric":_s(
                (hcomp.get("driverAttributionFoundation") or {}).get("topDriverMetric")
            ),
            "causalClaimEligible":False,
            "alertEligible":False,
            "diagnosisEligible":False,
        },
        "diagnosis":{
            "status":"HISTORICAL_COMPARATOR_CONTEXT_ONLY" if historical_used else "DERIVED_SCOPE_ONLY",
            "confidence":0.0,
            "alertEligible":False,
        },
        "smartIssues":_smart_issues_for_period(historical_context,key),
        "comparisonAvailable":has_previous,
        "comparisonCoverage":{
            "currentExpectedDays":current_expected_days,
            "currentObservedDays":current["days"],
            "currentComplete":current_complete,
            "previousExpectedDays":previous_expected_days,
            "previousObservedDays":previous["days"],
            "previousComplete":previous_complete,
        },
    }


def _source_health(
    scope_label: str,
    coverage: Mapping[str,Any],
    shop_meta: Mapping[str,Any]|None=None,
) -> List[Dict[str,Any]]:
    start=_s(coverage.get("windowStart"))
    end=_s(coverage.get("windowEnd"))
    rows=[{
        "name":scope_label,
        "range":f"{start} → {end}",
        "status":"ready",
        "months":0,
        "note":"Cửa sổ dữ liệu đã đối soát",
    }]
    if shop_meta:
        verified=(shop_meta.get("freshness") or {}).get("sourceVerifiedThrough") or {}
        for name,key in (
            ("Đơn hàng","orders"),
            ("Quảng cáo","ads"),
            ("Phân tích kinh doanh","business_insights"),
        ):
            rows.append({
                "name":name,
                "range":_s(verified.get(key)) or end,
                "status":"ready",
                "months":0,
                "note":"Nguồn đã được xác minh thời điểm cập nhật",
            })
    return rows


def _to_v2_payload(
    *,
    scope_label: str,
    daily: Sequence[Mapping[str,Any]],
    coverage: Mapping[str,Any],
    period: str,
    shop_meta: Mapping[str,Any]|None=None,
    historical_context: Mapping[str,Any]|None=None,
) -> Dict[str,Any]:
    dates=sorted({_date(r.get("date")) for r in daily if _date(r.get("date"))})
    if not dates:
        raise ValueError(f"{scope_label}: no daily rows")
    latest=min(dates[-1],_s(coverage.get("windowEnd")) or dates[-1])
    start=max(dates[0],_s(coverage.get("windowStart")) or dates[0])
    rows=[r for r in daily if start <= _date(r.get("date")) <= latest]
    periods={
        k:_period_model(rows,k,latest,historical_context)
        for k in ("yesterday","last7","mtd")
    }
    last7_current=periods["last7"]["current"]
    mtd_current=periods["mtd"]["current"]
    last7_label=(
        f"7 ngày gần nhất · "
        f"{_shift_date(latest,-6)[8:10]}/{_shift_date(latest,-6)[5:7]}"
        f"–{latest[8:10]}/{latest[5:7]}"
        if periods["last7"]["comparisonCoverage"]["currentComplete"] else
        f"{last7_current['days']} ngày khả dụng · "
        f"{last7_current['observedStart'][8:10]}/{last7_current['observedStart'][5:7]}"
        f"–{last7_current['observedEnd'][8:10]}/{last7_current['observedEnd'][5:7]}"
    )
    mtd_label=(
        f"Tháng này · 01–{latest[8:10]}/{latest[5:7]}"
        if periods["mtd"]["comparisonCoverage"]["currentComplete"] else
        f"MTD khả dụng · "
        f"{mtd_current['observedStart'][8:10]}/{mtd_current['observedStart'][5:7]}"
        f"–{mtd_current['observedEnd'][8:10]}/{mtd_current['observedEnd'][5:7]}"
    )
    labels={
        "yesterday":f"Ngày gần nhất · {latest[8:10]}/{latest[5:7]}",
        "last7":last7_label,
        "mtd":mtd_label,
    }
    return {
        "meta":{
            "loadedStart":start,
            "loadedEnd":latest,
            "period":period,
            "scopeLabel":scope_label,
            "derivedFrom":"multi_shop_ui_payload",
            "uniqueMetricPolicy":"DAILY_ONLY_DO_NOT_SUM",
            "historicalComparatorBound":bool(historical_context),
        },
        "health":{
            "sources":_source_health(scope_label,coverage,shop_meta),
        },
        "commandCenter":{
            "status":"READY",
            "commercialStage":"placed",
            "latestCompleteDate":latest,
            "periods":periods,
            "labels":labels,
            "historicalContextStatus":_s((historical_context or {}).get("status")) or "NOT_BOUND",
        },
    }


def derive_v2_compat_template(source: str) -> str:
    """Apply minimal compatibility behavior to the read-only production V2 source."""
    anchor=(
        'const periods=Object.fromEntries(["yesterday","last7","mtd"]'
        '.map(function(k){return [k,adaptLivePeriod(k,LIVE_CC.periods[k])] }));'
    )
    if anchor not in source:
        anchor=anchor.replace('] }',']}')
    if anchor not in source:
        raise ValueError("V2 compatibility patch anchor not found")

    patch=r'''
const periods=Object.fromEntries(["yesterday","last7","mtd"].map(function(k){return [k,adaptLivePeriod(k,LIVE_CC.periods[k])]}));
Object.entries(LIVE_CC.periods||{}).forEach(function(entry){
  const key=entry[0],raw=entry[1]||{};
  const bridge=raw.drivers&&raw.drivers.clickBridge;
  if(periods[key]&&bridge){
    const parts=[];
    if(bridge.visits&&bridge.visits.deltaPct!==null&&bridge.visits.deltaPct!==undefined){
      parts.push("Lượt truy cập "+pct(bridge.visits.deltaPct));
    }
    if(bridge.derivedClickRate&&bridge.derivedClickRate.userFacing!==false&&bridge.derivedClickRate.deltaPct!==null&&bridge.derivedClickRate.deltaPct!==undefined){
      parts.push("Tỷ lệ click "+pct(bridge.derivedClickRate.deltaPct));
    }
    if(bridge.productClicks&&bridge.productClicks.deltaPct!==null&&bridge.productClicks.deltaPct!==undefined){
      parts.push("Lượt nhấp vào sản phẩm "+pct(bridge.productClicks.deltaPct));
    }
    if(parts.length)periods[key].support=parts.join("; ")+".";
  }
  if(raw.smartIssues&&periods[key]){
    periods[key].guard=(raw.context&&raw.context.note)||"Dữ liệu kỳ so sánh đã được đối soát.";
    const cq=raw.historicalComparator&&raw.historicalComparator.contextQualification;
    const contextLabel=cq==="CONTEXT_COMPATIBLE"
      ?"Bối cảnh tương đồng"
      :(cq==="CONTEXT_DIFFERENT"?"Khác bối cảnh":(cq==="CONTEXT_UNKNOWN"?"Chưa xác định bối cảnh":""));
    periods[key].confidence=raw.comparisonAvailable===false
      ?"Chưa có kỳ đối chiếu"
      :(raw.historicalComparator&&raw.historicalComparator.status==="READY"
        ?("Đủ dữ liệu so sánh"+(contextLabel?" · "+contextLabel:""))
        :"So sánh cùng kỳ");
    if(contextLabel&&periods[key]){
      const contextExtra=contextLabel+"; kết quả dùng để nhận diện diễn biến, chưa đủ để kết luận nguyên nhân.";
      periods[key].support=periods[key].support
        ?periods[key].support+" "+contextExtra
        :contextExtra;
    }
    const ae=raw.historicalComparator&&raw.historicalComparator.anomalyEligibilityStatus;
    const df=raw.historicalComparator&&raw.historicalComparator.anomalyDetectionFoundationStatus;
    if(df==="DEVIATION_CANDIDATE"){
      const n=Number(raw.historicalComparator.deviationCandidateMetricCount||0);
      periods[key].support=(periods[key].support?periods[key].support+" ":"")+"Có "+n+" chỉ số cần theo dõi thêm; chưa đủ điều kiện phát hành cảnh báo.";
    }else if(ae==="ANOMALY_BLOCKED"){
      periods[key].support=(periods[key].support?periods[key].support+" ":"")+"Cần thêm dữ liệu lịch sử trước khi đánh giá mức độ bất thường.";
    }else if(ae==="ANOMALY_ELIGIBLE"&&df==="NORMAL"){
      periods[key].support=(periods[key].support?periods[key].support+" ":"")+"Các chỉ số đủ điều kiện hiện chưa cho thấy biến động cần cảnh báo.";
    }
    const b=raw.baseline||{};
    if(b.method==="SAME_WEEKDAY_MEDIAN_FACTUAL"&&Number(b.candidateComparisons||0)>0){
      const extra="Đã tham chiếu "+Number(b.candidateComparisons||0)+" ngày cùng thứ trong lịch sử.";
      periods[key].support=periods[key].support?periods[key].support+" "+extra:extra;
      const mb=b.contextMatchedBaseline||{};
      let matchedText="";
      if(mb.status==="READY"){
        matchedText="Có "+Number(mb.sampleCount||0)+" kỳ lịch sử cùng bối cảnh để tham chiếu.";
      }else if(mb.status==="INSUFFICIENT_CONTEXT_MATCHED_HISTORY"){
        matchedText="Chưa đủ kỳ lịch sử cùng bối cảnh ("+Number(mb.sampleCount||0)+"/"+Number(mb.requiredSampleCount||0)+"); hệ thống không dùng kỳ khác bối cảnh để thay thế.";
      }
      if(matchedText)periods[key].support=periods[key].support+" "+matchedText;
      const bdf=b.anomalyDetectionFoundation||{};
      if(bdf.status==="DEVIATION_CANDIDATE"){
        periods[key].support=periods[key].support+" Kết quả khác mức thường thấy và cần được theo dõi thêm.";
      }else if(bdf.status==="NORMAL"){
        periods[key].support=periods[key].support+" Kết quả đang nằm trong vùng thường thấy của các ngày cùng thứ.";
      }
    }
  }
  if(raw.comparisonAvailable===false&&periods[key]){
    const p=periods[key],cur=raw.current||{};
    p.delta="—";
    p.compare="chưa có kỳ đối chiếu";
    p.tone="neutral";
    p.pulse=horizonName(key)+" · GMV đơn đã đặt "+money(cur.gmv)+".";
    p.detail="Chưa đủ dữ liệu kỳ đối chiếu cho kỳ này.";
    p.guard=(raw.context&&raw.context.note)||"Chưa có dữ liệu kỳ đối chiếu.";
    p.confidence="Chưa có kỳ đối chiếu";
    p.kpis=(p.kpis||[]).map(function(x){return [x[0],x[1],"—","neutral"]});
    p.drivers=[];
    p.insights=[];
    p.action="Theo dõi thêm đến khi có một kỳ đối chiếu đầy đủ.";
    p.support="Chưa phân tích yếu tố tác động vì kỳ đối chiếu chưa đầy đủ.";
  }
});
'''.strip()
    derived=source.replace(anchor,patch,1)

    horizon_anchor=r'''function horizonName(key){
  if(key==="yesterday")return "Hôm qua";
  if(key==="last7")return "7 ngày gần nhất";
  return "Tháng này · MTD";
}'''
    horizon_patch=r'''function horizonName(key){
  if(key==="yesterday")return "Ngày gần nhất";
  if(key==="last7")return "7 ngày gần nhất";
  return "Tháng này · MTD";
}'''
    if horizon_anchor not in derived:
        raise ValueError("V2 latest-complete-day wording anchor not found")
    derived=derived.replace(horizon_anchor,horizon_patch,1)

    issue_anchor=r'''function renderIssues(){
  const issues=liveIssuesFor(selected);
  if(!issues.length){
    issueList.innerHTML='<div class="issue-empty">Không có vấn đề nào đạt ngưỡng cần xử lý trong kỳ đang xem.</div>';
    return;
  }'''
    issue_patch=r'''function renderIssues(){
  const issues=liveIssuesFor(selected);
  const rawStatus=periods[selected]&&periods[selected].raw&&periods[selected].raw.smartIssues&&periods[selected].raw.smartIssues.status;
  const issueCard=issueList&&issueList.closest(".card");
  const issueGrid=issueCard&&issueCard.parentElement;
  if(rawStatus==="NOT_AVAILABLE_IN_MULTI_SHOP_PAYLOAD"){
    if(issueCard)issueCard.hidden=true;
    if(issueGrid)issueGrid.style.gridTemplateColumns="1fr";
    return;
  }
  if(issueCard)issueCard.hidden=false;
  if(issueGrid)issueGrid.style.removeProperty("grid-template-columns");
  if(!issues.length){
    issueList.innerHTML='<div class="issue-empty">Không có vấn đề nào đạt ngưỡng cần xử lý trong kỳ đang xem.</div>';
    return;
  }'''
    if issue_anchor not in derived:
        raise ValueError("V2 issue-state compatibility anchor not found")
    derived=derived.replace(issue_anchor,issue_patch,1)

    title_anchor='title:x.label+" · toàn shop",'
    if title_anchor not in derived:
        raise ValueError("V2 Smart Issue title anchor not found")
    derived=derived.replace(title_anchor,'title:x.label,',1)

    action_anchor='''action:"Mở chẩn đoán →",
      drawer:true,'''
    if action_anchor not in derived:
        raise ValueError("V2 Smart Issue diagnosis-action anchor not found")
    action_patch='''action:x.operationalDiagnosisEnabled===true
        ?"Mở chẩn đoán →"
        :(Number(x.reviewOptionCount||0)>0
          ?Number(x.reviewOptionCount||0)+" lựa chọn review"
          :"Bằng chứng đã tổng hợp"),
      drawer:x.operationalDiagnosisEnabled===true,'''
    derived=derived.replace(action_anchor,action_patch,1)
    return derived


def validate_v2_template(text: str) -> Dict[str,bool]:
    return {
        "oneDataMarker":text.count(DATA_MARKER)==1,
        "sidebarPin":'id="sidebarPin"' in text,
        "scale125Preserved":"transform:scale(1.25)" in text,
        "darkMode":'[data-theme="dark"]' in text,
        "commandCenterRenderer":"const LIVE_CC=" in text and "function render()" in text,
    }
