"""Context-qualified Dynamic Ads Diagnosis for PREPRODUCTION.

This layer is downstream of the locked Ads Intelligence foundation and Business
Context Qualification. It never rewrites canonical Ads facts or raw evidence.
Only context-compatible qualified signals may be promoted into operator-facing
diagnosis. Diagnosis remains evidence-only, non-causal, non-alerting and
non-acting.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence


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
    raw = dict(contract.get("dynamic_diagnosis_policy") or {})
    if not raw:
        raise ValueError("Ads dynamic_diagnosis_policy is required")
    if not bool(raw.get("enabled")):
        raise ValueError("Dynamic Ads Diagnosis must be enabled")
    if s(raw.get("input_signal_source")) != "qualifiedSignals":
        raise ValueError("Dynamic Ads Diagnosis may only consume qualifiedSignals")
    if s(raw.get("context_gate")) != "CONTEXT_COMPATIBLE_ONLY":
        raise ValueError("Dynamic Ads Diagnosis context gate must remain CONTEXT_COMPATIBLE_ONLY")
    if bool(raw.get("causal_claims_enabled")):
        raise ValueError("Dynamic Ads Diagnosis causal claims must remain disabled")
    if bool(raw.get("automatic_alerts_enabled")) or bool(raw.get("automatic_actions_enabled")):
        raise ValueError("Dynamic Ads Diagnosis alerts/actions must remain disabled")
    max_items = int(raw.get("max_diagnosis_items") or 6)
    high = float(raw.get("priority_high_min") or 75)
    medium = float(raw.get("priority_medium_min") or 55)
    if max_items < 1 or max_items > 12:
        raise ValueError("Dynamic Ads Diagnosis max_diagnosis_items out of range")
    if not (0 <= medium <= high <= 100):
        raise ValueError("Dynamic Ads Diagnosis priority thresholds invalid")
    return {
        **raw,
        "max_diagnosis_items": max_items,
        "priority_high_min": high,
        "priority_medium_min": medium,
    }


def _priority_tier(score: Any, policy: Mapping[str, Any]) -> str:
    value = n(score)
    if value >= float(policy.get("priority_high_min") or 75):
        return "HIGH"
    if value >= float(policy.get("priority_medium_min") or 55):
        return "MEDIUM"
    return "WATCH"


def _confidence_tier(value: Any) -> str:
    confidence = n(value)
    if confidence >= 0.85:
        return "HIGH"
    if confidence >= 0.70:
        return "MEDIUM"
    return "LOW"


def _pct_text(value: Any) -> str:
    number = n(value) * 100
    text = f"{abs(number):.1f}".replace(".", ",")
    return text + "%"


def _signed_pct_text(value: Any) -> str:
    number = n(value) * 100
    sign = "+" if number > 0 else ("−" if number < 0 else "")
    text = f"{abs(number):.1f}".replace(".", ",")
    return sign + text + "%"


def _review_focus(signal: Mapping[str, Any], kind: str) -> str:
    spend_delta = signal.get("spendDelta")
    sales_delta = signal.get("salesDelta")
    if kind == "PROBLEM":
        if spend_delta is not None and sales_delta is not None and n(spend_delta) >= 0 and n(sales_delta) < 0:
            return "Ưu tiên kiểm tra chênh lệch giữa chi tiêu tăng và doanh số Ads giảm trước khi thay đổi ngân sách."
        if spend_delta is not None and sales_delta is not None and n(spend_delta) > n(sales_delta):
            return "Ưu tiên kiểm tra CPC, CVR và AOV vì tốc độ chi tiêu đang cao hơn tốc độ doanh số Ads."
        return "Ưu tiên kiểm tra CPC, CVR và AOV của sản phẩm để xác định điểm suy giảm hiệu quả."
    if spend_delta is not None and sales_delta is not None and n(sales_delta) > n(spend_delta):
        return "Theo dõi thêm CPC, CVR và AOV để xác nhận mức cải thiện có tiếp tục khi mở rộng chi tiêu."
    return "Theo dõi thêm hiệu quả và tỷ trọng chi tiêu trước khi coi đây là cơ hội có thể mở rộng."


def _diagnosis_item(signal: Mapping[str, Any], *, scope: str, option_key: str, policy: Mapping[str, Any]) -> Dict[str, Any]:
    signal_type = s(signal.get("type"))
    kind = "PROBLEM" if signal_type == "Vấn đề" else "OPPORTUNITY"
    product_name = s(signal.get("productName")) or "Sản phẩm chưa xác định"
    roas_delta = signal.get("roasDelta")
    spend_share = signal.get("spendShare")
    direction = "giảm" if kind == "PROBLEM" else "tăng"
    headline = f"{product_name}: hiệu quả Ads {direction} trong bối cảnh so sánh tương đồng"
    summary = (
        f"ROAS {_signed_pct_text(roas_delta)} so với kỳ trước tương đồng; "
        f"sản phẩm chiếm {_pct_text(spend_share)} chi tiêu Ads trong kỳ."
    )
    product_id = s(signal.get("productId"))
    diagnosis_key = {
        "scope": scope,
        "optionKey": option_key,
        "kind": kind,
        "productId": product_id,
        "roasDelta": roas_delta,
        "spendShare": spend_share,
    }
    return {
        "diagnosisId": "ads_diag_" + _sha(diagnosis_key)[:16],
        "kind": kind,
        "operatorType": "Vấn đề" if kind == "PROBLEM" else "Cơ hội",
        "priorityTier": _priority_tier(signal.get("priorityScore"), policy),
        "priorityScore": n(signal.get("priorityScore")),
        "confidenceTier": _confidence_tier(signal.get("confidence")),
        "confidence": n(signal.get("confidence")),
        "productId": product_id,
        "productName": s(signal.get("productName")),
        "productSku": s(signal.get("productSku")),
        "headline": headline,
        "summary": summary,
        "reviewFocus": _review_focus(signal, kind),
        "evidence": {
            "roasDelta": roas_delta,
            "spendShare": spend_share,
            "spendDelta": signal.get("spendDelta"),
            "salesDelta": signal.get("salesDelta"),
            "currentRoas": signal.get("currentRoas"),
            "currentSpend": signal.get("currentSpend"),
            "currentAttributedSales": signal.get("currentAttributedSales"),
            "relationType": s(signal.get("relationType")) or "PERIOD_OVER_PERIOD_EVIDENCE",
        },
        "contextQualified": True,
        "evidenceOnly": True,
        "causalClaim": False,
        "automaticAlertEligible": False,
        "automaticActionEligible": False,
    }


def build_snapshot_diagnosis(snapshot: Dict[str, Any], *, policy: Mapping[str, Any]) -> Dict[str, Any]:
    bc = snapshot.get("businessContext") or {}
    evaluation = s(bc.get("matchEvaluation"))
    comparison_status = s(snapshot.get("comparisonStatus"))
    eligible = bool(snapshot.get("strongDirectionalDiagnosisEligible"))
    qualified = list(snapshot.get("qualifiedSignals") or [])

    if comparison_status != "READY":
        status = "BLOCKED_COMPARISON_NOT_READY"
        reason = "Chưa đủ kỳ trước tương đương để tạo chẩn đoán."
    elif evaluation == "CONTEXT_DIFFERENT":
        status = "BLOCKED_CONTEXT_DIFFERENT"
        reason = "Bối cảnh sale của kỳ hiện tại và kỳ so sánh khác nhau; giữ số liệu nhưng không nâng thành chẩn đoán mạnh."
    elif evaluation != "CONTEXT_COMPATIBLE" or not eligible:
        status = "BLOCKED_CONTEXT_UNKNOWN"
        reason = "Chưa xác minh được bối cảnh sale tương đồng; giữ số liệu nhưng không nâng thành chẩn đoán mạnh."
    else:
        items = [
            _diagnosis_item(signal, scope=s(snapshot.get("scope")), option_key=s(snapshot.get("optionKey")), policy=policy)
            for signal in qualified
        ]
        items.sort(key=lambda x: (-n(x.get("priorityScore")), -n(x.get("confidence")), s(x.get("productId"))))
        items = items[: int(policy.get("max_diagnosis_items") or 6)]
        status = "READY" if items else "NO_MATERIAL_DIAGNOSIS"
        reason = (
            "Có tín hiệu đã qua Context Qualification và đủ điều kiện diễn giải."
            if items else
            "Bối cảnh so sánh tương đồng nhưng chưa có tín hiệu sản phẩm đủ ngưỡng chẩn đoán."
        )
        diagnosis = {
            "status": status,
            "reason": reason,
            "contextEvaluation": evaluation,
            "comparisonStatus": comparison_status,
            "items": items,
            "problemCount": sum(1 for x in items if x.get("kind") == "PROBLEM"),
            "opportunityCount": sum(1 for x in items if x.get("kind") == "OPPORTUNITY"),
            "sourceQualifiedSignalCount": len(qualified),
            "evidenceOnly": True,
            "causalClaim": False,
            "automaticAlertsEnabled": False,
            "automaticActionsEnabled": False,
        }
        snapshot["dynamicDiagnosis"] = diagnosis
        return diagnosis

    diagnosis = {
        "status": status,
        "reason": reason,
        "contextEvaluation": evaluation,
        "comparisonStatus": comparison_status,
        "items": [],
        "problemCount": 0,
        "opportunityCount": 0,
        "sourceQualifiedSignalCount": len(qualified),
        "evidenceOnly": True,
        "causalClaim": False,
        "automaticAlertsEnabled": False,
        "automaticActionsEnabled": False,
    }
    snapshot["dynamicDiagnosis"] = diagnosis
    return diagnosis


def bind_dynamic_diagnosis(payload: Dict[str, Any], *, contract: Mapping[str, Any]) -> Dict[str, Any]:
    policy = _policy(contract)
    for shop in (payload.get("shops") or {}).values():
        status_counts: Dict[str, int] = {}
        diagnosis_count = 0
        for scope_key in ("day", "week", "month", "year"):
            for snapshot in ((((shop.get("periods") or {}).get(scope_key) or {}).get("snapshots") or {}).values()):
                if s(snapshot.get("status")) != "READY":
                    continue
                diagnosis = build_snapshot_diagnosis(snapshot, policy=policy)
                status = s(diagnosis.get("status"))
                status_counts[status] = status_counts.get(status, 0) + 1
                diagnosis_count += len(diagnosis.get("items") or [])
        shop["dynamicDiagnosisLineage"] = {
            "mode": s(policy.get("mode")),
            "inputSignalSource": "qualifiedSignals",
            "contextGate": "CONTEXT_COMPATIBLE_ONLY",
            "diagnosisItemCount": diagnosis_count,
            "statusCounts": status_counts,
        }
    payload.setdefault("capabilities", {})["adsDynamicDiagnosis"] = True
    payload["capabilities"]["adsDiagnosisContextQualifiedOnly"] = True
    return payload


def validate_dynamic_diagnosis(payload: Mapping[str, Any]) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []

    def ck(name: str, ok: bool, detail: Any = None) -> None:
        checks.append({"name": name, "status": "PASS" if ok else "FAIL", "detail": detail or {}})

    caps = payload.get("capabilities") or {}
    ck("dynamic_diagnosis_capability", bool(caps.get("adsDynamicDiagnosis")))
    ck("diagnosis_context_qualified_only", bool(caps.get("adsDiagnosisContextQualifiedOnly")))

    for shop_id, shop in (payload.get("shops") or {}).items():
        lineage = shop.get("dynamicDiagnosisLineage") or {}
        ck(f"{shop_id}_diagnosis_lineage", s(lineage.get("inputSignalSource")) == "qualifiedSignals")
        for scope_key in ("day", "week", "month", "year"):
            for option_key, snapshot in ((((shop.get("periods") or {}).get(scope_key) or {}).get("snapshots") or {}).items()):
                if s(snapshot.get("status")) != "READY":
                    continue
                diagnosis = snapshot.get("dynamicDiagnosis") or {}
                status = s(diagnosis.get("status"))
                allowed_statuses = {
                    "READY", "NO_MATERIAL_DIAGNOSIS", "BLOCKED_COMPARISON_NOT_READY",
                    "BLOCKED_CONTEXT_DIFFERENT", "BLOCKED_CONTEXT_UNKNOWN",
                }
                ck(f"{shop_id}_{scope_key}_{option_key}_diagnosis_status", status in allowed_statuses, {"status": status})
                items = list(diagnosis.get("items") or [])
                eligible = bool(snapshot.get("strongDirectionalDiagnosisEligible"))
                evaluation = s((snapshot.get("businessContext") or {}).get("matchEvaluation"))
                if items:
                    ck(f"{shop_id}_{scope_key}_{option_key}_diagnosis_gate", eligible and evaluation == "CONTEXT_COMPATIBLE")
                else:
                    ck(f"{shop_id}_{scope_key}_{option_key}_diagnosis_gate", True)
                qualified_ids = {s(x.get("productId")) for x in snapshot.get("qualifiedSignals") or []}
                item_ids = {s(x.get("productId")) for x in items}
                ck(
                    f"{shop_id}_{scope_key}_{option_key}_diagnosis_from_qualified_only",
                    item_ids.issubset(qualified_ids),
                    {"diagnosisProductIds": sorted(item_ids), "qualifiedProductIds": sorted(qualified_ids)},
                )
                ck(
                    f"{shop_id}_{scope_key}_{option_key}_diagnosis_noncausal",
                    not bool(diagnosis.get("causalClaim")) and all(not bool(x.get("causalClaim")) for x in items),
                )
                ck(
                    f"{shop_id}_{scope_key}_{option_key}_diagnosis_no_automation",
                    not bool(diagnosis.get("automaticAlertsEnabled"))
                    and not bool(diagnosis.get("automaticActionsEnabled"))
                    and all(not bool(x.get("automaticAlertEligible")) and not bool(x.get("automaticActionEligible")) for x in items),
                )
    failed = [x for x in checks if x["status"] == "FAIL"]
    return {"status": "PASS" if not failed else "FAIL", "failedCheckCount": len(failed), "checks": checks}


def build_diagnosis_candidate_preview(payload: Mapping[str, Any]) -> Dict[str, Any]:
    shops: Dict[str, Any] = {}
    for shop_id, shop in (payload.get("shops") or {}).items():
        periods = shop.get("periods") or {}
        scopes: Dict[str, Any] = {}
        total_ready = 0
        total_items = 0
        for scope_key in ("day", "week", "month", "year"):
            block = periods.get(scope_key) or {}
            options = list(block.get("options") or [])
            latest_key = options[-1] if options else ""
            latest = (block.get("snapshots") or {}).get(latest_key) or {}
            diagnosis = latest.get("dynamicDiagnosis") or {}
            ready_count = 0
            item_count = 0
            for snapshot in (block.get("snapshots") or {}).values():
                diag = snapshot.get("dynamicDiagnosis") or {}
                if s(diag.get("status")) == "READY":
                    ready_count += 1
                    item_count += len(diag.get("items") or [])
            total_ready += ready_count
            total_items += item_count
            scopes[scope_key] = {
                "optionKey": latest_key,
                "diagnosisStatus": s(diagnosis.get("status")),
                "reason": s(diagnosis.get("reason")),
                "contextEvaluation": s(diagnosis.get("contextEvaluation")),
                "diagnosisCount": len(diagnosis.get("items") or []),
                "problemCount": int(diagnosis.get("problemCount") or 0),
                "opportunityCount": int(diagnosis.get("opportunityCount") or 0),
                "topDiagnosis": (diagnosis.get("items") or [None])[0],
                "readyDiagnosisSnapshotCount": ready_count,
                "historicalDiagnosisItemCount": item_count,
            }
        shops[shop_id] = {
            "displayName": s(shop.get("displayName")),
            "readyDiagnosisSnapshotCount": total_ready,
            "diagnosisItemCount": total_items,
            "scopes": scopes,
        }
    return {
        "status": "PREPRODUCTION_CANDIDATE",
        "adsIntelligenceFingerprint": s((payload.get("meta") or {}).get("adsIntelligenceFingerprint")),
        "adsContextQualificationFingerprint": s((payload.get("meta") or {}).get("adsContextQualificationFingerprint")),
        "shops": shops,
        "safety": {
            "productionActivationEnabled": False,
            "automaticAlertsEnabled": False,
            "automaticActionsEnabled": False,
            "causalClaimsEnabled": False,
        },
    }


def bind_ads_dynamic_diagnosis_artifacts(
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
            raise ValueError(f"required Dynamic Ads Diagnosis artifact missing: {path}")

    payload = _read_json(payload_path)
    qa = _read_json(qa_path)
    manifest = _read_json(manifest_path)
    contract = _read_json(contract_path)
    context_fingerprint = s((payload.get("meta") or {}).get("adsContextQualificationFingerprint"))
    current_fingerprint = s((payload.get("meta") or {}).get("adsIntelligenceFingerprint"))
    if not context_fingerprint or not current_fingerprint:
        raise ValueError("Context-qualified Ads fingerprint is required before Dynamic Ads Diagnosis")
    if current_fingerprint != s(qa.get("adsIntelligenceFingerprint")) or current_fingerprint != s(manifest.get("adsIntelligenceFingerprint")):
        raise ValueError("Ads fingerprint mismatch before Dynamic Ads Diagnosis")

    bind_dynamic_diagnosis(payload, contract=contract)
    diagnosis_qa = validate_dynamic_diagnosis(payload)
    if diagnosis_qa["status"] != "PASS":
        failed = [x["name"] for x in diagnosis_qa["checks"] if x["status"] == "FAIL"]
        raise ValueError(f"Dynamic Ads Diagnosis QA failed: {failed[:20]}")

    final_fingerprint = _sha({
        "contextQualificationFingerprint": context_fingerprint,
        "preDiagnosisAdsIntelligenceFingerprint": current_fingerprint,
        "dynamicDiagnosisPolicy": _policy(contract),
        "payload": payload,
    })
    payload["meta"]["preDiagnosisAdsIntelligenceFingerprint"] = current_fingerprint
    payload["meta"]["adsDynamicDiagnosisFingerprint"] = final_fingerprint
    payload["meta"]["adsIntelligenceFingerprint"] = final_fingerprint

    qa["preDiagnosisAdsIntelligenceFingerprint"] = current_fingerprint
    qa["adsDynamicDiagnosisFingerprint"] = final_fingerprint
    qa["adsIntelligenceFingerprint"] = final_fingerprint
    qa["dynamicDiagnosis"] = diagnosis_qa

    manifest["preDiagnosisAdsIntelligenceFingerprint"] = current_fingerprint
    manifest["adsDynamicDiagnosisFingerprint"] = final_fingerprint
    manifest["adsIntelligenceFingerprint"] = final_fingerprint
    files = list(manifest.get("files") or [])
    if "ads_diagnosis_candidate_preview.json" not in files:
        files.append("ads_diagnosis_candidate_preview.json")
    manifest["files"] = files

    preview = build_diagnosis_candidate_preview(payload)
    preview["adsIntelligenceFingerprint"] = final_fingerprint
    _write_json(payload_path, payload)
    _write_json(qa_path, qa)
    _write_json(manifest_path, manifest)
    _write_json(ads_dir / "ads_diagnosis_candidate_preview.json", preview)
    return {
        "status": "PASS",
        "preDiagnosisAdsIntelligenceFingerprint": current_fingerprint,
        "adsContextQualificationFingerprint": context_fingerprint,
        "adsDynamicDiagnosisFingerprint": final_fingerprint,
        "adsIntelligenceFingerprint": final_fingerprint,
        "dynamicDiagnosisStatus": diagnosis_qa["status"],
        "candidatePreview": preview,
    }
