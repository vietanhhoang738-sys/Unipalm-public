"""Deterministic historical-intelligence foundation for PREPRODUCTION.

Trusted history comes only from QA-passed published Semantic partitions.
RAW source presence is inventory evidence for future backfill, never trusted
business history by itself.
"""
from __future__ import annotations

import calendar
import datetime as dt
import hashlib
import itertools
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

ADDITIVE_FIELDS = (
    "placed_gmv", "placed_orders", "product_clicks",
    "ads_spend", "ads_attributed_sales", "cancelled_sales",
    "net_sales_after_cancel", "order_fees",
)
METRIC_NAMES = (
    "placedGmv", "placedOrders", "productClicks", "placedAov", "placedCvr",
    "adsSpend", "adsAttributedSales", "roas", "cancelledSales",
    "netSalesAfterCancel", "orderFees", "totalPlatformCostRatio",
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

def ratio(num: Any, den: Any) -> float:
    d = n(den)
    return n(num) / d if d else 0.0

def _sha256_json(value: Any) -> str:
    raw=json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":"),default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def _read_json(path: str | Path) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))

def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,sort_keys=True),encoding="utf-8")

def load_contract(path: str | Path) -> Dict[str, Any]:
    data=_read_json(path)
    if s(data.get("layer_name"))!="multi_shop_historical_intelligence_v1":
        raise ValueError("unexpected historical intelligence layer")
    if s(data.get("status"))!="PREPRODUCTION":
        raise ValueError("historical intelligence contract must remain PREPRODUCTION")
    inv=data.get("inventory_policy") or {}
    if s(inv.get("trusted_history_source"))!="PUBLISHED_SEMANTIC_QA_PASS":
        raise ValueError("trusted history must come from published semantic QA PASS")
    if s(inv.get("raw_source_presence_role"))!="BACKFILL_CANDIDATE_ONLY":
        raise ValueError("RAW source presence must remain backfill-candidate-only")
    safety=data.get("safety") or {}
    if any(bool(safety.get(k)) for k in (
        "write_production_data_mart","modify_production_ui","publish_legacy_payload",
        "enable_historical_alerts","enable_diagnosis",
    )):
        raise ValueError("historical intelligence safety contract is not fail-closed")
    detection=data.get("anomaly_detection_foundation") or {}
    if detection:
        if s(detection.get("statistical_method"))!="MODIFIED_Z_SCORE_MAD":
            raise ValueError("anomaly detection foundation must use MODIFIED_Z_SCORE_MAD")
        if any(bool(detection.get(k)) for k in (
            "operational_anomaly_detection_enabled","severity_enabled",
            "alerts_enabled","diagnosis_enabled","causal_claims_enabled",
        )):
            raise ValueError("anomaly detection foundation safety is not fail-closed")
        stats=set((data.get("baseline_policy") or {}).get("statistics") or [])
        if "mad" not in stats:
            raise ValueError("anomaly detection foundation requires MAD baseline statistics")
    severity=data.get("anomaly_severity_confidence") or {}
    if severity:
        if s(severity.get("source_state"))!="DEVIATION_CANDIDATE_ONLY":
            raise ValueError("severity/confidence must be candidate-only")
        if any(bool(severity.get(k)) for k in (
            "automatic_alerts_enabled","diagnosis_enabled","causal_claims_enabled"
        )):
            raise ValueError("severity/confidence safety is not fail-closed")
    attribution=data.get("driver_attribution_foundation") or {}
    if attribution:
        if s(attribution.get("source_detector_state"))!="DEVIATION_CANDIDATE_ONLY":
            raise ValueError("driver attribution must be deviation-candidate-only")
        if s(attribution.get("attribution_method"))!="EXACT_SHAPLEY_ON_BUSINESS_IDENTITY":
            raise ValueError("driver attribution must use exact identity Shapley")
        if any(bool(attribution.get(k)) for k in (
            "identity_contribution_is_causal_claim","operational_diagnosis_enabled",
            "automatic_alerts_enabled","causal_claims_enabled"
        )):
            raise ValueError("driver attribution safety is not fail-closed")
    smart=data.get("smart_issues_foundation") or {}
    if smart:
        if s(smart.get("source_detector_state"))!="DEVIATION_CANDIDATE_ONLY":
            raise ValueError("Smart Issues must be deviation-candidate-only")
        if any(bool(smart.get(k)) for k in (
            "operational_alerts_enabled","action_recommendations_enabled",
            "operational_diagnosis_enabled","causal_claims_enabled"
        )):
            raise ValueError("Smart Issues safety is not fail-closed")
        if int(smart.get("max_issues_per_comparator") or 0)!=1:
            raise ValueError("Smart Issues foundation requires one issue max per comparator")
    action=data.get("operator_action_policy_foundation") or {}
    if action:
        if s(action.get("source_issue_state"))!="ISSUE_READY_ONLY":
            raise ValueError("Operator Action Policy must be ISSUE_READY-only")
        if not bool(action.get("requires_human_review")):
            raise ValueError("Operator Action Policy requires human review")
        if any(bool(action.get(k)) for k in (
            "platform_mutation_allowed","automatic_execution_enabled",
            "automatic_alerts_enabled","causal_claims_enabled"
        )):
            raise ValueError("Operator Action Policy safety is not fail-closed")
        if int(action.get("max_options_per_issue") or 0)<=0:
            raise ValueError("Operator Action Policy requires bounded options per issue")
    shadow=data.get("production_cutover_shadow_mode_v1") or {}
    if not shadow or s(shadow.get("mode"))!="PREPRODUCTION_OBSERVE_ONLY":
        raise ValueError("Production cutover shadow mode must remain PREPRODUCTION_OBSERVE_ONLY")
    if not bool(shadow.get("cutover_requires_explicit_human_approval")):
        raise ValueError("Production cutover must require explicit human approval")
    if not bool(shadow.get("rollback_required")):
        raise ValueError("Production cutover shadow mode requires rollback controls")
    if any(bool(shadow.get(k)) for k in (
        "automatic_cutover_enabled","production_activation_enabled",
        "production_writes_enabled","platform_mutation_allowed",
        "automatic_alerts_enabled",
    )):
        raise ValueError("Production cutover shadow mode safety is not fail-closed")
    if int(shadow.get("minimum_consecutive_safe_refreshes") or 0)<2:
        raise ValueError("Shadow mode requires multiple safe refreshes")
    if int(shadow.get("minimum_consecutive_stable_refreshes") or 0)<2:
        raise ValueError("Shadow mode requires multiple stable refreshes")
    return data

def _date(v: Any) -> str:
    return s(v)[:10]

def _to_date(v: str) -> dt.date:
    return dt.date.fromisoformat(v)

def _shift_date(v: str, days: int) -> str:
    return (_to_date(v)+dt.timedelta(days=days)).isoformat()

def _month_start(v: str) -> str:
    return v[:7]+"-01"

def _previous_month_same_day(v: str) -> str:
    d=_to_date(v)
    if d.month==1:
        year,month=d.year-1,12
    else:
        year,month=d.year,d.month-1
    last=calendar.monthrange(year,month)[1]
    if d.day>last:
        return ""
    return dt.date(year,month,d.day).isoformat()

def _months_back_same_day(v: str, count: int) -> List[str]:
    d=_to_date(v); out=[]; year,month=d.year,d.month
    for _ in range(count):
        month-=1
        if month==0:
            year-=1; month=12
        last=calendar.monthrange(year,month)[1]
        if d.day<=last:
            out.append(dt.date(year,month,d.day).isoformat())
    return out

def _expected_dates(start: str, end: str) -> List[str]:
    if not start or not end or start>end:
        return []
    a,b=_to_date(start),_to_date(end)
    return [(a+dt.timedelta(days=i)).isoformat() for i in range((b-a).days+1)]

def _aggregate(rows: Sequence[Mapping[str,Any]]) -> Dict[str,Any]:
    totals=defaultdict(float)
    for row in rows:
        for field in ADDITIVE_FIELDS:
            totals[field]+=n(row.get(field))
    return {
        "placedGmv":totals["placed_gmv"],
        "placedOrders":int(round(totals["placed_orders"])),
        "productClicks":int(round(totals["product_clicks"])),
        "placedAov":ratio(totals["placed_gmv"],totals["placed_orders"]),
        "placedCvr":ratio(totals["placed_orders"],totals["product_clicks"]),
        "adsSpend":totals["ads_spend"],
        "adsAttributedSales":totals["ads_attributed_sales"],
        "roas":ratio(totals["ads_attributed_sales"],totals["ads_spend"]),
        "cancelledSales":totals["cancelled_sales"],
        "netSalesAfterCancel":totals["net_sales_after_cancel"],
        "orderFees":totals["order_fees"],
        "totalPlatformCostRatio":ratio(
            totals["order_fees"]+totals["ads_spend"],totals["net_sales_after_cancel"]
        ),
    }

def _normalize_daily_row(row: Mapping[str,Any]) -> Dict[str,Any]:
    out={field:n(row.get(field)) for field in ADDITIVE_FIELDS}
    out["shop_id"]=s(row.get("shop_id"))
    out["data_date"]=_date(row.get("data_date"))
    return out

def _scope_rows(rows: Sequence[Mapping[str,Any]], shop_ids: Sequence[str]) -> List[Dict[str,Any]]:
    expected=list(shop_ids)
    by_date: Dict[str,Dict[str,Dict[str,Any]]]=defaultdict(dict)
    for raw in rows:
        row=_normalize_daily_row(raw); sid=row["shop_id"]; d=row["data_date"]
        if sid not in expected or not d:
            continue
        if sid in by_date[d]:
            raise ValueError(f"duplicate historical daily grain: {sid}/{d}")
        by_date[d][sid]=row
    out=[]
    for d in sorted(by_date):
        present=by_date[d]
        if set(present)!=set(expected):
            continue
        totals=defaultdict(float)
        for sid in expected:
            for field in ADDITIVE_FIELDS:
                totals[field]+=n(present[sid].get(field))
        out.append({"data_date":d,"shop_count_included":len(expected),**dict(totals)})
    return out

def _index(rows: Sequence[Mapping[str,Any]]) -> Dict[str,Mapping[str,Any]]:
    out={}
    for row in rows:
        d=_date(row.get("data_date"))
        if not d:
            continue
        if d in out:
            raise ValueError(f"duplicate scope date: {d}")
        out[d]=row
    return out

def _complete_window(idx: Mapping[str,Mapping[str,Any]], start: str, end: str):
    expected=_expected_dates(start,end)
    missing=[d for d in expected if d not in idx]
    return not missing,[idx[d] for d in expected if d in idx],missing

def _delta(current: Mapping[str,Any], reference: Mapping[str,Any]) -> Dict[str,Any]:
    out={}
    for metric in METRIC_NAMES:
        cv=n(current.get(metric)); rv=n(reference.get(metric))
        out[metric]={
            "current":cv,"reference":rv,"difference":cv-rv,
            "differencePct":(cv/rv-1.0) if rv else None,
        }
    return out

def _window_comparator(idx,current_start,current_end,reference_start,reference_end):
    cur_ok,cur_rows,cur_missing=_complete_window(idx,current_start,current_end)
    ref_ok,ref_rows,ref_missing=_complete_window(idx,reference_start,reference_end)
    status="READY" if cur_ok and ref_ok else "INSUFFICIENT_HISTORY"
    result={
        "status":status,
        "currentWindow":{"start":current_start,"end":current_end},
        "referenceWindow":{"start":reference_start,"end":reference_end},
        "currentMissingDates":cur_missing,
        "referenceMissingDates":ref_missing,
        "alertEligible":False,"diagnosisEligible":False,
    }
    if status=="READY":
        current=_aggregate(cur_rows); reference=_aggregate(ref_rows)
        result.update({"current":current,"reference":reference,"metrics":_delta(current,reference)})
    return result

def _stats(samples: Sequence[Mapping[str,Any]]) -> Dict[str,Any]:
    result={}
    for metric in METRIC_NAMES:
        vals=[n(x.get(metric)) for x in samples]
        if vals:
            median=statistics.median(vals)
            mad=statistics.median([abs(x-median) for x in vals])
            result[metric]={
                "median":median,"mean":sum(vals)/len(vals),
                "min":min(vals),"max":max(vals),"mad":mad,
            }
    return result

def _sample_comparator(idx,dates,min_samples):
    observed=[d for d in dates if d in idx]
    snapshots=[_aggregate([idx[d]]) for d in observed]
    return {
        "status":"READY" if len(observed)>=min_samples else "INSUFFICIENT_HISTORY",
        "requiredSampleCount":min_samples,"sampleCount":len(observed),
        "sampleDates":observed,"baseline":_stats(snapshots),
        "alertEligible":False,"diagnosisEligible":False,
    }

def _coverage(
    rows: Sequence[Mapping[str,Any]],
    lifecycle: Mapping[str,Any] | None = None,
) -> Dict[str,Any]:
    dates=sorted({_date(x.get("data_date")) for x in rows if _date(x.get("data_date"))})
    months=sorted({d[:7] for d in dates}); complete=[]; dset=set(dates)
    for month in months:
        year,mon=map(int,month.split("-"))
        expected={f"{month}-{day:02d}" for day in range(1,calendar.monthrange(year,mon)[1]+1)}
        if expected.issubset(dset):
            complete.append(month)
    lifecycle=dict(lifecycle or {})
    origin=s(lifecycle.get("origin")) or "UNSPECIFIED"
    start_policy=s(lifecycle.get("start_policy")) or "UNSPECIFIED"
    first=dates[0] if dates else ""
    last=dates[-1] if dates else ""
    lifecycle_start=(
        first
        if first and start_policy in {"FIRST_TRUSTED_SEMANTIC_DATE","LATEST_SHOP_LAUNCH_BOUNDARY"}
        else ""
    )
    pre_start=lifecycle.get("pre_start_dates_are_missing")
    history_span_days=(
        (_to_date(last)-_to_date(first)).days+1
        if first and last else 0
    )
    if origin=="SHOP_LAUNCH":
        interpretation="TRUSTED_HISTORY_BEGINS_AT_SHOP_LAUNCH"
    elif origin=="ALL_ENABLED_SHOPS_ACTIVE":
        interpretation="PORTFOLIO_BEGINS_WHEN_ALL_ENABLED_SHOPS_ARE_ACTIVE"
    elif origin=="PREEXISTING_BEFORE_TRUSTED_WINDOW":
        interpretation="TRUSTED_WINDOW_STARTS_AFTER_SHOP_LAUNCH"
    else:
        interpretation="TRUSTED_WINDOW_ONLY"
    return {
        "start":first,"end":last,
        "dayCount":len(dates),"historySpanDays":history_span_days,
        "availableMonths":months,"availableMonthCount":len(months),
        "completeMonths":complete,"completeMonthCount":len(complete),
        "calendarCompleteMonths":complete,"calendarCompleteMonthCount":len(complete),
        "coverageOrigin":origin,"startPolicy":start_policy,
        "lifecycleStartDate":lifecycle_start,
        "preStartDatesAreMissing":pre_start,
        "coverageInterpretation":interpretation,
    }

def _context_scope_rows(
    rows: Sequence[Mapping[str,Any]],
    *,
    platforms: Sequence[str],
    shop_ids: Sequence[str],
) -> List[Dict[str,Any]]:
    platform_set={s(x) for x in platforms if s(x)}
    shop_set={s(x) for x in shop_ids if s(x)}
    out=[]
    for raw in rows or []:
        row=dict(raw)
        scope=s(row.get("scope_type"))
        platform=s(row.get("platform"))
        sid=s(row.get("shop_id"))
        if scope=="MARKET":
            out.append(row)
        elif scope=="PLATFORM" and platform in platform_set:
            out.append(row)
        elif scope=="SHOP" and sid in shop_set:
            out.append(row)
    return out


def _matching_profile(
    rows: Sequence[Mapping[str,Any]],
    dates: Sequence[str],
) -> List[Dict[str,Any]]:
    wanted=set(dates)
    profiles: Dict[tuple[str,str,str], Dict[str,Any]]={}
    for raw in rows:
        row=dict(raw)
        d=_date(row.get("data_date"))
        if d not in wanted or not bool(row.get("matching_eligible")):
            continue
        key=(
            s(row.get("scope_type")),
            s(row.get("platform")),
            s(row.get("context_family")),
        )
        if not all(key):
            continue
        item=profiles.setdefault(key,{
            "scopeType":key[0],
            "platform":key[1],
            "contextFamily":key[2],
            "_dates":set(),
            "_peakDates":set(),
        })
        item["_dates"].add(d)
        if bool(row.get("is_peak_date")):
            item["_peakDates"].add(d)
    out=[]
    total=max(1,len(wanted))
    for key in sorted(profiles):
        item=profiles[key]
        day_count=len(item["_dates"])
        peak_count=len(item["_peakDates"])
        out.append({
            "scopeType":item["scopeType"],
            "platform":item["platform"],
            "contextFamily":item["contextFamily"],
            "dayCount":day_count,
            "peakDayCount":peak_count,
            "dayShare":day_count/total,
            "peakDayShare":peak_count/total,
        })
    return out


