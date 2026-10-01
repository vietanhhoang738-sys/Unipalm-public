"""PREPRODUCTION Smart Issue Alert Policy v1.

Consumes only the validated human-reviewed Smart Issue operator workflow.
It creates alert intents, routing recommendations, dedupe and cooldown metadata,
but never sends notifications or mutates the locked Ads/Registry fingerprint.
"""
from __future__ import annotations

import datetime as dt
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
    if s(contract.get("status")) != "PREPRODUCTION":
        raise ValueError("Alert Policy contract must remain PREPRODUCTION")
    raw = dict(contract.get("alert_policy") or {})
    if not raw or not bool(raw.get("enabled")):
        raise ValueError("alert_policy must be enabled")
    if s(raw.get("input_source")) != "ads_smart_issue_review_workflow.json":
        raise ValueError("Alert Policy may only consume the operator review workflow")
    if s(raw.get("delivery_event_source")) != "ads_alert_delivery_events.json":
        raise ValueError("unexpected Alert Policy delivery event source")
    if not bool(raw.get("human_promoted_issue_required")):
        raise ValueError("Alert Policy human-review gate missing")
    forbidden_true = (
        "candidate_alerting_enabled", "repeated_reminders_enabled",
        "automatic_issue_promotion_enabled", "automatic_issue_transition_enabled",
        "automatic_issue_resolution_enabled", "automatic_actions_enabled",
        "causal_claims_enabled", "production_activation_enabled",
    )
    if any(bool(raw.get(k)) for k in forbidden_true):
        raise ValueError("unsafe Alert Policy automation flag")
    if list(raw.get("eligible_kinds") or []) != ["PROBLEM"]:
        raise ValueError("Alert Policy v1 may only interrupt for PROBLEM Smart Issues")
    if list(raw.get("eligible_issue_states") or []) != ["OPEN"]:
        raise ValueError("Alert Policy v1 eligible issue state must remain OPEN only")
    if list(raw.get("suppressed_issue_states") or []) != ["ACKNOWLEDGED", "MONITORING", "RESOLVED"]:
        raise ValueError("Alert Policy issue suppression states mismatch")
    if list(raw.get("trigger_actions") or []) != ["PROMOTE", "REOPEN"]:
        raise ValueError("Alert Policy trigger actions mismatch")

    severity = dict(raw.get("severity") or {})
    expected = {
        "HIGH": ("HIGH", 75.0, ["COMMAND_CENTER", "OPERATOR_NOTIFICATION"], 24),
        "MEDIUM": ("MEDIUM", 55.0, ["COMMAND_CENTER"], 72),
    }
    for name, (tier, minimum, channels, hours) in expected.items():
        row = dict(severity.get(name) or {})
        if [s(x) for x in row.get("priority_tiers") or []] != [tier]:
            raise ValueError(f"{name} priority tier mapping mismatch")
        if n(row.get("minimum_priority_score")) != minimum:
            raise ValueError(f"{name} minimum priority score mismatch")
        if [s(x) for x in row.get("recommended_channel_classes") or []] != channels:
            raise ValueError(f"{name} routing mismatch")
        if int(row.get("cooldown_hours") or 0) != hours:
            raise ValueError(f"{name} cooldown mismatch")

    dedup = dict(raw.get("deduplication") or {})
    if list(dedup.get("alert_key_fields") or []) != ["shopId", "issueId", "triggerEventId", "severity"]:
        raise ValueError("Alert Policy alert key contract mismatch")
    if list(dedup.get("delivery_dedupe_fields") or []) != ["alertKey", "channelClass"]:
        raise ValueError("Alert Policy delivery dedupe contract mismatch")
    required_dedup_true = (
        "one_intent_per_alert_key", "delivered_event_suppresses_same_alert_key_channel",
        "only_delivered_events_start_cooldown", "reopen_bypasses_previous_epoch_cooldown",
    )
    if any(not bool(dedup.get(k)) for k in required_dedup_true):
        raise ValueError("Alert Policy dedup/cooldown safety requirement missing")
    if list(dedup.get("cooldown_scope") or []) != ["shopId", "issueId", "channelClass"]:
        raise ValueError("Alert Policy cooldown scope mismatch")

    delivery = dict(raw.get("delivery") or {})
    if any(bool(delivery.get(k)) for k in ("enabled", "automatic_delivery_enabled", "provider_binding_enabled")):
        raise ValueError("Alert Policy v1 delivery/provider binding must remain disabled")
    if delivery.get("command_center_is_presentation_only") is not True:
        raise ValueError("Command Center must remain presentation-only in Alert Policy v1")
    return raw


