"""Human-reviewed Smart Issue registry for Ads Intelligence.

This PREPRODUCTION layer is downstream of Smart Issue Candidate v1. Eligible
candidates never become issues automatically. Issue creation and every issue
state transition require an explicit event from an append-only human review
ledger.

The registry is event-sourced and deterministic: a review ledger plus the
current candidate payload is sufficient to rebuild review queues and issue
state. Candidate disappearance never resolves an issue, alerts/actions remain
disabled, and no causal claim is introduced.
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


def _time(value: Any) -> dt.datetime:
    text = s(value)
    if not text:
        raise ValueError("reviewedAt is required")
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = dt.datetime.fromisoformat(text)
    except Exception as exc:
        raise ValueError(f"invalid reviewedAt: {value!r}") from exc
    if parsed.tzinfo is None:
        raise ValueError("reviewedAt must include an explicit timezone")
    return parsed


def _policy(contract: Mapping[str, Any]) -> Dict[str, Any]:
    raw = dict(contract.get("smart_issue_registry_policy") or {})
    if not raw or not bool(raw.get("enabled")):
        raise ValueError("Ads smart_issue_registry_policy must be enabled")
    if s(raw.get("input_source")) != "smartIssueCandidates":
        raise ValueError("Smart Issue Registry may only consume smartIssueCandidates")
    if s(raw.get("review_event_source")) != "EXPLICIT_APPEND_ONLY_JSON_LEDGER":
        raise ValueError("Smart Issue Registry requires an explicit append-only review ledger")
    if not bool(raw.get("explicit_human_review_required")):
        raise ValueError("Smart Issue Registry must require explicit human review")
    if s(raw.get("candidate_default_review_state")) != "PENDING_REVIEW":
        raise ValueError("unreviewed candidates must remain PENDING_REVIEW")
    if s(raw.get("promotion_initial_state")) != "OPEN":
        raise ValueError("human promotion must start an issue in OPEN state")
    if s(raw.get("issue_id_mode")) != "DETERMINISTIC_FROM_CANDIDATE_KEY":
        raise ValueError("Smart Issue IDs must be deterministic from candidateKey")
    if not bool(raw.get("review_actor_required")) or not bool(raw.get("promotion_snapshot_required")):
        raise ValueError("review actor and promotion snapshot are mandatory")
    forbidden = (
        "candidate_disappearance_auto_resolve",
        "automatic_promotion_enabled",
        "automatic_state_transition_enabled",
        "automatic_issue_resolution_enabled",
        "automatic_alerts_enabled",
        "automatic_actions_enabled",
        "causal_claims_enabled",
    )
    if any(bool(raw.get(k)) for k in forbidden):
        raise ValueError("unsafe Smart Issue Registry policy")

    candidate_actions = [s(x) for x in raw.get("candidate_review_actions") or []]
    issue_actions = [s(x) for x in raw.get("issue_transition_actions") or []]
    states = [s(x) for x in raw.get("issue_states") or []]
    if candidate_actions != ["PROMOTE", "DEFER", "DISMISS"]:
        raise ValueError("candidate review action contract mismatch")
    if issue_actions != ["ACKNOWLEDGE", "MONITOR", "RESOLVE", "REOPEN"]:
        raise ValueError("issue transition action contract mismatch")
    if states != ["OPEN", "ACKNOWLEDGED", "MONITORING", "RESOLVED"]:
        raise ValueError("issue state contract mismatch")
    if list(raw.get("event_order") or []) != ["reviewedAt", "eventId"]:
        raise ValueError("review event ordering contract mismatch")
    return raw


def _issue_id(candidate_key: str) -> str:
    if not candidate_key:
        raise ValueError("candidateKey is required for issue identity")
    return "ads_issue_" + hashlib.sha256(candidate_key.encode("utf-8")).hexdigest()[:16]


def _candidate_snapshot(shop_id: str, candidate: Mapping[str, Any]) -> Dict[str, Any]:
    persistence = candidate.get("persistence") or {}
    return {
        "shopId": shop_id,
        "candidateId": s(candidate.get("candidateId")),
        "candidateKey": s(candidate.get("candidateKey")),
        "candidateType": s(candidate.get("candidateType")),
        "kind": s(candidate.get("kind")),
        "productId": s(candidate.get("productId")),
        "productName": s(candidate.get("productName")),
        "productSku": s(candidate.get("productSku")),
        "scope": s(candidate.get("scope")),
        "contextSignature": list(persistence.get("contextSignature") or []),
        "headline": s(candidate.get("headline")),
        "summary": s(candidate.get("summary")),
        "reviewFocus": s(candidate.get("reviewFocus")),
        "priorityTier": s(candidate.get("priorityTier")),
        "priorityScore": n(candidate.get("priorityScore")),
        "coverageEnd": s(candidate.get("coverageEnd")),
        "latestEvidenceDate": s(candidate.get("latestEvidenceDate")),
    }


def _normalize_promotion_snapshot(value: Mapping[str, Any], *, candidate_key: str) -> Dict[str, Any]:
    snapshot = dict(value or {})
    required = ("shopId", "candidateId", "candidateKey", "kind", "productId", "scope")
    missing = [k for k in required if not s(snapshot.get(k))]
    if missing:
        raise ValueError(f"PROMOTE candidateSnapshot missing fields: {missing}")
    if s(snapshot.get("candidateKey")) != candidate_key:
        raise ValueError("PROMOTE candidateSnapshot candidateKey mismatch")
    snapshot["contextSignature"] = list(snapshot.get("contextSignature") or [])
    snapshot["priorityScore"] = n(snapshot.get("priorityScore"))
    return snapshot


def _normalized_events(ledger: Mapping[str, Any], *, policy: Mapping[str, Any]) -> List[Dict[str, Any]]:
    if s(ledger.get("ledger_name")) != "ads_smart_issue_review_events":
        raise ValueError("unexpected Smart Issue review ledger")
    events = list(ledger.get("events") or [])
    allowed_candidate = set(policy.get("candidate_review_actions") or [])
    allowed_issue = set(policy.get("issue_transition_actions") or [])
    allowed = allowed_candidate | allowed_issue
    seen = set()
    out = []
    for raw in events:
        if not isinstance(raw, dict):
            raise ValueError("review ledger events must be objects")
        event_id = s(raw.get("eventId"))
        action = s(raw.get("action"))
        reviewed_by = s(raw.get("reviewedBy"))
        reviewed_at = s(raw.get("reviewedAt"))
        if not event_id or event_id in seen:
            raise ValueError(f"duplicate or missing review eventId: {event_id!r}")
        seen.add(event_id)
        if action not in allowed:
            raise ValueError(f"unsupported Smart Issue review action: {action!r}")
        if not reviewed_by:
            raise ValueError(f"reviewedBy is required for event {event_id}")
        parsed = _time(reviewed_at)
        event = {
            "eventId": event_id,
            "action": action,
            "reviewedAt": reviewed_at,
            "reviewedBy": reviewed_by,
            "note": s(raw.get("note")),
            "candidateKey": s(raw.get("candidateKey")),
            "issueId": s(raw.get("issueId")),
        }
        if action in allowed_candidate:
            if not event["candidateKey"]:
                raise ValueError(f"candidateKey is required for {action} event {event_id}")
            if action == "PROMOTE":
                event["candidateSnapshot"] = _normalize_promotion_snapshot(
                    raw.get("candidateSnapshot") or {}, candidate_key=event["candidateKey"]
                )
        else:
            if not event["issueId"]:
                raise ValueError(f"issueId is required for {action} event {event_id}")
        event["_sortTime"] = parsed.isoformat()
        out.append(event)
    out.sort(key=lambda x: (x["_sortTime"], x["eventId"]))
    return out


def _public_event(event: Mapping[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in event.items() if not k.startswith("_")}


def _new_issue(event: Mapping[str, Any]) -> Dict[str, Any]:
    snapshot = dict(event.get("candidateSnapshot") or {})
    candidate_key = s(event.get("candidateKey"))
    issue_id = _issue_id(candidate_key)
    return {
        "issueId": issue_id,
        "issueKey": candidate_key,
        "sourceCandidateId": s(snapshot.get("candidateId")),
        "shopId": s(snapshot.get("shopId")),
        "candidateType": s(snapshot.get("candidateType")),
        "kind": s(snapshot.get("kind")),
        "productId": s(snapshot.get("productId")),
        "productName": s(snapshot.get("productName")),
        "productSku": s(snapshot.get("productSku")),
        "scope": s(snapshot.get("scope")),
        "contextSignature": list(snapshot.get("contextSignature") or []),
        "headline": s(snapshot.get("headline")),
        "summary": s(snapshot.get("summary")),
        "reviewFocus": s(snapshot.get("reviewFocus")),
        "priorityTier": s(snapshot.get("priorityTier")),
        "priorityScoreAtPromotion": n(snapshot.get("priorityScore")),
        "coverageEndAtPromotion": s(snapshot.get("coverageEnd")),
        "latestEvidenceDateAtPromotion": s(snapshot.get("latestEvidenceDate")),
        "state": "OPEN",
        "openedAt": s(event.get("reviewedAt")),
        "openedBy": s(event.get("reviewedBy")),
        "lastUpdatedAt": s(event.get("reviewedAt")),
        "lastUpdatedBy": s(event.get("reviewedBy")),
        "resolvedAt": "",
        "resolvedBy": "",
        "reopenCount": 0,
        "humanPromoted": True,
        "source": "EXPLICIT_HUMAN_REVIEW_LEDGER",
        "eventHistory": [_public_event(event)],
        "operatorNotes": ([{
            "eventId": s(event.get("eventId")),
            "reviewedAt": s(event.get("reviewedAt")),
            "reviewedBy": s(event.get("reviewedBy")),
            "note": s(event.get("note")),
        }] if s(event.get("note")) else []),
        "evidenceOnly": True,
        "causalClaim": False,
        "automaticAlertEligible": False,
        "automaticActionEligible": False,
    }


def _transition_issue(issue: Dict[str, Any], event: Mapping[str, Any]) -> None:
    action = s(event.get("action"))
    state = s(issue.get("state"))
    allowed: Dict[Tuple[str, str], str] = {
        ("OPEN", "ACKNOWLEDGE"): "ACKNOWLEDGED",
        ("OPEN", "MONITOR"): "MONITORING",
        ("ACKNOWLEDGED", "MONITOR"): "MONITORING",
        ("MONITORING", "MONITOR"): "MONITORING",
        ("OPEN", "RESOLVE"): "RESOLVED",
        ("ACKNOWLEDGED", "RESOLVE"): "RESOLVED",
        ("MONITORING", "RESOLVE"): "RESOLVED",
        ("RESOLVED", "REOPEN"): "OPEN",
    }
    target = allowed.get((state, action))
    if not target:
        raise ValueError(f"invalid Smart Issue transition {state} --{action}--> ? for {issue.get('issueId')}")
    issue["state"] = target
    issue["lastUpdatedAt"] = s(event.get("reviewedAt"))
    issue["lastUpdatedBy"] = s(event.get("reviewedBy"))
    if target == "RESOLVED":
        issue["resolvedAt"] = s(event.get("reviewedAt"))
        issue["resolvedBy"] = s(event.get("reviewedBy"))
    elif action == "REOPEN":
        issue["resolvedAt"] = ""
        issue["resolvedBy"] = ""
        issue["reopenCount"] = int(issue.get("reopenCount") or 0) + 1
    issue.setdefault("eventHistory", []).append(_public_event(event))
    if s(event.get("note")):
        issue.setdefault("operatorNotes", []).append({
            "eventId": s(event.get("eventId")),
            "reviewedAt": s(event.get("reviewedAt")),
            "reviewedBy": s(event.get("reviewedBy")),
            "note": s(event.get("note")),
        })


def _rebuild_event_state(events: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    issues: Dict[str, Dict[str, Any]] = {}
    candidate_to_issue: Dict[str, str] = {}
    latest_candidate_review: Dict[str, Dict[str, Any]] = {}

    for event in events:
        action = s(event.get("action"))
        candidate_key = s(event.get("candidateKey"))
        if action in {"DEFER", "DISMISS"}:
            if candidate_key in candidate_to_issue:
                raise ValueError(f"candidate {candidate_key} already promoted; {action} is not allowed")
            latest_candidate_review[candidate_key] = _public_event(event)
            continue
        if action == "PROMOTE":
            if candidate_key in candidate_to_issue:
                raise ValueError(f"candidate {candidate_key} already has a promoted Smart Issue")
            issue = _new_issue(event)
            issue_id = s(issue.get("issueId"))
            if issue_id in issues:
                raise ValueError(f"duplicate Smart Issue identity {issue_id}")
            issues[issue_id] = issue
            candidate_to_issue[candidate_key] = issue_id
            latest_candidate_review[candidate_key] = _public_event(event)
            continue

        issue_id = s(event.get("issueId"))
        issue = issues.get(issue_id)
        if not issue:
            raise ValueError(f"issue transition references unknown issue {issue_id}")
        _transition_issue(issue, event)

    return {
        "issues": issues,
        "candidateToIssue": candidate_to_issue,
        "latestCandidateReview": latest_candidate_review,
    }


def _attach_review_to_diagnosis_items(shop: Dict[str, Any], review_by_candidate_id: Mapping[str, Mapping[str, Any]]) -> None:
    for scope in ("day", "week", "month", "year"):
        snapshots = ((((shop.get("periods") or {}).get(scope) or {}).get("snapshots") or {}))
        for snapshot in snapshots.values():
            for item in ((snapshot.get("dynamicDiagnosis") or {}).get("items") or []):
                evaluation = item.get("smartIssueCandidate") or {}
                candidate_id = s(evaluation.get("candidateId"))
                if candidate_id and candidate_id in review_by_candidate_id:
                    evaluation["humanReview"] = dict(review_by_candidate_id[candidate_id])


def bind_smart_issue_registry(
    payload: Dict[str, Any],
    *,
    contract: Mapping[str, Any],
    review_ledger: Mapping[str, Any],
) -> Dict[str, Any]:
    policy = _policy(contract)
    events = _normalized_events(review_ledger, policy=policy)
    state = _rebuild_event_state(events)
    issues_by_id: Dict[str, Dict[str, Any]] = state["issues"]
    candidate_to_issue: Dict[str, str] = state["candidateToIssue"]
    latest_reviews: Dict[str, Dict[str, Any]] = state["latestCandidateReview"]
    known_shops = set((payload.get("shops") or {}).keys())

    for issue in issues_by_id.values():
        if s(issue.get("shopId")) not in known_shops:
            raise ValueError(f"Smart Issue ledger references unknown shop {issue.get('shopId')}")

    ledger_fingerprint = _sha({"ledger_name": review_ledger.get("ledger_name"), "events": [_public_event(x) for x in events]})

    for shop_id, shop in (payload.get("shops") or {}).items():
        queue: List[Dict[str, Any]] = []
        review_by_candidate_id: Dict[str, Dict[str, Any]] = {}
        current_candidates = list(shop.get("smartIssueCandidates") or [])

        for candidate in current_candidates:
            candidate_key = s(candidate.get("candidateKey"))
            candidate_id = s(candidate.get("candidateId"))
            linked_issue_id = candidate_to_issue.get(candidate_key, "")
            linked_issue = issues_by_id.get(linked_issue_id) if linked_issue_id else None
            latest_review = latest_reviews.get(candidate_key) or {}
            if linked_issue:
                if s(linked_issue.get("state")) == "RESOLVED":
                    review_state = "REOPEN_REVIEW_REQUIRED"
                else:
                    review_state = "LINKED_ISSUE"
            elif s(latest_review.get("action")) == "DEFER":
                review_state = "DEFERRED"
            elif s(latest_review.get("action")) == "DISMISS":
                review_state = "DISMISSED"
            else:
                review_state = "PENDING_REVIEW"

            review = {
                "state": review_state,
                "issueId": linked_issue_id,
                "issueState": s((linked_issue or {}).get("state")),
                "latestReviewAction": s(latest_review.get("action")),
                "latestReviewedAt": s(latest_review.get("reviewedAt")),
                "latestReviewedBy": s(latest_review.get("reviewedBy")),
                "explicitHumanReviewRequired": True,
                "automaticPromotion": False,
                "automaticAlertEligible": False,
                "automaticActionEligible": False,
            }
            candidate["humanReview"] = review
            if candidate_id:
                review_by_candidate_id[candidate_id] = review

            if review_state != "LINKED_ISSUE":
                queue.append({
                    **_candidate_snapshot(shop_id, candidate),
                    "reviewState": review_state,
                    "linkedIssueId": linked_issue_id,
                    "linkedIssueState": s((linked_issue or {}).get("state")),
                    "latestReviewAction": s(latest_review.get("action")),
                    "latestReviewedAt": s(latest_review.get("reviewedAt")),
                    "latestReviewedBy": s(latest_review.get("reviewedBy")),
                    "explicitHumanReviewRequired": True,
                    "automaticPromotion": False,
                })

        _attach_review_to_diagnosis_items(shop, review_by_candidate_id)
        shop_issues = [dict(x) for x in issues_by_id.values() if s(x.get("shopId")) == shop_id]
        shop_issues.sort(key=lambda x: (s(x.get("state")) == "RESOLVED", -n(x.get("priorityScoreAtPromotion")), s(x.get("issueId"))))
        queue.sort(key=lambda x: (-n(x.get("priorityScore")), s(x.get("candidateId"))))
        state_counts: Dict[str, int] = {}
        for issue in shop_issues:
            st = s(issue.get("state"))
            state_counts[st] = state_counts.get(st, 0) + 1
        review_counts: Dict[str, int] = {}
        for row in queue:
            st = s(row.get("reviewState"))
            review_counts[st] = review_counts.get(st, 0) + 1

        shop["smartIssues"] = shop_issues
        shop["smartIssueReviewQueue"] = queue
        shop["smartIssueRegistryLineage"] = {
            "mode": s(policy.get("mode")),
            "inputSource": "smartIssueCandidates",
            "reviewEventSource": s(policy.get("review_event_source")),
            "reviewLedgerFingerprint": ledger_fingerprint,
            "currentCandidateCount": len(current_candidates),
            "reviewQueueCount": len(queue),
            "issueCount": len(shop_issues),
            "issueStateCounts": state_counts,
            "reviewStateCounts": review_counts,
            "explicitHumanReviewRequired": True,
            "candidateDisappearanceAutoResolve": False,
            "automaticPromotionEnabled": False,
            "automaticIssueResolutionEnabled": False,
            "automaticAlertsEnabled": False,
            "automaticActionsEnabled": False,
        }

    payload.setdefault("capabilities", {})["adsSmartIssueRegistry"] = True
    payload["capabilities"]["adsSmartIssueHumanReview"] = True
    payload["capabilities"]["adsHumanPromotedSmartIssuesEnabled"] = True
    payload["capabilities"]["adsSmartIssuesEnabled"] = True
    payload["capabilities"]["adsSmartIssueAutomaticAlertsEnabled"] = False
    payload["capabilities"]["adsSmartIssueAutomaticActionsEnabled"] = False
    return payload


def validate_smart_issue_registry(
    payload: Mapping[str, Any],
    *,
    contract: Mapping[str, Any],
    review_ledger: Mapping[str, Any],
) -> Dict[str, Any]:
    policy = _policy(contract)
    events = _normalized_events(review_ledger, policy=policy)
    event_state = _rebuild_event_state(events)
    promotion_keys = set(event_state["candidateToIssue"].keys())
    event_issue_ids = set(event_state["issues"].keys())
    checks: List[Dict[str, Any]] = []

    def ck(name: str, ok: bool, detail: Any = None) -> None:
        checks.append({"name": name, "status": "PASS" if ok else "FAIL", "detail": detail or {}})

    caps = payload.get("capabilities") or {}
    ck("smart_issue_registry_capability", bool(caps.get("adsSmartIssueRegistry")))
    ck("smart_issue_human_review_capability", bool(caps.get("adsSmartIssueHumanReview")))
    ck("human_promoted_smart_issues_enabled", bool(caps.get("adsHumanPromotedSmartIssuesEnabled")))
    ck("smart_issue_alerts_disabled", caps.get("adsSmartIssueAutomaticAlertsEnabled") is False)
    ck("smart_issue_actions_disabled", caps.get("adsSmartIssueAutomaticActionsEnabled") is False)

    payload_issue_ids = set()
    for shop_id, shop in (payload.get("shops") or {}).items():
        lineage = shop.get("smartIssueRegistryLineage") or {}
        ck(f"{shop_id}_registry_source", s(lineage.get("inputSource")) == "smartIssueCandidates")
        ck(f"{shop_id}_registry_review_source", s(lineage.get("reviewEventSource")) == "EXPLICIT_APPEND_ONLY_JSON_LEDGER")
        ck(f"{shop_id}_registry_no_auto_promotion", lineage.get("automaticPromotionEnabled") is False)
        ck(f"{shop_id}_registry_no_auto_resolution", lineage.get("automaticIssueResolutionEnabled") is False)

        candidates = {s(x.get("candidateKey")): x for x in (shop.get("smartIssueCandidates") or [])}
        queue = list(shop.get("smartIssueReviewQueue") or [])
        issues = list(shop.get("smartIssues") or [])
        queue_keys = [s(x.get("candidateKey")) for x in queue]
        ck(f"{shop_id}_review_queue_unique", len(queue_keys) == len(set(queue_keys)))
        ck(f"{shop_id}_review_queue_current_candidates", all(k in candidates for k in queue_keys))

        for row in queue:
            key = s(row.get("candidateKey"))
            state = s(row.get("reviewState"))
            ck(f"{shop_id}_{key}_review_state", state in {"PENDING_REVIEW", "DEFERRED", "DISMISSED", "REOPEN_REVIEW_REQUIRED"})
            if key not in promotion_keys and not s((event_state["latestCandidateReview"].get(key) or {}).get("action")):
                ck(f"{shop_id}_{key}_unreviewed_pending", state == "PENDING_REVIEW")
            ck(f"{shop_id}_{key}_review_explicit", bool(row.get("explicitHumanReviewRequired")) and row.get("automaticPromotion") is False)

        for issue in issues:
            issue_id = s(issue.get("issueId"))
            key = s(issue.get("issueKey"))
            payload_issue_ids.add(issue_id)
            name = f"{shop_id}_{issue_id}"
            ck(f"{name}_human_promoted", bool(issue.get("humanPromoted")) and key in promotion_keys)
            ck(f"{name}_deterministic_id", issue_id == _issue_id(key))
            ck(f"{name}_valid_state", s(issue.get("state")) in {"OPEN", "ACKNOWLEDGED", "MONITORING", "RESOLVED"})
            history = list(issue.get("eventHistory") or [])
            ck(f"{name}_promotion_first", bool(history) and s(history[0].get("action")) == "PROMOTE")
            ck(f"{name}_noncausal", bool(issue.get("evidenceOnly")) and not bool(issue.get("causalClaim")))
            ck(f"{name}_no_automation", not bool(issue.get("automaticAlertEligible")) and not bool(issue.get("automaticActionEligible")))
            ck(f"{name}_shop_scope", s(issue.get("shopId")) == shop_id)

        linked_active_keys = {s(x.get("issueKey")) for x in issues if s(x.get("state")) != "RESOLVED"}
        for key, candidate in candidates.items():
            review = candidate.get("humanReview") or {}
            if key in linked_active_keys:
                ck(f"{shop_id}_{key}_active_issue_link", s(review.get("state")) == "LINKED_ISSUE")
            if key in promotion_keys:
                issue_id = event_state["candidateToIssue"].get(key, "")
                issue = event_state["issues"].get(issue_id) or {}
                if s(issue.get("state")) == "RESOLVED" and key in candidates:
                    ck(f"{shop_id}_{key}_resolved_requires_reopen_review", s(review.get("state")) == "REOPEN_REVIEW_REQUIRED")

    ck("registry_issue_set_matches_ledger", payload_issue_ids == event_issue_ids, {
        "payloadIssueIds": sorted(payload_issue_ids), "ledgerIssueIds": sorted(event_issue_ids)
    })
    failed = [x for x in checks if x["status"] == "FAIL"]
    return {"status": "PASS" if not failed else "FAIL", "failedCheckCount": len(failed), "checks": checks}


def build_smart_issue_registry_preview(payload: Mapping[str, Any]) -> Dict[str, Any]:
    shops: Dict[str, Any] = {}
    for shop_id, shop in (payload.get("shops") or {}).items():
        issues = list(shop.get("smartIssues") or [])
        queue = list(shop.get("smartIssueReviewQueue") or [])
        shops[shop_id] = {
            "displayName": s(shop.get("displayName")),
            "currentCandidateCount": len(shop.get("smartIssueCandidates") or []),
            "reviewQueueCount": len(queue),
            "issueCount": len(issues),
            "reviewQueue": queue[:10],
            "issues": issues[:10],
            "lineage": dict(shop.get("smartIssueRegistryLineage") or {}),
        }
    return {
        "status": "PREPRODUCTION_REGISTRY",
        "preSmartIssueRegistryAdsIntelligenceFingerprint": s((payload.get("meta") or {}).get("preSmartIssueRegistryAdsIntelligenceFingerprint")),
        "adsSmartIssueCandidateFingerprint": s((payload.get("meta") or {}).get("adsSmartIssueCandidateFingerprint")),
        "adsSmartIssueRegistryFingerprint": s((payload.get("meta") or {}).get("adsSmartIssueRegistryFingerprint")),
        "adsIntelligenceFingerprint": s((payload.get("meta") or {}).get("adsIntelligenceFingerprint")),
        "shops": shops,
        "safety": {
            "productionActivationEnabled": False,
            "explicitHumanReviewRequired": True,
            "automaticPromotionEnabled": False,
            "automaticIssueResolutionEnabled": False,
            "automaticAlertsEnabled": False,
            "automaticActionsEnabled": False,
            "causalClaimsEnabled": False,
        },
    }


def _registry_document(payload: Mapping[str, Any], ledger_fingerprint: str) -> Dict[str, Any]:
    return {
        "status": "PREPRODUCTION_REGISTRY",
        "reviewLedgerFingerprint": ledger_fingerprint,
        "shops": {
            shop_id: {
                "displayName": s(shop.get("displayName")),
                "reviewQueue": list(shop.get("smartIssueReviewQueue") or []),
                "issues": list(shop.get("smartIssues") or []),
                "lineage": dict(shop.get("smartIssueRegistryLineage") or {}),
            }
            for shop_id, shop in (payload.get("shops") or {}).items()
        },
        "safety": {
            "explicitHumanReviewRequired": True,
            "automaticPromotionEnabled": False,
            "automaticIssueResolutionEnabled": False,
            "automaticAlertsEnabled": False,
            "automaticActionsEnabled": False,
            "causalClaimsEnabled": False,
        },
    }


def bind_ads_smart_issue_registry_artifacts(
    *,
    ads_output_dir: str | Path,
    contract_path: str | Path,
    review_events_path: str | Path,
) -> Dict[str, Any]:
    ads_dir = Path(ads_output_dir)
    payload_path = ads_dir / "ads_intelligence.json"
    qa_path = ads_dir / "ads_intelligence_qa_report.json"
    manifest_path = ads_dir / "ads_intelligence_manifest.json"
    for path in (payload_path, qa_path, manifest_path, Path(contract_path), Path(review_events_path)):
        if not path.exists():
            raise ValueError(f"required Smart Issue Registry artifact missing: {path}")

    payload = _read_json(payload_path)
    qa = _read_json(qa_path)
    manifest = _read_json(manifest_path)
    contract = _read_json(contract_path)
    ledger = _read_json(review_events_path)
    candidate_fingerprint = s((payload.get("meta") or {}).get("adsSmartIssueCandidateFingerprint"))
    current_fingerprint = s((payload.get("meta") or {}).get("adsIntelligenceFingerprint"))
    if not candidate_fingerprint or not current_fingerprint:
        raise ValueError("Smart Issue Candidate fingerprint is required before Registry")
    if current_fingerprint != candidate_fingerprint:
        raise ValueError("Smart Issue Registry must bind directly after Smart Issue Candidate v1")
    if current_fingerprint != s(qa.get("adsIntelligenceFingerprint")) or current_fingerprint != s(manifest.get("adsIntelligenceFingerprint")):
        raise ValueError("Ads fingerprint mismatch before Smart Issue Registry")

    policy = _policy(contract)
    events = _normalized_events(ledger, policy=policy)
    ledger_fingerprint = _sha({"ledger_name": ledger.get("ledger_name"), "events": [_public_event(x) for x in events]})
    bind_smart_issue_registry(payload, contract=contract, review_ledger=ledger)
    registry_qa = validate_smart_issue_registry(payload, contract=contract, review_ledger=ledger)
    if registry_qa["status"] != "PASS":
        failed = [x["name"] for x in registry_qa["checks"] if x["status"] == "FAIL"]
        raise ValueError(f"Ads Smart Issue Registry QA failed: {failed[:20]}")

    final_fingerprint = _sha({
        "preSmartIssueRegistryAdsIntelligenceFingerprint": current_fingerprint,
        "adsSmartIssueCandidateFingerprint": candidate_fingerprint,
        "reviewLedgerFingerprint": ledger_fingerprint,
        "smartIssueRegistryPolicy": policy,
        "payload": payload,
    })
    payload["meta"]["preSmartIssueRegistryAdsIntelligenceFingerprint"] = current_fingerprint
    payload["meta"]["adsSmartIssueReviewLedgerFingerprint"] = ledger_fingerprint
    payload["meta"]["adsSmartIssueRegistryFingerprint"] = final_fingerprint
    payload["meta"]["adsIntelligenceFingerprint"] = final_fingerprint

    qa["preSmartIssueRegistryAdsIntelligenceFingerprint"] = current_fingerprint
    qa["adsSmartIssueReviewLedgerFingerprint"] = ledger_fingerprint
    qa["adsSmartIssueRegistryFingerprint"] = final_fingerprint
    qa["adsIntelligenceFingerprint"] = final_fingerprint
    qa["smartIssueRegistry"] = registry_qa

    manifest["preSmartIssueRegistryAdsIntelligenceFingerprint"] = current_fingerprint
    manifest["adsSmartIssueReviewLedgerFingerprint"] = ledger_fingerprint
    manifest["adsSmartIssueRegistryFingerprint"] = final_fingerprint
    manifest["adsIntelligenceFingerprint"] = final_fingerprint
    files = list(manifest.get("files") or [])
    for name in ("ads_smart_issue_registry.json", "ads_smart_issue_registry_preview.json"):
        if name not in files:
            files.append(name)
    manifest["files"] = files

    registry_doc = _registry_document(payload, ledger_fingerprint)
    registry_doc["adsSmartIssueRegistryFingerprint"] = final_fingerprint
    preview = build_smart_issue_registry_preview(payload)
    preview["preSmartIssueRegistryAdsIntelligenceFingerprint"] = current_fingerprint
    preview["adsSmartIssueCandidateFingerprint"] = candidate_fingerprint
    preview["adsSmartIssueRegistryFingerprint"] = final_fingerprint
    preview["adsIntelligenceFingerprint"] = final_fingerprint

    _write_json(payload_path, payload)
    _write_json(qa_path, qa)
    _write_json(manifest_path, manifest)
    _write_json(ads_dir / "ads_smart_issue_registry.json", registry_doc)
    _write_json(ads_dir / "ads_smart_issue_registry_preview.json", preview)
    return {
        "status": "PASS",
        "preSmartIssueRegistryAdsIntelligenceFingerprint": current_fingerprint,
        "adsSmartIssueCandidateFingerprint": candidate_fingerprint,
        "adsSmartIssueReviewLedgerFingerprint": ledger_fingerprint,
        "adsSmartIssueRegistryFingerprint": final_fingerprint,
        "adsIntelligenceFingerprint": final_fingerprint,
        "smartIssueRegistryStatus": registry_qa["status"],
        "registryPreview": preview,
    }