def _matching_signature(profile: Sequence[Mapping[str,Any]]) -> List[str]:
    return [
        "|".join([
            s(x.get("scopeType")),
            s(x.get("platform")),
            s(x.get("contextFamily")),
            str(int(x.get("dayCount") or 0)),
            str(int(x.get("peakDayCount") or 0)),
        ])
        for x in profile
    ]


def _context_window_summary(
    rows: Sequence[Mapping[str,Any]],
    dates: Sequence[str],
) -> Dict[str,Any]:
    wanted=set(dates)
    selected=[dict(x) for x in rows if _date(x.get("data_date")) in wanted]
    event_ids=sorted({s(x.get("context_id")) for x in selected if s(x.get("context_id"))})
    matching=[x for x in selected if bool(x.get("matching_eligible"))]
    profile=_matching_profile(rows,dates)
    matching_dates=sorted({_date(x.get("data_date")) for x in matching if _date(x.get("data_date"))})
    return {
        "status":"CONTEXT_AVAILABLE",
        "dateCount":len(wanted),
        "contextDayCount":len({_date(x.get("data_date")) for x in selected if _date(x.get("data_date"))}),
        "eventCount":len(event_ids),
        "eventIds":event_ids,
        "contextFamilies":sorted({s(x.get("context_family")) for x in selected if s(x.get("context_family"))}),
        "contextTypes":sorted({s(x.get("context_type")) for x in selected if s(x.get("context_type"))}),
        "platforms":sorted({s(x.get("platform")) for x in selected if s(x.get("platform"))}),
        "matchingEligibleEventIds":sorted({
            s(x.get("context_id")) for x in matching if s(x.get("context_id"))
        }),
        "matchingEligibleDayCount":len(matching_dates),
        "matchingEligibleDates":matching_dates,
        "matchingProfile":profile,
        "matchingSignature":_matching_signature(profile),
        "peakEventIds":sorted({
            s(x.get("context_id")) for x in selected
            if bool(x.get("is_peak_date")) and s(x.get("context_id"))
        }),
        "sourceTiers":sorted({s(x.get("source_tier")) for x in selected if s(x.get("source_tier"))}),
        "alertEligible":False,
        "diagnosisEligible":False,
    }


def _qualify_context_pair(
    current: Mapping[str,Any],
    reference: Mapping[str,Any],
    *,
    comparator_status: str,
) -> Dict[str,Any]:
    if comparator_status!="READY":
        return {
            "status":"CONTEXT_UNKNOWN",
            "reason":"COMPARATOR_NOT_READY",
            "currentSignature":list(current.get("matchingSignature") or []),
            "referenceSignature":list(reference.get("matchingSignature") or []),
            "alertEligible":False,
            "diagnosisEligible":False,
            "causalClaimEligible":False,
        }
    current_days=int(current.get("dateCount") or 0)
    reference_days=int(reference.get("dateCount") or 0)
    if current_days<=0 or reference_days<=0 or current_days!=reference_days:
        return {
            "status":"CONTEXT_UNKNOWN",
            "reason":"UNEQUAL_OR_EMPTY_WINDOW",
            "currentSignature":list(current.get("matchingSignature") or []),
            "referenceSignature":list(reference.get("matchingSignature") or []),
            "alertEligible":False,
            "diagnosisEligible":False,
            "causalClaimEligible":False,
        }
    cur_sig=list(current.get("matchingSignature") or [])
    ref_sig=list(reference.get("matchingSignature") or [])
    cur_has=bool(cur_sig)
    ref_has=bool(ref_sig)
    if not cur_has and not ref_has:
        status="CONTEXT_UNKNOWN"
        reason="NO_EXACT_MATCHING_EVENT_ON_EITHER_SIDE"
    elif cur_has!=ref_has:
        status="CONTEXT_DIFFERENT"
        reason="EXACT_MATCHING_EVENT_PRESENT_ON_ONE_SIDE_ONLY"
    elif cur_sig==ref_sig:
        status="CONTEXT_COMPATIBLE"
        reason="EXACT_MATCHING_PROFILE_EQUAL"
    else:
        status="CONTEXT_DIFFERENT"
        reason="EXACT_MATCHING_PROFILE_DIFFERENT"
    return {
        "status":status,
        "reason":reason,
        "currentSignature":cur_sig,
        "referenceSignature":ref_sig,
        "alertEligible":False,
        "diagnosisEligible":False,
        "causalClaimEligible":False,
    }


def _bind_window_context(
    comparator: Dict[str,Any],
    rows: Sequence[Mapping[str,Any]],
) -> None:
    cur=comparator.get("currentWindow") or {}
    ref=comparator.get("referenceWindow") or {}
    cur_dates=(
        _expected_dates(s(cur.get("start")),s(cur.get("end")))
        if s(cur.get("start")) and s(cur.get("end")) else []
    )
    ref_dates=(
        _expected_dates(s(ref.get("start")),s(ref.get("end")))
        if s(ref.get("start")) and s(ref.get("end")) else []
    )
    current=_context_window_summary(rows,cur_dates)
    reference=_context_window_summary(rows,ref_dates)
    qualification=_qualify_context_pair(
        current,reference,comparator_status=s(comparator.get("status"))
    )
    comparator["businessContext"]={
        "status":"CONTEXT_AVAILABLE",
        "current":current,
        "reference":reference,
        "matchEvaluation":qualification["status"],
        "qualification":qualification,
        "comparatorStatus":s(comparator.get("status")),
        "contextMatchedBaselineEligible":False,
        "alertEligible":False,
        "diagnosisEligible":False,
        "causalClaimEligible":False,
    }


def _build_context_matched_baseline(
    comparator: Dict[str,Any],
    idx: Mapping[str,Mapping[str,Any]],
    sample_qualifications: Sequence[Mapping[str,Any]],
) -> Dict[str,Any]:
    required=int(comparator.get("requiredSampleCount") or 0)
    compatible_dates=[
        s(x.get("sampleDate")) for x in sample_qualifications
        if s(x.get("status"))=="CONTEXT_COMPATIBLE"
        and s(x.get("sampleDate")) in idx
    ]
    out={
        "status":(
            "READY"
            if required>0 and len(compatible_dates)>=required
            else "INSUFFICIENT_CONTEXT_MATCHED_HISTORY"
        ),
        "requiredSampleCount":required,
        "sampleCount":len(compatible_dates),
        "sampleDates":compatible_dates,
        "sourceQualification":"CONTEXT_COMPATIBLE_ONLY",
        "allHistoryBaselinePreserved":True,
        "silentFallbackUsed":False,
        "alertEligible":False,
        "diagnosisEligible":False,
        "causalClaimEligible":False,
    }
    if out["status"]=="READY":
        snapshots=[_aggregate([idx[d]]) for d in compatible_dates]
        out["baseline"]=_stats(snapshots)
    return out


def _bind_sample_context(
    comparator: Dict[str,Any],
    rows: Sequence[Mapping[str,Any]],
    current_date: str,
    idx: Mapping[str,Mapping[str,Any]],
) -> None:
    dates=[s(x) for x in comparator.get("sampleDates") or [] if s(x)]
    current=_context_window_summary(rows,[current_date] if current_date else [])
    sample_qualifications=[]
    for d in dates:
        sample=_context_window_summary(rows,[d])
        q=_qualify_context_pair(
            current,sample,
            comparator_status="READY" if s(comparator.get("status"))=="READY" else s(comparator.get("status")),
        )
        sample_qualifications.append({
            "sampleDate":d,
            "status":q["status"],
            "reason":q["reason"],
            "sampleSignature":q["referenceSignature"],
        })
    compatible=sum(1 for x in sample_qualifications if x["status"]=="CONTEXT_COMPATIBLE")
    different=sum(1 for x in sample_qualifications if x["status"]=="CONTEXT_DIFFERENT")
    unknown=sum(1 for x in sample_qualifications if x["status"]=="CONTEXT_UNKNOWN")
    if s(comparator.get("status"))!="READY":
        overall="CONTEXT_UNKNOWN"; reason="COMPARATOR_NOT_READY"
    elif compatible and not different and not unknown:
        overall="CONTEXT_COMPATIBLE"; reason="ALL_SAMPLES_CONTEXT_COMPATIBLE"
    elif different and not compatible and not unknown:
        overall="CONTEXT_DIFFERENT"; reason="ALL_SAMPLES_CONTEXT_DIFFERENT"
    else:
        overall="CONTEXT_UNKNOWN"; reason="MIXED_OR_UNKNOWN_SAMPLE_CONTEXT"
    matched=_build_context_matched_baseline(comparator,idx,sample_qualifications)
    comparator["contextMatchedBaseline"]=matched
    comparator["businessContext"]={
        "status":"CONTEXT_AVAILABLE",
        "current":current,
        "samples":_context_window_summary(rows,dates),
        "sampleQualifications":sample_qualifications,
        "sampleQualificationCounts":{
            "compatible":compatible,
            "different":different,
            "unknown":unknown,
        },
        "matchEvaluation":overall,
        "qualification":{
            "status":overall,
            "reason":reason,
            "alertEligible":False,
            "diagnosisEligible":False,
            "causalClaimEligible":False,
        },
        "contextMatchedBaselineEligible":matched["status"]=="READY",
        "contextMatchedBaselineStatus":matched["status"],
        "alertEligible":False,
        "diagnosisEligible":False,
        "causalClaimEligible":False,
    }


def _history_depth_reason_code(
    scope_status: str,
    coverage: Mapping[str,Any],
) -> str:
    if scope_status=="READY":
        return ""
    origin=s(coverage.get("coverageOrigin"))
    if origin=="SHOP_LAUNCH":
        return "SHOP_LIFECYCLE_HISTORY_TOO_SHORT"
    if origin=="ALL_ENABLED_SHOPS_ACTIVE":
        return "PORTFOLIO_LIFECYCLE_HISTORY_TOO_SHORT"
    return "INSUFFICIENT_HISTORY_DEPTH"


def _anomaly_eligibility_for_comparator(
    *,
    key: str,
    comparator: Mapping[str,Any],
    scope_status: str,
    coverage: Mapping[str,Any],
    context: Mapping[str,Any],
) -> Dict[str,Any]:
    reasons=[]
    if s(comparator.get("status"))!="READY":
        reasons.append("COMPARATOR_NOT_READY")
    if comparator.get("currentMissingDates") or comparator.get("referenceMissingDates"):
        reasons.append("DATA_WINDOW_INCOMPLETE")
    depth_reason=_history_depth_reason_code(scope_status,coverage)
    if depth_reason:
        reasons.append(depth_reason)

    context_ready=(
        s(context.get("status"))=="CONTEXT_AVAILABLE"
        and bool(s(context.get("sourceFingerprint")))
    )
    if not context_ready:
        reasons.append("CONTEXT_LINEAGE_UNAVAILABLE")

    bc=comparator.get("businessContext") or {}
    qualification=s(bc.get("matchEvaluation"))
    if key in {"previousDay","previous7d","previousMonthMtd"}:
        reasons.append("NO_STATISTICAL_BASELINE_METHOD")
        if qualification=="CONTEXT_DIFFERENT":
            reasons.append("CONTEXT_DIFFERENT")
        elif qualification=="CONTEXT_UNKNOWN":
            reasons.append("CONTEXT_UNKNOWN")
    else:
        matched=comparator.get("contextMatchedBaseline") or {}
        if s(matched.get("status"))!="READY":
            reasons.append("INSUFFICIENT_CONTEXT_MATCHED_HISTORY")
        if qualification=="CONTEXT_DIFFERENT":
            reasons.append("CONTEXT_DIFFERENT")
        elif qualification=="CONTEXT_UNKNOWN" and s(matched.get("status"))!="READY":
            reasons.append("CONTEXT_UNKNOWN")

    reasons=list(dict.fromkeys(reasons))
    metric_eligibility={}
    matched_baseline=(comparator.get("contextMatchedBaseline") or {}).get("baseline") or {}
    for metric in METRIC_NAMES:
        metric_reasons=list(reasons)
        if key in {"sameWeekday","sameDayOfMonth"}:
            if s((comparator.get("contextMatchedBaseline") or {}).get("status"))=="READY":
                if metric not in matched_baseline:
                    metric_reasons.append("METRIC_BASELINE_UNAVAILABLE")
        metric_reasons=list(dict.fromkeys(metric_reasons))
        metric_eligibility[metric]={
            "status":"ANOMALY_ELIGIBLE" if not metric_reasons else "ANOMALY_BLOCKED",
            "reasonCodes":metric_reasons,
            "severityEligible":False,
            "alertEligible":False,
            "diagnosisEligible":False,
            "causalClaimEligible":False,
        }

    any_eligible=any(x["status"]=="ANOMALY_ELIGIBLE" for x in metric_eligibility.values())
    return {
        "status":"ANOMALY_ELIGIBLE" if any_eligible else "ANOMALY_BLOCKED",
        "evaluationMethod":(
            "CONTEXT_MATCHED_SAMPLE_BASELINE"
            if key in {"sameWeekday","sameDayOfMonth"}
            else "FACTUAL_WINDOW_COMPARISON_ONLY"
        ),
        "reasonCodes":reasons,
        "metricEligibility":metric_eligibility,
        "anomalyDetectionEnabled":False,
        "severityEnabled":False,
        "alertEligible":False,
        "diagnosisEligible":False,
        "causalClaimEligible":False,
    }


def _bind_anomaly_eligibility(
    *,
    scope_status: str,
    coverage: Mapping[str,Any],
    context: Mapping[str,Any],
    comparators: Mapping[str,Any],
) -> Dict[str,Any]:
    eligible_count=0
    blocked_count=0
    metric_eligible_count=0
    metric_blocked_count=0
    for key,comp in comparators.items():
        result=_anomaly_eligibility_for_comparator(
            key=key,
            comparator=comp or {},
            scope_status=scope_status,
            coverage=coverage,
            context=context,
        )
        comp["anomalyEligibility"]=result
        if result["status"]=="ANOMALY_ELIGIBLE":
            eligible_count+=1
        else:
            blocked_count+=1
        for item in result["metricEligibility"].values():
            if item["status"]=="ANOMALY_ELIGIBLE":
                metric_eligible_count+=1
            else:
                metric_blocked_count+=1
    return {
        "status":"ANOMALY_ELIGIBLE" if metric_eligible_count else "ANOMALY_BLOCKED",
        "eligibleComparatorCount":eligible_count,
        "blockedComparatorCount":blocked_count,
        "eligibleMetricCount":metric_eligible_count,
        "blockedMetricCount":metric_blocked_count,
        "anomalyDetectionEnabled":False,
        "severityEnabled":False,
        "alertsEnabled":False,
        "diagnosisEnabled":False,
        "causalClaimsEnabled":False,
    }


def _observed_direction(current: float, baseline: float) -> str:
    if current>baseline:
        return "HIGHER"
    if current<baseline:
        return "LOWER"
    return "FLAT"


def _direction_passes(policy: str, observed: str) -> bool:
    if policy=="TWO_SIDED":
        return observed!="FLAT"
    if policy=="LOWER_ONLY":
        return observed=="LOWER"
    if policy=="HIGHER_ONLY":
        return observed=="HIGHER"
    return False


def _not_evaluated_detection(
    *,
    metric: str,
    reason: str,
    eligibility: Mapping[str,Any],
    current_value: float,
    directionality: str,
    min_effect_pct: float,
    z_threshold: float,
) -> Dict[str,Any]:
    return {
        "status":"NOT_EVALUATED",
        "reason":reason,
        "metric":metric,
        "currentValue":current_value,
        "eligibilityStatus":s(eligibility.get("status")) or "ANOMALY_BLOCKED",
        "eligibilityReasonCodes":list(eligibility.get("reasonCodes") or []),
        "method":"MODIFIED_Z_SCORE_MAD",
        "directionalityPolicy":directionality,
        "minimumEffectPct":min_effect_pct,
        "absoluteZThreshold":z_threshold,
        "scorePublished":False,
        "deviationCandidateIsAlert":False,
        "severityEligible":False,
        "alertEligible":False,
        "diagnosisEligible":False,
        "causalClaimEligible":False,
    }