def alert_delivery_ledger_fingerprint(ledger: Mapping[str, Any]) -> str:
    return _sha({
        "version": s(ledger.get("version")),
        "ledger_name": s(ledger.get("ledger_name")),
        "events": list(ledger.get("events") or []),
    })


def _delivery_events(ledger: Mapping[str, Any]) -> List[Dict[str, Any]]:
    if s(ledger.get("version")) != "1.0" or s(ledger.get("ledger_name")) != "ads_alert_delivery_events":
        raise ValueError("unexpected Alert Policy delivery ledger")
    seen = set()
    out = []
    for raw in ledger.get("events") or []:
        if not isinstance(raw, dict):
            raise ValueError("Alert delivery events must be objects")
        event_id = s(raw.get("eventId"))
        alert_key = s(raw.get("alertKey"))
        shop_id = s(raw.get("shopId"))
        issue_id = s(raw.get("issueId"))
        channel = s(raw.get("channelClass"))
        status = s(raw.get("status"))
        delivered_at = s(raw.get("deliveredAt"))
        if not event_id or event_id in seen:
            raise ValueError(f"duplicate or missing Alert delivery eventId: {event_id!r}")
        seen.add(event_id)
        if not alert_key or not shop_id or not issue_id or not channel:
            raise ValueError(f"Alert delivery event identity incomplete: {event_id}")
        if status not in {"DELIVERED", "FAILED"}:
            raise ValueError(f"unsupported Alert delivery status: {status!r}")
        _time(delivered_at)
        out.append({
            "eventId": event_id,
            "alertKey": alert_key,
            "shopId": shop_id,
            "issueId": issue_id,
            "channelClass": channel,
            "status": status,
            "deliveredAt": delivered_at,
            "providerRef": s(raw.get("providerRef")),
        })
    out.sort(key=lambda x: (_time(x["deliveredAt"]), x["eventId"]))
    return out


def _trigger(issue: Mapping[str, Any], policy: Mapping[str, Any]) -> Dict[str, Any]:
    if issue.get("humanPromoted") is not True or s(issue.get("source")) != "EXPLICIT_HUMAN_REVIEW_LEDGER":
        raise ValueError(f"Alert Policy requires a human-promoted issue: {issue.get('issueId')}")
    history = list(issue.get("eventHistory") or [])
    if not history or s(history[0].get("action")) != "PROMOTE":
        raise ValueError(f"Smart Issue promotion history missing: {issue.get('issueId')}")
    last = history[-1]
    action = s(last.get("action"))
    if s(issue.get("state")) == "OPEN" and action not in set(policy.get("trigger_actions") or []):
        raise ValueError(f"OPEN Smart Issue has invalid alert trigger history: {issue.get('issueId')}")
    return {
        "action": action,
        "eventId": s(last.get("eventId")),
        "reviewedAt": s(last.get("reviewedAt")),
        "reviewedBy": s(last.get("reviewedBy")),
    }


def _severity(issue: Mapping[str, Any], policy: Mapping[str, Any]) -> str:
    tier = s(issue.get("priorityTier"))
    score = n(issue.get("priorityScoreAtPromotion"))
    for name in ("HIGH", "MEDIUM"):
        row = (policy.get("severity") or {}).get(name) or {}
        if tier in [s(x) for x in row.get("priority_tiers") or []] and score >= n(row.get("minimum_priority_score")):
            return name
    return ""


def _evaluation_at(workflow: Mapping[str, Any], events: Sequence[Mapping[str, Any]], explicit: str = "") -> dt.datetime | None:
    values: List[dt.datetime] = []
    if explicit:
        values.append(_time(explicit))
    for shop in (workflow.get("shops") or {}).values():
        for issue in shop.get("issues") or []:
            for event in issue.get("eventHistory") or []:
                if s(event.get("reviewedAt")):
                    values.append(_time(event.get("reviewedAt")))
    for event in events:
        values.append(_time(event.get("deliveredAt")))
    return max(values) if values else None


