"""Multi-window persistence confirmation for Dynamic Ads Diagnosis.

This PREPRODUCTION layer is downstream of context-qualified Dynamic Diagnosis.
It never creates new diagnoses and never reuses raw Ads signals. It asks a
narrower question: has the same product diagnosis repeated across independent,
context-equivalent observation windows strongly enough to be considered
persistent?

Confirmation is deliberately conservative:
- same shop and same time scope only;
- same current Business Context signature only;
- only context-compatible READY / NO_MATERIAL_DIAGNOSIS observations count;
- blocked context windows are excluded rather than treated as misses;
- observation windows must not overlap;
- an opposite diagnosis kind in the lookback blocks confirmation;
- Smart Issue generation, alerts, actions and causal claims remain disabled.
"""
from __future__ import annotations

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


def _policy(contract: Mapping[str, Any]) -> Dict[str, Any]:
    raw = dict(contract.get("diagnosis_persistence_policy") or {})
    if not raw:
        raise ValueError("Ads diagnosis_persistence_policy is required")
    if not bool(raw.get("enabled")):
        raise ValueError("Ads Diagnosis Persistence must be enabled")
    if s(raw.get("input_source")) != "dynamicDiagnosis.items":
        raise ValueError("Ads Diagnosis Persistence may only consume dynamicDiagnosis.items")
    if s(raw.get("scope_mode")) != "SAME_SCOPE_ONLY":
        raise ValueError("Ads Diagnosis Persistence must remain same-scope only")
    if s(raw.get("context_signature_mode")) != "SAME_CURRENT_CONTEXT_SIGNATURE":
        raise ValueError("Ads Diagnosis Persistence must require the same current context signature")
    if s(raw.get("independence_rule")) != "NON_OVERLAPPING_WINDOWS_ONLY":
        raise ValueError("Ads Diagnosis Persistence must use non-overlapping windows only")
    if bool(raw.get("smart_issue_candidate_generation_enabled")):
        raise ValueError("Smart Issue candidate generation must remain disabled")
    if bool(raw.get("causal_claims_enabled")):
        raise ValueError("Ads Diagnosis Persistence causal claims must remain disabled")
    if bool(raw.get("automatic_alerts_enabled")) or bool(raw.get("automatic_actions_enabled")):
        raise ValueError("Ads Diagnosis Persistence alerts/actions must remain disabled")

    lookback = int(raw.get("lookback_observations") or 3)
    min_support = int(raw.get("minimum_support_windows") or 2)
    min_ratio = float(raw.get("minimum_support_ratio") or (2.0 / 3.0))
    if lookback < 2 or lookback > 12:
        raise ValueError("lookback_observations must be between 2 and 12")
    if min_support < 2 or min_support > lookback:
        raise ValueError("minimum_support_windows must be between 2 and lookback_observations")
    if not (0.5 <= min_ratio <= 1.0):
        raise ValueError("minimum_support_ratio must be between 0.5 and 1.0")
    return {
        **raw,
        "lookback_observations": lookback,
        "minimum_support_windows": min_support,
        "minimum_support_ratio": min_ratio,
    }


def _context_signature(snapshot: Mapping[str, Any]) -> Tuple[str, ...]:
    qualification = ((snapshot.get("businessContext") or {}).get("qualification") or {})
    return tuple(sorted(s(x) for x in (qualification.get("currentSignature") or []) if s(x)))


def _coverage(snapshot: Mapping[str, Any]) -> Tuple[str, str]:
    return s(snapshot.get("coverageStart")), s(snapshot.get("coverageEnd"))


def _eligible_observation(snapshot: Mapping[str, Any]) -> bool:
    if s(snapshot.get("status")) != "READY":
        return False
    if s((snapshot.get("businessContext") or {}).get("matchEvaluation")) != "CONTEXT_COMPATIBLE":
        return False
    if not bool(snapshot.get("strongDirectionalDiagnosisEligible")):
        return False
    if s((snapshot.get("dynamicDiagnosis") or {}).get("status")) not in {"READY", "NO_MATERIAL_DIAGNOSIS"}:
        return False
    start, end = _coverage(snapshot)
    return bool(start and end and _context_signature(snapshot))