def _detect_metric_deviation(
    *,
    metric: str,
    current_value: float,
    baseline_stat: Mapping[str,Any],
    eligibility: Mapping[str,Any],
    policy: Mapping[str,Any],
) -> Dict[str,Any]:
    directionality=s((policy.get("directionality") or {}).get(metric)) or "TWO_SIDED"
    min_effect=float((policy.get("minimum_effect_pct") or {}).get(metric) or 0.0)
    z_threshold=float(policy.get("absolute_z_threshold") or 3.5)
    z_constant=float(policy.get("modified_z_constant") or 0.67448975)

    if s(eligibility.get("status"))!="ANOMALY_ELIGIBLE":
        return _not_evaluated_detection(
            metric=metric,reason="ANOMALY_ELIGIBILITY_BLOCKED",
            eligibility=eligibility,current_value=current_value,
            directionality=directionality,min_effect_pct=min_effect,
            z_threshold=z_threshold,
        )
    if "median" not in baseline_stat or "mad" not in baseline_stat:
        return _not_evaluated_detection(
            metric=metric,reason="BASELINE_STATISTICS_UNAVAILABLE",
            eligibility=eligibility,current_value=current_value,
            directionality=directionality,min_effect_pct=min_effect,
            z_threshold=z_threshold,
        )

    median=float(baseline_stat.get("median") or 0.0)
    mad=float(baseline_stat.get("mad") or 0.0)
    if mad<=0:
        return _not_evaluated_detection(
            metric=metric,reason="ROBUST_SCALE_ZERO",
            eligibility=eligibility,current_value=current_value,
            directionality=directionality,min_effect_pct=min_effect,
            z_threshold=z_threshold,
        )
    if median==0:
        return _not_evaluated_detection(
            metric=metric,reason="RELATIVE_EFFECT_UNDEFINED",
            eligibility=eligibility,current_value=current_value,
            directionality=directionality,min_effect_pct=min_effect,
            z_threshold=z_threshold,
        )

    difference=current_value-median
    effect_pct=difference/abs(median)
    modified_z=z_constant*difference/mad
    observed=_observed_direction(current_value,median)
    direction_pass=_direction_passes(directionality,observed)
    effect_pass=abs(effect_pct)>=min_effect
    score_pass=abs(modified_z)>=z_threshold
    candidate=direction_pass and effect_pass and score_pass
    return {
        "status":"DEVIATION_CANDIDATE" if candidate else "NORMAL",
        "reason":"ROBUST_THRESHOLD_AND_EFFECT_GATE_MET" if candidate else "WITHIN_FOUNDATION_GUARDRAILS",
        "metric":metric,
        "currentValue":current_value,
        "baselineMedian":median,
        "baselineMad":mad,
        "difference":difference,
        "effectPct":effect_pct,
        "modifiedZScore":modified_z,
        "absoluteModifiedZScore":abs(modified_z),
        "observedDirection":observed,
        "directionalityPolicy":directionality,
        "directionGatePassed":direction_pass,
        "effectGatePassed":effect_pass,
        "scoreGatePassed":score_pass,
        "minimumEffectPct":min_effect,
        "absoluteZThreshold":z_threshold,
        "eligibilityStatus":"ANOMALY_ELIGIBLE",
        "eligibilityReasonCodes":[],
        "method":"MODIFIED_Z_SCORE_MAD",
        "scorePublished":True,
        "deviationCandidateIsAlert":False,
        "severityEligible":False,
        "alertEligible":False,
        "diagnosisEligible":False,
        "causalClaimEligible":False,
    }


def _bind_anomaly_detection_foundation(
    *,
    current_observation: Mapping[str,Any],
    comparators: Mapping[str,Any],
    contract: Mapping[str,Any],
) -> Dict[str,Any]:
    policy=contract.get("anomaly_detection_foundation") or {}
    scope_evaluated=0
    scope_candidates=0
    scope_normal=0
    scope_not_evaluated=0
    for key,comp in comparators.items():
        eligibility=comp.get("anomalyEligibility") or {}
        metric_eligibility=eligibility.get("metricEligibility") or {}
        matched=(comp.get("contextMatchedBaseline") or {}).get("baseline") or {}
        metric_results={}
        for metric in METRIC_NAMES:
            result=_detect_metric_deviation(
                metric=metric,
                current_value=n(current_observation.get(metric)),
                baseline_stat=matched.get(metric) or {},
                eligibility=metric_eligibility.get(metric) or {},
                policy=policy,
            )
            metric_results[metric]=result
            if result["status"]=="DEVIATION_CANDIDATE":
                scope_evaluated+=1; scope_candidates+=1
            elif result["status"]=="NORMAL":
                scope_evaluated+=1; scope_normal+=1
            else:
                scope_not_evaluated+=1
        comp_evaluated=sum(
            1 for x in metric_results.values()
            if x["status"] in {"NORMAL","DEVIATION_CANDIDATE"}
        )
        comp_candidates=sum(
            1 for x in metric_results.values()
            if x["status"]=="DEVIATION_CANDIDATE"
        )
        comp["anomalyDetectionFoundation"]={
            "status":(
                "DEVIATION_CANDIDATE" if comp_candidates
                else ("NORMAL" if comp_evaluated else "NOT_EVALUATED")
            ),
            "method":"MODIFIED_Z_SCORE_MAD",
            "currentObservationDate":s(current_observation.get("dataDate")),
            "evaluatedMetricCount":comp_evaluated,
            "deviationCandidateMetricCount":comp_candidates,
            "notEvaluatedMetricCount":len(metric_results)-comp_evaluated,
            "metricResults":metric_results,
            "operationalAnomalyDetectionEnabled":False,
            "severityEnabled":False,
            "alertsEnabled":False,
            "diagnosisEnabled":False,
            "causalClaimsEnabled":False,
        }
    return {
        "status":(
            "DEVIATION_CANDIDATE" if scope_candidates
            else ("NORMAL" if scope_evaluated else "NOT_EVALUATED")
        ),
        "method":"MODIFIED_Z_SCORE_MAD",
        "currentObservationDate":s(current_observation.get("dataDate")),
        "evaluatedMetricCount":scope_evaluated,
        "normalMetricCount":scope_normal,
        "deviationCandidateMetricCount":scope_candidates,
        "notEvaluatedMetricCount":scope_not_evaluated,
        "operationalAnomalyDetectionEnabled":False,
        "severityEnabled":False,
        "alertsEnabled":False,
        "diagnosisEnabled":False,
        "causalClaimsEnabled":False,
    }


def _evidence_tier(score: float, *, low_max: float, high_min: float) -> str:
    if score>=high_min:
        return "HIGH"
    if score>=low_max:
        return "MEDIUM"
    return "LOW"


def _not_assessed_severity_confidence(
    detector_status: str,
) -> Dict[str,Any]:
    return {
        "status":"NOT_ASSESSED",
        "sourceDetectorStatus":detector_status,
        "severityPublished":False,
        "confidencePublished":False,
        "businessImpactClaim":False,
        "alertEligible":False,
        "diagnosisEligible":False,
        "causalClaimEligible":False,
    }


def _assess_candidate_severity_confidence(
    *,
    detector_result: Mapping[str,Any],
    comparator: Mapping[str,Any],
    scope_status: str,
    policy: Mapping[str,Any],
) -> Dict[str,Any]:
    detector_status=s(detector_result.get("status"))
    if detector_status!="DEVIATION_CANDIDATE":
        return _not_assessed_severity_confidence(detector_status)

    severity_cfg=policy.get("severity_score") or {}
    confidence_cfg=policy.get("confidence_score") or {}
    abs_z=float(detector_result.get("absoluteModifiedZScore") or 0.0)
    z_threshold=float(detector_result.get("absoluteZThreshold") or 0.0)
    effect=abs(float(detector_result.get("effectPct") or 0.0))
    min_effect=float(detector_result.get("minimumEffectPct") or 0.0)

    statistical_component=(
        min(abs_z/(z_threshold*2.0),1.0)
        if z_threshold>0 else 0.0
    )
    effect_component=(
        min(effect/(min_effect*3.0),1.0)
        if min_effect>0 else 0.0
    )
    stat_weight=float(severity_cfg.get("statistical_weight") or 0.5)
    effect_weight=float(severity_cfg.get("effect_weight") or 0.5)
    weight_total=stat_weight+effect_weight or 1.0
    severity_score=(
        statistical_component*stat_weight+effect_component*effect_weight
    )/weight_total
    severity_level=_evidence_tier(
        severity_score,
        low_max=float(severity_cfg.get("low_max_exclusive") or 0.55),
        high_min=float(severity_cfg.get("high_min_inclusive") or 0.8),
    )

    matched=comparator.get("contextMatchedBaseline") or {}
    required=int(matched.get("requiredSampleCount") or 0)
    sample_count=int(matched.get("sampleCount") or 0)
    sample_depth_component=(
        min(sample_count/(required*2.0),1.0)
        if required>0 else 0.0
    )
    business_context=comparator.get("businessContext") or {}
    current_context=business_context.get("current") or {}
    exact_context_component=(
        1.0
        if bool(current_context.get("matchingSignature"))
        and s(business_context.get("status"))=="CONTEXT_AVAILABLE"
        else 0.0
    )
    history_component=1.0 if scope_status=="READY" else 0.0
    robust_component=(
        1.0
        if bool(detector_result.get("scorePublished"))
        and float(detector_result.get("baselineMad") or 0.0)>0
        else 0.0
    )
    sample_weight=float(confidence_cfg.get("sample_depth_weight") or 0.5)
    context_weight=float(confidence_cfg.get("context_lineage_weight") or 0.2)
    history_weight=float(confidence_cfg.get("history_readiness_weight") or 0.15)
    robust_weight=float(confidence_cfg.get("robust_scale_weight") or 0.15)
    conf_weight_total=sample_weight+context_weight+history_weight+robust_weight or 1.0
    confidence_score=(
        sample_depth_component*sample_weight
        + exact_context_component*context_weight
        + history_component*history_weight
        + robust_component*robust_weight
    )/conf_weight_total
    confidence_level=_evidence_tier(
        confidence_score,
        low_max=float(confidence_cfg.get("low_max_exclusive") or 0.6),
        high_min=float(confidence_cfg.get("high_min_inclusive") or 0.85),
    )

    return {
        "status":"ASSESSED",
        "sourceDetectorStatus":"DEVIATION_CANDIDATE",
        "severityLevel":severity_level,
        "severityScore":severity_score,
        "severityMeaning":"STATISTICAL_AND_RELATIVE_MAGNITUDE_ONLY_NOT_BUSINESS_IMPACT",
        "severityComponents":{
            "statisticalStrength":statistical_component,
            "relativeEffectStrength":effect_component,
        },
        "confidenceLevel":confidence_level,
        "confidenceScore":confidence_score,
        "confidenceComponents":{
            "contextMatchedSampleDepth":sample_depth_component,
            "exactContextLineage":exact_context_component,
            "historyReadiness":history_component,
            "robustScale":robust_component,
        },
        "sampleEvidence":{
            "sampleCount":sample_count,
            "requiredSampleCount":required,
        },
        "severityPublished":True,
        "confidencePublished":True,
        "businessImpactClaim":False,
        "alertEligible":False,
        "diagnosisEligible":False,
        "causalClaimEligible":False,
    }


def _bind_anomaly_severity_confidence(
    *,
    scope_status: str,
    comparators: Mapping[str,Any],
    contract: Mapping[str,Any],
) -> Dict[str,Any]:
    policy=contract.get("anomaly_severity_confidence") or {}
    assessed_count=0
    not_assessed_count=0
    severity_counts={"LOW":0,"MEDIUM":0,"HIGH":0}
    confidence_counts={"LOW":0,"MEDIUM":0,"HIGH":0}

    for comp in comparators.values():
        detection=comp.get("anomalyDetectionFoundation") or {}
        metric_results=detection.get("metricResults") or {}
        comp_assessed=0
        comp_severity={"LOW":0,"MEDIUM":0,"HIGH":0}
        comp_confidence={"LOW":0,"MEDIUM":0,"HIGH":0}
        for result in metric_results.values():
            assessment=_assess_candidate_severity_confidence(
                detector_result=result,
                comparator=comp,
                scope_status=scope_status,
                policy=policy,
            )
            result["severityConfidence"]=assessment
            if assessment["status"]=="ASSESSED":
                assessed_count+=1
                comp_assessed+=1
                severity_counts[assessment["severityLevel"]]+=1
                confidence_counts[assessment["confidenceLevel"]]+=1
                comp_severity[assessment["severityLevel"]]+=1
                comp_confidence[assessment["confidenceLevel"]]+=1
            else:
                not_assessed_count+=1
        comp["anomalySeverityConfidence"]={
            "status":"ASSESSED" if comp_assessed else "NOT_ASSESSED",
            "assessedCandidateMetricCount":comp_assessed,
            "notAssessedMetricCount":len(metric_results)-comp_assessed,
            "severityCounts":comp_severity,
            "confidenceCounts":comp_confidence,
            "highestSignalSeverity":next(
                (x for x in ("HIGH","MEDIUM","LOW") if comp_severity[x]>0),""
            ),
            "lowestEvidenceConfidence":next(
                (x for x in ("LOW","MEDIUM","HIGH") if comp_confidence[x]>0),""
            ),
            "businessImpactClaim":False,
            "automaticAlertsEnabled":False,
            "diagnosisEnabled":False,
            "causalClaimsEnabled":False,
        }

    return {
        "status":"ASSESSED" if assessed_count else "NOT_ASSESSED",
        "assessedCandidateMetricCount":assessed_count,
        "notAssessedMetricCount":not_assessed_count,
        "severityCounts":severity_counts,
        "confidenceCounts":confidence_counts,
        "highestSignalSeverity":next(
            (x for x in ("HIGH","MEDIUM","LOW") if severity_counts[x]>0),""
        ),
        "lowestEvidenceConfidence":next(
            (x for x in ("LOW","MEDIUM","HIGH") if confidence_counts[x]>0),""
        ),
        "businessImpactClaim":False,
        "automaticAlertsEnabled":False,
        "diagnosisEnabled":False,
        "causalClaimsEnabled":False,
    }


def _confidence_rank(level: str) -> int:
    return {"LOW":0,"MEDIUM":1,"HIGH":2}.get(s(level),-1)


def _identity_value(target_metric: str, values: Mapping[str,Any]) -> float | None:
    if target_metric=="placedGmv":
        return n(values.get("productClicks"))*n(values.get("placedCvr"))*n(values.get("placedAov"))
    if target_metric=="placedOrders":
        return n(values.get("productClicks"))*n(values.get("placedCvr"))
    if target_metric=="roas":
        den=n(values.get("adsSpend"))
        return n(values.get("adsAttributedSales"))/den if den else None
    if target_metric=="netSalesAfterCancel":
        return n(values.get("placedGmv"))-n(values.get("cancelledSales"))
    if target_metric=="totalPlatformCostRatio":
        den=n(values.get("netSalesAfterCancel"))
        return (n(values.get("orderFees"))+n(values.get("adsSpend")))/den if den else None
    return None


def _exact_identity_shapley(
    *,
    target_metric: str,
    drivers: Sequence[str],
    current_values: Mapping[str,Any],
    reference_values: Mapping[str,Any],
) -> Dict[str,Any] | None:
    drivers=list(drivers)
    if not drivers:
        return None
    reference_state={k:n(reference_values.get(k)) for k in drivers}
    current_state={k:n(current_values.get(k)) for k in drivers}
    ref_value=_identity_value(target_metric,reference_state)
    cur_value=_identity_value(target_metric,current_state)
    if ref_value is None or cur_value is None:
        return None
    contributions={k:0.0 for k in drivers}
    perms=list(itertools.permutations(drivers))
    for perm in perms:
        state=dict(reference_state)
        previous=_identity_value(target_metric,state)
        if previous is None:
            return None
        for driver in perm:
            state[driver]=current_state[driver]
            value=_identity_value(target_metric,state)
            if value is None:
                return None
            contributions[driver]+=value-previous
            previous=value
    denom=float(len(perms) or 1)
    contributions={k:v/denom for k,v in contributions.items()}
    return {
        "referenceModelValue":ref_value,
        "currentModelValue":cur_value,
        "modeledDifference":cur_value-ref_value,
        "contributions":contributions,
        "referenceDrivers":reference_state,
        "currentDrivers":current_state,
    }


