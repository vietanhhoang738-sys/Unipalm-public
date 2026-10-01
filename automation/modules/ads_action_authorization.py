"""PREPRODUCTION Recommendation / Action Authorization v1.

This sidecar consumes only human-reviewed Smart Issues and current Ads evidence.
It creates bounded review proposals plus an append-only authorization decision
state. Even an APPROVE decision authorizes review only: no authenticated executor,
provider binding, production activation or platform mutation exists in v1.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence


def s(value: Any) -> str:
    return "" if value is None else str(value).strip()


def n(value: Any) -> float:
    try:
        return float(value or 0)
    except Exception:
        return 0.0


def _sha(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _read_json(path: str | Path) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json(path: str | Path, value: Any) -> None:
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _time(value: Any) -> dt.datetime:
    text = s(value)
    if not text:
        raise ValueError("timezone-aware timestamp is required")
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = dt.datetime.fromisoformat(normalized)
    except Exception as exc:
        raise ValueError(f"invalid timezone-aware timestamp: {value!r}") from exc
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include an explicit timezone")
    return parsed


def _policy(contract: Mapping[str, Any]) -> Dict[str, Any]:
    if s(contract.get("layer_name")) != "multi_shop_ads_action_authorization_v1":
        raise ValueError("unexpected Action Authorization layer")
    if s(contract.get("status")) != "PREPRODUCTION":
        raise ValueError("Action Authorization contract must remain PREPRODUCTION")
    raw = dict(contract.get("action_authorization") or {})
    if not raw or raw.get("enabled") is not True:
        raise ValueError("action_authorization must be enabled")
    expected_sources = {
        "input_source": "ads_smart_issue_review_workflow.json",
        "ads_evidence_source": "ads_intelligence.json",
        "alert_policy_source": "ads_alert_policy.json",
        "authorization_event_source": "ads_action_authorization_events.json",
    }
    for key, expected in expected_sources.items():
        if s(raw.get(key)) != expected:
            raise ValueError(f"Action Authorization source mismatch: {key}")
    if raw.get("human_promoted_issue_required") is not True:
        raise ValueError("Action Authorization must require human-promoted Smart Issues")
    if list(raw.get("eligible_issue_states") or []) != ["OPEN", "ACKNOWLEDGED", "MONITORING"]:
        raise ValueError("Action Authorization eligible issue states mismatch")
    if list(raw.get("suppressed_issue_states") or []) != ["RESOLVED"]:
        raise ValueError("Action Authorization suppressed issue states mismatch")
    if int(raw.get("max_proposals_per_issue") or 0) != 2:
        raise ValueError("Action Authorization v1 must remain bounded to two proposals per issue")
    if s(raw.get("generic_validation_option")) != "VALIDATE_EVIDENCE_BEFORE_CHANGE":
        raise ValueError("Action Authorization generic validation option mismatch")
    if raw.get("targeted_review_requires_attributed_driver") is not True:
        raise ValueError("targeted review must require explicit attributed driver evidence")

    expected_rules = {
        "productClicks": "REVIEW_TRAFFIC_AND_LISTING_VISIBILITY",
        "placedCvr": "REVIEW_CONVERSION_FUNNEL_AND_OFFER",
        "placedAov": "REVIEW_AOV_PRICE_PROMOTION_MIX",
        "adsSpend": "REVIEW_ADS_SPEND_EFFICIENCY",
        "adsAttributedSales": "REVIEW_ADS_ATTRIBUTED_SALES",
        "cancelledSales": "REVIEW_CANCELLATION_AND_FULFILLMENT",
        "orderFees": "REVIEW_FEE_AND_PROMOTION_COST",
        "netSalesAfterCancel": "REVIEW_NET_SALES_QUALITY",
    }
    rules = {s(k): s(v) for k, v in (raw.get("targeted_driver_rules") or {}).items()}
    if rules != expected_rules:
        raise ValueError("Action Authorization targeted driver rules mismatch")
    forbidden = [s(x) for x in raw.get("forbidden_directives") or []]
    expected_forbidden = [
        "CHANGE_BID", "CHANGE_BUDGET", "CHANGE_PRICE", "CHANGE_PROMOTION",
        "PAUSE_CAMPAIGN", "PUBLISH_LISTING_CHANGE", "CONTACT_CUSTOMER_AUTOMATICALLY",
    ]
    if forbidden != expected_forbidden:
        raise ValueError("Action Authorization forbidden directives mismatch")

    proposal = dict(raw.get("proposal_requirements") or {})
    required_true = (
        "deterministic_proposal_id", "issue_epoch_binding_required", "why_relevant_required",
        "prerequisites_required", "kpis_to_monitor_required", "verification_checks_required",
        "stop_or_reversal_checks_required", "uncertainty_required", "requires_human_review",
    )
    if any(proposal.get(k) is not True for k in required_true):
        raise ValueError("Action Authorization proposal safety requirement missing")
    forbidden_true = (
        "prescriptive_recommendation", "platform_mutation_allowed",
        "automatic_execution_eligible", "automatic_alert_eligible", "causal_claim_eligible",
    )
    if any(bool(proposal.get(k)) for k in forbidden_true):
        raise ValueError("unsafe Action Authorization proposal requirement")

    auth = dict(raw.get("authorization") or {})
    if auth.get("append_only") is not True:
        raise ValueError("authorization ledger must be append-only")
    if list(auth.get("actions") or []) != ["APPROVE", "REJECT", "REVOKE"]:
        raise ValueError("authorization actions mismatch")
    if list(auth.get("pending_actions") or []) != ["APPROVE", "REJECT"]:
        raise ValueError("pending authorization actions mismatch")
    if list(auth.get("approved_actions") or []) != ["REVOKE"]:
        raise ValueError("approved authorization actions mismatch")
    if list(auth.get("rejected_actions") or []) or list(auth.get("revoked_actions") or []):
        raise ValueError("rejected/revoked authorization states must be terminal in v1")
    if s(auth.get("approval_status")) != "APPROVED_REVIEW_ONLY":
        raise ValueError("v1 approval must remain review-only")
    for key in (
        "expected_ledger_fingerprint_required", "deterministic_event_id",
        "authorized_at_timezone_required", "authorized_by_required",
        "ledger_apply_requires_explicit_flag", "proposal_fingerprint_binding_required",
    ):
        if auth.get(key) is not True:
            raise ValueError(f"authorization safety requirement missing: {key}")

    execution = dict(raw.get("execution_boundary") or {})
    if execution.get("authenticated_executor_required") is not True:
        raise ValueError("authenticated executor must be required")
    for key in ("idempotency_key_required", "audit_trail_required", "rollback_metadata_required"):
        if execution.get(key) is not True:
            raise ValueError(f"execution boundary requirement missing: {key}")
    for key in (
        "authenticated_executor_bound", "execution_enabled", "provider_binding_enabled",
        "platform_mutation_allowed", "production_activation_enabled",
    ):
        if bool(execution.get(key)):
            raise ValueError(f"unsafe execution boundary flag: {key}")
    if execution.get("dry_run_only") is not True:
        raise ValueError("Action Authorization v1 execution boundary must remain dry-run-only")
    for key in (
        "automatic_issue_transition_enabled", "automatic_issue_resolution_enabled",
        "automatic_actions_enabled", "causal_claims_enabled", "production_activation_enabled",
    ):
        if bool(raw.get(key)):
            raise ValueError(f"unsafe Action Authorization policy flag: {key}")
    return raw


def authorization_ledger_fingerprint(ledger: Mapping[str, Any]) -> str:
    return _sha({
        "version": s(ledger.get("version")),
        "ledger_name": s(ledger.get("ledger_name")),
        "events": list(ledger.get("events") or []),
    })


def _authorization_events(ledger: Mapping[str, Any]) -> List[Dict[str, Any]]:
    if s(ledger.get("version")) != "1.0" or s(ledger.get("ledger_name")) != "ads_action_authorization_events":
        raise ValueError("unexpected Action Authorization ledger")
    seen = set()
    out: List[Dict[str, Any]] = []
    for raw in ledger.get("events") or []:
        if not isinstance(raw, dict):
            raise ValueError("Action Authorization events must be objects")
        event_id = s(raw.get("eventId"))
        action = s(raw.get("action")).upper()
        proposal_id = s(raw.get("proposalId"))
        proposal_fp = s(raw.get("proposalFingerprint"))
        shop_id = s(raw.get("shopId"))
        issue_id = s(raw.get("issueId"))
        authorized_at = s(raw.get("authorizedAt"))
        authorized_by = s(raw.get("authorizedBy"))
        if not event_id or event_id in seen:
            raise ValueError(f"duplicate or missing authorization eventId: {event_id!r}")
        seen.add(event_id)
        if action not in {"APPROVE", "REJECT", "REVOKE"}:
            raise ValueError(f"unsupported authorization action: {action!r}")
        if not proposal_id or not proposal_fp or not shop_id or not issue_id:
            raise ValueError(f"authorization event identity incomplete: {event_id}")
        if not authorized_by:
            raise ValueError(f"authorizedBy is required for event {event_id}")
        _time(authorized_at)
        out.append({
            "eventId": event_id,
            "action": action,
            "proposalId": proposal_id,
            "proposalFingerprint": proposal_fp,
            "shopId": shop_id,
            "issueId": issue_id,
            "authorizedAt": authorized_at,
            "authorizedBy": authorized_by,
            "note": s(raw.get("note")),
        })
    out.sort(key=lambda x: (_time(x["authorizedAt"]), x["eventId"]))
    return out


def _issue_epoch(issue: Mapping[str, Any]) -> str:
    history = list(issue.get("eventHistory") or [])
    if not history:
        raise ValueError(f"Smart Issue event history is required: {issue.get('issueId')}")
    event_id = s(history[-1].get("eventId"))
    if not event_id:
        raise ValueError(f"Smart Issue latest eventId is required: {issue.get('issueId')}")
    return event_id


def _find_source_diagnosis(ads_payload: Mapping[str, Any], *, shop_id: str, source_candidate_id: str) -> Dict[str, Any]:
    if not source_candidate_id:
        return {}
    shop = ((ads_payload.get("shops") or {}).get(shop_id) or {})
    matches: List[Dict[str, Any]] = []
    for scope in ("day", "week", "month", "year"):
        snapshots = ((((shop.get("periods") or {}).get(scope) or {}).get("snapshots") or {}))
        for snapshot in snapshots.values():
            for item in ((snapshot.get("dynamicDiagnosis") or {}).get("items") or []):
                candidate = item.get("smartIssueCandidate") or {}
                if s(candidate.get("candidateId")) == source_candidate_id:
                    matches.append(dict(item))
    if len(matches) > 1:
        matches.sort(key=lambda x: s((x.get("smartIssueCandidate") or {}).get("coverageEnd")))
    return matches[-1] if matches else {}


def _attribution(issue: Mapping[str, Any], source_diagnosis: Mapping[str, Any]) -> Dict[str, Any]:
    raw = issue.get("driverAttribution") or issue.get("attribution") or source_diagnosis.get("driverAttribution") or source_diagnosis.get("attribution") or {}
    return dict(raw) if isinstance(raw, Mapping) else {}


def _top_driver(attribution: Mapping[str, Any], rules: Mapping[str, str]) -> Dict[str, Any]:
    if s(attribution.get("status")) != "ATTRIBUTED":
        return {}
    raw = attribution.get("topDriver") or {}
    if not isinstance(raw, Mapping):
        return {}
    metric = s(raw.get("metric") or raw.get("driverKey") or raw.get("key"))
    if metric not in rules:
        return {}
    contribution = raw.get("contributionValue")
    if contribution in (None, ""):
        contribution = raw.get("contribution")
    if contribution in (None, ""):
        return {}
    try:
        contribution_value = float(contribution)
    except Exception:
        return {}
    if contribution_value == 0:
        return {}
    return {
        "metric": metric,
        "label": s(raw.get("label") or raw.get("name")) or metric,
        "contributionValue": contribution_value,
        "contributionShare": raw.get("contributionShare"),
        "direction": s(raw.get("direction")),
    }


def _proposal_details(action_type: str, issue: Mapping[str, Any], top_driver: Mapping[str, Any] | None = None) -> Dict[str, Any]:
    product = s(issue.get("productName")) or s(issue.get("productId")) or "Smart Issue"
    if action_type == "VALIDATE_EVIDENCE_BEFORE_CHANGE":
        return {
            "category": "EVIDENCE_VALIDATION",
            "title": "Xác minh evidence trước khi thay đổi vận hành",
            "whyRelevant": f"{product} đã được human-promote thành Smart Issue; cần xác minh dữ liệu, bối cảnh và độ bền của tín hiệu trước mọi thay đổi.",
            "prerequisites": [
                "Xác nhận source data và lineage vẫn khớp với Smart Issue hiện tại.",
                "Xác nhận bối cảnh so sánh vẫn tương đồng và issue chưa được resolve.",
            ],
            "kpisToMonitor": ["roas", "adsSpend", "adsAttributedSales"],
            "verificationChecks": [
                "Đối chiếu lại ROAS, Ads Spend và Ads Attributed Sales ở refresh kế tiếp.",
                "Kiểm tra không có source/schema/context drift làm thay đổi diễn giải.",
            ],
            "stopOrReversalChecks": [
                "Dừng review nếu Smart Issue chuyển RESOLVED hoặc lineage/evidence fingerprint thay đổi.",
                "Không chuyển thành platform action nếu nguyên nhân chưa được xác minh.",
            ],
        }
    driver = dict(top_driver or {})
    metric = s(driver.get("metric"))
    return {
        "category": "TARGETED_DRIVER_REVIEW",
        "title": f"Review driver đã được attribution: {s(driver.get('label')) or metric}",
        "whyRelevant": f"Driver {s(driver.get('label')) or metric} có quantified contribution trong attribution đã được xác nhận; proposal chỉ yêu cầu operator review, không chỉ định thay đổi nền tảng.",
        "prerequisites": [
            "Attribution status phải còn là ATTRIBUTED trên đúng issue epoch.",
            "Quantified top driver và proposal fingerprint phải còn khớp.",
        ],
        "kpisToMonitor": [metric, "roas"],
        "verificationChecks": [
            "Xác minh driver movement còn tồn tại ở refresh kế tiếp.",
            "Đối chiếu contribution với KPI đích và business context trước khi quyết định thủ công.",
        ],
        "stopOrReversalChecks": [
            "Dừng targeted review nếu attribution không còn ATTRIBUTED hoặc top driver thay đổi.",
            "Nếu evidence đảo chiều/không còn material, không thực hiện thay đổi vận hành.",
        ],
    }


def _build_proposal(*, issue: Mapping[str, Any], action_type: str, attribution: Mapping[str, Any], top_driver: Mapping[str, Any] | None = None) -> Dict[str, Any]:
    epoch = _issue_epoch(issue)
    details = _proposal_details(action_type, issue, top_driver)
    identity = {
        "shopId": s(issue.get("shopId")),
        "issueId": s(issue.get("issueId")),
        "issueEpoch": epoch,
        "actionType": action_type,
        "topDriver": dict(top_driver or {}),
    }
    proposal_id = "ads_action_" + _sha(identity)[:18]
    proposal = {
        "proposalId": proposal_id,
        "shopId": s(issue.get("shopId")),
        "issueId": s(issue.get("issueId")),
        "issueKey": s(issue.get("issueKey")),
        "issueEpoch": epoch,
        "issueState": s(issue.get("state")),
        "kind": s(issue.get("kind")),
        "productId": s(issue.get("productId")),
        "productName": s(issue.get("productName")),
        "productSku": s(issue.get("productSku")),
        "scope": s(issue.get("scope")),
        "priorityTier": s(issue.get("priorityTier")),
        "priorityScore": n(issue.get("priorityScoreAtPromotion")),
        "sourceCandidateId": s(issue.get("sourceCandidateId")),
        "actionType": action_type,
        **details,
        "attributionStatus": s(attribution.get("status")) or "NOT_AVAILABLE",
        "topDriver": dict(top_driver or {}),
        "uncertainty": ["CAUSALITY_NOT_ESTABLISHED", "HUMAN_REVIEW_REQUIRED", "PLATFORM_MUTATION_DISABLED"],
        "status": "REVIEW_OPTION",
        "executionMode": "HUMAN_REVIEW_ONLY",
        "requiresHumanReview": True,
        "prescriptiveRecommendation": False,
        "platformMutationAllowed": False,
        "automaticExecutionEligible": False,
        "automaticAlertEligible": False,
        "causalClaimEligible": False,
    }
    proposal["proposalFingerprint"] = _sha({
        "identity": identity,
        "details": details,
        "attributionStatus": proposal["attributionStatus"],
        "uncertainty": proposal["uncertainty"],
    })
    return proposal


def _authorization_for_proposal(proposal: Mapping[str, Any], events: Sequence[Mapping[str, Any]], policy: Mapping[str, Any]) -> Dict[str, Any]:
    relevant = [x for x in events if s(x.get("proposalId")) == s(proposal.get("proposalId"))]
    state = "PENDING_AUTHORIZATION"
    history = []
    latest_event_id = ""
    for event in relevant:
        if s(event.get("proposalFingerprint")) != s(proposal.get("proposalFingerprint")):
            raise ValueError(f"authorization event binds stale proposal fingerprint: {proposal.get('proposalId')}")
        if s(event.get("shopId")) != s(proposal.get("shopId")) or s(event.get("issueId")) != s(proposal.get("issueId")):
            raise ValueError(f"authorization event scope mismatch: {event.get('eventId')}")
        action = s(event.get("action"))
        if state == "PENDING_AUTHORIZATION" and action == "APPROVE":
            state = "APPROVED_REVIEW_ONLY"
        elif state == "PENDING_AUTHORIZATION" and action == "REJECT":
            state = "REJECTED"
        elif state == "APPROVED_REVIEW_ONLY" and action == "REVOKE":
            state = "REVOKED"
        else:
            raise ValueError(f"invalid Action Authorization transition {state} --{action}--> ?")
        history.append(dict(event))
        latest_event_id = s(event.get("eventId"))

    auth_policy = policy.get("authorization") or {}
    if state == "PENDING_AUTHORIZATION":
        available = list(auth_policy.get("pending_actions") or [])
        execution_status = "BLOCKED_HUMAN_AUTHORIZATION_REQUIRED"
    elif state == "APPROVED_REVIEW_ONLY":
        available = list(auth_policy.get("approved_actions") or [])
        execution_status = "BLOCKED_AUTHENTICATED_EXECUTOR_NOT_BOUND"
    elif state == "REJECTED":
        available = []
        execution_status = "BLOCKED_OPERATOR_REJECTED"
    else:
        available = []
        execution_status = "BLOCKED_AUTHORIZATION_REVOKED"

    idempotency_key = "ads_exec_" + _sha({
        "proposalId": s(proposal.get("proposalId")),
        "proposalFingerprint": s(proposal.get("proposalFingerprint")),
        "issueEpoch": s(proposal.get("issueEpoch")),
        "latestAuthorizationEventId": latest_event_id,
    })[:24]
    return {
        "state": state,
        "availableActions": available,
        "authorizationSatisfiedForManualReview": state == "APPROVED_REVIEW_ONLY",
        "latestAuthorizationEventId": latest_event_id,
        "eventHistory": history,
        "executionEligibility": {
            "status": execution_status,
            "authenticatedExecutorRequired": True,
            "authenticatedExecutorBound": False,
            "executionEnabled": False,
            "dryRunOnly": True,
            "providerBindingEnabled": False,
            "platformMutationAllowed": False,
            "productionActivationEnabled": False,
            "authorizationPermitIssued": False,
            "idempotencyKey": idempotency_key,
            "auditTrailRequired": True,
            "rollbackMetadataRequired": True,
        },
    }


def build_action_authorization(
    workflow: Mapping[str, Any], *, ads_payload: Mapping[str, Any], alert_policy: Mapping[str, Any],
    authorization_ledger: Mapping[str, Any], contract: Mapping[str, Any]
) -> Dict[str, Any]:
    policy = _policy(contract)
    if s(workflow.get("status")) not in {"READY", "READY_EMPTY"}:
        raise ValueError("operator review workflow is not ready")
    if s(alert_policy.get("status")) not in {"READY", "READY_EMPTY"}:
        raise ValueError("Alert Policy is not ready")
    workflow_fp = s(workflow.get("workflowFingerprint"))
    registry_fp = s(workflow.get("sourceRegistryFingerprint"))
    operator_fp = s(workflow.get("operatorLedgerFingerprint"))
    ads_fp = s((ads_payload.get("meta") or {}).get("adsIntelligenceFingerprint"))
    if not workflow_fp or not registry_fp or not operator_fp or not ads_fp:
        raise ValueError("Action Authorization source lineage missing")
    if s(alert_policy.get("sourceReviewWorkflowFingerprint")) != workflow_fp:
        raise ValueError("Action Authorization Alert Policy workflow lineage mismatch")
    if s(alert_policy.get("sourceRegistryFingerprint")) != registry_fp:
        raise ValueError("Action Authorization Alert Policy Registry lineage mismatch")
    if s(alert_policy.get("adsIntelligenceFingerprint")) != ads_fp:
        raise ValueError("Action Authorization Alert Policy Ads lineage mismatch")
    if s(workflow.get("adsIntelligenceFingerprint")) and s(workflow.get("adsIntelligenceFingerprint")) != ads_fp:
        raise ValueError("Action Authorization workflow Ads lineage mismatch")
    safety = workflow.get("safety") or {}
    if safety.get("explicitHumanReviewRequired") is not True or safety.get("automaticActionsEnabled") is not False:
        raise ValueError("Action Authorization source workflow safety mismatch")

    events = _authorization_events(authorization_ledger)
    ledger_fp = authorization_ledger_fingerprint(authorization_ledger)
    workflow_shops = workflow.get("shops") or {}
    ads_shops = ads_payload.get("shops") or {}
    if set(workflow_shops) != set(ads_shops):
        raise ValueError("Action Authorization workflow/Ads shop scope mismatch")

    eligible_states = set(policy.get("eligible_issue_states") or [])
    suppressed_states = set(policy.get("suppressed_issue_states") or [])
    rules = dict(policy.get("targeted_driver_rules") or {})
    max_per_issue = int(policy.get("max_proposals_per_issue") or 2)
    shops: Dict[str, Any] = {}
    total = 0
    suppressed_total = 0
    auth_counts = {"PENDING_AUTHORIZATION": 0, "APPROVED_REVIEW_ONLY": 0, "REJECTED": 0, "REVOKED": 0}

    for shop_id, block in workflow_shops.items():
        proposals: List[Dict[str, Any]] = []
        suppressed: List[Dict[str, Any]] = []
        for issue in block.get("issues") or []:
            if s(issue.get("shopId")) != shop_id:
                raise ValueError(f"Action Authorization issue shop mismatch: {issue.get('issueId')}")
            if issue.get("humanPromoted") is not True or s(issue.get("source")) != "EXPLICIT_HUMAN_REVIEW_LEDGER":
                raise ValueError(f"Action Authorization requires human-promoted issue: {issue.get('issueId')}")
            state = s(issue.get("state"))
            if state in suppressed_states:
                suppressed.append({
                    "shopId": shop_id, "issueId": s(issue.get("issueId")), "issueState": state,
                    "suppressionReason": "ISSUE_STATE_SUPPRESSED", "proposalEligible": False,
                })
                continue
            if state not in eligible_states:
                suppressed.append({
                    "shopId": shop_id, "issueId": s(issue.get("issueId")), "issueState": state,
                    "suppressionReason": "ISSUE_STATE_NOT_ELIGIBLE", "proposalEligible": False,
                })
                continue

            source_diag = _find_source_diagnosis(
                ads_payload, shop_id=shop_id, source_candidate_id=s(issue.get("sourceCandidateId"))
            )
            attribution = _attribution(issue, source_diag)
            issue_proposals = [
                _build_proposal(
                    issue=issue,
                    action_type=s(policy.get("generic_validation_option")),
                    attribution=attribution,
                )
            ]
            top = _top_driver(attribution, rules)
            if top:
                issue_proposals.append(_build_proposal(
                    issue=issue,
                    action_type=s(rules.get(top["metric"])),
                    attribution=attribution,
                    top_driver=top,
                ))
            issue_proposals = issue_proposals[:max_per_issue]
            for proposal in issue_proposals:
                proposal["authorization"] = _authorization_for_proposal(proposal, events, policy)
                proposal["executionBoundary"] = dict(proposal["authorization"]["executionEligibility"])
                auth_state = s((proposal.get("authorization") or {}).get("state"))
                auth_counts[auth_state] = auth_counts.get(auth_state, 0) + 1
                proposals.append(proposal)

        proposals.sort(key=lambda x: (-n(x.get("priorityScore")), s(x.get("issueId")), s(x.get("actionType"))))
        total += len(proposals)
        suppressed_total += len(suppressed)
        shops[shop_id] = {
            "displayName": s(block.get("displayName")),
            "proposals": proposals,
            "proposalCount": len(proposals),
            "suppressedIssues": suppressed,
            "suppressedIssueCount": len(suppressed),
        }

    result = {
        "status": "READY" if total else "READY_EMPTY",
        "mode": s(policy.get("mode")),
        "sourceReviewWorkflowFingerprint": workflow_fp,
        "sourceRegistryFingerprint": registry_fp,
        "sourceOperatorLedgerFingerprint": operator_fp,
        "sourceAlertPolicyFingerprint": s(alert_policy.get("alertPolicyFingerprint")),
        "adsIntelligenceFingerprint": ads_fp,
        "authorizationLedgerFingerprint": ledger_fp,
        "proposalCount": total,
        "suppressedIssueCount": suppressed_total,
        "authorizationStateCounts": auth_counts,
        "shops": shops,
        "executionBoundary": {
            "authenticatedExecutorRequired": True,
            "authenticatedExecutorBound": False,
            "executionEnabled": False,
            "dryRunOnly": True,
            "providerBindingEnabled": False,
            "platformMutationAllowed": False,
            "productionActivationEnabled": False,
        },
        "safety": {
            "humanPromotedIssueRequired": True,
            "targetedReviewRequiresAttributedDriver": True,
            "prescriptiveRecommendationsEnabled": False,
            "automaticExecutionEnabled": False,
            "authenticatedExecutorBound": False,
            "providerBindingEnabled": False,
            "platformMutationAllowed": False,
            "automaticIssueTransitionEnabled": False,
            "automaticIssueResolutionEnabled": False,
            "automaticActionsEnabled": False,
            "causalClaimsEnabled": False,
            "productionActivationEnabled": False,
        },
    }
    result["actionAuthorizationFingerprint"] = _sha({
        "sourceReviewWorkflowFingerprint": workflow_fp,
        "sourceRegistryFingerprint": registry_fp,
        "sourceAlertPolicyFingerprint": result["sourceAlertPolicyFingerprint"],
        "adsIntelligenceFingerprint": ads_fp,
        "authorizationLedgerFingerprint": ledger_fp,
        "policy": policy,
        "shops": shops,
    })
    return result


def validate_action_authorization(value: Mapping[str, Any], *, contract: Mapping[str, Any]) -> Dict[str, Any]:
    policy = _policy(contract)
    checks: List[Dict[str, Any]] = []

    def ck(name: str, ok: bool, detail: Any = None) -> None:
        checks.append({"name": name, "status": "PASS" if ok else "FAIL", "detail": detail or {}})

    ck("status", s(value.get("status")) in {"READY", "READY_EMPTY"})
    ck("fingerprint_present", bool(s(value.get("actionAuthorizationFingerprint"))))
    ck("workflow_lineage_present", bool(s(value.get("sourceReviewWorkflowFingerprint"))))
    ck("registry_lineage_present", bool(s(value.get("sourceRegistryFingerprint"))))
    ck("alert_lineage_present", bool(s(value.get("sourceAlertPolicyFingerprint"))))
    ck("ads_lineage_present", bool(s(value.get("adsIntelligenceFingerprint"))))
    ck("authorization_ledger_fingerprint_present", bool(s(value.get("authorizationLedgerFingerprint"))))
    execution = value.get("executionBoundary") or {}
    ck("authenticated_executor_required", execution.get("authenticatedExecutorRequired") is True)
    ck("authenticated_executor_not_bound", execution.get("authenticatedExecutorBound") is False)
    ck("execution_disabled", execution.get("executionEnabled") is False)
    ck("dry_run_only", execution.get("dryRunOnly") is True)
    ck("provider_binding_disabled", execution.get("providerBindingEnabled") is False)
    ck("platform_mutation_disabled", execution.get("platformMutationAllowed") is False)
    ck("production_activation_disabled", execution.get("productionActivationEnabled") is False)

    forbidden = set(policy.get("forbidden_directives") or [])
    seen = set()
    proposal_count = 0
    suppressed_count = 0
    for shop_id, block in (value.get("shops") or {}).items():
        proposals = list(block.get("proposals") or [])
        suppressed = list(block.get("suppressedIssues") or [])
        ck(f"{shop_id}_proposal_count", int(block.get("proposalCount") or 0) == len(proposals))
        ck(f"{shop_id}_suppressed_count", int(block.get("suppressedIssueCount") or 0) == len(suppressed))
        proposal_count += len(proposals)
        suppressed_count += len(suppressed)
        per_issue: Dict[str, int] = {}
        for proposal in proposals:
            pid = s(proposal.get("proposalId"))
            issue_id = s(proposal.get("issueId"))
            action_type = s(proposal.get("actionType"))
            name = f"{shop_id}_{pid}"
            ck(f"{name}_unique", bool(pid) and pid not in seen)
            seen.add(pid)
            ck(f"{name}_shop_scope", s(proposal.get("shopId")) == shop_id)
            ck(f"{name}_issue_epoch", bool(s(proposal.get("issueEpoch"))))
            ck(f"{name}_fingerprint", bool(s(proposal.get("proposalFingerprint"))))
            ck(f"{name}_not_forbidden", action_type not in forbidden)
            ck(f"{name}_review_option", s(proposal.get("status")) == "REVIEW_OPTION" and s(proposal.get("executionMode")) == "HUMAN_REVIEW_ONLY")
            ck(f"{name}_human_gate", proposal.get("requiresHumanReview") is True)
            ck(f"{name}_nonprescriptive", proposal.get("prescriptiveRecommendation") is False)
            ck(f"{name}_no_mutation", proposal.get("platformMutationAllowed") is False and proposal.get("automaticExecutionEligible") is False)
            ck(f"{name}_noncausal", proposal.get("causalClaimEligible") is False)
            ck(f"{name}_complete_review_metadata", all(bool(proposal.get(k)) for k in (
                "whyRelevant", "prerequisites", "kpisToMonitor", "verificationChecks", "stopOrReversalChecks", "uncertainty"
            )))
            if action_type != s(policy.get("generic_validation_option")):
                top = proposal.get("topDriver") or {}
                ck(f"{name}_targeted_attributed_only", s(proposal.get("attributionStatus")) == "ATTRIBUTED" and bool(s(top.get("metric"))) and top.get("contributionValue") not in (None, ""))
            auth = proposal.get("authorization") or {}
            state = s(auth.get("state"))
            ck(f"{name}_authorization_state", state in {"PENDING_AUTHORIZATION", "APPROVED_REVIEW_ONLY", "REJECTED", "REVOKED"})
            ex = proposal.get("executionBoundary") or {}
            ck(f"{name}_executor_blocked", ex.get("authenticatedExecutorBound") is False and ex.get("executionEnabled") is False)
            ck(f"{name}_no_provider", ex.get("providerBindingEnabled") is False and ex.get("platformMutationAllowed") is False)
            ck(f"{name}_no_permit", ex.get("authorizationPermitIssued") is False and bool(s(ex.get("idempotencyKey"))))
            per_issue[issue_id] = per_issue.get(issue_id, 0) + 1
        ck(f"{shop_id}_bounded_proposals", all(v <= int(policy.get("max_proposals_per_issue") or 2) for v in per_issue.values()), per_issue)
    ck("proposal_count", int(value.get("proposalCount") or 0) == proposal_count)
    ck("suppressed_issue_count", int(value.get("suppressedIssueCount") or 0) == suppressed_count)
    failed = [x for x in checks if x["status"] == "FAIL"]
    return {"status": "PASS" if not failed else "FAIL", "failedCheckCount": len(failed), "checks": checks}


def _find_proposal(authorization: Mapping[str, Any], proposal_id: str) -> Dict[str, Any]:
    matches = []
    for block in (authorization.get("shops") or {}).values():
        matches.extend([dict(x) for x in block.get("proposals") or [] if s(x.get("proposalId")) == proposal_id])
    if len(matches) != 1:
        raise ValueError(f"proposalId must resolve to exactly one current proposal: {proposal_id!r}")
    return matches[0]


def build_authorization_event_command(
    authorization: Mapping[str, Any], *, action: str, proposal_id: str,
    authorized_by: str, authorized_at: str, note: str = ""
) -> Dict[str, Any]:
    if s(authorization.get("status")) not in {"READY", "READY_EMPTY"}:
        raise ValueError("Action Authorization artifact is not ready")
    action = s(action).upper()
    proposal_id = s(proposal_id)
    authorized_by = s(authorized_by)
    authorized_at = s(authorized_at)
    note = s(note)
    if not authorized_by:
        raise ValueError("authorizedBy is required")
    _time(authorized_at)
    proposal = _find_proposal(authorization, proposal_id)
    available = [s(x) for x in ((proposal.get("authorization") or {}).get("availableActions") or [])]
    if action not in available:
        raise ValueError(f"action {action!r} is not available for proposal state {(proposal.get('authorization') or {}).get('state')!r}")
    core = {
        "action": action,
        "proposalId": proposal_id,
        "proposalFingerprint": s(proposal.get("proposalFingerprint")),
        "shopId": s(proposal.get("shopId")),
        "issueId": s(proposal.get("issueId")),
        "authorizedAt": authorized_at,
        "authorizedBy": authorized_by,
        "note": note,
    }
    event = {"eventId": "ads_auth_evt_" + _sha(core)[:18], **core}
    return {
        "status": "READY_TO_APPLY",
        "expectedAuthorizationLedgerFingerprint": s(authorization.get("authorizationLedgerFingerprint")),
        "expectedProposalFingerprint": s(proposal.get("proposalFingerprint")),
        "event": event,
        "executionEnabled": False,
        "platformMutationAllowed": False,
        "productionActivationEnabled": False,
    }


def apply_authorization_event_command(
    authorization_ledger: Mapping[str, Any], *, command: Mapping[str, Any],
    expected_ledger_fingerprint: str, apply: bool = False
) -> Dict[str, Any]:
    current_fp = authorization_ledger_fingerprint(authorization_ledger)
    expected = s(expected_ledger_fingerprint)
    if not expected or current_fp != expected:
        raise ValueError("stale Action Authorization ledger fingerprint; refresh before applying")
    event = dict(command.get("event") or {})
    if not event:
        raise ValueError("authorization command event is required")
    proposed = json.loads(json.dumps(authorization_ledger))
    existing_ids = {s(x.get("eventId")) for x in proposed.get("events") or []}
    if s(event.get("eventId")) in existing_ids:
        raise ValueError("authorization eventId already exists")
    proposed.setdefault("events", []).append(event)
    _authorization_events(proposed)
    proposed_fp = authorization_ledger_fingerprint(proposed)
    return {
        "status": "APPLIED" if apply else "DRY_RUN",
        "currentAuthorizationLedgerFingerprint": current_fp,
        "proposedAuthorizationLedgerFingerprint": proposed_fp,
        "event": event,
        "proposedLedger": proposed,
        "platformMutationPerformed": False,
        "productionMutationPerformed": False,
    }


def bind_ads_action_authorization_artifact(
    *, ads_output_dir: str | Path, contract_path: str | Path,
    authorization_events_path: str | Path
) -> Dict[str, Any]:
    ads_dir = Path(ads_output_dir)
    workflow_path = ads_dir / "ads_smart_issue_review_workflow.json"
    alert_path = ads_dir / "ads_alert_policy.json"
    payload_path = ads_dir / "ads_intelligence.json"
    qa_path = ads_dir / "ads_intelligence_qa_report.json"
    manifest_path = ads_dir / "ads_intelligence_manifest.json"
    for path in (workflow_path, alert_path, payload_path, qa_path, manifest_path, Path(contract_path), Path(authorization_events_path)):
        if not path.exists():
            raise ValueError(f"required Action Authorization artifact missing: {path}")

    workflow = _read_json(workflow_path)
    alert_policy = _read_json(alert_path)
    payload = _read_json(payload_path)
    qa = _read_json(qa_path)
    manifest = _read_json(manifest_path)
    contract = _read_json(contract_path)
    ledger = _read_json(authorization_events_path)

    ads_fp = s((payload.get("meta") or {}).get("adsIntelligenceFingerprint"))
    registry_fp = s((payload.get("meta") or {}).get("adsSmartIssueRegistryFingerprint"))
    if not ads_fp or ads_fp != registry_fp:
        raise ValueError("Action Authorization must bind to locked Registry / Ads fingerprint")
    if ads_fp != s(qa.get("adsIntelligenceFingerprint")) or ads_fp != s(manifest.get("adsIntelligenceFingerprint")):
        raise ValueError("Ads fingerprint mismatch before Action Authorization sidecar")
    if s(workflow.get("sourceRegistryFingerprint")) != registry_fp:
        raise ValueError("Action Authorization workflow Registry fingerprint mismatch")
    if s(alert_policy.get("adsSmartIssueRegistryFingerprint")) != registry_fp:
        raise ValueError("Action Authorization Alert Policy Registry fingerprint mismatch")

    authorization = build_action_authorization(
        workflow, ads_payload=payload, alert_policy=alert_policy,
        authorization_ledger=ledger, contract=contract,
    )
    validation = validate_action_authorization(authorization, contract=contract)
    if validation["status"] != "PASS":
        failed = [x["name"] for x in validation["checks"] if x["status"] == "FAIL"]
        raise ValueError(f"Action Authorization QA failed: {failed[:30]}")

    authorization["adsSmartIssueRegistryFingerprint"] = registry_fp
    authorization["doesNotModifyAdsIntelligenceFingerprint"] = True
    _write_json(ads_dir / "ads_action_authorization.json", authorization)

    qa["smartIssueActionAuthorization"] = validation
    qa["adsActionAuthorizationFingerprint"] = authorization["actionAuthorizationFingerprint"]
    qa["adsIntelligenceFingerprint"] = ads_fp
    files = list(manifest.get("files") or [])
    if "ads_action_authorization.json" not in files:
        files.append("ads_action_authorization.json")
    manifest["files"] = files
    manifest["adsActionAuthorizationFingerprint"] = authorization["actionAuthorizationFingerprint"]
    manifest["adsIntelligenceFingerprint"] = ads_fp
    _write_json(qa_path, qa)
    _write_json(manifest_path, manifest)

    return {
        "status": "PASS",
        "adsIntelligenceFingerprint": ads_fp,
        "adsSmartIssueRegistryFingerprint": registry_fp,
        "adsActionAuthorizationFingerprint": authorization["actionAuthorizationFingerprint"],
        "authorizationLedgerFingerprint": authorization["authorizationLedgerFingerprint"],
        "actionAuthorizationStatus": validation["status"],
        "proposalCount": authorization["proposalCount"],
        "suppressedIssueCount": authorization["suppressedIssueCount"],
        "authenticatedExecutorBound": False,
        "executionEnabled": False,
        "platformMutationAllowed": False,
        "authorization": authorization,
    }