def _non_overlapping_history(
    snapshots: Mapping[str, Mapping[str, Any]],
    *,
    current_key: str,
    current_snapshot: Mapping[str, Any],
    lookback: int,
) -> List[Tuple[str, Mapping[str, Any]]]:
    """Return current + prior independent observations, newest first.

    Prior rolling windows are greedily selected backwards and each selected
    window must end before the next newer selected window begins. This prevents
    adjacent rolling 7D windows sharing six days from masquerading as two
    independent confirmations.
    """
    if not _eligible_observation(current_snapshot):
        return []
    signature = _context_signature(current_snapshot)
    current_start, _ = _coverage(current_snapshot)
    selected: List[Tuple[str, Mapping[str, Any]]] = [(current_key, current_snapshot)]
    boundary_start = current_start

    candidates = []
    for option_key, snapshot in snapshots.items():
        if option_key == current_key or not _eligible_observation(snapshot):
            continue
        if _context_signature(snapshot) != signature:
            continue
        start, end = _coverage(snapshot)
        if end >= boundary_start:
            continue
        candidates.append((end, option_key, start, snapshot))
    candidates.sort(reverse=True, key=lambda x: (x[0], x[1]))

    for end, option_key, start, snapshot in candidates:
        if end >= boundary_start:
            continue
        selected.append((option_key, snapshot))
        boundary_start = start
        if len(selected) >= lookback:
            break
    return selected


def _persistence_reason(state: str, support: int, eligible: int, conflicts: int) -> str:
    if state == "CONFIRMED":
        return f"Chẩn đoán cùng chiều lặp lại ở {support}/{eligible} cửa sổ độc lập, cùng bối cảnh và cùng scope."
    if state == "CONFLICTED":
        return f"Có {conflicts} cửa sổ xuất hiện chẩn đoán ngược chiều cho cùng sản phẩm; chưa được xác nhận bền vững."
    if state == "FIRST_OBSERVATION":
        return "Chưa có đủ cửa sổ độc lập cùng bối cảnh để kiểm tra độ bền của chẩn đoán."
    return f"Chẩn đoán hiện chỉ xuất hiện ở {support}/{eligible} cửa sổ độc lập đủ điều kiện; tiếp tục theo dõi trước khi xác nhận."


def _evaluate_item_persistence(
    item: Mapping[str, Any],
    windows: Sequence[Tuple[str, Mapping[str, Any]]],
    *,
    scope_key: str,
    policy: Mapping[str, Any],
) -> Dict[str, Any]:
    pid = s(item.get("productId"))
    kind = s(item.get("kind"))
    support_keys: List[str] = []
    conflict_keys: List[str] = []
    observations: List[Dict[str, Any]] = []

    for option_key, snapshot in windows:
        diag_items = list((snapshot.get("dynamicDiagnosis") or {}).get("items") or [])
        kinds = {s(x.get("kind")) for x in diag_items if s(x.get("productId")) == pid}
        same = kind in kinds
        opposite = any(k and k != kind for k in kinds)
        if same:
            support_keys.append(option_key)
        if opposite:
            conflict_keys.append(option_key)
        start, end = _coverage(snapshot)
        observations.append({
            "optionKey": option_key,
            "scope": scope_key,
            "coverageStart": start,
            "coverageEnd": end,
            "contextSignature": list(_context_signature(snapshot)),
            "sameDirectionObserved": same,
            "oppositeDirectionObserved": opposite,
            "diagnosisStatus": s((snapshot.get("dynamicDiagnosis") or {}).get("status")),
        })

    eligible_count = len(windows)
    support_count = len(support_keys)
    conflict_count = len(conflict_keys)
    support_ratio = support_count / eligible_count if eligible_count else 0.0
    min_support = int(policy.get("minimum_support_windows") or 2)
    min_ratio = float(policy.get("minimum_support_ratio") or (2.0 / 3.0))

    if eligible_count < min_support:
        state = "FIRST_OBSERVATION"
    elif conflict_count > 0:
        state = "CONFLICTED"
    elif support_count >= min_support and support_ratio >= min_ratio:
        state = "CONFIRMED"
    else:
        state = "ONE_OFF"

    confirmed = state == "CONFIRMED"
    return {
        "state": state,
        "reason": _persistence_reason(state, support_count, eligible_count, conflict_count),
        "scope": scope_key,
        "contextSignature": list(_context_signature(windows[0][1])) if windows else [],
        "lookbackObservationLimit": int(policy.get("lookback_observations") or 3),
        "eligibleIndependentWindowCount": eligible_count,
        "supportWindowCount": support_count,
        "supportRatio": support_ratio,
        "oppositeDirectionWindowCount": conflict_count,
        "supportWindowKeys": support_keys,
        "conflictWindowKeys": conflict_keys,
        "observations": observations,
        "confirmationEligible": confirmed,
        "smartIssueCandidateEligible": False,
        "evidenceOnly": True,
        "causalClaim": False,
        "automaticAlertEligible": False,
        "automaticActionEligible": False,
    }