def _associated_candidate_signals(
    metric_results: Mapping[str,Any],
    target_metric: str,
) -> List[Dict[str,Any]]:
    out=[]
    for metric,result in metric_results.items():
        if metric==target_metric or s(result.get("status"))!="DEVIATION_CANDIDATE":
            continue
        out.append({
            "metric":metric,
            "effectPct":result.get("effectPct"),
            "observedDirection":s(result.get("observedDirection")),
            "modifiedZScore":result.get("modifiedZScore"),
            "severityLevel":s((result.get("severityConfidence") or {}).get("severityLevel")),
            "confidenceLevel":s((result.get("severityConfidence") or {}).get("confidenceLevel")),
            "relationType":"CO_MOVING_DEVIATION_CANDIDATE",
            "causalClaim":False,
        })
    out.sort(key=lambda x:abs(float(x.get("effectPct") or 0.0)),reverse=True)
    return out


def _not_diagnosed_driver_attribution(
    *,
    detector_status: str,
    reason: str,
    associated_signals: Sequence[Mapping[str,Any]] | None = None,
) -> Dict[str,Any]:
    return {
        "status":"NOT_DIAGNOSED",
        "reason":reason,
        "sourceDetectorStatus":detector_status,
        "driverContributions":[],
        "associatedSignals":[dict(x) for x in (associated_signals or [])],
        "identityContributionIsCausalClaim":False,
        "operationalDiagnosisEnabled":False,
        "alertEligible":False,
        "diagnosisEligible":False,
        "causalClaimEligible":False,
    }


def _attribute_candidate_metric(
    *,
    metric: str,
    detector_result: Mapping[str,Any],
    metric_results: Mapping[str,Any],
    comparator: Mapping[str,Any],
    current_observation: Mapping[str,Any],
    policy: Mapping[str,Any],
) -> Dict[str,Any]:
    detector_status=s(detector_result.get("status"))
    associations=_associated_candidate_signals(metric_results,metric)
    if detector_status!="DEVIATION_CANDIDATE":
        return _not_diagnosed_driver_attribution(
            detector_status=detector_status,
            reason="NOT_DEVIATION_CANDIDATE",
            associated_signals=associations,
        )

    severity=detector_result.get("severityConfidence") or {}
    if s(severity.get("status"))!="ASSESSED":
        return _not_diagnosed_driver_attribution(
            detector_status=detector_status,
            reason="SEVERITY_CONFIDENCE_NOT_ASSESSED",
            associated_signals=associations,
        )
    minimum_conf=s(policy.get("minimum_confidence_level")) or "MEDIUM"
    if _confidence_rank(s(severity.get("confidenceLevel")))<_confidence_rank(minimum_conf):
        return _not_diagnosed_driver_attribution(
            detector_status=detector_status,
            reason="INSUFFICIENT_EVIDENCE_CONFIDENCE",
            associated_signals=associations,
        )

    spec=((policy.get("supported_identities") or {}).get(metric) or {})
    drivers=list(spec.get("drivers") or [])
    if not drivers:
        return {
            "status":"ASSOCIATION_ONLY",
            "reason":"NO_SUPPORTED_BUSINESS_IDENTITY",
            "sourceDetectorStatus":"DEVIATION_CANDIDATE",
            "identity":"",
            "driverContributions":[],
            "associatedSignals":associations,
            "identityContributionIsCausalClaim":False,
            "operationalDiagnosisEnabled":False,
            "alertEligible":False,
            "diagnosisEligible":False,
            "causalClaimEligible":False,
        }

    matched=(comparator.get("contextMatchedBaseline") or {}).get("baseline") or {}
    reference_values={}
    for driver in drivers:
        stat=matched.get(driver) or {}
        if "median" not in stat:
            return {
                "status":"ASSOCIATION_ONLY",
                "reason":"DRIVER_BASELINE_UNAVAILABLE",
                "sourceDetectorStatus":"DEVIATION_CANDIDATE",
                "identity":s(spec.get("identity")),
                "driverContributions":[],
                "associatedSignals":associations,
                "identityContributionIsCausalClaim":False,
                "operationalDiagnosisEnabled":False,
                "alertEligible":False,
                "diagnosisEligible":False,
                "causalClaimEligible":False,
            }
        reference_values[driver]=n(stat.get("median"))

    shapley=_exact_identity_shapley(
        target_metric=metric,
        drivers=drivers,
        current_values=current_observation,
        reference_values=reference_values,
    )
    if not shapley:
        return {
            "status":"ASSOCIATION_ONLY",
            "reason":"IDENTITY_EVALUATION_UNDEFINED",
            "sourceDetectorStatus":"DEVIATION_CANDIDATE",
            "identity":s(spec.get("identity")),
            "driverContributions":[],
            "associatedSignals":associations,
            "identityContributionIsCausalClaim":False,
            "operationalDiagnosisEnabled":False,
            "alertEligible":False,
            "diagnosisEligible":False,
            "causalClaimEligible":False,
        }

    target_baseline=float(detector_result.get("baselineMedian") or 0.0)
    baseline_residual=target_baseline-float(shapley["referenceModelValue"])
    alignment_pct=(
        abs(baseline_residual)/abs(target_baseline)
        if target_baseline else (0.0 if baseline_residual==0 else float("inf"))
    )
    max_alignment=float(policy.get("max_baseline_alignment_residual_pct") or 0.25)
    if alignment_pct>max_alignment:
        return {
            "status":"ASSOCIATION_ONLY",
            "reason":"BASELINE_IDENTITY_ALIGNMENT_TOO_WEAK",
            "sourceDetectorStatus":"DEVIATION_CANDIDATE",
            "identity":s(spec.get("identity")),
            "baselineAlignmentResidual":baseline_residual,
            "baselineAlignmentResidualPct":alignment_pct,
            "driverContributions":[],
            "associatedSignals":associations,
            "identityContributionIsCausalClaim":False,
            "operationalDiagnosisEnabled":False,
            "alertEligible":False,
            "diagnosisEligible":False,
            "causalClaimEligible":False,
        }

    modeled_gap=float(shapley["modeledDifference"])
    contributions=[]
    for driver,value in shapley["contributions"].items():
        ref=n(shapley["referenceDrivers"].get(driver))
        cur=n(shapley["currentDrivers"].get(driver))
        contributions.append({
            "driverMetric":driver,
            "contributionValue":value,
            "contributionShareOfModeledGap":value/modeled_gap if modeled_gap else None,
            "driverCurrent":cur,
            "driverReferenceMedian":ref,
            "driverDifference":cur-ref,
            "driverDirection":_observed_direction(cur,ref),
            "relationType":"IDENTITY_CONTRIBUTION",
            "causalClaim":False,
        })
    contributions.sort(key=lambda x:abs(float(x.get("contributionValue") or 0.0)),reverse=True)

    return {
        "status":"ATTRIBUTED",
        "reason":"SUPPORTED_BUSINESS_IDENTITY_SHAPLEY",
        "sourceDetectorStatus":"DEVIATION_CANDIDATE",
        "identity":s(spec.get("identity")),
        "attributionMethod":"EXACT_SHAPLEY_ON_BUSINESS_IDENTITY",
        "referenceSource":"CONTEXT_MATCHED_BASELINE_MEDIANS",
        "targetMetric":metric,
        "targetCurrentValue":detector_result.get("currentValue"),
        "targetBaselineMedian":detector_result.get("baselineMedian"),
        "targetObservedDifference":detector_result.get("difference"),
        "referenceModelValue":shapley["referenceModelValue"],
        "currentModelValue":shapley["currentModelValue"],
        "modeledDifference":modeled_gap,
        "baselineAlignmentResidual":baseline_residual,
        "baselineAlignmentResidualPct":alignment_pct,
        "identityClosureResidual":modeled_gap-sum(
            float(x.get("contributionValue") or 0.0) for x in contributions
        ),
        "driverContributions":contributions,
        "topDriverMetric":s((contributions[0] if contributions else {}).get("driverMetric")),
        "associatedSignals":associations,
        "evidenceConfidenceLevel":s(severity.get("confidenceLevel")),
        "signalSeverityLevel":s(severity.get("severityLevel")),
        "identityContributionIsCausalClaim":False,
        "operationalDiagnosisEnabled":False,
        "alertEligible":False,
        "diagnosisEligible":False,
        "causalClaimEligible":False,
    }


def _bind_driver_attribution_foundation(
    *,
    current_observation: Mapping[str,Any],
    comparators: Mapping[str,Any],
    contract: Mapping[str,Any],
) -> Dict[str,Any]:
    policy=contract.get("driver_attribution_foundation") or {}
    attributed=0
    association_only=0
    not_diagnosed=0
    for comp in comparators.values():
        detection=comp.get("anomalyDetectionFoundation") or {}
        metric_results=detection.get("metricResults") or {}
        comp_counts={"ATTRIBUTED":0,"ASSOCIATION_ONLY":0,"NOT_DIAGNOSED":0}
        for metric,result in metric_results.items():
            attribution=_attribute_candidate_metric(
                metric=metric,
                detector_result=result,
                metric_results=metric_results,
                comparator=comp,
                current_observation=current_observation,
                policy=policy,
            )
            result["driverAttribution"]=attribution
            comp_counts[attribution["status"]]+=1
            if attribution["status"]=="ATTRIBUTED":
                attributed+=1
            elif attribution["status"]=="ASSOCIATION_ONLY":
                association_only+=1
            else:
                not_diagnosed+=1
        attributed_items=[
            (metric,result.get("driverAttribution") or {},result)
            for metric,result in metric_results.items()
            if s((result.get("driverAttribution") or {}).get("status"))=="ATTRIBUTED"
        ]
        attributed_items.sort(
            key=lambda item:float(((item[2].get("severityConfidence") or {}).get("severityScore")) or 0.0),
            reverse=True,
        )
        top_item=attributed_items[0] if attributed_items else None
        comp["driverAttributionFoundation"]={
            "status":(
                "ATTRIBUTED" if comp_counts["ATTRIBUTED"]
                else ("ASSOCIATION_ONLY" if comp_counts["ASSOCIATION_ONLY"] else "NOT_DIAGNOSED")
            ),
            "counts":comp_counts,
            "topAttributedTargetMetric":top_item[0] if top_item else "",
            "topDriverMetric":s((top_item[1] if top_item else {}).get("topDriverMetric")),
            "operationalDiagnosisEnabled":False,
            "automaticAlertsEnabled":False,
            "causalClaimsEnabled":False,
        }
    return {
        "status":(
            "ATTRIBUTED" if attributed
            else ("ASSOCIATION_ONLY" if association_only else "NOT_DIAGNOSED")
        ),
        "attributedMetricCount":attributed,
        "associationOnlyMetricCount":association_only,
        "notDiagnosedMetricCount":not_diagnosed,
        "operationalDiagnosisEnabled":False,
        "automaticAlertsEnabled":False,
        "causalClaimsEnabled":False,
    }


def _signal_level_rank(level: str) -> int:
    return {"LOW":0,"MEDIUM":1,"HIGH":2}.get(s(level),-1)


def _smart_issue_rank(issue: Mapping[str,Any], policy: Mapping[str,Any]) -> tuple:
    attr_priority=(policy.get("attribution_priority") or {})
    metric_priority=(policy.get("business_metric_priority") or {})
    return (
        int(attr_priority.get(s(issue.get("attributionStatus"))) or 0),
        int(metric_priority.get(s(issue.get("affectedMetric"))) or 0),
        float(issue.get("severityScore") or 0.0),
        float(issue.get("confidenceScore") or 0.0),
        abs(float(issue.get("effectPct") or 0.0)),
    )


def _smart_issue_candidate(
    *,
    scope_key: str,
    comparator_key: str,
    metric: str,
    detector_result: Mapping[str,Any],
    comparator: Mapping[str,Any],
    coverage: Mapping[str,Any],
    history_depth_reason: str,
    latest_observation_date: str,
    policy: Mapping[str,Any],
) -> Dict[str,Any] | None:
    if s(detector_result.get("status"))!="DEVIATION_CANDIDATE":
        return None
    severity=detector_result.get("severityConfidence") or {}
    if s(severity.get("status"))!="ASSESSED":
        return None
    min_severity=s(policy.get("minimum_severity_level")) or "MEDIUM"
    min_conf=s(policy.get("minimum_confidence_level")) or "MEDIUM"
    if _signal_level_rank(s(severity.get("severityLevel")))<_signal_level_rank(min_severity):
        return None
    if _signal_level_rank(s(severity.get("confidenceLevel")))<_signal_level_rank(min_conf):
        return None

    attribution=detector_result.get("driverAttribution") or {}
    attr_status=s(attribution.get("status"))
    if attr_status not in set(policy.get("allowed_attribution_statuses") or []):
        return None

    bc=comparator.get("businessContext") or {}
    qualification=bc.get("qualification") or {}
    matched=comparator.get("contextMatchedBaseline") or {}
    top_contribution={}
    if attr_status=="ATTRIBUTED":
        contributions=list(attribution.get("driverContributions") or [])
        top_contribution=dict(contributions[0]) if contributions else {}

    uncertainty=list(policy.get("required_uncertainty") or [])
    if attr_status=="ATTRIBUTED":
        uncertainty.append("IDENTITY_CONTRIBUTION_NOT_CAUSAL")
    else:
        uncertainty.append("ASSOCIATION_ONLY_NOT_ATTRIBUTION")
    if s(bc.get("matchEvaluation"))!="CONTEXT_COMPATIBLE":
        uncertainty.append("CONTEXT_COMPATIBILITY_NOT_CONFIRMED")
    uncertainty=list(dict.fromkeys(x for x in uncertainty if x))

    issue_key={
        "scopeKey":scope_key,
        "observationDate":latest_observation_date,
        "affectedMetric":metric,
    }
    issue_id="SI_"+_sha256_json(issue_key)[:20]
    associated_metrics=[
        s(x.get("metric"))
        for x in attribution.get("associatedSignals") or []
        if s(x.get("metric"))
    ]
    return {
        "issueId":issue_id,
        "issueType":s(policy.get("issue_type")) or "PERFORMANCE_DEVIATION",
        "status":"ISSUE_READY",
        "scopeKey":scope_key,
        "observationDate":latest_observation_date,
        "sourceComparator":comparator_key,
        "affectedMetric":metric,
        "detectorStatus":"DEVIATION_CANDIDATE",
        "observedDirection":s(detector_result.get("observedDirection")),
        "currentValue":detector_result.get("currentValue"),
        "baselineMedian":detector_result.get("baselineMedian"),
        "effectPct":detector_result.get("effectPct"),
        "modifiedZScore":detector_result.get("modifiedZScore"),
        "severityLevel":s(severity.get("severityLevel")),
        "severityScore":severity.get("severityScore"),
        "confidenceLevel":s(severity.get("confidenceLevel")),
        "confidenceScore":severity.get("confidenceScore"),
        "attributionStatus":attr_status,
        "driverEvidence":{
            "identity":s(attribution.get("identity")),
            "topDriverMetric":s(attribution.get("topDriverMetric")),
            "topDriverContribution":top_contribution,
            "associatedSignalMetrics":associated_metrics[:5],
            "identityContributionIsCausalClaim":False,
        },
        "contextEvidence":{
            "status":s(bc.get("status")),
            "matchEvaluation":s(bc.get("matchEvaluation")),
            "qualificationReason":s(qualification.get("reason")),
            "matchedSampleCount":int(matched.get("sampleCount") or 0),
            "requiredMatchedSampleCount":int(matched.get("requiredSampleCount") or 0),
        },
        "lifecycleEvidence":{
            "coverageOrigin":s(coverage.get("coverageOrigin")),
            "historyDepthReason":history_depth_reason,
            "historySpanDays":int(coverage.get("historySpanDays") or 0),
        },
        "unresolvedUncertainty":uncertainty,
        "automaticAlertEligible":False,
        "actionRecommendationEligible":False,
        "operationalDiagnosisEnabled":False,
        "causalClaimEligible":False,
    }


