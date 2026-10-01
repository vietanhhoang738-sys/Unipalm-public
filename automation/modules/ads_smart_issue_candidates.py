"""Smart Issue candidate qualification for persistent Ads diagnoses.

This PREPRODUCTION layer is downstream of Diagnosis Persistence. It does not
create Smart Issues, alerts or actions. It only decides whether a CONFIRMED
persistent diagnosis is sufficiently material, economically exposed and recent
to become an operator-review candidate.

Economic exposure is evidence-only. Current spend, attributed sales and spend
share are never converted into a causal loss estimate.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple


def s(v: Any) -> str:
    return "" if v is None else str(v).strip()


def n(v: Any) -> float:
    try:
        return float(v or 0)
    except Exception:
        return 0.0


def _sha(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _read_json(path: str | Path) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json(path: str | Path, value: Any) -> None:
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _date(value: Any) -> dt.date | None:
    text = s(value)[:10]
    if not text:
        return None
    try:
        return dt.date.fromisoformat(text)
    except Exception:
        return None


def _policy(contract: Mapping[str, Any]) -> Dict[str, Any]:
    raw = dict(contract.get("smart_issue_candidate_policy") or {})
    if not raw or not bool(raw.get("enabled")):
        raise ValueError("Ads smart_issue_candidate_policy must be enabled")
    if s(raw.get("input_source")) != "dynamicDiagnosis.items.persistence":
        raise ValueError("Smart Issue candidates may only consume persistent Dynamic Diagnosis items")
    if s(raw.get("required_persistence_state")) != "CONFIRMED":
        raise ValueError("Smart Issue candidates must require CONFIRMED persistence")
    if bool(raw.get("smart_issue_creation_enabled")):
        raise ValueError("Smart Issue creation must remain disabled")
    if bool(raw.get("causal_claims_enabled")):
        raise ValueError("Smart Issue candidate causal claims must remain disabled")
    if bool(raw.get("automatic_alerts_enabled")) or bool(raw.get("automatic_actions_enabled")):
        raise ValueError("Smart Issue candidate alerts/actions must remain disabled")

    materiality = dict(raw.get("materiality") or {})
    exposure = dict(raw.get("economic_exposure") or {})
    recency = dict(raw.get("recency") or {})
    dedup = dict(raw.get("deduplication") or {})
    lifecycle = dict(raw.get("lifecycle") or {})
    scopes = ("day", "week", "month", "year")

    min_priority = float(materiality.get("minimum_priority_score") or 55)
    min_abs_delta = float(materiality.get("minimum_abs_roas_delta") or 0.25)
    min_share = float(exposure.get("minimum_spend_share") or 0.05)
    high_share = float(exposure.get("high_share_override") or 0.10)
    floors = dict(exposure.get("scope_current_spend_floor_vnd") or {})
    max_age = dict(recency.get("scope_max_age_days") or {})
    continuity = dict(lifecycle.get("scope_continuity_gap_days") or {})
    cooldown = dict(lifecycle.get("scope_reopen_cooldown_days") or {})

    if not (0 <= min_priority <= 100):
        raise ValueError("minimum_priority_score out of range")
    if min_abs_delta <= 0 or not (0 < min_share <= high_share <= 1):
        raise ValueError("Smart Issue materiality/exposure thresholds invalid")
    if s(exposure.get("mode")) != "RELATIVE_AND_SCOPE_ABSOLUTE_OR_HIGH_SHARE_OVERRIDE":
        raise ValueError("unexpected economic exposure mode")
    if s(recency.get("anchor")) != "SHOP_LATEST_READY_DAY_COVERAGE_END":
        raise ValueError("unexpected Smart Issue recency anchor")
    if not bool(dedup.get("one_active_candidate_per_key")) or not bool(dedup.get("latest_material_occurrence_wins")):
        raise ValueError("Smart Issue candidate deduplication must remain latest-one-per-key")
    if not bool(lifecycle.get("cooldown_suppresses_reopen_candidate")):
        raise ValueError("Smart Issue candidate cooldown suppression must remain enabled")

    for scope in scopes:
        if n(floors.get(scope)) < 0:
            raise ValueError(f"negative spend floor for {scope}")
        if int(max_age.get(scope) or 0) < 1:
            raise ValueError(f"missing recency max age for {scope}")
        if int(continuity.get(scope) or 0) < 1:
            raise ValueError(f"missing continuity gap for {scope}")
        if int(cooldown.get(scope) or 0) < int(continuity.get(scope) or 0):
            raise ValueError(f"cooldown must be >= continuity gap for {scope}")

    return {
        **raw,
        "materiality": {**materiality, "minimum_priority_score": min_priority, "minimum_abs_roas_delta": min_abs_delta},
        "economic_exposure": {
            **exposure,
            "minimum_spend_share": min_share,
            "high_share_override": high_share,
            "scope_current_spend_floor_vnd": {k: n(floors.get(k)) for k in scopes},
        },
        "recency": {**recency, "scope_max_age_days": {k: int(max_age.get(k)) for k in scopes}},
        "lifecycle": {
            **lifecycle,
            "scope_continuity_gap_days": {k: int(continuity.get(k)) for k in scopes},
            "scope_reopen_cooldown_days": {k: int(cooldown.get(k)) for k in scopes},
        },
    }


def _latest_evidence_date(shop: Mapping[str, Any]) -> str:
    snapshots = ((((shop.get("periods") or {}).get("day") or {}).get("snapshots") or {}))
    ends = [s(x.get("coverageEnd")) for x in snapshots.values() if s(x.get("status")) == "READY" and s(x.get("coverageEnd"))]
    return max(ends) if ends else ""


def _candidate_identity(shop_id: str, scope: str, item: Mapping[str, Any]) -> Dict[str, Any]:
    persistence = item.get("persistence") or {}
    return {
        "shopId": shop_id,
        "productId": s(item.get("productId")),
        "kind": s(item.get("kind")),
        "scope": scope,
        "contextSignature": list(persistence.get("contextSignature") or []),
    }


def _material_evaluation(item: Mapping[str, Any], *, scope: str, policy: Mapping[str, Any]) -> Dict[str, Any]:
    materiality = policy.get("materiality") or {}
    exposure_policy = policy.get("economic_exposure") or {}
    evidence = item.get("evidence") or {}
    priority = n(item.get("priorityScore"))
    abs_delta = abs(n(evidence.get("roasDelta")))
    spend_share = n(evidence.get("spendShare"))
    current_spend = n(evidence.get("currentSpend"))
    current_sales = n(evidence.get("currentAttributedSales"))
    min_priority = n(materiality.get("minimum_priority_score"))
    min_abs_delta = n(materiality.get("minimum_abs_roas_delta"))
    min_share = n(exposure_policy.get("minimum_spend_share"))
    high_share = n(exposure_policy.get("high_share_override"))
    spend_floor = n((exposure_policy.get("scope_current_spend_floor_vnd") or {}).get(scope))

    priority_ok = priority >= min_priority
    roas_delta_ok = abs_delta >= min_abs_delta
    share_ok = spend_share >= min_share
    absolute_or_override_ok = current_spend >= spend_floor or spend_share >= high_share
    materiality_ok = priority_ok and roas_delta_ok
    economic_exposure_ok = share_ok and absolute_or_override_ok
    blockers = []
    if not priority_ok:
        blockers.append("PRIORITY_BELOW_MINIMUM")
    if not roas_delta_ok:
        blockers.append("ROAS_DELTA_BELOW_MINIMUM")
    if not share_ok:
        blockers.append("SPEND_SHARE_BELOW_MINIMUM")
    if not absolute_or_override_ok:
        blockers.append("SPEND_EXPOSURE_BELOW_SCOPE_FLOOR")
    return {
        "materialityPassed": materiality_ok,
        "economicExposurePassed": economic_exposure_ok,
        "priorityScore": priority,
        "minimumPriorityScore": min_priority,
        "absRoasDelta": abs_delta,
        "minimumAbsRoasDelta": min_abs_delta,
        "currentSpend": current_spend,
        "currentAttributedSales": current_sales,
        "spendShare": spend_share,
        "minimumSpendShare": min_share,
        "scopeSpendFloorVnd": spend_floor,
        "highShareOverride": high_share,
        "economicExposureIsLossEstimate": False,
        "blockers": blockers,
    }


def _age_days(latest_evidence_date: str, coverage_end: str) -> int | None:
    latest = _date(latest_evidence_date)
    end = _date(coverage_end)
    if not latest or not end:
        return None
    return max(0, (latest - end).days)


def _gap_days(previous_end: str, current_end: str) -> int | None:
    prev = _date(previous_end)
    cur = _date(current_end)
    if not prev or not cur:
        return None
    return max(0, (cur - prev).days)


def _candidate_record(item: Mapping[str, Any], *, evaluation: Mapping[str, Any]) -> Dict[str, Any]:
    kind = s(item.get("kind"))
    return {
        "candidateId": s(evaluation.get("candidateId")),
        "candidateKey": s(evaluation.get("candidateKey")),
        "candidateType": "RISK" if kind == "PROBLEM" else "OPPORTUNITY",
        "kind": kind,
        "operatorType": s(item.get("operatorType")),
        "productId": s(item.get("productId")),
        "productName": s(item.get("productName")),
        "productSku": s(item.get("productSku")),
        "sourceDiagnosisId": s(item.get("diagnosisId")),
        "scope": s(evaluation.get("scope")),
        "optionKey": s(evaluation.get("optionKey")),
        "coverageEnd": s(evaluation.get("coverageEnd")),
        "latestEvidenceDate": s(evaluation.get("latestEvidenceDate")),
        "evidenceAgeDays": evaluation.get("evidenceAgeDays"),
        "lifecycleState": s(evaluation.get("lifecycleState")),
        "priorityTier": s(item.get("priorityTier")),
        "priorityScore": n(item.get("priorityScore")),
        "headline": s(item.get("headline")),
        "summary": s(item.get("summary")),
        "reviewFocus": s(item.get("reviewFocus")),
        "persistence": dict(item.get("persistence") or {}),
        "economicExposure": dict(evaluation.get("economicExposure") or {}),
        "evidenceOnly": True,
        "causalClaim": False,
        "smartIssueCreated": False,
        "automaticAlertEligible": False,
        "automaticActionEligible": False,
    }


def bind_smart_issue_candidates(payload: Dict[str, Any], *, contract: Mapping[str, Any]) -> Dict[str, Any]:
    policy = _policy(contract)
    allowed_kinds = {s(x) for x in policy.get("candidate_kinds") or []}
    required_state = s(policy.get("required_persistence_state"))

    for shop_id, shop in (payload.get("shops") or {}).items():
        latest_date = _latest_evidence_date(shop)
        confirmed_records: List[Dict[str, Any]] = []
        blocked_counts: Dict[str, int] = {}

        for scope in ("day", "week", "month", "year"):
            snapshots = ((((shop.get("periods") or {}).get(scope) or {}).get("snapshots") or {}))
            for option_key, snapshot in snapshots.items():
                coverage_end = s(snapshot.get("coverageEnd"))
                for item in ((snapshot.get("dynamicDiagnosis") or {}).get("items") or []):
                    persistence = item.get("persistence") or {}
                    if s(persistence.get("state")) != required_state:
                        continue
                    identity = _candidate_identity(shop_id, scope, item)
                    key = _sha(identity)
                    candidate_id = "ads_sic_" + key[:16]
                    material = _material_evaluation(item, scope=scope, policy=policy)
                    kind_allowed = s(item.get("kind")) in allowed_kinds
                    if not kind_allowed:
                        material = {**material, "blockers": list(material.get("blockers") or []) + ["KIND_NOT_ALLOWED"]}
                    base_material = kind_allowed and bool(material.get("materialityPassed")) and bool(material.get("economicExposurePassed"))
                    evaluation = {
                        "status": "PENDING_LIFECYCLE" if base_material else ("BLOCKED_MATERIALITY" if not bool(material.get("materialityPassed")) else "BLOCKED_ECONOMIC_EXPOSURE"),
                        "eligible": False,
                        "candidateId": candidate_id,
                        "candidateKey": key,
                        "scope": scope,
                        "optionKey": option_key,
                        "coverageEnd": coverage_end,
                        "latestEvidenceDate": latest_date,
                        "evidenceAgeDays": _age_days(latest_date, coverage_end),
                        "requiredPersistenceState": required_state,
                        "sourcePersistenceState": s(persistence.get("state")),
                        "lifecycleState": "NOT_APPLICABLE",
                        "duplicateSuppressed": False,
                        "cooldownSuppressed": False,
                        "materialityPassed": bool(material.get("materialityPassed")),
                        "economicExposurePassed": bool(material.get("economicExposurePassed")),
                        "economicExposure": material,
                        "evidenceOnly": True,
                        "causalClaim": False,
                        "smartIssueCreated": False,
                        "automaticAlertEligible": False,
                        "automaticActionEligible": False,
                    }
                    item["smartIssueCandidate"] = evaluation
                    rec = {
                        "item": item,
                        "evaluation": evaluation,
                        "candidateKey": key,
                        "coverageEnd": coverage_end,
                        "scope": scope,
                        "baseMaterial": base_material,
                    }
                    confirmed_records.append(rec)
                    if not base_material:
                        blocked_counts[evaluation["status"]] = blocked_counts.get(evaluation["status"], 0) + 1

        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for rec in confirmed_records:
            if rec["baseMaterial"]:
                grouped.setdefault(rec["candidateKey"], []).append(rec)

        active_candidates: List[Dict[str, Any]] = []
        for key, records in grouped.items():
            records.sort(key=lambda x: (s(x.get("coverageEnd")), s((x.get("evaluation") or {}).get("optionKey"))))
            previous: Dict[str, Any] | None = None
            for rec in records:
                evaluation = rec["evaluation"]
                scope = rec["scope"]
                lifecycle_policy = policy.get("lifecycle") or {}
                continuity = int((lifecycle_policy.get("scope_continuity_gap_days") or {}).get(scope) or 1)
                cooldown = int((lifecycle_policy.get("scope_reopen_cooldown_days") or {}).get(scope) or continuity)
                if previous is None:
                    lifecycle_state = "NEW"
                else:
                    gap = _gap_days(previous.get("coverageEnd"), rec.get("coverageEnd"))
                    if gap is None or gap <= continuity:
                        lifecycle_state = "CONTINUING"
                    elif gap <= cooldown:
                        lifecycle_state = "COOLDOWN_SUPPRESSED"
                    else:
                        lifecycle_state = "REOPENED"
                evaluation["lifecycleState"] = lifecycle_state
                previous = rec

            latest = records[-1]
            for rec in records[:-1]:
                ev = rec["evaluation"]
                ev["status"] = "DUPLICATE_SUPPRESSED"
                ev["duplicateSuppressed"] = True
                blocked_counts["DUPLICATE_SUPPRESSED"] = blocked_counts.get("DUPLICATE_SUPPRESSED", 0) + 1

            ev = latest["evaluation"]
            scope = latest["scope"]
            max_age = int(((policy.get("recency") or {}).get("scope_max_age_days") or {}).get(scope) or 1)
            age = ev.get("evidenceAgeDays")
            recency_ok = age is not None and int(age) <= max_age
            ev["maximumEvidenceAgeDays"] = max_age
            ev["recencyPassed"] = recency_ok
            if s(ev.get("lifecycleState")) == "COOLDOWN_SUPPRESSED":
                ev["status"] = "COOLDOWN_SUPPRESSED"
                ev["cooldownSuppressed"] = True
                blocked_counts["COOLDOWN_SUPPRESSED"] = blocked_counts.get("COOLDOWN_SUPPRESSED", 0) + 1
            elif not recency_ok:
                ev["status"] = "BLOCKED_RECENCY"
                blocked_counts["BLOCKED_RECENCY"] = blocked_counts.get("BLOCKED_RECENCY", 0) + 1
            else:
                ev["status"] = "ELIGIBLE"
                ev["eligible"] = True
                active_candidates.append(_candidate_record(latest["item"], evaluation=ev))

        active_candidates.sort(key=lambda x: (-n(x.get("priorityScore")), -n((x.get("economicExposure") or {}).get("spendShare")), s(x.get("candidateId"))))
        shop["smartIssueCandidates"] = active_candidates
        shop["smartIssueCandidateLineage"] = {
            "mode": s(policy.get("mode")),
            "inputSource": "dynamicDiagnosis.items.persistence",
            "requiredPersistenceState": required_state,
            "latestEvidenceDate": latest_date,
            "confirmedDiagnosisEvaluatedCount": len(confirmed_records),
            "materialPersistentOccurrenceCount": sum(1 for x in confirmed_records if x.get("baseMaterial")),
            "activeCandidateCount": len(active_candidates),
            "blockedCounts": blocked_counts,
            "oneActiveCandidatePerKey": True,
            "smartIssueCreationEnabled": False,
            "automaticAlertsEnabled": False,
            "automaticActionsEnabled": False,
        }

    payload.setdefault("capabilities", {})["adsSmartIssueCandidates"] = True
    payload["capabilities"]["adsSmartIssueCandidatesEnabled"] = True
    payload["capabilities"]["adsSmartIssuesEnabled"] = False
    payload["capabilities"]["adsSmartIssueAutomaticAlertsEnabled"] = False
    payload["capabilities"]["adsSmartIssueAutomaticActionsEnabled"] = False
    return payload


def validate_smart_issue_candidates(payload: Mapping[str, Any], *, contract: Mapping[str, Any]) -> Dict[str, Any]:
    policy = _policy(contract)
    checks: List[Dict[str, Any]] = []

    def ck(name: str, ok: bool, detail: Any = None) -> None:
        checks.append({"name": name, "status": "PASS" if ok else "FAIL", "detail": detail or {}})

    caps = payload.get("capabilities") or {}
    ck("smart_issue_candidate_capability", bool(caps.get("adsSmartIssueCandidates")))
    ck("smart_issue_candidates_enabled", bool(caps.get("adsSmartIssueCandidatesEnabled")))
    ck("smart_issues_disabled", caps.get("adsSmartIssuesEnabled") is False)
    ck("smart_issue_alerts_disabled", caps.get("adsSmartIssueAutomaticAlertsEnabled") is False)
    ck("smart_issue_actions_disabled", caps.get("adsSmartIssueAutomaticActionsEnabled") is False)

    for shop_id, shop in (payload.get("shops") or {}).items():
        lineage = shop.get("smartIssueCandidateLineage") or {}
        ck(f"{shop_id}_candidate_lineage_source", s(lineage.get("inputSource")) == "dynamicDiagnosis.items.persistence")
        ck(f"{shop_id}_candidate_lineage_state", s(lineage.get("requiredPersistenceState")) == "CONFIRMED")
        candidates = list(shop.get("smartIssueCandidates") or [])
        keys = [s(x.get("candidateKey")) for x in candidates]
        ids = [s(x.get("candidateId")) for x in candidates]
        ck(f"{shop_id}_candidate_key_unique", len(keys) == len(set(keys)))
        ck(f"{shop_id}_candidate_id_unique", len(ids) == len(set(ids)))

        eligible_item_ids = set()
        for scope in ("day", "week", "month", "year"):
            snapshots = ((((shop.get("periods") or {}).get(scope) or {}).get("snapshots") or {}))
            for option_key, snapshot in snapshots.items():
                for item in ((snapshot.get("dynamicDiagnosis") or {}).get("items") or []):
                    ev = item.get("smartIssueCandidate") or {}
                    if not ev:
                        continue
                    name = f"{shop_id}_{scope}_{option_key}_{s(item.get('productId'))}"
                    ck(f"{name}_candidate_from_confirmed", s((item.get("persistence") or {}).get("state")) == "CONFIRMED")
                    ck(f"{name}_candidate_noncausal", not bool(ev.get("causalClaim")) and not bool(ev.get("smartIssueCreated")))
                    ck(f"{name}_candidate_no_automation", not bool(ev.get("automaticAlertEligible")) and not bool(ev.get("automaticActionEligible")))
                    if bool(ev.get("eligible")):
                        eligible_item_ids.add(s(ev.get("candidateId")))
                        ck(f"{name}_eligible_materiality", bool(ev.get("materialityPassed")) and bool(ev.get("economicExposurePassed")))
                        ck(f"{name}_eligible_recency", bool(ev.get("recencyPassed")))
                        ck(f"{name}_eligible_lifecycle", s(ev.get("lifecycleState")) in {"NEW", "CONTINUING", "REOPENED"})
                        ck(f"{name}_eligible_not_suppressed", not bool(ev.get("duplicateSuppressed")) and not bool(ev.get("cooldownSuppressed")))
                        ck(f"{name}_eligible_status", s(ev.get("status")) == "ELIGIBLE")
                    exposure = ev.get("economicExposure") or {}
                    ck(f"{name}_economic_exposure_not_loss", exposure.get("economicExposureIsLossEstimate") is False)

        ck(f"{shop_id}_candidate_list_matches_eligible_items", set(ids) == eligible_item_ids, {"candidateIds": ids, "eligibleItemIds": sorted(eligible_item_ids)})
        for candidate in candidates:
            name = f"{shop_id}_{s(candidate.get('candidateId'))}"
            ck(f"{name}_candidate_evidence_only", bool(candidate.get("evidenceOnly")) and not bool(candidate.get("causalClaim")))
            ck(f"{name}_candidate_not_created", candidate.get("smartIssueCreated") is False)
            ck(f"{name}_candidate_no_automation", not bool(candidate.get("automaticAlertEligible")) and not bool(candidate.get("automaticActionEligible")))

    failed = [x for x in checks if x["status"] == "FAIL"]
    return {"status": "PASS" if not failed else "FAIL", "failedCheckCount": len(failed), "checks": checks}


def build_smart_issue_candidate_preview(payload: Mapping[str, Any]) -> Dict[str, Any]:
    shops: Dict[str, Any] = {}
    for shop_id, shop in (payload.get("shops") or {}).items():
        blocked_examples = []
        status_counts: Dict[str, int] = {}
        confirmed_count = 0
        for scope in ("day", "week", "month", "year"):
            snapshots = ((((shop.get("periods") or {}).get(scope) or {}).get("snapshots") or {}))
            for option_key, snapshot in snapshots.items():
                for item in ((snapshot.get("dynamicDiagnosis") or {}).get("items") or []):
                    ev = item.get("smartIssueCandidate") or {}
                    if not ev:
                        continue
                    confirmed_count += 1
                    status = s(ev.get("status"))
                    status_counts[status] = status_counts.get(status, 0) + 1
                    if status != "ELIGIBLE" and len(blocked_examples) < 5:
                        blocked_examples.append({
                            "productId": s(item.get("productId")),
                            "productName": s(item.get("productName")),
                            "kind": s(item.get("kind")),
                            "scope": scope,
                            "optionKey": option_key,
                            "status": status,
                            "priorityScore": n(item.get("priorityScore")),
                            "evidenceAgeDays": ev.get("evidenceAgeDays"),
                            "blockers": list(((ev.get("economicExposure") or {}).get("blockers") or [])),
                        })
        shops[shop_id] = {
            "displayName": s(shop.get("displayName")),
            "latestEvidenceDate": s((shop.get("smartIssueCandidateLineage") or {}).get("latestEvidenceDate")),
            "confirmedDiagnosisEvaluatedCount": confirmed_count,
            "activeCandidateCount": len(shop.get("smartIssueCandidates") or []),
            "statusCounts": status_counts,
            "activeCandidates": list(shop.get("smartIssueCandidates") or []),
            "blockedConfirmedExamples": blocked_examples,
        }
    return {
        "status": "PREPRODUCTION_CANDIDATE",
        "preSmartIssueAdsIntelligenceFingerprint": s((payload.get("meta") or {}).get("preSmartIssueAdsIntelligenceFingerprint")),
        "adsDiagnosisPersistenceFingerprint": s((payload.get("meta") or {}).get("adsDiagnosisPersistenceFingerprint")),
        "adsSmartIssueCandidateFingerprint": s((payload.get("meta") or {}).get("adsSmartIssueCandidateFingerprint")),
        "adsIntelligenceFingerprint": s((payload.get("meta") or {}).get("adsIntelligenceFingerprint")),
        "shops": shops,
        "safety": {
            "productionActivationEnabled": False,
            "smartIssueCreationEnabled": False,
            "automaticAlertsEnabled": False,
            "automaticActionsEnabled": False,
            "causalClaimsEnabled": False,
        },
    }


def bind_ads_smart_issue_candidate_artifacts(*, ads_output_dir: str | Path, contract_path: str | Path) -> Dict[str, Any]:
    ads_dir = Path(ads_output_dir)
    payload_path = ads_dir / "ads_intelligence.json"
    qa_path = ads_dir / "ads_intelligence_qa_report.json"
    manifest_path = ads_dir / "ads_intelligence_manifest.json"
    for path in (payload_path, qa_path, manifest_path):
        if not path.exists():
            raise ValueError(f"required Smart Issue candidate artifact missing: {path}")

    payload = _read_json(payload_path)
    qa = _read_json(qa_path)
    manifest = _read_json(manifest_path)
    contract = _read_json(contract_path)
    persistence_fingerprint = s((payload.get("meta") or {}).get("adsDiagnosisPersistenceFingerprint"))
    current_fingerprint = s((payload.get("meta") or {}).get("adsIntelligenceFingerprint"))
    if not persistence_fingerprint or not current_fingerprint:
        raise ValueError("Diagnosis Persistence fingerprint is required before Smart Issue candidates")
    if current_fingerprint != persistence_fingerprint:
        raise ValueError("Smart Issue candidates must bind directly after Diagnosis Persistence")
    if current_fingerprint != s(qa.get("adsIntelligenceFingerprint")) or current_fingerprint != s(manifest.get("adsIntelligenceFingerprint")):
        raise ValueError("Ads fingerprint mismatch before Smart Issue candidate qualification")

    bind_smart_issue_candidates(payload, contract=contract)
    candidate_qa = validate_smart_issue_candidates(payload, contract=contract)
    if candidate_qa["status"] != "PASS":
        failed = [x["name"] for x in candidate_qa["checks"] if x["status"] == "FAIL"]
        raise ValueError(f"Ads Smart Issue Candidate QA failed: {failed[:20]}")

    final_fingerprint = _sha({
        "preSmartIssueAdsIntelligenceFingerprint": current_fingerprint,
        "adsDiagnosisPersistenceFingerprint": persistence_fingerprint,
        "smartIssueCandidatePolicy": _policy(contract),
        "payload": payload,
    })
    payload["meta"]["preSmartIssueAdsIntelligenceFingerprint"] = current_fingerprint
    payload["meta"]["adsSmartIssueCandidateFingerprint"] = final_fingerprint
    payload["meta"]["adsIntelligenceFingerprint"] = final_fingerprint

    qa["preSmartIssueAdsIntelligenceFingerprint"] = current_fingerprint
    qa["adsSmartIssueCandidateFingerprint"] = final_fingerprint
    qa["adsIntelligenceFingerprint"] = final_fingerprint
    qa["smartIssueCandidates"] = candidate_qa

    manifest["preSmartIssueAdsIntelligenceFingerprint"] = current_fingerprint
    manifest["adsSmartIssueCandidateFingerprint"] = final_fingerprint
    manifest["adsIntelligenceFingerprint"] = final_fingerprint
    files = list(manifest.get("files") or [])
    if "ads_smart_issue_candidate_preview.json" not in files:
        files.append("ads_smart_issue_candidate_preview.json")
    manifest["files"] = files

    preview = build_smart_issue_candidate_preview(payload)
    preview["preSmartIssueAdsIntelligenceFingerprint"] = current_fingerprint
    preview["adsSmartIssueCandidateFingerprint"] = final_fingerprint
    preview["adsIntelligenceFingerprint"] = final_fingerprint
    _write_json(payload_path, payload)
    _write_json(qa_path, qa)
    _write_json(manifest_path, manifest)
    _write_json(ads_dir / "ads_smart_issue_candidate_preview.json", preview)
    return {
        "status": "PASS",
        "preSmartIssueAdsIntelligenceFingerprint": current_fingerprint,
        "adsDiagnosisPersistenceFingerprint": persistence_fingerprint,
        "adsSmartIssueCandidateFingerprint": final_fingerprint,
        "adsIntelligenceFingerprint": final_fingerprint,
        "smartIssueCandidateStatus": candidate_qa["status"],
        "candidatePreview": preview,
    }
