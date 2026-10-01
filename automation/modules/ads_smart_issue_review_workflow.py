"""Operator review workflow for the human-reviewed Ads Smart Issue Registry.

This PREPRODUCTION sidecar does not alter the locked Ads Intelligence / Registry
fingerprint. It turns the Registry review queue and issue states into an explicit
set of human actions and can build an append-only review ledger event. Writing a
ledger event always requires an explicit apply flag and an expected-ledger
fingerprint, so a stale operator view fails closed.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Mapping


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


def operator_ledger_fingerprint(ledger: Mapping[str, Any]) -> str:
    return _sha({
        "version": s(ledger.get("version")),
        "ledger_name": s(ledger.get("ledger_name")),
        "events": list(ledger.get("events") or []),
    })


def _review_time(value: Any) -> str:
    text = s(value)
    if not text:
        raise ValueError("reviewedAt is required")
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = dt.datetime.fromisoformat(normalized)
    except Exception as exc:
        raise ValueError(f"invalid reviewedAt: {value!r}") from exc
    if parsed.tzinfo is None:
        raise ValueError("reviewedAt must include an explicit timezone")
    return text


def _policy(contract: Mapping[str, Any]) -> Dict[str, Any]:
    raw = dict(contract.get("operator_review_workflow_policy") or {})
    if not raw or not bool(raw.get("enabled")):
        raise ValueError("operator_review_workflow_policy must be enabled")
    if s(raw.get("input_source")) != "ads_smart_issue_registry.json":
        raise ValueError("operator review workflow must consume the Smart Issue Registry artifact")
    if s(raw.get("review_ledger_source")) != "ads_smart_issue_review_events.json":
        raise ValueError("unexpected Smart Issue review ledger source")
    required_true = (
        "append_only",
        "explicit_human_review_required",
        "expected_ledger_fingerprint_required",
        "deterministic_event_id",
        "reviewed_at_timezone_required",
        "reviewed_by_required",
        "ledger_apply_requires_explicit_flag",
    )
    if any(not bool(raw.get(k)) for k in required_true):
        raise ValueError("operator review workflow safety requirement missing")
    forbidden = (
        "automatic_promotion_enabled",
        "automatic_state_transition_enabled",
        "automatic_issue_resolution_enabled",
        "automatic_alerts_enabled",
        "automatic_actions_enabled",
        "causal_claims_enabled",
    )
    if any(bool(raw.get(k)) for k in forbidden):
        raise ValueError("unsafe operator review workflow policy")

    candidate_actions = {s(k): [s(x) for x in v] for k, v in (raw.get("candidate_actions_by_review_state") or {}).items()}
    issue_actions = {s(k): [s(x) for x in v] for k, v in (raw.get("issue_actions_by_state") or {}).items()}
    expected_candidates = {
        "PENDING_REVIEW": ["PROMOTE", "DEFER", "DISMISS"],
        "DEFERRED": ["PROMOTE", "DEFER", "DISMISS"],
        "DISMISSED": ["PROMOTE", "DEFER", "DISMISS"],
        "REOPEN_REVIEW_REQUIRED": ["REOPEN"],
    }
    expected_issues = {
        "OPEN": ["ACKNOWLEDGE", "MONITOR", "RESOLVE"],
        "ACKNOWLEDGED": ["MONITOR", "RESOLVE"],
        "MONITORING": ["MONITOR", "RESOLVE"],
        "RESOLVED": ["REOPEN"],
    }
    if candidate_actions != expected_candidates:
        raise ValueError("candidate review workflow action contract mismatch")
    if issue_actions != expected_issues:
        raise ValueError("issue review workflow action contract mismatch")
    return {**raw, "candidate_actions_by_review_state": candidate_actions, "issue_actions_by_state": issue_actions}


def _candidate_snapshot(row: Mapping[str, Any]) -> Dict[str, Any]:
    keys = (
        "shopId",
        "candidateId",
        "candidateKey",
        "candidateType",
        "kind",
        "productId",
        "productName",
        "productSku",
        "scope",
        "contextSignature",
        "headline",
        "summary",
        "reviewFocus",
        "priorityTier",
        "priorityScore",
        "coverageEnd",
        "latestEvidenceDate",
    )
    out = {k: row.get(k) for k in keys}
    required = ("shopId", "candidateId", "candidateKey", "kind", "productId", "scope")
    missing = [k for k in required if not s(out.get(k))]
    if missing:
        raise ValueError(f"candidate review row missing promotion snapshot fields: {missing}")
    out["contextSignature"] = list(out.get("contextSignature") or [])
    out["priorityScore"] = n(out.get("priorityScore"))
    return out


def build_operator_review_workflow(
    registry: Mapping[str, Any],
    *,
    review_ledger: Mapping[str, Any],
    contract: Mapping[str, Any],
) -> Dict[str, Any]:
    policy = _policy(contract)
    if s(registry.get("status")) != "PREPRODUCTION_REGISTRY":
        raise ValueError("Smart Issue Registry must be PREPRODUCTION_REGISTRY")
    if s(review_ledger.get("ledger_name")) != "ads_smart_issue_review_events":
        raise ValueError("unexpected Smart Issue review ledger")

    shops: Dict[str, Any] = {}
    candidate_action_count = 0
    issue_action_count = 0
    for shop_id, block in (registry.get("shops") or {}).items():
        review_queue = []
        for row in (block.get("reviewQueue") or []):
            state = s(row.get("reviewState"))
            actions = list((policy.get("candidate_actions_by_review_state") or {}).get(state) or [])
            if not actions:
                raise ValueError(f"unsupported review queue state {state!r}")
            review_queue.append({
                **dict(row),
                "availableActions": actions,
                "humanDecisionRequired": True,
                "automaticPromotion": False,
            })
            candidate_action_count += len(actions)

        issues = []
        for issue in (block.get("issues") or []):
            state = s(issue.get("state"))
            actions = list((policy.get("issue_actions_by_state") or {}).get(state) or [])
            if not actions:
                raise ValueError(f"unsupported Smart Issue state {state!r}")
            issues.append({
                **dict(issue),
                "availableActions": actions,
                "explicitOperatorEventRequired": True,
                "automaticStateTransition": False,
            })
            issue_action_count += len(actions)

        shops[shop_id] = {
            "displayName": s(block.get("displayName")),
            "reviewQueue": review_queue,
            "issues": issues,
            "reviewQueueCount": len(review_queue),
            "issueCount": len(issues),
        }

    operator_fp = operator_ledger_fingerprint(review_ledger)
    workflow = {
        "status": "READY" if candidate_action_count or issue_action_count else "READY_EMPTY",
        "mode": s(policy.get("mode")),
        "sourceRegistryFingerprint": s(registry.get("adsSmartIssueRegistryFingerprint")),
        "sourceRegistryReviewLedgerFingerprint": s(registry.get("reviewLedgerFingerprint")),
        "operatorLedgerFingerprint": operator_fp,
        "candidateActionCount": candidate_action_count,
        "issueActionCount": issue_action_count,
        "shops": shops,
        "commandContract": {
            "target": "candidateKey XOR issueId",
            "reviewedByRequired": True,
            "reviewedAtTimezoneRequired": True,
            "expectedLedgerFingerprintRequired": True,
            "ledgerApplyRequiresExplicitFlag": True,
            "deterministicEventId": True,
        },
        "safety": {
            "explicitHumanReviewRequired": True,
            "appendOnly": True,
            "automaticPromotionEnabled": False,
            "automaticStateTransitionEnabled": False,
            "automaticIssueResolutionEnabled": False,
            "automaticAlertsEnabled": False,
            "automaticActionsEnabled": False,
            "causalClaimsEnabled": False,
            "productionActivationEnabled": False,
        },
    }
    workflow["workflowFingerprint"] = _sha({
        "sourceRegistryFingerprint": workflow["sourceRegistryFingerprint"],
        "operatorLedgerFingerprint": operator_fp,
        "policy": policy,
        "shops": shops,
    })
    return workflow


def validate_operator_review_workflow(workflow: Mapping[str, Any], *, contract: Mapping[str, Any]) -> Dict[str, Any]:
    policy = _policy(contract)
    checks: List[Dict[str, Any]] = []

    def ck(name: str, ok: bool, detail: Any = None) -> None:
        checks.append({"name": name, "status": "PASS" if ok else "FAIL", "detail": detail or {}})

    ck("workflow_status", s(workflow.get("status")) in {"READY", "READY_EMPTY"})
    ck("registry_fingerprint_present", bool(s(workflow.get("sourceRegistryFingerprint"))))
    ck("operator_ledger_fingerprint_present", bool(s(workflow.get("operatorLedgerFingerprint"))))
    safety = workflow.get("safety") or {}
    ck("explicit_human_review", bool(safety.get("explicitHumanReviewRequired")))
    ck("append_only", bool(safety.get("appendOnly")))
    ck("no_auto_promotion", safety.get("automaticPromotionEnabled") is False)
    ck("no_auto_transition", safety.get("automaticStateTransitionEnabled") is False)
    ck("no_auto_resolution", safety.get("automaticIssueResolutionEnabled") is False)
    ck("no_auto_alerts", safety.get("automaticAlertsEnabled") is False)
    ck("no_auto_actions", safety.get("automaticActionsEnabled") is False)
    ck("no_causal_claims", safety.get("causalClaimsEnabled") is False)

    candidate_count = 0
    issue_count = 0
    for shop_id, shop in (workflow.get("shops") or {}).items():
        seen_candidates = set()
        seen_issues = set()
        for row in (shop.get("reviewQueue") or []):
            key = s(row.get("candidateKey"))
            state = s(row.get("reviewState"))
            actions = list(row.get("availableActions") or [])
            ck(f"{shop_id}_{key}_candidate_unique", bool(key) and key not in seen_candidates)
            seen_candidates.add(key)
            ck(f"{shop_id}_{key}_candidate_actions", actions == list((policy.get("candidate_actions_by_review_state") or {}).get(state) or []))
            ck(f"{shop_id}_{key}_candidate_human_gate", bool(row.get("humanDecisionRequired")) and row.get("automaticPromotion") is False)
            candidate_count += len(actions)
        for issue in (shop.get("issues") or []):
            issue_id = s(issue.get("issueId"))
            state = s(issue.get("state"))
            actions = list(issue.get("availableActions") or [])
            ck(f"{shop_id}_{issue_id}_issue_unique", bool(issue_id) and issue_id not in seen_issues)
            seen_issues.add(issue_id)
            ck(f"{shop_id}_{issue_id}_issue_actions", actions == list((policy.get("issue_actions_by_state") or {}).get(state) or []))
            ck(f"{shop_id}_{issue_id}_issue_human_gate", bool(issue.get("explicitOperatorEventRequired")) and issue.get("automaticStateTransition") is False)
            issue_count += len(actions)

    ck("candidate_action_count", int(workflow.get("candidateActionCount") or 0) == candidate_count)
    ck("issue_action_count", int(workflow.get("issueActionCount") or 0) == issue_count)
    failed = [x for x in checks if x["status"] == "FAIL"]
    return {"status": "PASS" if not failed else "FAIL", "failedCheckCount": len(failed), "checks": checks}


def _find_candidate(workflow: Mapping[str, Any], candidate_key: str) -> Dict[str, Any]:
    matches = []
    for shop in (workflow.get("shops") or {}).values():
        matches.extend([dict(x) for x in (shop.get("reviewQueue") or []) if s(x.get("candidateKey")) == candidate_key])
    if len(matches) != 1:
        raise ValueError(f"candidateKey must resolve to exactly one current review row: {candidate_key!r}")
    return matches[0]


def _find_issue(workflow: Mapping[str, Any], issue_id: str) -> Dict[str, Any]:
    matches = []
    for shop in (workflow.get("shops") or {}).values():
        matches.extend([dict(x) for x in (shop.get("issues") or []) if s(x.get("issueId")) == issue_id])
    if len(matches) != 1:
        raise ValueError(f"issueId must resolve to exactly one Smart Issue: {issue_id!r}")
    return matches[0]


def build_review_event_command(
    workflow: Mapping[str, Any],
    *,
    action: str,
    reviewed_by: str,
    reviewed_at: str,
    note: str = "",
    candidate_key: str = "",
    issue_id: str = "",
) -> Dict[str, Any]:
    action = s(action).upper()
    reviewed_by = s(reviewed_by)
    reviewed_at = _review_time(reviewed_at)
    note = s(note)
    candidate_key = s(candidate_key)
    issue_id = s(issue_id)
    if not reviewed_by:
        raise ValueError("reviewedBy is required")
    if bool(candidate_key) == bool(issue_id):
        raise ValueError("exactly one of candidateKey or issueId is required")

    event: Dict[str, Any]
    target_identity: Dict[str, Any]
    if candidate_key:
        row = _find_candidate(workflow, candidate_key)
        available = [s(x) for x in row.get("availableActions") or []]
        if action not in available:
            raise ValueError(f"action {action!r} is not available for candidate review state {row.get('reviewState')!r}")
        if action == "REOPEN":
            linked_issue_id = s(row.get("linkedIssueId"))
            if not linked_issue_id:
                raise ValueError("REOPEN_REVIEW_REQUIRED candidate must reference a resolved issue")
            event = {
                "action": "REOPEN",
                "reviewedAt": reviewed_at,
                "reviewedBy": reviewed_by,
                "note": note,
                "issueId": linked_issue_id,
            }
            target_identity = {"candidateKey": candidate_key, "issueId": linked_issue_id}
        else:
            event = {
                "action": action,
                "reviewedAt": reviewed_at,
                "reviewedBy": reviewed_by,
                "note": note,
                "candidateKey": candidate_key,
            }
            if action == "PROMOTE":
                event["candidateSnapshot"] = _candidate_snapshot(row)
            target_identity = {"candidateKey": candidate_key}
    else:
        issue = _find_issue(workflow, issue_id)
        available = [s(x) for x in issue.get("availableActions") or []]
        if action not in available:
            raise ValueError(f"action {action!r} is not available for issue state {issue.get('state')!r}")
        event = {
            "action": action,
            "reviewedAt": reviewed_at,
            "reviewedBy": reviewed_by,
            "note": note,
            "issueId": issue_id,
        }
        target_identity = {"issueId": issue_id}

    event_id = "ads_review_" + _sha({
        "expectedOperatorLedgerFingerprint": s(workflow.get("operatorLedgerFingerprint")),
        "action": action,
        "target": target_identity,
        "reviewedAt": reviewed_at,
        "reviewedBy": reviewed_by,
        "note": note,
    })[:20]
    event["eventId"] = event_id
    return {
        "status": "PROPOSED",
        "sourceWorkflowFingerprint": s(workflow.get("workflowFingerprint")),
        "sourceRegistryFingerprint": s(workflow.get("sourceRegistryFingerprint")),
        "expectedOperatorLedgerFingerprint": s(workflow.get("operatorLedgerFingerprint")),
        "applyRequiresExplicitFlag": True,
        "event": event,
    }


def append_review_event(
    *,
    review_ledger_path: str | Path,
    command: Mapping[str, Any],
    apply: bool = False,
) -> Dict[str, Any]:
    path = Path(review_ledger_path)
    ledger = _read_json(path)
    if s(ledger.get("ledger_name")) != "ads_smart_issue_review_events":
        raise ValueError("unexpected Smart Issue review ledger")
    current_fp = operator_ledger_fingerprint(ledger)
    expected_fp = s(command.get("expectedOperatorLedgerFingerprint"))
    if not expected_fp or current_fp != expected_fp:
        raise ValueError("review ledger changed since workflow generation; rebuild workflow before applying event")
    event = dict(command.get("event") or {})
    event_id = s(event.get("eventId"))
    if not event_id:
        raise ValueError("review command eventId is required")
    if any(s(x.get("eventId")) == event_id for x in (ledger.get("events") or [])):
        raise ValueError(f"review event already exists: {event_id}")

    proposed = json.loads(json.dumps(ledger))
    proposed.setdefault("events", []).append(event)
    new_fp = operator_ledger_fingerprint(proposed)
    if apply:
        _write_json(path, proposed)
    return {
        "status": "APPLIED" if apply else "DRY_RUN",
        "applied": bool(apply),
        "previousOperatorLedgerFingerprint": current_fp,
        "newOperatorLedgerFingerprint": new_fp,
        "event": event,
        "proposedLedger": proposed,
    }


def bind_ads_smart_issue_review_workflow_artifact(
    *,
    ads_output_dir: str | Path,
    contract_path: str | Path,
    review_events_path: str | Path,
) -> Dict[str, Any]:
    ads_dir = Path(ads_output_dir)
    registry_path = ads_dir / "ads_smart_issue_registry.json"
    payload_path = ads_dir / "ads_intelligence.json"
    qa_path = ads_dir / "ads_intelligence_qa_report.json"
    manifest_path = ads_dir / "ads_intelligence_manifest.json"
    for path in (registry_path, payload_path, qa_path, manifest_path, Path(contract_path), Path(review_events_path)):
        if not path.exists():
            raise ValueError(f"required operator review workflow artifact missing: {path}")

    registry = _read_json(registry_path)
    payload = _read_json(payload_path)
    qa = _read_json(qa_path)
    manifest = _read_json(manifest_path)
    contract = _read_json(contract_path)
    ledger = _read_json(review_events_path)

    registry_fp = s(registry.get("adsSmartIssueRegistryFingerprint"))
    ads_fp = s((payload.get("meta") or {}).get("adsIntelligenceFingerprint"))
    payload_registry_fp = s((payload.get("meta") or {}).get("adsSmartIssueRegistryFingerprint"))
    if not registry_fp or registry_fp != ads_fp or registry_fp != payload_registry_fp:
        raise ValueError("operator review workflow must bind to the locked Smart Issue Registry fingerprint")
    if ads_fp != s(qa.get("adsIntelligenceFingerprint")) or ads_fp != s(manifest.get("adsIntelligenceFingerprint")):
        raise ValueError("Ads fingerprint mismatch before operator review workflow sidecar")

    workflow = build_operator_review_workflow(registry, review_ledger=ledger, contract=contract)
    workflow_qa = validate_operator_review_workflow(workflow, contract=contract)
    if workflow_qa["status"] != "PASS":
        failed = [x["name"] for x in workflow_qa["checks"] if x["status"] == "FAIL"]
        raise ValueError(f"Smart Issue operator review workflow QA failed: {failed[:20]}")

    workflow["adsIntelligenceFingerprint"] = ads_fp
    workflow["adsSmartIssueRegistryFingerprint"] = registry_fp
    workflow["doesNotModifyAdsIntelligenceFingerprint"] = True
    _write_json(ads_dir / "ads_smart_issue_review_workflow.json", workflow)

    qa["smartIssueOperatorReviewWorkflow"] = workflow_qa
    qa["adsSmartIssueOperatorReviewWorkflowFingerprint"] = workflow["workflowFingerprint"]
    qa["adsIntelligenceFingerprint"] = ads_fp
    files = list(manifest.get("files") or [])
    if "ads_smart_issue_review_workflow.json" not in files:
        files.append("ads_smart_issue_review_workflow.json")
    manifest["files"] = files
    manifest["adsSmartIssueOperatorReviewWorkflowFingerprint"] = workflow["workflowFingerprint"]
    manifest["adsIntelligenceFingerprint"] = ads_fp
    _write_json(qa_path, qa)
    _write_json(manifest_path, manifest)

    return {
        "status": "PASS",
        "adsIntelligenceFingerprint": ads_fp,
        "adsSmartIssueRegistryFingerprint": registry_fp,
        "adsSmartIssueOperatorReviewWorkflowFingerprint": workflow["workflowFingerprint"],
        "smartIssueOperatorReviewWorkflowStatus": workflow_qa["status"],
        "reviewQueueCount": sum(int(x.get("reviewQueueCount") or 0) for x in workflow.get("shops", {}).values()),
        "issueCount": sum(int(x.get("issueCount") or 0) for x in workflow.get("shops", {}).values()),
        "workflow": workflow,
    }