def _bind_smart_issues_foundation(
    *,
    scope_key: str,
    latest_observation_date: str,
    coverage: Mapping[str,Any],
    history_depth_reason: str,
    comparators: Mapping[str,Any],
    contract: Mapping[str,Any],
) -> Dict[str,Any]:
    policy=contract.get("smart_issues_foundation") or {}
    comparator_issues=[]
    max_per_comp=int(policy.get("max_issues_per_comparator") or 1)
    max_scope=int(policy.get("max_issues_per_scope") or 5)

    for comparator_key,comp in comparators.items():
        metric_results=((comp.get("anomalyDetectionFoundation") or {}).get("metricResults") or {})
        candidates=[]
        for metric,result in metric_results.items():
            issue=_smart_issue_candidate(
                scope_key=scope_key,
                comparator_key=comparator_key,
                metric=metric,
                detector_result=result,
                comparator=comp,
                coverage=coverage,
                history_depth_reason=history_depth_reason,
                latest_observation_date=latest_observation_date,
                policy=policy,
            )
            if issue:
                candidates.append(issue)
        candidates.sort(key=lambda x:_smart_issue_rank(x,policy),reverse=True)
        selected=candidates[:max_per_comp]
        comp["smartIssuesFoundation"]={
            "status":"ISSUE_READY" if selected else "NO_ISSUE",
            "issueCount":len(selected),
            "issues":selected,
            "automaticAlertsEnabled":False,
            "actionRecommendationsEnabled":False,
            "operationalDiagnosisEnabled":False,
            "causalClaimsEnabled":False,
        }
        comparator_issues.extend(selected)

    best_by_metric={}
    for issue in comparator_issues:
        metric=s(issue.get("affectedMetric"))
        current=best_by_metric.get(metric)
        if current is None or _smart_issue_rank(issue,policy)>_smart_issue_rank(current,policy):
            best_by_metric[metric]=issue
    scope_issues=sorted(
        best_by_metric.values(),
        key=lambda x:_smart_issue_rank(x,policy),
        reverse=True,
    )[:max_scope]
    return {
        "status":"ISSUE_READY" if scope_issues else "NO_ISSUE",
        "issueCount":len(scope_issues),
        "issues":scope_issues,
        "dedupeKey":"AFFECTED_METRIC",
        "surface":"LATEST_TRUSTED_OBSERVATION",
        "automaticAlertsEnabled":False,
        "actionRecommendationsEnabled":False,
        "operationalDiagnosisEnabled":False,
        "causalClaimsEnabled":False,
    }


ACTION_REVIEW_TEMPLATES={
    "productClicks":{
        "title":"Rà soát traffic & khả năng hiển thị listing",
        "why":"Product Clicks là contribution đã định lượng; cần kiểm tra nguồn traffic và khả năng hiển thị trước khi thay đổi vận hành.",
        "prerequisites":[
            "Đối chiếu traffic source và trạng thái hiển thị listing trong cùng ngày quan sát.",
            "Xác nhận campaign/context hiện tại không tạo khác biệt ngoài evidence đã ghi nhận.",
        ],
        "monitor":["productClicks","placedCvr","placedGmv"],
        "verification":[
            "Xác minh Product Clicks có tiếp tục lệch khỏi baseline cùng bối cảnh ở lần refresh kế tiếp.",
            "Kiểm tra GMV/CVR có cùng chiều với thay đổi Product Clicks hay không.",
        ],
    },
    "placedCvr":{
        "title":"Rà soát conversion funnel & offer",
        "why":"CVR là contribution đã định lượng; cần kiểm tra funnel và offer trước khi cân nhắc bất kỳ thay đổi thương mại nào.",
        "prerequisites":[
            "Đối chiếu Product Clicks để loại trừ thay đổi traffic volume.",
            "Kiểm tra listing/offer/campaign context đang áp dụng trong ngày quan sát.",
        ],
        "monitor":["placedCvr","placedOrders","placedGmv"],
        "verification":[
            "Xác minh CVR vẫn lệch khỏi baseline cùng bối cảnh ở lần refresh kế tiếp.",
            "Kiểm tra Orders và GMV có phản ánh cùng hướng thay đổi CVR hay không.",
        ],
    },
    "placedAov":{
        "title":"Rà soát AOV, price & promotion mix",
        "why":"AOV là contribution đã định lượng; cần kiểm tra mix giá trị đơn và promotion trước khi cân nhắc thay đổi giá/khuyến mại.",
        "prerequisites":[
            "Đối chiếu product mix và promotion context của ngày quan sát.",
            "Xác nhận Orders/CVR không phải driver chính thay thế.",
        ],
        "monitor":["placedAov","placedOrders","placedGmv"],
        "verification":[
            "Xác minh AOV vẫn lệch khỏi baseline cùng bối cảnh ở lần refresh kế tiếp.",
            "Kiểm tra thay đổi product mix có giải thích được phần lớn chênh lệch AOV hay không.",
        ],
    },
    "adsSpend":{
        "title":"Rà soát Ads spend efficiency",
        "why":"Ads Spend là contribution đã định lượng; cần kiểm tra hiệu suất trước khi cân nhắc bất kỳ thay đổi bid/budget nào.",
        "prerequisites":[
            "Đối chiếu Ads Spend, Ads Sales và ROAS trong cùng cửa sổ.",
            "Xác nhận campaign context và trạng thái phân phối quảng cáo.",
        ],
        "monitor":["adsSpend","adsAttributedSales","roas"],
        "verification":[
            "Xác minh ROAS/Ads Sales có cùng pattern với thay đổi Ads Spend.",
            "Kiểm tra deviation còn tồn tại ở lần refresh kế tiếp.",
        ],
    },
    "adsAttributedSales":{
        "title":"Rà soát Ads-attributed sales",
        "why":"Ads Sales là contribution đã định lượng; cần kiểm tra chất lượng doanh thu quảng cáo trước khi thay đổi cấu hình Ads.",
        "prerequisites":[
            "Đối chiếu Ads Spend và ROAS trong cùng ngày.",
            "Xác nhận campaign context không thay đổi ngoài evidence đã ghi nhận.",
        ],
        "monitor":["adsAttributedSales","adsSpend","roas","placedGmv"],
        "verification":[
            "Xác minh Ads Sales vẫn lệch khỏi baseline cùng bối cảnh.",
            "Kiểm tra phần biến động Ads Sales có đồng thời xuất hiện ở GMV hay không.",
        ],
    },
    "cancelledSales":{
        "title":"Rà soát cancellation & fulfillment quality",
        "why":"Cancelled Sales là contribution đã định lượng; cần kiểm tra chất lượng đơn và fulfillment trước khi đưa ra biện pháp vận hành.",
        "prerequisites":[
            "Đối chiếu lý do hủy và trạng thái fulfillment nếu nguồn dữ liệu chi tiết khả dụng.",
            "Xác nhận biến động không đến từ thay đổi mix/campaign bất thường.",
        ],
        "monitor":["cancelledSales","netSalesAfterCancel","placedGmv"],
        "verification":[
            "Xác minh tỷ trọng hủy tiếp tục cao hơn baseline.",
            "Kiểm tra Net Sales After Cancel có cải thiện khi cancellation trở về vùng bình thường.",
        ],
    },
    "orderFees":{
        "title":"Rà soát fee & promotion cost structure",
        "why":"Order Fees là contribution đã định lượng; cần kiểm tra cấu trúc phí trước khi cân nhắc thay đổi promotion hay pricing.",
        "prerequisites":[
            "Đối chiếu các thành phần fixed/service/transaction fee nếu nguồn chi tiết khả dụng.",
            "Xác nhận campaign/promotion context của ngày quan sát.",
        ],
        "monitor":["orderFees","totalPlatformCostRatio","netSalesAfterCancel"],
        "verification":[
            "Xác minh tỷ lệ phí còn lệch sau khi điều chỉnh theo Net Sales.",
            "Kiểm tra deviation còn tồn tại ở lần refresh kế tiếp.",
        ],
    },
    "netSalesAfterCancel":{
        "title":"Rà soát chất lượng Net Sales",
        "why":"Net Sales After Cancel là contribution đã định lượng; cần kiểm tra GMV và cancellation trước khi quyết định can thiệp.",
        "prerequisites":[
            "Đối chiếu Placed GMV và Cancelled Sales trong cùng ngày.",
            "Xác nhận context/campaign không làm sai khác chất lượng đơn.",
        ],
        "monitor":["netSalesAfterCancel","placedGmv","cancelledSales"],
        "verification":[
            "Xác minh Net Sales vẫn lệch khỏi baseline cùng bối cảnh.",
            "Kiểm tra driver GMV/cancellation có còn chi phối modeled gap hay không.",
        ],
    },
}


def _review_option(
    *,
    issue: Mapping[str,Any],
    option_key: str,
    title: str,
    why: str,
    prerequisites: Sequence[str],
    monitor: Sequence[str],
    verification: Sequence[str],
    policy: Mapping[str,Any],
) -> Dict[str,Any]:
    option_id="AO_"+_sha256_json({
        "issueId":s(issue.get("issueId")),"optionKey":option_key
    })[:20]
    stop_checks=[
        "Dừng review option nếu Smart Issue không còn ISSUE_READY ở lần refresh kế tiếp.",
        "Không chuyển thành thay đổi vận hành nếu confidence giảm dưới MEDIUM hoặc context không còn đủ tương thích.",
    ]
    return {
        "actionOptionId":option_id,
        "status":s(policy.get("option_status")) or "REVIEW_OPTION",
        "optionKey":option_key,
        "title":title,
        "whyRelevant":why,
        "sourceIssueId":s(issue.get("issueId")),
        "scopeKey":s(issue.get("scopeKey")),
        "observationDate":s(issue.get("observationDate")),
        "affectedMetric":s(issue.get("affectedMetric")),
        "sourceComparator":s(issue.get("sourceComparator")),
        "evidenceLineage":{
            "severityLevel":s(issue.get("severityLevel")),
            "confidenceLevel":s(issue.get("confidenceLevel")),
            "attributionStatus":s(issue.get("attributionStatus")),
            "topDriverMetric":s((issue.get("driverEvidence") or {}).get("topDriverMetric")),
            "contextMatchEvaluation":s((issue.get("contextEvidence") or {}).get("matchEvaluation")),
        },
        "prerequisites":list(prerequisites),
        "monitorKpis":list(dict.fromkeys(x for x in monitor if x)),
        "verificationChecks":list(verification),
        "stopOrReversalChecks":stop_checks,
        "unresolvedUncertainty":list(issue.get("unresolvedUncertainty") or []),
        "executionMode":"HUMAN_REVIEW_ONLY",
        "requiresHumanReview":True,
        "prescriptiveRecommendation":False,
        "platformMutationAllowed":False,
        "automaticExecutionEligible":False,
        "automaticAlertEligible":False,
        "causalClaimEligible":False,
    }


def _action_options_for_issue(
    issue: Mapping[str,Any],
    policy: Mapping[str,Any],
) -> List[Dict[str,Any]]:
    if s(issue.get("status"))!="ISSUE_READY":
        return []
    affected=s(issue.get("affectedMetric"))
    options=[
        _review_option(
            issue=issue,
            option_key="VALIDATE_EVIDENCE_BEFORE_CHANGE",
            title="Xác minh evidence trước khi thay đổi vận hành",
            why=(
                "Smart Issue đã đủ ngưỡng evidence nhưng vẫn còn uncertainty; "
                "cần xác minh dữ liệu/context trước khi cân nhắc hành động."
            ),
            prerequisites=[
                "Xác nhận dữ liệu nguồn và ngày quan sát vẫn nằm trong trusted window.",
                "Đọc lại context, severity/confidence và attribution boundary của Smart Issue.",
            ],
            monitor=[affected,s((issue.get("driverEvidence") or {}).get("topDriverMetric"))],
            verification=[
                "Kiểm tra Smart Issue còn ISSUE_READY ở lần refresh kế tiếp.",
                "Xác nhận affected KPI vẫn vượt ngưỡng deviation trong cùng logic baseline.",
            ],
            policy=policy,
        )
    ]
    if (
        bool(policy.get("targeted_review_requires_attributed_driver"))
        and s(issue.get("attributionStatus"))=="ATTRIBUTED"
    ):
        driver=s((issue.get("driverEvidence") or {}).get("topDriverMetric"))
        template=ACTION_REVIEW_TEMPLATES.get(driver)
        rule=s((policy.get("targeted_driver_rules") or {}).get(driver))
        if template and rule:
            options.append(_review_option(
                issue=issue,
                option_key=rule,
                title=template["title"],
                why=template["why"],
                prerequisites=template["prerequisites"],
                monitor=template["monitor"],
                verification=template["verification"],
                policy=policy,
            ))
    return options[:int(policy.get("max_options_per_issue") or 2)]


def _bind_operator_action_policy_foundation(
    *,
    smart_issues: Mapping[str,Any],
    contract: Mapping[str,Any],
) -> Dict[str,Any]:
    policy=contract.get("operator_action_policy_foundation") or {}
    issues=list(smart_issues.get("issues") or [])
    actions=[]
    issue_options={}
    for issue in issues:
        options=_action_options_for_issue(issue,policy)
        issue_options[s(issue.get("issueId"))]=[x["actionOptionId"] for x in options]
        actions.extend(options)
    actions=actions[:int(policy.get("max_options_per_scope") or 6)]
    allowed_ids={x["actionOptionId"] for x in actions}
    issue_options={
        issue_id:[x for x in ids if x in allowed_ids]
        for issue_id,ids in issue_options.items()
    }
    return {
        "status":"ACTION_OPTIONS_READY" if actions else "NO_ACTION_OPTIONS",
        "actionOptionCount":len(actions),
        "actionOptions":actions,
        "issueActionOptionIds":issue_options,
        "sourceIssueCount":len(issues),
        "requiresHumanReview":True,
        "platformMutationAllowed":False,
        "automaticExecutionEnabled":False,
        "automaticAlertsEnabled":False,
        "causalClaimsEnabled":False,
    }


def _shadow_issue_action_state(
    portfolio: Mapping[str,Any],
    shops: Mapping[str,Mapping[str,Any]],
) -> Dict[str,Any]:
    issues={}
    actions={}
    scopes={"portfolio":portfolio,**dict(shops)}
    for scope_key,scope in scopes.items():
        smart=scope.get("smartIssuesFoundation") or {}
        action_policy=scope.get("operatorActionPolicyFoundation") or {}
        for issue in smart.get("issues") or []:
            issue_id=s(issue.get("issueId"))
            if issue_id:
                issues[issue_id]={
                    "scopeKey":scope_key,
                    "affectedMetric":s(issue.get("affectedMetric")),
                    "observationDate":s(issue.get("observationDate")),
                    "sourceComparator":s(issue.get("sourceComparator")),
                    "attributionStatus":s(issue.get("attributionStatus")),
                }
        for action in action_policy.get("actionOptions") or []:
            action_id=s(action.get("actionOptionId"))
            if action_id:
                actions[action_id]={
                    "scopeKey":scope_key,
                    "sourceIssueId":s(action.get("sourceIssueId")),
                    "optionKey":s(action.get("optionKey")),
                    "status":s(action.get("status")),
                }
    return {
        "issueIds":sorted(issues),
        "actionOptionIds":sorted(actions),
        "issues":{key:issues[key] for key in sorted(issues)},
        "actionOptions":{key:actions[key] for key in sorted(actions)},
    }


def _shadow_transition(
    previous: Mapping[str,Any],
    current: Mapping[str,Any],
) -> Dict[str,Any]:
    previous_issue_ids=set(previous.get("issueIds") or [])
    current_issue_ids=set(current.get("issueIds") or [])
    previous_action_ids=set(previous.get("actionOptionIds") or [])
    current_action_ids=set(current.get("actionOptionIds") or [])
    disappeared_issues=previous_issue_ids-current_issue_ids
    current_actions=current.get("actionOptions") or {}
    lineage_errors=[]
    for action_id,action in current_actions.items():
        source_issue=s(action.get("sourceIssueId"))
        if source_issue not in current_issue_ids:
            lineage_errors.append({
                "actionOptionId":action_id,
                "reason":"SOURCE_ISSUE_NOT_CURRENT",
            })
        if source_issue in disappeared_issues:
            lineage_errors.append({
                "actionOptionId":action_id,
                "reason":"ACTION_PERSISTED_AFTER_ISSUE_DISAPPEARED",
            })
    return {
        "issues":{
            "appeared":sorted(current_issue_ids-previous_issue_ids),
            "persisted":sorted(current_issue_ids&previous_issue_ids),
            "disappeared":sorted(previous_issue_ids-current_issue_ids),
        },
        "actionOptions":{
            "appeared":sorted(current_action_ids-previous_action_ids),
            "persisted":sorted(current_action_ids&previous_action_ids),
            "disappeared":sorted(previous_action_ids-current_action_ids),
        },
        "stateStable":(
            previous_issue_ids==current_issue_ids
            and previous_action_ids==current_action_ids
        ),
        "lineageValid":not lineage_errors,
        "lineageErrors":lineage_errors,
    }