def bind_diagnosis_persistence(payload: Dict[str, Any], *, contract: Mapping[str, Any]) -> Dict[str, Any]:
    policy = _policy(contract)
    for shop in (payload.get("shops") or {}).values():
        state_counts: Dict[str, int] = {}
        confirmed_count = 0
        evaluated_count = 0
        for scope_key in ("day", "week", "month", "year"):
            block = (shop.get("periods") or {}).get(scope_key) or {}
            snapshots = block.get("snapshots") or {}
            for option_key in sorted(snapshots):
                snapshot = snapshots[option_key]
                diagnosis = snapshot.get("dynamicDiagnosis") or {}
                items = list(diagnosis.get("items") or [])
                summary = {
                    "status": "NOT_APPLICABLE",
                    "reason": "Kỳ này chưa có Dynamic Diagnosis đủ điều kiện để kiểm tra persistence.",
                    "evaluatedItemCount": 0,
                    "confirmedCount": 0,
                    "oneOffCount": 0,
                    "conflictedCount": 0,
                    "firstObservationCount": 0,
                    "smartIssueCandidatesEnabled": False,
                    "automaticAlertsEnabled": False,
                    "automaticActionsEnabled": False,
                    "causalClaim": False,
                }
                if s(diagnosis.get("status")) == "READY" and items:
                    windows = _non_overlapping_history(
                        snapshots,
                        current_key=option_key,
                        current_snapshot=snapshot,
                        lookback=int(policy.get("lookback_observations") or 3),
                    )
                    for item in items:
                        persistence = _evaluate_item_persistence(item, windows, scope_key=scope_key, policy=policy)
                        item["persistence"] = persistence
                        state = s(persistence.get("state"))
                        state_counts[state] = state_counts.get(state, 0) + 1
                        evaluated_count += 1
                        if state == "CONFIRMED":
                            confirmed_count += 1
                    states = [s((x.get("persistence") or {}).get("state")) for x in items]
                    summary = {
                        "status": "EVALUATED",
                        "reason": "Đã kiểm tra chẩn đoán trên các cửa sổ độc lập cùng bối cảnh và cùng scope.",
                        "evaluatedItemCount": len(items),
                        "confirmedCount": sum(1 for x in states if x == "CONFIRMED"),
                        "oneOffCount": sum(1 for x in states if x == "ONE_OFF"),
                        "conflictedCount": sum(1 for x in states if x == "CONFLICTED"),
                        "firstObservationCount": sum(1 for x in states if x == "FIRST_OBSERVATION"),
                        "smartIssueCandidatesEnabled": False,
                        "automaticAlertsEnabled": False,
                        "automaticActionsEnabled": False,
                        "causalClaim": False,
                    }
                snapshot["diagnosisPersistence"] = summary
        shop["diagnosisPersistenceLineage"] = {
            "mode": s(policy.get("mode")),
            "inputSource": "dynamicDiagnosis.items",
            "scopeMode": "SAME_SCOPE_ONLY",
            "contextSignatureMode": "SAME_CURRENT_CONTEXT_SIGNATURE",
            "independenceRule": "NON_OVERLAPPING_WINDOWS_ONLY",
            "lookbackObservations": int(policy.get("lookback_observations") or 3),
            "minimumSupportWindows": int(policy.get("minimum_support_windows") or 2),
            "minimumSupportRatio": float(policy.get("minimum_support_ratio") or (2.0 / 3.0)),
            "evaluatedDiagnosisItemCount": evaluated_count,
            "confirmedDiagnosisItemCount": confirmed_count,
            "stateCounts": state_counts,
            "smartIssueCandidatesEnabled": False,
        }
    payload.setdefault("capabilities", {})["adsDiagnosisPersistence"] = True
    payload["capabilities"]["adsMultiWindowConfirmation"] = True
    payload["capabilities"]["adsSmartIssueCandidatesEnabled"] = False
    return payload