def _channel_decisions(*, issue: Mapping[str, Any], alert_key: str, severity: str,
                       trigger: Mapping[str, Any], policy: Mapping[str, Any],
                       delivery_events: Sequence[Mapping[str, Any]],
                       evaluation_at: dt.datetime | None) -> List[Dict[str, Any]]:
    severity_policy = (policy.get("severity") or {}).get(severity) or {}
    channels = [s(x) for x in severity_policy.get("recommended_channel_classes") or []]
    cooldown_hours = int(severity_policy.get("cooldown_hours") or 0)
    reopen = s(trigger.get("action")) == "REOPEN"
    out = []
    for channel in channels:
        if channel == "COMMAND_CENTER":
            out.append({
                "channelClass": channel, "policyEligible": True, "deliveryEnabled": False,
                "status": "PRESENTATION_ONLY", "cooldownHours": 0,
                "cooldownUntil": "", "suppressionReason": "",
            })
            continue
        same_key = [
            x for x in delivery_events
            if s(x.get("status")) == "DELIVERED"
            and s(x.get("alertKey")) == alert_key
            and s(x.get("channelClass")) == channel
        ]
        if same_key:
            out.append({
                "channelClass": channel, "policyEligible": False, "deliveryEnabled": False,
                "status": "SUPPRESSED", "cooldownHours": cooldown_hours,
                "cooldownUntil": "", "suppressionReason": "ALREADY_DELIVERED_SAME_ALERT_KEY",
            })
            continue
        prior = [
            x for x in delivery_events
            if s(x.get("status")) == "DELIVERED"
            and s(x.get("shopId")) == s(issue.get("shopId"))
            and s(x.get("issueId")) == s(issue.get("issueId"))
            and s(x.get("channelClass")) == channel
        ]
        cooldown_until = ""
        cooldown_active = False
        if prior and not (reopen and bool((policy.get("deduplication") or {}).get("reopen_bypasses_previous_epoch_cooldown"))):
            latest = max(_time(x.get("deliveredAt")) for x in prior)
            until = latest + dt.timedelta(hours=cooldown_hours)
            cooldown_until = until.isoformat()
            cooldown_active = evaluation_at is not None and evaluation_at < until
        out.append({
            "channelClass": channel,
            "policyEligible": not cooldown_active,
            "deliveryEnabled": False,
            "status": "SUPPRESSED" if cooldown_active else "DELIVERY_DISABLED",
            "cooldownHours": cooldown_hours,
            "cooldownUntil": cooldown_until,
            "suppressionReason": "COOLDOWN_ACTIVE" if cooldown_active else "",
        })
    return out


def _suppressed_issue(issue: Mapping[str, Any], reason: str) -> Dict[str, Any]:
    return {
        "shopId": s(issue.get("shopId")),
        "issueId": s(issue.get("issueId")),
        "issueKey": s(issue.get("issueKey")),
        "kind": s(issue.get("kind")),
        "productId": s(issue.get("productId")),
        "productName": s(issue.get("productName")),
        "scope": s(issue.get("scope")),
        "state": s(issue.get("state")),
        "priorityTier": s(issue.get("priorityTier")),
        "priorityScoreAtPromotion": n(issue.get("priorityScoreAtPromotion")),
        "suppressionReason": reason,
        "policyEligible": False,
        "automaticDelivery": False,
    }


