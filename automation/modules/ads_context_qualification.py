"""Business Context Qualification for Dynamic Ads Intelligence.

This module is deliberately downstream of the locked Ads Intelligence foundation.
It binds explicit-source Business Context to already-built Ads snapshots without
rewriting canonical Ads facts, ratios, product signals, or ROAS identity
attribution. Strong directional diagnosis is exposed only when the current and
reference windows are context-compatible.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence


ALLOWED_STATUSES = {"CONTEXT_COMPATIBLE", "CONTEXT_DIFFERENT", "CONTEXT_UNKNOWN"}


def s(v: Any) -> str:
    return "" if v is None else str(v).strip()


def _sha(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _read_json(path: str | Path) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json(path: str | Path, value: Any) -> None:
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _read_jsonl(path: str | Path) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for line_no, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"context_days.jsonl line {line_no} is not an object")
        out.append(value)
    return out


def _date_range(start: str, end: str) -> List[str]:
    if not start or not end:
        return []
    a, b = dt.date.fromisoformat(start), dt.date.fromisoformat(end)
    if b < a:
        return []
    return [(a + dt.timedelta(days=i)).isoformat() for i in range((b - a).days + 1)]


def _policy(contract: Mapping[str, Any]) -> Dict[str, Any]:
    raw = dict(contract.get("business_context_qualification") or {})
    if not raw:
        raise ValueError("Ads business_context_qualification policy is required")
    if not bool(raw.get("enabled")):
        raise ValueError("Ads business context qualification must be enabled")
    allowed_families = [s(x) for x in raw.get("qualifying_context_families") or [] if s(x)]
    allowed_platforms = [s(x) for x in raw.get("qualifying_platforms") or [] if s(x)]
    if not allowed_families:
        raise ValueError("Ads business context qualification requires qualifying families")
    if not allowed_platforms:
        raise ValueError("Ads business context qualification requires qualifying platforms")
    if s(raw.get("strong_directional_diagnosis_rule")) != "CONTEXT_COMPATIBLE_ONLY":
        raise ValueError("strong directional diagnosis must remain CONTEXT_COMPATIBLE_ONLY")
    return {
        **raw,
        "qualifying_context_families": allowed_families,
        "qualifying_platforms": allowed_platforms,
    }


def _row_in_scope(row: Mapping[str, Any], *, shop_id: str, policy: Mapping[str, Any]) -> bool:
    if not bool(row.get("matching_eligible")):
        return False
    if s(row.get("context_family")) not in set(policy.get("qualifying_context_families") or []):
        return False
    if s(row.get("platform")) not in set(policy.get("qualifying_platforms") or []):
        return False
    scope_type = s(row.get("scope_type"))
    row_shop = s(row.get("shop_id"))
    if scope_type == "SHOP" and row_shop != shop_id:
        return False
    return True


def _matching_profile(
    rows: Sequence[Mapping[str, Any]],
    dates: Sequence[str],
    *,
    shop_id: str,
    policy: Mapping[str, Any],
) -> List[Dict[str, Any]]:
    wanted = set(dates)
    profiles: Dict[tuple[str, str, str], Dict[str, Any]] = {}
    for row in rows:
        data_date = s(row.get("data_date"))[:10]
        if data_date not in wanted or not _row_in_scope(row, shop_id=shop_id, policy=policy):
            continue
        key = (s(row.get("scope_type")), s(row.get("platform")), s(row.get("context_family")))
        if not all(key):
            continue
        item = profiles.setdefault(key, {
            "scopeType": key[0], "platform": key[1], "contextFamily": key[2],
            "_dates": set(), "_peakDates": set(),
        })
        item["_dates"].add(data_date)
        if bool(row.get("is_peak_date")):
            item["_peakDates"].add(data_date)

    total = max(1, len(wanted))
    out: List[Dict[str, Any]] = []
    for key in sorted(profiles):
        item = profiles[key]
        day_count = len(item["_dates"])
        peak_count = len(item["_peakDates"])
        out.append({
            "scopeType": item["scopeType"],
            "platform": item["platform"],
            "contextFamily": item["contextFamily"],
            "dayCount": day_count,
            "peakDayCount": peak_count,
            "dayShare": day_count / total,
            "peakDayShare": peak_count / total,
        })
    return out


def _signature(profile: Sequence[Mapping[str, Any]]) -> List[str]:
    return [
        "|".join([
            s(x.get("scopeType")), s(x.get("platform")), s(x.get("contextFamily")),
            str(int(x.get("dayCount") or 0)), str(int(x.get("peakDayCount") or 0)),
        ])
        for x in profile
    ]


def resolve_window_context(
    rows: Sequence[Mapping[str, Any]],
    dates: Sequence[str],
    *,
    shop_id: str,
    policy: Mapping[str, Any],
) -> Dict[str, Any]:
    wanted = set(dates)
    selected = [
        dict(row) for row in rows
        if s(row.get("data_date"))[:10] in wanted and _row_in_scope(row, shop_id=shop_id, policy=policy)
    ]
    profile = _matching_profile(rows, dates, shop_id=shop_id, policy=policy)
    event_ids = sorted({s(x.get("context_id")) for x in selected if s(x.get("context_id"))})
    matching_dates = sorted({s(x.get("data_date"))[:10] for x in selected if s(x.get("data_date"))})
    return {
        "status": "CONTEXT_AVAILABLE",
        "dateCount": len(wanted),
        "contextDayCount": len(matching_dates),
        "eventCount": len(event_ids),
        "eventIds": event_ids,
        "contextFamilies": sorted({s(x.get("context_family")) for x in selected if s(x.get("context_family"))}),
        "platforms": sorted({s(x.get("platform")) for x in selected if s(x.get("platform"))}),
        "matchingEligibleDates": matching_dates,
        "matchingProfile": profile,
        "matchingSignature": _signature(profile),
        "peakEventIds": sorted({
            s(x.get("context_id")) for x in selected
            if bool(x.get("is_peak_date")) and s(x.get("context_id"))
        }),
        "sourceTiers": sorted({s(x.get("source_tier")) for x in selected if s(x.get("source_tier"))}),
    }


def qualify_context_pair(
    current: Mapping[str, Any],
    reference: Mapping[str, Any],
    *,
    comparison_status: str,
) -> Dict[str, Any]:
    cur_sig = list(current.get("matchingSignature") or [])
    ref_sig = list(reference.get("matchingSignature") or [])
    if comparison_status != "READY":
        status, reason = "CONTEXT_UNKNOWN", "COMPARISON_NOT_READY"
    else:
        current_days = int(current.get("dateCount") or 0)
        reference_days = int(reference.get("dateCount") or 0)
        if current_days <= 0 or reference_days <= 0 or current_days != reference_days:
            status, reason = "CONTEXT_UNKNOWN", "UNEQUAL_OR_EMPTY_WINDOW"
        elif not cur_sig and not ref_sig:
            status, reason = "CONTEXT_UNKNOWN", "NO_EXACT_MATCHING_EVENT_ON_EITHER_SIDE"
        elif bool(cur_sig) != bool(ref_sig):
            status, reason = "CONTEXT_DIFFERENT", "EXACT_EVENT_ON_ONE_SIDE_ONLY"
        elif cur_sig == ref_sig:
            status, reason = "CONTEXT_COMPATIBLE", "EXACT_MATCHING_PROFILE_EQUAL"
        else:
            status, reason = "CONTEXT_DIFFERENT", "EXACT_MATCHING_PROFILE_DIFFERENT"
    eligible = status == "CONTEXT_COMPATIBLE" and comparison_status == "READY"
    return {
        "status": status,
        "reason": reason,
        "currentSignature": cur_sig,
        "referenceSignature": ref_sig,
        "strongDirectionalDiagnosisEligible": eligible,
        "causalClaimEligible": False,
        "automaticAlertEligible": False,
        "automaticActionEligible": False,
    }


def bind_snapshot_context(
    snapshot: Dict[str, Any],
    *,
    context_rows: Sequence[Mapping[str, Any]],
    shop_id: str,
    policy: Mapping[str, Any],
) -> None:
    current_dates = _date_range(s(snapshot.get("coverageStart")), s(snapshot.get("coverageEnd")))
    comparison_status = s(snapshot.get("comparisonStatus"))
    reference_dates = (
        _date_range(s(snapshot.get("comparisonStart")), s(snapshot.get("comparisonEnd")))
        if comparison_status == "READY" else []
    )
    current = resolve_window_context(context_rows, current_dates, shop_id=shop_id, policy=policy)
    reference = resolve_window_context(context_rows, reference_dates, shop_id=shop_id, policy=policy)
    qualification = qualify_context_pair(current, reference, comparison_status=comparison_status)
    eligible = bool(qualification["strongDirectionalDiagnosisEligible"])
    base_signals = list(snapshot.get("signals") or [])
    snapshot["businessContext"] = {
        "status": "CONTEXT_AVAILABLE",
        "current": current,
        "reference": reference,
        "matchEvaluation": qualification["status"],
        "qualification": qualification,
        "policyMode": s(policy.get("mode")),
        "strongDirectionalDiagnosisEligible": eligible,
        "strongDirectionalDiagnosisGate": (
            "QUALIFIED_CONTEXT_COMPATIBLE" if eligible
            else "BLOCKED_CONTEXT_DIFFERENT" if qualification["status"] == "CONTEXT_DIFFERENT"
            else "BLOCKED_CONTEXT_UNKNOWN"
        ),
        "baseEvidencePreserved": True,
        "causalClaimEligible": False,
        "automaticAlertEligible": False,
        "automaticActionEligible": False,
    }
    snapshot["qualifiedSignals"] = base_signals if eligible else []
    snapshot["qualifiedProblemCount"] = sum(1 for x in snapshot["qualifiedSignals"] if s(x.get("type")) == "Vấn đề")
    snapshot["qualifiedOpportunityCount"] = sum(1 for x in snapshot["qualifiedSignals"] if s(x.get("type")) == "Cơ hội")
    snapshot["strongDirectionalDiagnosisEligible"] = eligible


def bind_payload_context(
    payload: Dict[str, Any],
    *,
    context_rows: Sequence[Mapping[str, Any]],
    context_fingerprint: str,
    contract: Mapping[str, Any],
) -> Dict[str, Any]:
    policy = _policy(contract)
    for shop_id, shop in (payload.get("shops") or {}).items():
        periods = shop.get("periods") or {}
        for scope_key in ("day", "week", "month", "year"):
            for snapshot in ((periods.get(scope_key) or {}).get("snapshots") or {}).values():
                if s(snapshot.get("status")) != "READY":
                    continue
                bind_snapshot_context(
                    snapshot,
                    context_rows=context_rows,
                    shop_id=s(shop_id),
                    policy=policy,
                )
        shop["businessContextLineage"] = {
            "contextBuildFingerprint": context_fingerprint,
            "policyMode": s(policy.get("mode")),
            "qualifyingContextFamilies": list(policy.get("qualifying_context_families") or []),
            "qualifyingPlatforms": list(policy.get("qualifying_platforms") or []),
        }
    payload.setdefault("capabilities", {})["adsBusinessContextQualification"] = True
    payload["capabilities"]["adsStrongDirectionalDiagnosisGuard"] = True
    payload.setdefault("meta", {})["sourceBusinessContextFingerprint"] = context_fingerprint
    return payload


def validate_context_binding(payload: Mapping[str, Any]) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []

    def ck(name: str, ok: bool, detail: Any = None) -> None:
        checks.append({"name": name, "status": "PASS" if ok else "FAIL", "detail": detail or {}})

    meta = payload.get("meta") or {}
    ck("context_fingerprint_bound", bool(s(meta.get("sourceBusinessContextFingerprint"))))
    caps = payload.get("capabilities") or {}
    ck("context_capability_enabled", bool(caps.get("adsBusinessContextQualification")))
    ck("directional_guard_enabled", bool(caps.get("adsStrongDirectionalDiagnosisGuard")))

    for shop_id, shop in (payload.get("shops") or {}).items():
        lineage = shop.get("businessContextLineage") or {}
        ck(f"{shop_id}_context_lineage", bool(s(lineage.get("contextBuildFingerprint"))))
        for scope_key in ("day", "week", "month", "year"):
            for option_key, snapshot in (((shop.get("periods") or {}).get(scope_key) or {}).get("snapshots") or {}).items():
                if s(snapshot.get("status")) != "READY":
                    continue
                bc = snapshot.get("businessContext") or {}
                evaluation = s(bc.get("matchEvaluation"))
                ck(f"{shop_id}_{scope_key}_{option_key}_context_bound", evaluation in ALLOWED_STATUSES, {"evaluation": evaluation})
                expected_eligible = evaluation == "CONTEXT_COMPATIBLE" and s(snapshot.get("comparisonStatus")) == "READY"
                ck(
                    f"{shop_id}_{scope_key}_{option_key}_directional_gate",
                    bool(snapshot.get("strongDirectionalDiagnosisEligible")) == expected_eligible,
                )
                qualified = list(snapshot.get("qualifiedSignals") or [])
                ck(
                    f"{shop_id}_{scope_key}_{option_key}_qualified_signals_gate",
                    expected_eligible or not qualified,
                    {"qualifiedSignalCount": len(qualified)},
                )
                ck(
                    f"{shop_id}_{scope_key}_{option_key}_base_signals_preserved",
                    bool(bc.get("baseEvidencePreserved")),
                )
                ck(
                    f"{shop_id}_{scope_key}_{option_key}_non_causal",
                    not bool((bc.get("qualification") or {}).get("causalClaimEligible")),
                )
    failed = [x for x in checks if x["status"] == "FAIL"]
    return {"status": "PASS" if not failed else "FAIL", "failedCheckCount": len(failed), "checks": checks}


def build_candidate_preview(payload: Mapping[str, Any]) -> Dict[str, Any]:
    shops: Dict[str, Any] = {}
    for shop_id, shop in (payload.get("shops") or {}).items():
        periods = shop.get("periods") or {}
        scope_preview: Dict[str, Any] = {}
        for scope_key in ("day", "week", "month", "year"):
            block = periods.get(scope_key) or {}
            options = list(block.get("options") or [])
            latest_key = options[-1] if options else ""
            snapshot = (block.get("snapshots") or {}).get(latest_key) or {}
            bc = snapshot.get("businessContext") or {}
            q = bc.get("qualification") or {}
            scope_preview[scope_key] = {
                "optionKey": latest_key,
                "snapshotStatus": s(snapshot.get("status")),
                "comparisonStatus": s(snapshot.get("comparisonStatus")),
                "matchEvaluation": s(bc.get("matchEvaluation")),
                "reason": s(q.get("reason")),
                "strongDirectionalDiagnosisEligible": bool(snapshot.get("strongDirectionalDiagnosisEligible")),
                "baseSignalCount": len(snapshot.get("signals") or []),
                "qualifiedSignalCount": len(snapshot.get("qualifiedSignals") or []),
                "currentSignature": list(q.get("currentSignature") or []),
                "referenceSignature": list(q.get("referenceSignature") or []),
            }
        shops[shop_id] = {
            "displayName": s(shop.get("displayName")),
            "scopes": scope_preview,
        }
    return {
        "status": "PREPRODUCTION_CANDIDATE",
        "sourceBusinessContextFingerprint": s((payload.get("meta") or {}).get("sourceBusinessContextFingerprint")),
        "adsIntelligenceFingerprint": s((payload.get("meta") or {}).get("adsIntelligenceFingerprint")),
        "shops": shops,
        "safety": {
            "productionUiModified": False,
            "productionActivationEnabled": False,
            "automaticAlertsEnabled": False,
            "automaticActionsEnabled": False,
            "causalClaimsEnabled": False,
        },
    }


def bind_ads_business_context_artifacts(
    *,
    ads_output_dir: str | Path,
    context_dir: str | Path,
    contract_path: str | Path,
) -> Dict[str, Any]:
    ads_dir = Path(ads_output_dir)
    context_root = Path(context_dir)
    payload_path = ads_dir / "ads_intelligence.json"
    qa_path = ads_dir / "ads_intelligence_qa_report.json"
    manifest_path = ads_dir / "ads_intelligence_manifest.json"
    context_days_path = context_root / "context_days.jsonl"
    context_manifest_path = context_root / "context_manifest.json"
    for path in (payload_path, qa_path, manifest_path, context_days_path, context_manifest_path):
        if not path.exists():
            raise ValueError(f"required Ads context binding artifact missing: {path}")

    payload = _read_json(payload_path)
    qa = _read_json(qa_path)
    manifest = _read_json(manifest_path)
    context_manifest = _read_json(context_manifest_path)
    context_rows = _read_jsonl(context_days_path)
    contract = _read_json(contract_path)
    context_fingerprint = s(context_manifest.get("contextBuildFingerprint"))
    if not context_fingerprint:
        raise ValueError("Business Context fingerprint is required")
    if s(context_manifest.get("asOfPeriod")) != s((payload.get("meta") or {}).get("asOfPeriod")):
        raise ValueError("Business Context period does not match Ads Intelligence period")

    base_fingerprint = s((payload.get("meta") or {}).get("adsIntelligenceFingerprint"))
    if not base_fingerprint:
        raise ValueError("base Ads Intelligence fingerprint missing")
    bind_payload_context(
        payload,
        context_rows=context_rows,
        context_fingerprint=context_fingerprint,
        contract=contract,
    )
    binding_qa = validate_context_binding(payload)
    if binding_qa["status"] != "PASS":
        failed = [x["name"] for x in binding_qa["checks"] if x["status"] == "FAIL"]
        raise ValueError(f"Ads Business Context binding QA failed: {failed[:20]}")

    final_fingerprint = _sha({
        "baseAdsIntelligenceFingerprint": base_fingerprint,
        "businessContextFingerprint": context_fingerprint,
        "businessContextPolicy": _policy(contract),
        "payload": payload,
    })
    payload["meta"]["baseAdsIntelligenceFingerprint"] = base_fingerprint
    payload["meta"]["adsIntelligenceFingerprint"] = final_fingerprint
    payload["meta"]["adsContextQualificationFingerprint"] = final_fingerprint

    qa["baseAdsIntelligenceFingerprint"] = base_fingerprint
    qa["adsIntelligenceFingerprint"] = final_fingerprint
    qa["adsContextQualificationFingerprint"] = final_fingerprint
    qa["sourceBusinessContextFingerprint"] = context_fingerprint
    qa["businessContextQualification"] = binding_qa

    manifest["baseAdsIntelligenceFingerprint"] = base_fingerprint
    manifest["adsIntelligenceFingerprint"] = final_fingerprint
    manifest["adsContextQualificationFingerprint"] = final_fingerprint
    manifest["sourceBusinessContextFingerprint"] = context_fingerprint
    files = list(manifest.get("files") or [])
    if "ads_context_candidate_preview.json" not in files:
        files.append("ads_context_candidate_preview.json")
    manifest["files"] = files

    preview = build_candidate_preview(payload)
    preview["adsIntelligenceFingerprint"] = final_fingerprint
    _write_json(payload_path, payload)
    _write_json(qa_path, qa)
    _write_json(manifest_path, manifest)
    _write_json(ads_dir / "ads_context_candidate_preview.json", preview)
    return {
        "status": "PASS",
        "baseAdsIntelligenceFingerprint": base_fingerprint,
        "adsIntelligenceFingerprint": final_fingerprint,
        "adsContextQualificationFingerprint": final_fingerprint,
        "sourceBusinessContextFingerprint": context_fingerprint,
        "businessContextQualificationStatus": binding_qa["status"],
        "candidatePreview": preview,
    }