def _windows_are_non_overlapping(observations: Sequence[Mapping[str, Any]]) -> bool:
    windows = []
    for row in observations:
        start, end = s(row.get("coverageStart")), s(row.get("coverageEnd"))
        if not start or not end:
            return False
        windows.append((start, end))
    windows.sort()
    return all(windows[i - 1][1] < windows[i][0] for i in range(1, len(windows)))


def validate_diagnosis_persistence(payload: Mapping[str, Any], *, contract: Mapping[str, Any]) -> Dict[str, Any]:
    policy = _policy(contract)
    checks: List[Dict[str, Any]] = []

    def ck(name: str, ok: bool, detail: Any = None) -> None:
        checks.append({"name": name, "status": "PASS" if ok else "FAIL", "detail": detail or {}})

    caps = payload.get("capabilities") or {}
    ck("diagnosis_persistence_capability", bool(caps.get("adsDiagnosisPersistence")))
    ck("multi_window_confirmation_capability", bool(caps.get("adsMultiWindowConfirmation")))
    ck("smart_issue_candidates_disabled", caps.get("adsSmartIssueCandidatesEnabled") is False)

    min_support = int(policy.get("minimum_support_windows") or 2)
    min_ratio = float(policy.get("minimum_support_ratio") or (2.0 / 3.0))
    allowed_states = {"CONFIRMED", "ONE_OFF", "CONFLICTED", "FIRST_OBSERVATION"}

    for shop_id, shop in (payload.get("shops") or {}).items():
        lineage = shop.get("diagnosisPersistenceLineage") or {}
        ck(f"{shop_id}_persistence_lineage_source", s(lineage.get("inputSource")) == "dynamicDiagnosis.items")
        ck(f"{shop_id}_persistence_lineage_independence", s(lineage.get("independenceRule")) == "NON_OVERLAPPING_WINDOWS_ONLY")
        for scope_key in ("day", "week", "month", "year"):
            snapshots = ((((shop.get("periods") or {}).get(scope_key) or {}).get("snapshots") or {}))
            for option_key, snapshot in snapshots.items():
                diagnosis = snapshot.get("dynamicDiagnosis") or {}
                items = list(diagnosis.get("items") or [])
                summary = snapshot.get("diagnosisPersistence") or {}
                if s(diagnosis.get("status")) == "READY" and items:
                    ck(f"{shop_id}_{scope_key}_{option_key}_persistence_summary", s(summary.get("status")) == "EVALUATED")
                for item in items:
                    persistence = item.get("persistence") or {}
                    state = s(persistence.get("state"))
                    name = f"{shop_id}_{scope_key}_{option_key}_{s(item.get('productId'))}"
                    ck(f"{name}_persistence_state", state in allowed_states, {"state": state})
                    eligible = int(persistence.get("eligibleIndependentWindowCount") or 0)
                    support = int(persistence.get("supportWindowCount") or 0)
                    conflicts = int(persistence.get("oppositeDirectionWindowCount") or 0)
                    ratio = n(persistence.get("supportRatio"))
                    ck(f"{name}_support_bounds", 0 <= support <= eligible and 0 <= conflicts <= eligible)
                    ck(f"{name}_support_ratio", abs(ratio - (support / eligible if eligible else 0.0)) <= 1e-12)
                    observations = list(persistence.get("observations") or [])
                    ck(f"{name}_window_count", len(observations) == eligible)
                    ck(f"{name}_non_overlapping", _windows_are_non_overlapping(observations))
                    signatures = {tuple(row.get("contextSignature") or []) for row in observations}
                    ck(f"{name}_same_context_signature", len(signatures) <= 1 and bool(signatures))
                    ck(f"{name}_same_scope", all(s(row.get("scope")) == scope_key for row in observations))
                    if state == "CONFIRMED":
                        ck(f"{name}_confirmed_threshold", support >= min_support and ratio >= min_ratio and conflicts == 0)
                        ck(f"{name}_confirmed_flag", bool(persistence.get("confirmationEligible")))
                    else:
                        ck(f"{name}_unconfirmed_flag", not bool(persistence.get("confirmationEligible")))
                    ck(f"{name}_smart_issue_disabled", not bool(persistence.get("smartIssueCandidateEligible")))
                    ck(
                        f"{name}_persistence_safety",
                        not bool(persistence.get("causalClaim"))
                        and not bool(persistence.get("automaticAlertEligible"))
                        and not bool(persistence.get("automaticActionEligible")),
                    )

    failed = [x for x in checks if x["status"] == "FAIL"]
    return {"status": "PASS" if not failed else "FAIL", "failedCheckCount": len(failed), "checks": checks}