def build_alert_policy(workflow: Mapping[str, Any], *, delivery_ledger: Mapping[str, Any],
                       contract: Mapping[str, Any], evaluation_at: str = "") -> Dict[str, Any]:
    policy = _policy(contract)
    if s(workflow.get("status")) not in {"READY", "READY_EMPTY"}:
        raise ValueError("operator review workflow is not ready")
    if not s(workflow.get("workflowFingerprint")) or not s(workflow.get("sourceRegistryFingerprint")):
        raise ValueError("Alert Policy source workflow lineage missing")
    safety = workflow.get("safety") or {}
    if safety.get("explicitHumanReviewRequired") is not True or safety.get("automaticAlertsEnabled") is not False:
        raise ValueError("Alert Policy source workflow safety mismatch")

    delivery_events = _delivery_events(delivery_ledger)
    anchor = _evaluation_at(workflow, delivery_events, explicit=evaluation_at)
    shops: Dict[str, Any] = {}
    all_keys = set()
    eligible_count = 0
    suppressed_count = 0
    severity_counts = {"HIGH": 0, "MEDIUM": 0}

    for shop_id, block in (workflow.get("shops") or {}).items():
        alerts = []
        suppressed = []
        for issue in block.get("issues") or []:
            if s(issue.get("shopId")) != shop_id:
                raise ValueError(f"Alert Policy issue shop mismatch: {issue.get('issueId')}")
            trigger = _trigger(issue, policy)
            state = s(issue.get("state"))
            if state in set(policy.get("suppressed_issue_states") or []):
                suppressed.append(_suppressed_issue(issue, "ISSUE_STATE_SUPPRESSED"))
                continue
            if state not in set(policy.get("eligible_issue_states") or []):
                suppressed.append(_suppressed_issue(issue, "ISSUE_STATE_NOT_ELIGIBLE"))
                continue
            if s(issue.get("kind")) not in set(policy.get("eligible_kinds") or []):
                suppressed.append(_suppressed_issue(issue, "NON_INTERRUPTIVE_OPPORTUNITY"))
                continue
            severity = _severity(issue, policy)
            if not severity:
                suppressed.append(_suppressed_issue(issue, "PRIORITY_BELOW_ALERT_THRESHOLD"))
                continue
            if s(trigger.get("action")) not in set(policy.get("trigger_actions") or []):
                suppressed.append(_suppressed_issue(issue, "NO_ALERT_TRIGGER_EVENT"))
                continue
            identity = {
                "shopId": shop_id,
                "issueId": s(issue.get("issueId")),
                "triggerEventId": s(trigger.get("eventId")),
                "severity": severity,
            }
            if not identity["triggerEventId"]:
                raise ValueError(f"Alert Policy trigger eventId missing: {issue.get('issueId')}")
            alert_key = _sha(identity)
            if alert_key in all_keys:
                raise ValueError(f"duplicate Alert Policy alertKey: {alert_key}")
            all_keys.add(alert_key)
            channel_decisions = _channel_decisions(
                issue=issue, alert_key=alert_key, severity=severity, trigger=trigger,
                policy=policy, delivery_events=delivery_events, evaluation_at=anchor,
            )
            alerts.append({
                "alertId": "ads_alert_" + alert_key[:16],
                "alertKey": alert_key,
                "shopId": shop_id,
                "issueId": s(issue.get("issueId")),
                "issueKey": s(issue.get("issueKey")),
                "kind": s(issue.get("kind")),
                "productId": s(issue.get("productId")),
                "productName": s(issue.get("productName")),
                "productSku": s(issue.get("productSku")),
                "scope": s(issue.get("scope")),
                "headline": s(issue.get("headline")),
                "summary": s(issue.get("summary")),
                "severity": severity,
                "priorityTier": s(issue.get("priorityTier")),
                "priorityScoreAtPromotion": n(issue.get("priorityScoreAtPromotion")),
                "triggerAction": s(trigger.get("action")),
                "triggerEventId": s(trigger.get("eventId")),
                "triggeredAt": s(trigger.get("reviewedAt")),
                "triggeredBy": s(trigger.get("reviewedBy")),
                "recommendedChannelClasses": [
                    s(x) for x in ((policy.get("severity") or {}).get(severity) or {}).get("recommended_channel_classes") or []
                ],
                "channelDecisions": channel_decisions,
                "policyEligible": True,
                "deliveryEnabled": False,
                "automaticDelivery": False,
                "evidenceOnly": True,
                "causalClaim": False,
            })
            eligible_count += 1
            severity_counts[severity] += 1

        alerts.sort(key=lambda x: (0 if x["severity"] == "HIGH" else 1, -n(x.get("priorityScoreAtPromotion")), s(x.get("issueId"))))
        suppressed.sort(key=lambda x: (s(x.get("suppressionReason")), s(x.get("issueId"))))
        suppressed_count += len(suppressed)
        shops[shop_id] = {
            "displayName": s(block.get("displayName")),
            "eligibleAlerts": alerts,
            "suppressedIssues": suppressed,
            "eligibleAlertCount": len(alerts),
            "suppressedIssueCount": len(suppressed),
        }

    artifact = {
        "status": "READY" if eligible_count else "READY_EMPTY",
        "mode": s(policy.get("mode")),
        "sourceReviewWorkflowFingerprint": s(workflow.get("workflowFingerprint")),
        "sourceRegistryFingerprint": s(workflow.get("sourceRegistryFingerprint")),
        "sourceOperatorLedgerFingerprint": s(workflow.get("operatorLedgerFingerprint")),
        "deliveryLedgerFingerprint": alert_delivery_ledger_fingerprint(delivery_ledger),
        "evaluationAt": anchor.isoformat() if anchor else "",
        "eligibleAlertCount": eligible_count,
        "suppressedIssueCount": suppressed_count,
        "severityCounts": severity_counts,
        "shops": shops,
        "routingPolicy": json.loads(json.dumps(policy.get("severity") or {})),
        "deduplicationPolicy": json.loads(json.dumps(policy.get("deduplication") or {})),
        "delivery": {
            "enabled": False,
            "automaticDeliveryEnabled": False,
            "providerBindingEnabled": False,
            "commandCenterPresentationOnly": True,
        },
        "safety": {
            "humanPromotedIssueRequired": True,
            "candidateAlertingEnabled": False,
            "repeatedRemindersEnabled": False,
            "automaticIssuePromotionEnabled": False,
            "automaticIssueTransitionEnabled": False,
            "automaticIssueResolutionEnabled": False,
            "automaticDeliveryEnabled": False,
            "automaticActionsEnabled": False,
            "causalClaimsEnabled": False,
            "productionActivationEnabled": False,
        },
    }
    artifact["alertPolicyFingerprint"] = _sha({
        "sourceReviewWorkflowFingerprint": artifact["sourceReviewWorkflowFingerprint"],
        "deliveryLedgerFingerprint": artifact["deliveryLedgerFingerprint"],
        "policy": policy,
        "shops": shops,
    })
    return artifact