def _build_shadow_mode_v1(
    *,
    portfolio: Mapping[str,Any],
    shops: Mapping[str,Mapping[str,Any]],
    expected_shop_ids: Sequence[str],
    trusted_months: Sequence[str],
    trusted_fingerprints: Sequence[str],
    context_fingerprint: str,
    as_of_period: str,
    contract: Mapping[str,Any],
    refresh_id: str,
    previous_shadow_state: Mapping[str,Any] | None,
) -> Dict[str,Any]:
    policy=contract.get("production_cutover_shadow_mode_v1") or {}
    previous=dict(previous_shadow_state or {})
    if "shadowModeV1" in previous:
        previous=dict(previous.get("shadowModeV1") or {})
    previous_current=previous.get("currentState") or {}
    current=_shadow_issue_action_state(portfolio,shops)
    transition=_shadow_transition(previous_current,current)

    source_snapshot={
        "asOfPeriod":as_of_period,
        "trustedSemanticMonths":list(trusted_months),
        "trustedSemanticFingerprints":list(trusted_fingerprints),
        "businessContextFingerprint":context_fingerprint,
    }
    source_snapshot["snapshotKey"]=_sha256_json(source_snapshot)
    previous_snapshot=previous.get("sourceSnapshot") or {}
    if previous_snapshot:
        period_regressed=s(previous_snapshot.get("asOfPeriod"))>as_of_period
        months_regressed=not set(previous_snapshot.get("trustedSemanticMonths") or []).issubset(
            set(trusted_months)
        )
        context_regressed=(
            bool(s(previous_snapshot.get("businessContextFingerprint")))
            and not bool(context_fingerprint)
        )
        lineage_regressed=period_regressed or months_regressed or context_regressed
        if lineage_regressed:
            lineage_status="REGRESSION_BLOCKED"
        elif s(previous_snapshot.get("snapshotKey"))==source_snapshot["snapshotKey"]:
            lineage_status="CONSISTENT"
        else:
            lineage_status="ADVANCED"
    else:
        lineage_regressed=False
        lineage_status="INITIALIZED"

    scopes=[portfolio]+list(shops.values())
    trusted_lineage_complete=(
        bool(trusted_months)
        and len(trusted_months)==len(trusted_fingerprints)
        and all(bool(s(x)) for x in trusted_fingerprints)
        and bool(context_fingerprint)
        and all(bool(s(scope.get("latestTrustedDate"))) for scope in scopes)
    )
    scopes_complete=set(shops)==set(expected_shop_ids) and bool(portfolio)
    safety_ok=all(
        not bool(scope.get("alertEligible"))
        and not bool(scope.get("diagnosisEligible"))
        and not any(bool((scope.get("operatorActionPolicyFoundation") or {}).get(k)) for k in (
            "platformMutationAllowed","automaticExecutionEnabled",
            "automaticAlertsEnabled","causalClaimsEnabled",
        ))
        for scope in scopes
    )
    transition_ok=bool(transition.get("lineageValid"))
    base_safe=(
        trusted_lineage_complete and scopes_complete and safety_ok
        and transition_ok and not lineage_regressed
    )

    refresh_id=s(refresh_id) or "LOCAL_"+source_snapshot["snapshotKey"][:16]
    previous_refresh_id=s(previous.get("refreshId"))
    same_refresh=bool(previous_refresh_id) and previous_refresh_id==refresh_id
    previous_safe=int(previous.get("consecutiveSafeRefreshes") or 0)
    previous_stable=int(previous.get("consecutiveStableRefreshes") or 0)
    if same_refresh:
        refresh_sequence=max(1,int(previous.get("refreshSequence") or 1))
        consecutive_safe=max(1,previous_safe) if base_safe else 0
        consecutive_stable=max(1,previous_stable) if base_safe else 0
    else:
        refresh_sequence=int(previous.get("refreshSequence") or 0)+1
        consecutive_safe=(previous_safe+1) if base_safe else 0
        stable_now=base_safe and (not previous or bool(transition.get("stateStable")))
        consecutive_stable=(previous_stable+1) if stable_now else (1 if base_safe else 0)

    min_safe=int(policy.get("minimum_consecutive_safe_refreshes") or 3)
    min_stable=int(policy.get("minimum_consecutive_stable_refreshes") or 3)
    gate_values={
        "TRUSTED_LINEAGE_COMPLETE":trusted_lineage_complete,
        "LINEAGE_CONTINUITY":not lineage_regressed,
        "ALL_ENABLED_SCOPES_PRESENT":scopes_complete,
        "FAIL_CLOSED_SAFETY":safety_ok,
        "ISSUE_ACTION_TRANSITIONS_VALID":transition_ok,
        "MINIMUM_SAFE_REFRESHES":consecutive_safe>=min_safe,
        "MINIMUM_STABLE_REFRESHES":consecutive_stable>=min_stable,
        "HUMAN_VISUAL_BASELINE_RETAINED":int(policy.get("approved_visual_baseline_run") or 0)==216,
    }
    gates=[]
    for name in policy.get("required_readiness_gates") or gate_values:
        passed=bool(gate_values.get(name))
        pending=name in {"MINIMUM_SAFE_REFRESHES","MINIMUM_STABLE_REFRESHES"} and not passed
        gates.append({
            "gate":name,
            "status":"PASS" if passed else ("PENDING" if pending else "FAIL"),
        })
    failed_gates=[x["gate"] for x in gates if x["status"]=="FAIL"]
    pending_gates=[x["gate"] for x in gates if x["status"]=="PENDING"]
    if failed_gates:
        status="CUTOVER_BLOCKED"
    elif not pending_gates:
        status="READY_FOR_HUMAN_CUTOVER_REVIEW"
    else:
        status="SHADOW_OBSERVING"

    record={
        "refreshId":refresh_id,
        "refreshSequence":refresh_sequence,
        "sourceSnapshotKey":source_snapshot["snapshotKey"],
        "lineageStatus":lineage_status,
        "issueCount":len(current["issueIds"]),
        "actionOptionCount":len(current["actionOptionIds"]),
        "safe":base_safe,
        "stateStable":bool(transition.get("stateStable")) if previous else True,
    }
    records=list(previous.get("refreshRecords") or [])
    if same_refresh and records:
        records[-1]=record
    else:
        records.append(record)
    max_records=int(policy.get("max_retained_refresh_records") or 10)
    records=records[-max_records:]

    return {
        "status":status,
        "mode":"PREPRODUCTION_OBSERVE_ONLY",
        "refreshId":refresh_id,
        "refreshSequence":refresh_sequence,
        "previousRefreshId":previous_refresh_id,
        "idempotentRefresh":same_refresh,
        "consecutiveSafeRefreshes":consecutive_safe,
        "consecutiveStableRefreshes":consecutive_stable,
        "minimumConsecutiveSafeRefreshes":min_safe,
        "minimumConsecutiveStableRefreshes":min_stable,
        "sourceSnapshot":source_snapshot,
        "lineageStatus":lineage_status,
        "currentState":current,
        "transition":transition,
        "readinessGates":gates,
        "failedGates":failed_gates,
        "pendingGates":pending_gates,
        "refreshRecords":records,
        "cutoverChecklist":[
            {"item":"SHADOW_READINESS_GATES_PASS","status":"PASS" if not failed_gates and not pending_gates else "PENDING"},
            {"item":"APPROVED_VISUAL_BASELINE_RUN_216_RETAINED","status":"PASS"},
            {"item":"LEGACY_PRODUCTION_PATH_RETAINED_FOR_ROLLBACK","status":"PASS"},
            {"item":"EXPLICIT_HUMAN_CUTOVER_APPROVAL","status":"PENDING"},
            {"item":"EXPLICIT_PRODUCTION_DEPLOYMENT_APPROVAL","status":"PENDING"},
        ],
        "activationControls":{
            "requiresExplicitHumanApproval":True,
            "requiresAllReadinessGatesPass":True,
            "productionActivationAllowed":False,
            "automaticCutoverEnabled":False,
            "cutoverAuthorized":False,
        },
        "rollbackControls":{
            "required":True,
            "legacyProductionPathRetained":True,
            "rollbackTarget":"CURRENT_LEGACY_PRODUCTION_PIPELINE",
            "automaticRollbackEnabled":False,
        },
        "productionWritesEnabled":False,
        "platformMutationAllowed":False,
        "automaticAlertsEnabled":False,
    }


def _scope_history(
    rows: Sequence[Mapping[str,Any]],
    contract: Mapping[str,Any],
    lifecycle: Mapping[str,Any] | None = None,
    scope_key: str = "",
    context_rows: Sequence[Mapping[str,Any]] | None = None,
    scope_platforms: Sequence[str] | None = None,
    scope_shop_ids: Sequence[str] | None = None,
    context_fingerprint: str = "",
) -> Dict[str,Any]:
    idx=_index(rows); cov=_coverage(rows,lifecycle)
    if not idx:
        return {
            "status":"INSUFFICIENT_HISTORY","sixMonthStatus":"INSUFFICIENT_HISTORY",
            "coverage":cov,"comparators":{},
            "smartIssuesFoundation":{
                "status":"NO_ISSUE","issueCount":0,"issues":[],
                "dedupeKey":"AFFECTED_METRIC","surface":"LATEST_TRUSTED_OBSERVATION",
                "automaticAlertsEnabled":False,"actionRecommendationsEnabled":False,
                "operationalDiagnosisEnabled":False,"causalClaimsEnabled":False,
            },
            "operatorActionPolicyFoundation":{
                "status":"NO_ACTION_OPTIONS","actionOptionCount":0,"actionOptions":[],
                "issueActionOptionIds":{},"sourceIssueCount":0,
                "requiresHumanReview":True,"platformMutationAllowed":False,
                "automaticExecutionEnabled":False,"automaticAlertsEnabled":False,
                "causalClaimsEnabled":False,
            },
            "context":{
                "status":"CONTEXT_AVAILABLE" if context_fingerprint else "CONTEXT_UNAVAILABLE",
                "sourceFingerprint":context_fingerprint,
                "availableDimensions":[],"alertEligible":False,
            },
            "alertEligible":False,"diagnosisEligible":False,
        }
    latest=max(idx); comp=contract.get("comparator_policy") or {}; minimum=contract.get("minimum_history") or {}
    previous_day=_window_comparator(idx,latest,latest,_shift_date(latest,-1),_shift_date(latest,-1))
    cur7=_shift_date(latest,-6); prev7end=_shift_date(cur7,-1); prev7start=_shift_date(prev7end,-6)
    previous_7d=_window_comparator(idx,cur7,latest,prev7start,prev7end)
    prev_same=_previous_month_same_day(latest)
    previous_mtd=(
        _window_comparator(idx,_month_start(latest),latest,_month_start(prev_same),prev_same)
        if prev_same else {
            "status":"INSUFFICIENT_HISTORY","reason":"previous month has no matching day-of-month",
            "alertEligible":False,"diagnosisEligible":False,
        }
    )
    sw=comp.get("same_weekday") or {}
    sw_dates=[_shift_date(latest,-7*k) for k in range(1,int(sw.get("lookback_weeks",8))+1)]
    same_weekday=_sample_comparator(
        idx,sw_dates,int(sw.get("min_samples") or minimum.get("same_weekday_min_samples") or 4)
    )
    sdom=comp.get("same_day_of_month") or {}
    sdom_dates=_months_back_same_day(latest,int(sdom.get("lookback_months",6)))
    same_day=_sample_comparator(
        idx,sdom_dates,int(sdom.get("min_samples") or minimum.get("same_day_of_month_min_samples") or 3)
    )
    scoped_context=_context_scope_rows(
        context_rows or [],
        platforms=scope_platforms or [],
        shop_ids=scope_shop_ids or [],
    )
    if context_fingerprint:
        for item in (previous_day,previous_7d,previous_mtd):
            _bind_window_context(item,scoped_context)
        for item in (same_weekday,same_day):
            _bind_sample_context(item,scoped_context,latest,idx)
    min_months=int(minimum.get("history_ready_min_complete_months") or 3)
    min_6m=int(minimum.get("six_month_intelligence_min_complete_months") or 6)
    history_ready=cov["completeMonthCount"]>=min_months
    six_month_ready=cov["completeMonthCount"]>=min_6m
    if history_ready:
        depth_reason="SUFFICIENT_HISTORY_DEPTH"
    elif cov.get("coverageOrigin") in {"SHOP_LAUNCH","ALL_ENABLED_SHOPS_ACTIVE"}:
        depth_reason="HISTORY_LENGTH_NOT_DATA_GAP"
    else:
        depth_reason="MORE_TRUSTED_HISTORY_REQUIRED"
    scope_status="READY" if history_ready else "INSUFFICIENT_HISTORY"
    comparators={
        "previousDay":previous_day,"previous7d":previous_7d,"previousMonthMtd":previous_mtd,
        "sameWeekday":same_weekday,"sameDayOfMonth":same_day,
    }
    context={
        "status":"CONTEXT_AVAILABLE" if context_fingerprint else "CONTEXT_UNAVAILABLE",
        "sourceLayer":s((contract.get("context_policy") or {}).get("source_layer")),
        "sourceFingerprint":context_fingerprint,
        "availableDimensions":[
            "context_id","context_type","context_family","platform",
            "source_tier","matching_eligible","is_peak_date"
        ] if context_fingerprint else [],
        "coverage":_context_window_summary(scoped_context,sorted(idx)) if context_fingerprint else {},
        "requiredPolicy":s((contract.get("context_policy") or {}).get("source_policy")),
        "reason":(
            "Explicit business context calendar is bound; factual comparator qualification and separate context-matched sample baselines are available when minimum sample requirements are met."
            if context_fingerprint else
            "No explicit campaign/calendar context dataset is bound yet."
        ),
        "contextMatchedBaselineEnabled":any(
            s((x.get("contextMatchedBaseline") or {}).get("status"))=="READY"
            for x in (same_weekday,same_day)
        ),
        "alertEligible":False,
    }
    anomaly_eligibility=_bind_anomaly_eligibility(
        scope_status=scope_status,
        coverage=cov,
        context=context,
        comparators=comparators,
    )
    latest_observation=_aggregate([idx[latest]])
    latest_observation["dataDate"]=latest
    anomaly_detection_foundation=_bind_anomaly_detection_foundation(
        current_observation=latest_observation,
        comparators=comparators,
        contract=contract,
    )
    anomaly_severity_confidence=_bind_anomaly_severity_confidence(
        scope_status=scope_status,
        comparators=comparators,
        contract=contract,
    )
    driver_attribution_foundation=_bind_driver_attribution_foundation(
        current_observation=latest_observation,
        comparators=comparators,
        contract=contract,
    )
    smart_issues_foundation=_bind_smart_issues_foundation(
        scope_key=scope_key or "UNSPECIFIED_SCOPE",
        latest_observation_date=latest,
        coverage=cov,
        history_depth_reason=depth_reason,
        comparators=comparators,
        contract=contract,
    )
    operator_action_policy_foundation=_bind_operator_action_policy_foundation(
        smart_issues=smart_issues_foundation,
        contract=contract,
    )
    return {
        "status":scope_status,
        "sixMonthStatus":"READY" if six_month_ready else "INSUFFICIENT_HISTORY",
        "historyDepthReason":depth_reason,
        "latestTrustedDate":latest,"coverage":cov,
        "comparators":comparators,
        "context":context,
        "anomalyEligibility":anomaly_eligibility,
        "anomalyDetectionFoundation":anomaly_detection_foundation,
        "anomalySeverityConfidence":anomaly_severity_confidence,
        "driverAttributionFoundation":driver_attribution_foundation,
        "smartIssuesFoundation":smart_issues_foundation,
        "operatorActionPolicyFoundation":operator_action_policy_foundation,
        "alertEligible":False,"diagnosisEligible":False,
    }