def build_persistence_candidate_preview(payload: Mapping[str, Any]) -> Dict[str, Any]:
    shops: Dict[str, Any] = {}
    for shop_id, shop in (payload.get("shops") or {}).items():
        scopes: Dict[str, Any] = {}
        total_evaluated = 0
        total_confirmed = 0
        state_counts: Dict[str, int] = {}
        for scope_key in ("day", "week", "month", "year"):
            block = (shop.get("periods") or {}).get(scope_key) or {}
            options = list(block.get("options") or [])
            latest_key = options[-1] if options else ""
            latest = (block.get("snapshots") or {}).get(latest_key) or {}
            latest_summary = latest.get("diagnosisPersistence") or {}
            historical_evaluated = 0
            historical_confirmed = 0
            scope_states: Dict[str, int] = {}
            confirmed_examples = []
            for snapshot in (block.get("snapshots") or {}).values():
                for item in ((snapshot.get("dynamicDiagnosis") or {}).get("items") or []):
                    persistence = item.get("persistence") or {}
                    state = s(persistence.get("state"))
                    if not state:
                        continue
                    historical_evaluated += 1
                    scope_states[state] = scope_states.get(state, 0) + 1
                    state_counts[state] = state_counts.get(state, 0) + 1
                    if state == "CONFIRMED":
                        historical_confirmed += 1
                        if len(confirmed_examples) < 3:
                            confirmed_examples.append({
                                "productId": s(item.get("productId")),
                                "productName": s(item.get("productName")),
                                "kind": s(item.get("kind")),
                                "priorityTier": s(item.get("priorityTier")),
                                "supportWindowCount": int(persistence.get("supportWindowCount") or 0),
                                "eligibleIndependentWindowCount": int(persistence.get("eligibleIndependentWindowCount") or 0),
                                "supportWindowKeys": list(persistence.get("supportWindowKeys") or []),
                            })
            total_evaluated += historical_evaluated
            total_confirmed += historical_confirmed
            scopes[scope_key] = {
                "optionKey": latest_key,
                "latestDiagnosisStatus": s((latest.get("dynamicDiagnosis") or {}).get("status")),
                "latestPersistenceStatus": s(latest_summary.get("status")),
                "latestConfirmedCount": int(latest_summary.get("confirmedCount") or 0),
                "historicalEvaluatedItemCount": historical_evaluated,
                "historicalConfirmedItemCount": historical_confirmed,
                "stateCounts": scope_states,
                "confirmedExamples": confirmed_examples,
            }
        shops[shop_id] = {
            "displayName": s(shop.get("displayName")),
            "evaluatedDiagnosisItemCount": total_evaluated,
            "confirmedDiagnosisItemCount": total_confirmed,
            "stateCounts": state_counts,
            "scopes": scopes,
        }
    return {
        "status": "PREPRODUCTION_CANDIDATE",
        "prePersistenceAdsIntelligenceFingerprint": s((payload.get("meta") or {}).get("prePersistenceAdsIntelligenceFingerprint")),
        "adsDynamicDiagnosisFingerprint": s((payload.get("meta") or {}).get("adsDynamicDiagnosisFingerprint")),
        "adsDiagnosisPersistenceFingerprint": s((payload.get("meta") or {}).get("adsDiagnosisPersistenceFingerprint")),
        "adsIntelligenceFingerprint": s((payload.get("meta") or {}).get("adsIntelligenceFingerprint")),
        "shops": shops,
        "safety": {
            "productionActivationEnabled": False,
            "smartIssueCandidatesEnabled": False,
            "automaticAlertsEnabled": False,
            "automaticActionsEnabled": False,
            "causalClaimsEnabled": False,
        },
    }