def validate_alert_policy(artifact: Mapping[str, Any], *, contract: Mapping[str, Any]) -> Dict[str, Any]:
    policy = _policy(contract)
    checks: List[Dict[str, Any]] = []

    def ck(name: str, ok: bool, detail: Any = None) -> None:
        checks.append({"name": name, "status": "PASS" if ok else "FAIL", "detail": detail or {}})

    ck("status", s(artifact.get("status")) in {"READY", "READY_EMPTY"})
    ck("policy_fingerprint_present", bool(s(artifact.get("alertPolicyFingerprint"))))
    ck("source_workflow_fingerprint_present", bool(s(artifact.get("sourceReviewWorkflowFingerprint"))))
    ck("source_registry_fingerprint_present", bool(s(artifact.get("sourceRegistryFingerprint"))))
    ck("delivery_ledger_fingerprint_present", bool(s(artifact.get("deliveryLedgerFingerprint"))))
    delivery = artifact.get("delivery") or {}
    ck("delivery_disabled", delivery.get("enabled") is False)
    ck("automatic_delivery_disabled", delivery.get("automaticDeliveryEnabled") is False)
    ck("provider_binding_disabled", delivery.get("providerBindingEnabled") is False)
    safety = artifact.get("safety") or {}
    ck("human_promoted_gate", safety.get("humanPromotedIssueRequired") is True)
    ck("candidate_alerting_disabled", safety.get("candidateAlertingEnabled") is False)
    ck("repeated_reminders_disabled", safety.get("repeatedRemindersEnabled") is False)
    ck("automatic_actions_disabled", safety.get("automaticActionsEnabled") is False)
    ck("causal_claims_disabled", safety.get("causalClaimsEnabled") is False)
    ck("production_activation_disabled", safety.get("productionActivationEnabled") is False)

    eligible = 0
    suppressed = 0
    seen = set()
    severity_counts = {"HIGH": 0, "MEDIUM": 0}
    for shop_id, block in (artifact.get("shops") or {}).items():
        for alert in block.get("eligibleAlerts") or []:
            key = s(alert.get("alertKey"))
            sev = s(alert.get("severity"))
            ck(f"{shop_id}_{key}_unique", bool(key) and key not in seen)
            seen.add(key)
            ck(f"{shop_id}_{key}_shop", s(alert.get("shopId")) == shop_id)
            ck(f"{shop_id}_{key}_problem_only", s(alert.get("kind")) == "PROBLEM")
            ck(f"{shop_id}_{key}_severity", sev in {"HIGH", "MEDIUM"})
            ck(f"{shop_id}_{key}_policy_eligible", alert.get("policyEligible") is True)
            ck(f"{shop_id}_{key}_delivery_off", alert.get("deliveryEnabled") is False and alert.get("automaticDelivery") is False)
            ck(f"{shop_id}_{key}_noncausal", alert.get("evidenceOnly") is True and alert.get("causalClaim") is False)
            expected_channels = [s(x) for x in ((policy.get("severity") or {}).get(sev) or {}).get("recommended_channel_classes") or []]
            ck(f"{shop_id}_{key}_routing", list(alert.get("recommendedChannelClasses") or []) == expected_channels)
            eligible += 1
            severity_counts[sev] += 1
        suppressed += len(block.get("suppressedIssues") or [])
        ck(f"{shop_id}_eligible_count", int(block.get("eligibleAlertCount") or 0) == len(block.get("eligibleAlerts") or []))
        ck(f"{shop_id}_suppressed_count", int(block.get("suppressedIssueCount") or 0) == len(block.get("suppressedIssues") or []))

    ck("eligible_count", int(artifact.get("eligibleAlertCount") or 0) == eligible)
    ck("suppressed_count", int(artifact.get("suppressedIssueCount") or 0) == suppressed)
    ck("severity_counts", dict(artifact.get("severityCounts") or {}) == severity_counts)
    failed = [x for x in checks if x["status"] == "FAIL"]
    return {"status": "PASS" if not failed else "FAIL", "failedCheckCount": len(failed), "checks": checks}