def validate_historical_output(payload,expected_shop_ids,contract):
    checks=[]
    def ck(name,ok,detail=None):
        checks.append({"name":name,"status":"PASS" if ok else "FAIL","detail":dict(detail or {})})
    shops=payload.get("shops") or {}
    ck("shop_scopes_complete",set(shops)==set(expected_shop_ids),{"observed":sorted(shops),"expected":sorted(expected_shop_ids)})
    scopes=[payload.get("portfolio") or {}]+list(shops.values())
    ck("alerts_fail_closed",all(not bool(x.get("alertEligible")) for x in scopes))
    ck("diagnosis_fail_closed",all(not bool(x.get("diagnosisEligible")) for x in scopes))
    context_fp=s((payload.get("historySources") or {}).get("businessContextFingerprint"))
    allowed_context_status={"CONTEXT_UNAVAILABLE","CONTEXT_AVAILABLE"}
    ck("context_claims_fail_closed",all(
        s((x.get("context") or {}).get("status")) in allowed_context_status
        and not bool((x.get("context") or {}).get("alertEligible")) for x in scopes
    ))
    if context_fp:
        ck("business_context_bound_all_scopes",all(
            s((x.get("context") or {}).get("status"))=="CONTEXT_AVAILABLE"
            and s((x.get("context") or {}).get("sourceFingerprint"))==context_fp
            for x in scopes
        ))
        comparator_context_errors=[]
        for label,scope in [("portfolio",payload.get("portfolio") or {})]+list(shops.items()):
            for key,c in (scope.get("comparators") or {}).items():
                bc=c.get("businessContext") or {}
                if s(bc.get("status"))!="CONTEXT_AVAILABLE":
                    comparator_context_errors.append((label,key))
                if bool(bc.get("alertEligible")) or bool(bc.get("diagnosisEligible")):
                    comparator_context_errors.append((label,key,"unsafe"))
        ck("comparator_context_bound_fail_closed",not comparator_context_errors,{
            "errors":comparator_context_errors[:20]
        })
        qualification_errors=[]
        allowed_qualifications={"CONTEXT_COMPATIBLE","CONTEXT_DIFFERENT","CONTEXT_UNKNOWN"}
        for label,scope in [("portfolio",payload.get("portfolio") or {})]+list(shops.items()):
            for key,c in (scope.get("comparators") or {}).items():
                bc=c.get("businessContext") or {}
                evaluation=s(bc.get("matchEvaluation"))
                if evaluation not in allowed_qualifications:
                    qualification_errors.append((label,key,evaluation))
                q=bc.get("qualification") or {}
                if bool(q.get("alertEligible")) or bool(q.get("diagnosisEligible")) or bool(q.get("causalClaimEligible")):
                    qualification_errors.append((label,key,"unsafe_qualification"))
        ck("context_qualification_factual_only",not qualification_errors,{
            "errors":qualification_errors[:20]
        })

        matched_errors=[]
        allowed_matched={"READY","INSUFFICIENT_CONTEXT_MATCHED_HISTORY"}
        for label,scope in [("portfolio",payload.get("portfolio") or {})]+list(shops.items()):
            scope_ready=False
            for key in ("sameWeekday","sameDayOfMonth"):
                comp=(scope.get("comparators") or {}).get(key) or {}
                matched=comp.get("contextMatchedBaseline") or {}
                status=s(matched.get("status"))
                if status not in allowed_matched:
                    matched_errors.append((label,key,status))
                    continue
                required=int(matched.get("requiredSampleCount") or 0)
                count=int(matched.get("sampleCount") or 0)
                has_stats=bool(matched.get("baseline"))
                if status=="READY":
                    scope_ready=True
                    if required<=0 or count<required or not has_stats:
                        matched_errors.append((label,key,"ready_contract"))
                else:
                    if count>=required and required>0:
                        matched_errors.append((label,key,"insufficient_count_contract"))
                    if has_stats:
                        matched_errors.append((label,key,"insufficient_stats_leak"))
                if bool(matched.get("silentFallbackUsed")):
                    matched_errors.append((label,key,"silent_fallback"))
                if any(bool(matched.get(flag)) for flag in (
                    "alertEligible","diagnosisEligible","causalClaimEligible"
                )):
                    matched_errors.append((label,key,"unsafe_matched_baseline"))
            if bool((scope.get("context") or {}).get("contextMatchedBaselineEnabled"))!=scope_ready:
                matched_errors.append((label,"scope_capability_mismatch"))
        ck("context_matched_baseline_contract",not matched_errors,{
            "errors":matched_errors[:30]
        })
    eligibility_errors=[]
    allowed_status={"ANOMALY_ELIGIBLE","ANOMALY_BLOCKED"}
    allowed_reasons=set(
        ((contract.get("anomaly_eligibility_policy") or {}).get("reason_codes") or [])
    )
    for label,scope in [("portfolio",payload.get("portfolio") or {})]+list(shops.items()):
        summary=scope.get("anomalyEligibility") or {}
        if s(summary.get("status")) not in allowed_status:
            eligibility_errors.append((label,"scope_status",summary.get("status")))
        if any(bool(summary.get(k)) for k in (
            "anomalyDetectionEnabled","severityEnabled","alertsEnabled",
            "diagnosisEnabled","causalClaimsEnabled"
        )):
            eligibility_errors.append((label,"unsafe_scope"))
        for key,comp in (scope.get("comparators") or {}).items():
            elig=comp.get("anomalyEligibility") or {}
            if s(elig.get("status")) not in allowed_status:
                eligibility_errors.append((label,key,"status"))
            unknown=[x for x in (elig.get("reasonCodes") or []) if x not in allowed_reasons]
            if unknown:
                eligibility_errors.append((label,key,"unknown_reasons",unknown))
            if any(bool(elig.get(k)) for k in (
                "anomalyDetectionEnabled","severityEnabled","alertEligible",
                "diagnosisEligible","causalClaimEligible"
            )):
                eligibility_errors.append((label,key,"unsafe"))
            for metric,item in (elig.get("metricEligibility") or {}).items():
                if s(item.get("status")) not in allowed_status:
                    eligibility_errors.append((label,key,metric,"metric_status"))
                if any(bool(item.get(k)) for k in (
                    "severityEligible","alertEligible","diagnosisEligible","causalClaimEligible"
                )):
                    eligibility_errors.append((label,key,metric,"unsafe_metric"))
    ck("anomaly_eligibility_guardrails_fail_closed",not eligibility_errors,{
        "errors":eligibility_errors[:40]
    })

    detection_errors=[]
    allowed_detection={"NORMAL","DEVIATION_CANDIDATE","NOT_EVALUATED"}
    for label,scope in [("portfolio",payload.get("portfolio") or {})]+list(shops.items()):
        summary=scope.get("anomalyDetectionFoundation") or {}
        if s(summary.get("status")) not in allowed_detection:
            detection_errors.append((label,"scope_status",summary.get("status")))
        if any(bool(summary.get(k)) for k in (
            "operationalAnomalyDetectionEnabled","severityEnabled","alertsEnabled",
            "diagnosisEnabled","causalClaimsEnabled"
        )):
            detection_errors.append((label,"unsafe_scope_detection"))
        for key,comp in (scope.get("comparators") or {}).items():
            detection=comp.get("anomalyDetectionFoundation") or {}
            if s(detection.get("status")) not in allowed_detection:
                detection_errors.append((label,key,"status",detection.get("status")))
            if any(bool(detection.get(k)) for k in (
                "operationalAnomalyDetectionEnabled","severityEnabled","alertsEnabled",
                "diagnosisEnabled","causalClaimsEnabled"
            )):
                detection_errors.append((label,key,"unsafe_detection"))
            elig=(comp.get("anomalyEligibility") or {}).get("metricEligibility") or {}
            for metric,result in (detection.get("metricResults") or {}).items():
                status=s(result.get("status"))
                if status not in allowed_detection:
                    detection_errors.append((label,key,metric,"metric_status",status))
                    continue
                if any(bool(result.get(k)) for k in (
                    "severityEligible","alertEligible","diagnosisEligible","causalClaimEligible"
                )):
                    detection_errors.append((label,key,metric,"unsafe_metric_detection"))
                eligible=s((elig.get(metric) or {}).get("status"))=="ANOMALY_ELIGIBLE"
                if not eligible:
                    if status!="NOT_EVALUATED":
                        detection_errors.append((label,key,metric,"blocked_but_evaluated"))
                    if bool(result.get("scorePublished")) or "modifiedZScore" in result:
                        detection_errors.append((label,key,metric,"blocked_score_leak"))
                if status=="NOT_EVALUATED":
                    if bool(result.get("scorePublished")) or "modifiedZScore" in result:
                        detection_errors.append((label,key,metric,"not_evaluated_score_leak"))
                else:
                    if not bool(result.get("scorePublished")) or "modifiedZScore" not in result:
                        detection_errors.append((label,key,metric,"evaluated_without_score"))
                if status=="DEVIATION_CANDIDATE" and not eligible:
                    detection_errors.append((label,key,metric,"candidate_without_eligibility"))
    ck("anomaly_detection_foundation_fail_closed",not detection_errors,{
        "errors":detection_errors[:50]
    })

    severity_errors=[]
    allowed_levels={"LOW","MEDIUM","HIGH"}
    for label,scope in [("portfolio",payload.get("portfolio") or {})]+list(shops.items()):
        summary=scope.get("anomalySeverityConfidence") or {}
        if s(summary.get("status")) not in {"ASSESSED","NOT_ASSESSED"}:
            severity_errors.append((label,"scope_status",summary.get("status")))
        if any(bool(summary.get(k)) for k in (
            "businessImpactClaim","automaticAlertsEnabled","diagnosisEnabled","causalClaimsEnabled"
        )):
            severity_errors.append((label,"unsafe_scope"))
        for key,comp in (scope.get("comparators") or {}).items():
            comp_summary=comp.get("anomalySeverityConfidence") or {}
            if s(comp_summary.get("status")) not in {"ASSESSED","NOT_ASSESSED"}:
                severity_errors.append((label,key,"comp_status"))
            detection=(comp.get("anomalyDetectionFoundation") or {}).get("metricResults") or {}
            for metric,result in detection.items():
                assessment=result.get("severityConfidence") or {}
                detector_status=s(result.get("status"))
                if detector_status=="DEVIATION_CANDIDATE":
                    if s(assessment.get("status"))!="ASSESSED":
                        severity_errors.append((label,key,metric,"candidate_not_assessed"))
                    if s(assessment.get("severityLevel")) not in allowed_levels:
                        severity_errors.append((label,key,metric,"severity_level"))
                    if s(assessment.get("confidenceLevel")) not in allowed_levels:
                        severity_errors.append((label,key,metric,"confidence_level"))
                    if not (0.0<=float(assessment.get("severityScore") or 0.0)<=1.0):
                        severity_errors.append((label,key,metric,"severity_score_range"))
                    if not (0.0<=float(assessment.get("confidenceScore") or 0.0)<=1.0):
                        severity_errors.append((label,key,metric,"confidence_score_range"))
                    if not bool(assessment.get("severityPublished")) or not bool(assessment.get("confidencePublished")):
                        severity_errors.append((label,key,metric,"missing_published_evidence"))
                else:
                    if s(assessment.get("status"))!="NOT_ASSESSED":
                        severity_errors.append((label,key,metric,"non_candidate_assessed"))
                    if bool(assessment.get("severityPublished")) or bool(assessment.get("confidencePublished")):
                        severity_errors.append((label,key,metric,"non_candidate_evidence_leak"))
                    if "severityScore" in assessment or "confidenceScore" in assessment:
                        severity_errors.append((label,key,metric,"non_candidate_score_leak"))
                if any(bool(assessment.get(k)) for k in (
                    "businessImpactClaim","alertEligible","diagnosisEligible","causalClaimEligible"
                )):
                    severity_errors.append((label,key,metric,"unsafe_metric"))
    ck("anomaly_severity_confidence_candidate_only",not severity_errors,{
        "errors":severity_errors[:50]
    })

    attribution_errors=[]
    allowed_attr={"ATTRIBUTED","ASSOCIATION_ONLY","NOT_DIAGNOSED"}
    for label,scope in [("portfolio",payload.get("portfolio") or {})]+list(shops.items()):
        summary=scope.get("driverAttributionFoundation") or {}
        if s(summary.get("status")) not in allowed_attr:
            attribution_errors.append((label,"scope_status",summary.get("status")))
        if any(bool(summary.get(k)) for k in (
            "operationalDiagnosisEnabled","automaticAlertsEnabled","causalClaimsEnabled"
        )):
            attribution_errors.append((label,"unsafe_scope"))
        for key,comp in (scope.get("comparators") or {}).items():
            comp_summary=comp.get("driverAttributionFoundation") or {}
            if s(comp_summary.get("status")) not in allowed_attr:
                attribution_errors.append((label,key,"comp_status"))
            detection=(comp.get("anomalyDetectionFoundation") or {}).get("metricResults") or {}
            for metric,result in detection.items():
                attr=result.get("driverAttribution") or {}
                status=s(attr.get("status"))
                detector_status=s(result.get("status"))
                if status not in allowed_attr:
                    attribution_errors.append((label,key,metric,"status",status))
                    continue
                if detector_status!="DEVIATION_CANDIDATE" and status!="NOT_DIAGNOSED":
                    attribution_errors.append((label,key,metric,"non_candidate_diagnosed"))
                if status=="ATTRIBUTED":
                    contributions=attr.get("driverContributions") or []
                    if not contributions or not s(attr.get("identity")):
                        attribution_errors.append((label,key,metric,"missing_identity_contributions"))
                    closure=abs(float(attr.get("identityClosureResidual") or 0.0))
                    if closure>1e-6:
                        attribution_errors.append((label,key,metric,"identity_not_closed",closure))
                    if bool(attr.get("identityContributionIsCausalClaim")):
                        attribution_errors.append((label,key,metric,"causal_identity_claim"))
                if status=="ASSOCIATION_ONLY" and attr.get("driverContributions"):
                    attribution_errors.append((label,key,metric,"association_has_contributions"))
                if any(bool(attr.get(k)) for k in (
                    "operationalDiagnosisEnabled","alertEligible",
                    "diagnosisEligible","causalClaimEligible"
                )):
                    attribution_errors.append((label,key,metric,"unsafe_metric"))
                for signal in attr.get("associatedSignals") or []:
                    if bool(signal.get("causalClaim")):
                        attribution_errors.append((label,key,metric,"causal_association"))
    ck("driver_attribution_foundation_noncausal_fail_closed",not attribution_errors,{
        "errors":attribution_errors[:50]
    })

    smart_issue_errors=[]
    smart_policy=contract.get("smart_issues_foundation") or {}
    required_uncertainty=set(smart_policy.get("required_uncertainty") or [])
    min_issue_sev=s(smart_policy.get("minimum_severity_level")) or "MEDIUM"
    min_issue_conf=s(smart_policy.get("minimum_confidence_level")) or "MEDIUM"
    max_scope_issues=int(smart_policy.get("max_issues_per_scope") or 5)
    for label,scope in [("portfolio",payload.get("portfolio") or {})]+list(shops.items()):
        summary=scope.get("smartIssuesFoundation") or {}
        status=s(summary.get("status"))
        issues=list(summary.get("issues") or [])
        if status not in {"ISSUE_READY","NO_ISSUE"}:
            smart_issue_errors.append((label,"scope_status",status))
        if int(summary.get("issueCount") or 0)!=len(issues):
            smart_issue_errors.append((label,"scope_count"))
        if len(issues)>max_scope_issues:
            smart_issue_errors.append((label,"scope_limit"))
        if len({s(x.get("affectedMetric")) for x in issues})!=len(issues):
            smart_issue_errors.append((label,"dedupe_failure"))
        if status=="NO_ISSUE" and issues:
            smart_issue_errors.append((label,"no_issue_has_items"))
        if any(bool(summary.get(k)) for k in (
            "automaticAlertsEnabled","actionRecommendationsEnabled",
            "operationalDiagnosisEnabled","causalClaimsEnabled"
        )):
            smart_issue_errors.append((label,"unsafe_scope"))
        for key,comp in (scope.get("comparators") or {}).items():
            comp_summary=comp.get("smartIssuesFoundation") or {}
            comp_issues=list(comp_summary.get("issues") or [])
            if s(comp_summary.get("status")) not in {"ISSUE_READY","NO_ISSUE"}:
                smart_issue_errors.append((label,key,"comp_status"))
            if len(comp_issues)>1:
                smart_issue_errors.append((label,key,"comp_limit"))
            if int(comp_summary.get("issueCount") or 0)!=len(comp_issues):
                smart_issue_errors.append((label,key,"comp_count"))
        for issue in issues:
            if s(issue.get("status"))!="ISSUE_READY":
                smart_issue_errors.append((label,"issue_status"))
            if s(issue.get("detectorStatus"))!="DEVIATION_CANDIDATE":
                smart_issue_errors.append((label,"non_candidate_issue"))
            if _signal_level_rank(s(issue.get("severityLevel")))<_signal_level_rank(min_issue_sev):
                smart_issue_errors.append((label,"severity_below_threshold"))
            if _signal_level_rank(s(issue.get("confidenceLevel")))<_signal_level_rank(min_issue_conf):
                smart_issue_errors.append((label,"confidence_below_threshold"))
            if s(issue.get("attributionStatus")) not in set(
                smart_policy.get("allowed_attribution_statuses") or []
            ):
                smart_issue_errors.append((label,"attribution_boundary"))
            if not s(issue.get("issueId")):
                smart_issue_errors.append((label,"missing_issue_id"))
            if not required_uncertainty.issubset(set(issue.get("unresolvedUncertainty") or [])):
                smart_issue_errors.append((label,"missing_uncertainty"))
            if any(bool(issue.get(k)) for k in (
                "automaticAlertEligible","actionRecommendationEligible",
                "operationalDiagnosisEnabled","causalClaimEligible"
            )):
                smart_issue_errors.append((label,"unsafe_issue"))
            if bool((issue.get("driverEvidence") or {}).get("identityContributionIsCausalClaim")):
                smart_issue_errors.append((label,"causal_driver_claim"))
    ck("smart_issues_foundation_evidence_only_fail_closed",not smart_issue_errors,{
        "errors":smart_issue_errors[:50]
    })

    action_policy_errors=[]
    action_policy=contract.get("operator_action_policy_foundation") or {}
    forbidden=set(action_policy.get("forbidden_directives") or [])
    max_options=int(action_policy.get("max_options_per_scope") or 6)
    max_per_issue=int(action_policy.get("max_options_per_issue") or 2)
    for label,scope in [("portfolio",payload.get("portfolio") or {})]+list(shops.items()):
        smart=scope.get("smartIssuesFoundation") or {}
        summary=scope.get("operatorActionPolicyFoundation") or {}
        actions=list(summary.get("actionOptions") or [])
        status=s(summary.get("status"))
        if status not in {"ACTION_OPTIONS_READY","NO_ACTION_OPTIONS"}:
            action_policy_errors.append((label,"scope_status",status))
        if int(summary.get("actionOptionCount") or 0)!=len(actions):
            action_policy_errors.append((label,"count"))
        if len(actions)>max_options:
            action_policy_errors.append((label,"scope_limit"))
        if status=="NO_ACTION_OPTIONS" and actions:
            action_policy_errors.append((label,"no_options_has_items"))
        if s((smart.get("status")))!="ISSUE_READY" and actions:
            action_policy_errors.append((label,"actions_without_issue"))
        if any(bool(summary.get(k)) for k in (
            "platformMutationAllowed","automaticExecutionEnabled",
            "automaticAlertsEnabled","causalClaimsEnabled"
        )):
            action_policy_errors.append((label,"unsafe_scope"))
        if not bool(summary.get("requiresHumanReview")):
            action_policy_errors.append((label,"human_review_missing"))
        issue_ids={s(x.get("issueId")) for x in smart.get("issues") or []}
        per_issue=defaultdict(int)
        for action in actions:
            source_issue=s(action.get("sourceIssueId"))
            per_issue[source_issue]+=1
            if source_issue not in issue_ids:
                action_policy_errors.append((label,"unknown_issue",source_issue))
            if s(action.get("status"))!="REVIEW_OPTION":
                action_policy_errors.append((label,source_issue,"wrong_status"))
            if not s(action.get("whyRelevant")):
                action_policy_errors.append((label,source_issue,"why_missing"))
            if not (action.get("prerequisites") or []):
                action_policy_errors.append((label,source_issue,"prerequisites_missing"))
            if not (action.get("monitorKpis") or []):
                action_policy_errors.append((label,source_issue,"monitor_missing"))
            if not (action.get("verificationChecks") or []):
                action_policy_errors.append((label,source_issue,"verification_missing"))
            if not (action.get("stopOrReversalChecks") or []):
                action_policy_errors.append((label,source_issue,"stop_checks_missing"))
            if any(bool(action.get(k)) for k in (
                "platformMutationAllowed","automaticExecutionEligible",
                "automaticAlertEligible","causalClaimEligible","prescriptiveRecommendation"
            )):
                action_policy_errors.append((label,source_issue,"unsafe_option"))
            if not bool(action.get("requiresHumanReview")) or s(action.get("executionMode"))!="HUMAN_REVIEW_ONLY":
                action_policy_errors.append((label,source_issue,"execution_boundary"))
            if s(action.get("optionKey")) in forbidden:
                action_policy_errors.append((label,source_issue,"forbidden_directive"))
        if any(count>max_per_issue for count in per_issue.values()):
            action_policy_errors.append((label,"per_issue_limit",dict(per_issue)))
    ck("operator_action_policy_review_only_fail_closed",not action_policy_errors,{
        "errors":action_policy_errors[:50]
    })

    shadow_policy=contract.get("production_cutover_shadow_mode_v1") or {}
    shadow=payload.get("shadowModeV1") or {}
    shadow_errors=[]
    status=s(shadow.get("status"))
    if status not in {
        "SHADOW_OBSERVING","READY_FOR_HUMAN_CUTOVER_REVIEW","CUTOVER_BLOCKED"
    }:
        shadow_errors.append(("status",status))
    if s(shadow.get("mode"))!="PREPRODUCTION_OBSERVE_ONLY":
        shadow_errors.append(("mode",shadow.get("mode")))
    if not s(shadow.get("refreshId")) or int(shadow.get("refreshSequence") or 0)<1:
        shadow_errors.append(("refresh_identity",))
    if any(bool(shadow.get(k)) for k in (
        "productionWritesEnabled","platformMutationAllowed","automaticAlertsEnabled"
    )):
        shadow_errors.append(("unsafe_shadow_scope",))
    activation=shadow.get("activationControls") or {}
    if (
        not bool(activation.get("requiresExplicitHumanApproval"))
        or bool(activation.get("productionActivationAllowed"))
        or bool(activation.get("automaticCutoverEnabled"))
        or bool(activation.get("cutoverAuthorized"))
    ):
        shadow_errors.append(("unsafe_activation_controls",))
    rollback=shadow.get("rollbackControls") or {}
    if (
        not bool(rollback.get("required"))
        or not bool(rollback.get("legacyProductionPathRetained"))
        or bool(rollback.get("automaticRollbackEnabled"))
    ):
        shadow_errors.append(("rollback_controls",))
    gates=list(shadow.get("readinessGates") or [])
    gate_names=[s(x.get("gate")) for x in gates]
    required_gates=list(shadow_policy.get("required_readiness_gates") or [])
    if gate_names!=required_gates:
        shadow_errors.append(("gate_set",gate_names))
    if any(s(x.get("status")) not in {"PASS","PENDING","FAIL"} for x in gates):
        shadow_errors.append(("gate_status",))
    current=shadow.get("currentState") or {}
    expected_current=_shadow_issue_action_state(payload.get("portfolio") or {},shops)
    if current!=expected_current:
        shadow_errors.append(("current_state_mismatch",))
    transition=shadow.get("transition") or {}
    if not bool(transition.get("lineageValid")) or transition.get("lineageErrors"):
        shadow_errors.append(("transition_lineage",transition.get("lineageErrors")))
    records=list(shadow.get("refreshRecords") or [])
    max_records=int(shadow_policy.get("max_retained_refresh_records") or 10)
    if not records or len(records)>max_records:
        shadow_errors.append(("refresh_records",len(records)))
    if len({s(x.get("refreshId")) for x in records})!=len(records):
        shadow_errors.append(("duplicate_refresh_records",))
    min_safe=int(shadow_policy.get("minimum_consecutive_safe_refreshes") or 3)
    min_stable=int(shadow_policy.get("minimum_consecutive_stable_refreshes") or 3)
    if status=="READY_FOR_HUMAN_CUTOVER_REVIEW" and (
        int(shadow.get("consecutiveSafeRefreshes") or 0)<min_safe
        or int(shadow.get("consecutiveStableRefreshes") or 0)<min_stable
        or any(s(x.get("status"))!="PASS" for x in gates)
    ):
        shadow_errors.append(("premature_readiness",))
    if int(shadow_policy.get("approved_visual_baseline_run") or 0)!=216:
        shadow_errors.append(("visual_baseline_changed",))
    checklist={s(x.get("item")):s(x.get("status")) for x in shadow.get("cutoverChecklist") or []}
    if checklist.get("EXPLICIT_HUMAN_CUTOVER_APPROVAL")!="PENDING":
        shadow_errors.append(("human_approval_not_pending",))
    if checklist.get("EXPLICIT_PRODUCTION_DEPLOYMENT_APPROVAL")!="PENDING":
        shadow_errors.append(("deployment_approval_not_pending",))
    ck("production_cutover_shadow_mode_observe_only_fail_closed",not shadow_errors,{
        "errors":shadow_errors[:50],
        "status":status,
    })

    min_sw=int((contract.get("minimum_history") or {}).get("same_weekday_min_samples") or 4)
    bad=[]
    for label,scope in [("portfolio",payload.get("portfolio") or {})]+list(shops.items()):
        c=(scope.get("comparators") or {}).get("sameWeekday") or {}
        if s(c.get("status"))=="READY" and int(c.get("sampleCount") or 0)<min_sw:
            bad.append(label)
    ck("same_weekday_minimum_enforced",not bad,{"badScopes":bad})
    trusted=list((payload.get("historySources") or {}).get("trustedSemanticMonths") or [])
    inv=list(((payload.get("sourceInventory") or {}).get("semantic") or {}).get("trustedMonths") or [])
    ck("trusted_months_match_inventory",trusted==inv,{"payload":trusted,"inventory":inv})
    failed=[x for x in checks if x["status"]=="FAIL"]
    return {"status":"PASS" if not failed else "FAIL","failedCheckCount":len(failed),"checks":checks}