def bind_ads_diagnosis_persistence_artifacts(
    *,
    ads_output_dir: str | Path,
    contract_path: str | Path,
) -> Dict[str, Any]:
    ads_dir = Path(ads_output_dir)
    payload_path = ads_dir / "ads_intelligence.json"
    qa_path = ads_dir / "ads_intelligence_qa_report.json"
    manifest_path = ads_dir / "ads_intelligence_manifest.json"
    for path in (payload_path, qa_path, manifest_path):
        if not path.exists():
            raise ValueError(f"required Ads Diagnosis Persistence artifact missing: {path}")

    payload = _read_json(payload_path)
    qa = _read_json(qa_path)
    manifest = _read_json(manifest_path)
    contract = _read_json(contract_path)
    diagnosis_fingerprint = s((payload.get("meta") or {}).get("adsDynamicDiagnosisFingerprint"))
    current_fingerprint = s((payload.get("meta") or {}).get("adsIntelligenceFingerprint"))
    if not diagnosis_fingerprint or not current_fingerprint:
        raise ValueError("Dynamic Diagnosis fingerprint is required before Persistence")
    if current_fingerprint != diagnosis_fingerprint:
        raise ValueError("Persistence must bind directly after Dynamic Diagnosis")
    if current_fingerprint != s(qa.get("adsIntelligenceFingerprint")) or current_fingerprint != s(manifest.get("adsIntelligenceFingerprint")):
        raise ValueError("Ads fingerprint mismatch before Diagnosis Persistence")

    bind_diagnosis_persistence(payload, contract=contract)
    persistence_qa = validate_diagnosis_persistence(payload, contract=contract)
    if persistence_qa["status"] != "PASS":
        failed = [x["name"] for x in persistence_qa["checks"] if x["status"] == "FAIL"]
        raise ValueError(f"Ads Diagnosis Persistence QA failed: {failed[:20]}")

    final_fingerprint = _sha({
        "prePersistenceAdsIntelligenceFingerprint": current_fingerprint,
        "adsDynamicDiagnosisFingerprint": diagnosis_fingerprint,
        "diagnosisPersistencePolicy": _policy(contract),
        "payload": payload,
    })
    payload["meta"]["prePersistenceAdsIntelligenceFingerprint"] = current_fingerprint
    payload["meta"]["adsDiagnosisPersistenceFingerprint"] = final_fingerprint
    payload["meta"]["adsIntelligenceFingerprint"] = final_fingerprint

    qa["prePersistenceAdsIntelligenceFingerprint"] = current_fingerprint
    qa["adsDiagnosisPersistenceFingerprint"] = final_fingerprint
    qa["adsIntelligenceFingerprint"] = final_fingerprint
    qa["diagnosisPersistence"] = persistence_qa

    manifest["prePersistenceAdsIntelligenceFingerprint"] = current_fingerprint
    manifest["adsDiagnosisPersistenceFingerprint"] = final_fingerprint
    manifest["adsIntelligenceFingerprint"] = final_fingerprint
    files = list(manifest.get("files") or [])
    if "ads_persistence_candidate_preview.json" not in files:
        files.append("ads_persistence_candidate_preview.json")
    manifest["files"] = files

    preview = build_persistence_candidate_preview(payload)
    preview["adsDiagnosisPersistenceFingerprint"] = final_fingerprint
    preview["adsIntelligenceFingerprint"] = final_fingerprint
    _write_json(payload_path, payload)
    _write_json(qa_path, qa)
    _write_json(manifest_path, manifest)
    _write_json(ads_dir / "ads_persistence_candidate_preview.json", preview)
    return {
        "status": "PASS",
        "prePersistenceAdsIntelligenceFingerprint": current_fingerprint,
        "adsDynamicDiagnosisFingerprint": diagnosis_fingerprint,
        "adsDiagnosisPersistenceFingerprint": final_fingerprint,
        "adsIntelligenceFingerprint": final_fingerprint,
        "diagnosisPersistenceStatus": persistence_qa["status"],
        "candidatePreview": preview,
    }