def bind_ads_alert_policy_artifact(*, ads_output_dir: str | Path, contract_path: str | Path,
                                   delivery_events_path: str | Path, evaluation_at: str = "") -> Dict[str, Any]:
    ads_dir = Path(ads_output_dir)
    workflow_path = ads_dir / "ads_smart_issue_review_workflow.json"
    payload_path = ads_dir / "ads_intelligence.json"
    qa_path = ads_dir / "ads_intelligence_qa_report.json"
    manifest_path = ads_dir / "ads_intelligence_manifest.json"
    for path in (workflow_path, payload_path, qa_path, manifest_path, Path(contract_path), Path(delivery_events_path)):
        if not path.exists():
            raise ValueError(f"required Alert Policy artifact missing: {path}")

    workflow = _read_json(workflow_path)
    payload = _read_json(payload_path)
    qa = _read_json(qa_path)
    manifest = _read_json(manifest_path)
    contract = _read_json(contract_path)
    ledger = _read_json(delivery_events_path)

    ads_fp = s((payload.get("meta") or {}).get("adsIntelligenceFingerprint"))
    workflow_ads_fp = s(workflow.get("adsIntelligenceFingerprint"))
    registry_fp = s(workflow.get("sourceRegistryFingerprint"))
    if not ads_fp or ads_fp != workflow_ads_fp or ads_fp != registry_fp:
        raise ValueError("Alert Policy must bind to the locked Smart Issue Registry / Ads fingerprint")
    if workflow.get("doesNotModifyAdsIntelligenceFingerprint") is not True:
        raise ValueError("Alert Policy source workflow must preserve Ads fingerprint")
    if ads_fp != s(qa.get("adsIntelligenceFingerprint")) or ads_fp != s(manifest.get("adsIntelligenceFingerprint")):
        raise ValueError("Ads fingerprint mismatch before Alert Policy sidecar")

    artifact = build_alert_policy(workflow, delivery_ledger=ledger, contract=contract, evaluation_at=evaluation_at)
    artifact["adsIntelligenceFingerprint"] = ads_fp
    artifact["adsSmartIssueRegistryFingerprint"] = registry_fp
    artifact["doesNotModifyAdsIntelligenceFingerprint"] = True
    policy_qa = validate_alert_policy(artifact, contract=contract)
    if policy_qa["status"] != "PASS":
        failed = [x["name"] for x in policy_qa["checks"] if x["status"] == "FAIL"]
        raise ValueError(f"Ads Alert Policy QA failed: {failed[:20]}")
    _write_json(ads_dir / "ads_alert_policy.json", artifact)

    qa["smartIssueAlertPolicy"] = policy_qa
    qa["adsSmartIssueAlertPolicyFingerprint"] = artifact["alertPolicyFingerprint"]
    qa["adsIntelligenceFingerprint"] = ads_fp
    files = list(manifest.get("files") or [])
    if "ads_alert_policy.json" not in files:
        files.append("ads_alert_policy.json")
    manifest["files"] = files
    manifest["adsSmartIssueAlertPolicyFingerprint"] = artifact["alertPolicyFingerprint"]
    manifest["adsIntelligenceFingerprint"] = ads_fp
    _write_json(qa_path, qa)
    _write_json(manifest_path, manifest)

    return {
        "status": "PASS",
        "adsIntelligenceFingerprint": ads_fp,
        "adsSmartIssueRegistryFingerprint": registry_fp,
        "adsSmartIssueAlertPolicyFingerprint": artifact["alertPolicyFingerprint"],
        "smartIssueAlertPolicyStatus": policy_qa["status"],
        "eligibleAlertCount": int(artifact.get("eligibleAlertCount") or 0),
        "suppressedIssueCount": int(artifact.get("suppressedIssueCount") or 0),
        "deliveryEnabled": False,
        "automaticDeliveryEnabled": False,
        "artifact": artifact,
    }