def build_historical_intelligence(
    *,semantic_daily_rows,inventory,shops,as_of_period,contract_path,output_dir,
    context_rows=None,context_fingerprint="",refresh_id="",
    previous_shadow_state=None,
):
    contract=load_contract(contract_path)
    shop_ids=[s(x.get("shop_id")) for x in shops]
    if not shop_ids or any(not x for x in shop_ids):
        raise ValueError("historical intelligence requires explicit shop IDs")
    allowed=set(shop_ids)
    rows=[dict(x) for x in semantic_daily_rows if s(x.get("shop_id")) in allowed and _date(x.get("data_date"))[:7]<=as_of_period]
    by_shop={sid:_scope_rows(rows,[sid]) for sid in shop_ids}
    portfolio_rows=_scope_rows(rows,shop_ids)
    semantic_inv=inventory.get("semantic") or {}
    trusted_months=list(semantic_inv.get("trustedMonths") or [])
    trusted_fps=list(semantic_inv.get("trustedFingerprints") or [])
    lifecycle_by_shop={
        s(shop.get("shop_id")):dict(shop.get("history_lifecycle") or {})
        for shop in shops
    }
    portfolio_lifecycle={
        "origin":"ALL_ENABLED_SHOPS_ACTIVE",
        "start_policy":"LATEST_SHOP_LAUNCH_BOUNDARY",
        "pre_start_dates_are_missing":False,
    }
    shop_platforms={
        s(shop.get("shop_id")):s(shop.get("platform"))
        for shop in shops
    }
    portfolio=_scope_history(
        portfolio_rows,contract,portfolio_lifecycle,
        scope_key="portfolio",
        context_rows=context_rows or [],
        scope_platforms=sorted({x for x in shop_platforms.values() if x}),
        scope_shop_ids=shop_ids,
        context_fingerprint=context_fingerprint,
    )
    shop_history={
        sid:_scope_history(
            by_shop[sid],contract,lifecycle_by_shop.get(sid) or {},
            scope_key=sid,
            context_rows=context_rows or [],
            scope_platforms=[shop_platforms.get(sid)] if shop_platforms.get(sid) else [],
            scope_shop_ids=[sid],
            context_fingerprint=context_fingerprint,
        )
        for sid in shop_ids
    }
    shadow_mode_v1=_build_shadow_mode_v1(
        portfolio=portfolio,
        shops=shop_history,
        expected_shop_ids=shop_ids,
        trusted_months=trusted_months,
        trusted_fingerprints=trusted_fps,
        context_fingerprint=context_fingerprint,
        as_of_period=as_of_period,
        contract=contract,
        refresh_id=refresh_id,
        previous_shadow_state=previous_shadow_state,
    )
    payload={
        "meta":{"layer":s(contract.get("layer_name")),"contractVersion":s(contract.get("version")),"status":"PREPRODUCTION","asOfPeriod":as_of_period},
        "historySources":{
            "trustedSource":"PUBLISHED_SEMANTIC_QA_PASS",
            "trustedSemanticMonths":trusted_months,
            "trustedSemanticFingerprints":trusted_fps,
            "rawPresenceRole":"BACKFILL_CANDIDATE_ONLY",
            "businessContextFingerprint":context_fingerprint,
            "businessContextSource":"multi_shop_business_context_v1" if context_fingerprint else "",
        },
        "sourceInventory":inventory,
        "portfolio":portfolio,"shops":shop_history,
        "shadowModeV1":shadow_mode_v1,
        "capabilities":{
            "historicalAlerts":False,"historicalDiagnosis":False,
            "anomalyEligibilityGuardrails":True,
            "anomalyDetectionFoundation":True,
            "anomalySeverityConfidence":True,
            "driverAttributionFoundation":True,
            "smartIssuesFoundation":True,
            "operatorActionPolicyFoundation":True,
            "productionCutoverShadowMode":True,
            "productionCutover":False,
            "operatorActions":False,
            "smartIssues":False,
            "diagnosis":False,
            "anomalySeverity":False,
            "anomalyDetection":False,
            "contextComparatorQualification":bool(context_fingerprint),
            "contextMatchedBaseline":any(
                bool((scope.get("context") or {}).get("contextMatchedBaselineEnabled"))
                for scope in [portfolio]+list(shop_history.values())
            ),
            "sixMonthIntelligence":all(s(x.get("sixMonthStatus"))=="READY" for x in [portfolio]+list(shop_history.values())),
        },
        "safety":{
            "productionDataMartWritten":False,"productionUiModified":False,
            "legacyPayloadPublished":False,"historicalAlertsEnabled":False,"diagnosisEnabled":False,
            "productionCutoverAuthorized":False,"productionActivationEnabled":False,
        },
    }
    qa=validate_historical_output(payload,shop_ids,contract)
    if qa["status"]!="PASS":
        raise ValueError(f"historical intelligence QA failed: {[x['name'] for x in qa['checks'] if x['status']=='FAIL']}")
    fingerprint=_sha256_json({
        "contractVersion":contract.get("version"),"asOfPeriod":as_of_period,
        "trustedSemanticFingerprints":trusted_fps,"payload":payload,
    })
    payload["meta"]["historicalBuildFingerprint"]=fingerprint
    qa.update({
        "historicalBuildFingerprint":fingerprint,"asOfPeriod":as_of_period,
        "trustedSemanticMonths":trusted_months,"historyFoundationReady":True,
    })
    out=Path(output_dir); out.mkdir(parents=True,exist_ok=True)
    _write_json(out/"historical_intelligence.json",payload)
    _write_json(out/"history_qa_report.json",qa)
    _write_json(out/"shadow_mode_state.json",shadow_mode_v1)
    _write_json(out/"history_manifest.json",{
        "layer":s(contract.get("layer_name")),"contractVersion":s(contract.get("version")),
        "asOfPeriod":as_of_period,"historicalBuildFingerprint":fingerprint,
        "trustedSemanticMonths":trusted_months,"trustedSemanticFingerprints":trusted_fps,
        "businessContextFingerprint":context_fingerprint,
        "files":["historical_intelligence.json","history_qa_report.json","shadow_mode_state.json"],"safety":payload["safety"],
    })
    return {
        "status":"PASS","historyFoundationReady":True,"asOfPeriod":as_of_period,
        "historicalBuildFingerprint":fingerprint,"trustedSemanticMonths":trusted_months,
        "businessContextFingerprint":context_fingerprint,
        "portfolioHistoryStatus":s(portfolio.get("status")),
        "shopHistoryStatus":{sid:s(scope.get("status")) for sid,scope in shop_history.items()},
        "shadowModeStatus":shadow_mode_v1["status"],
        "shadowRefreshSequence":shadow_mode_v1["refreshSequence"],
        "productionCutoverAuthorized":False,
        "sixMonthIntelligence":bool(payload["capabilities"]["sixMonthIntelligence"]),
        "outputLocation":str(out),"safety":payload["safety"],
    }
