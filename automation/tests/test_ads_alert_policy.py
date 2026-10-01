import json
import tempfile
import unittest
from pathlib import Path

from modules.ads_alert_policy import (
    bind_ads_alert_policy_artifact,
    build_alert_policy,
    validate_alert_policy,
)


class AdsAlertPolicyTest(unittest.TestCase):
    def _contract(self):
        return {
            "version": "1.0",
            "status": "PREPRODUCTION",
            "alert_policy": {
                "enabled": True,
                "mode": "SMART_ISSUE_ALERT_POLICY_V1",
                "input_source": "ads_smart_issue_review_workflow.json",
                "delivery_event_source": "ads_alert_delivery_events.json",
                "human_promoted_issue_required": True,
                "candidate_alerting_enabled": False,
                "eligible_kinds": ["PROBLEM"],
                "eligible_issue_states": ["OPEN"],
                "suppressed_issue_states": ["ACKNOWLEDGED", "MONITORING", "RESOLVED"],
                "trigger_actions": ["PROMOTE", "REOPEN"],
                "repeated_reminders_enabled": False,
                "severity": {
                    "HIGH": {
                        "priority_tiers": ["HIGH"],
                        "minimum_priority_score": 75,
                        "recommended_channel_classes": ["COMMAND_CENTER", "OPERATOR_NOTIFICATION"],
                        "cooldown_hours": 24,
                    },
                    "MEDIUM": {
                        "priority_tiers": ["MEDIUM"],
                        "minimum_priority_score": 55,
                        "recommended_channel_classes": ["COMMAND_CENTER"],
                        "cooldown_hours": 72,
                    },
                },
                "deduplication": {
                    "alert_key_fields": ["shopId", "issueId", "triggerEventId", "severity"],
                    "delivery_dedupe_fields": ["alertKey", "channelClass"],
                    "one_intent_per_alert_key": True,
                    "delivered_event_suppresses_same_alert_key_channel": True,
                    "only_delivered_events_start_cooldown": True,
                    "cooldown_scope": ["shopId", "issueId", "channelClass"],
                    "reopen_bypasses_previous_epoch_cooldown": True,
                },
                "delivery": {
                    "enabled": False,
                    "automatic_delivery_enabled": False,
                    "provider_binding_enabled": False,
                    "command_center_is_presentation_only": True,
                },
                "automatic_issue_promotion_enabled": False,
                "automatic_issue_transition_enabled": False,
                "automatic_issue_resolution_enabled": False,
                "automatic_actions_enabled": False,
                "causal_claims_enabled": False,
                "production_activation_enabled": False,
            },
        }

    def _delivery_ledger(self, events=None):
        return {"version": "1.0", "ledger_name": "ads_alert_delivery_events", "events": list(events or [])}

    def _event(self, event_id, action, when):
        return {
            "eventId": event_id,
            "action": action,
            "reviewedAt": when,
            "reviewedBy": "operator@test",
            "note": "",
            "issueId": "ads_issue_1" if action != "PROMOTE" else "",
            "candidateKey": "candidate-key-1" if action == "PROMOTE" else "",
        }

    def _issue(self, *, state="OPEN", kind="PROBLEM", tier="HIGH", score=82.0, trigger="PROMOTE"):
        promote = self._event("evt-promote", "PROMOTE", "2026-09-30T10:00:00+07:00")
        history = [promote]
        reopen_count = 0
        if trigger == "REOPEN":
            history.extend([
                self._event("evt-resolve", "RESOLVE", "2026-09-30T11:00:00+07:00"),
                self._event("evt-reopen", "REOPEN", "2026-09-30T12:00:00+07:00"),
            ])
            reopen_count = 1
        elif state == "ACKNOWLEDGED":
            history.append(self._event("evt-ack", "ACKNOWLEDGE", "2026-09-30T11:00:00+07:00"))
        elif state == "MONITORING":
            history.append(self._event("evt-monitor", "MONITOR", "2026-09-30T11:00:00+07:00"))
        elif state == "RESOLVED":
            history.append(self._event("evt-resolve", "RESOLVE", "2026-09-30T11:00:00+07:00"))
        return {
            "issueId": "ads_issue_1",
            "issueKey": "candidate-key-1",
            "sourceCandidateId": "ads_sic_1",
            "shopId": "S1",
            "candidateType": "RISK" if kind == "PROBLEM" else "OPPORTUNITY",
            "kind": kind,
            "productId": "P1",
            "productName": "Găng tay Air S5 Plus",
            "productSku": "GL005",
            "scope": "day",
            "contextSignature": ["PLATFORM|shopee|DOUBLE_DAY_MEGA_SALE|1|0"],
            "headline": "Hiệu quả Ads giảm" if kind == "PROBLEM" else "Hiệu quả Ads cải thiện",
            "summary": "Evidence đã qua human review.",
            "reviewFocus": "Kiểm tra CPC, CVR và AOV.",
            "priorityTier": tier,
            "priorityScoreAtPromotion": score,
            "coverageEndAtPromotion": "2026-09-30",
            "latestEvidenceDateAtPromotion": "2026-09-30",
            "state": state,
            "openedAt": "2026-09-30T10:00:00+07:00",
            "openedBy": "operator@test",
            "lastUpdatedAt": history[-1]["reviewedAt"],
            "lastUpdatedBy": "operator@test",
            "reopenCount": reopen_count,
            "humanPromoted": True,
            "source": "EXPLICIT_HUMAN_REVIEW_LEDGER",
            "eventHistory": history,
            "operatorNotes": [],
            "evidenceOnly": True,
            "causalClaim": False,
            "automaticAlertEligible": False,
            "automaticActionEligible": False,
            "availableActions": ["ACKNOWLEDGE", "MONITOR", "RESOLVE"] if state == "OPEN" else [],
            "explicitOperatorEventRequired": True,
            "automaticStateTransition": False,
        }

    def _workflow(self, issues=None):
        issues = list(issues or [])
        return {
            "status": "READY" if issues else "READY_EMPTY",
            "mode": "SMART_ISSUE_OPERATOR_REVIEW_WORKFLOW_V1",
            "sourceRegistryFingerprint": "ads-fp",
            "sourceRegistryReviewLedgerFingerprint": "registry-ledger-fp",
            "operatorLedgerFingerprint": "operator-ledger-fp",
            "candidateActionCount": 0,
            "issueActionCount": len(issues) * 3,
            "workflowFingerprint": "workflow-fp",
            "adsIntelligenceFingerprint": "ads-fp",
            "adsSmartIssueRegistryFingerprint": "ads-fp",
            "doesNotModifyAdsIntelligenceFingerprint": True,
            "shops": {
                "S1": {
                    "displayName": "SYT+",
                    "reviewQueue": [],
                    "issues": issues,
                    "reviewQueueCount": 0,
                    "issueCount": len(issues),
                }
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

    def test_empty_workflow_is_ready_empty(self):
        artifact = build_alert_policy(
            self._workflow(), delivery_ledger=self._delivery_ledger(), contract=self._contract()
        )
        self.assertEqual(artifact["status"], "READY_EMPTY")
        self.assertEqual(artifact["eligibleAlertCount"], 0)
        self.assertEqual(validate_alert_policy(artifact, contract=self._contract())["status"], "PASS")

    def test_high_problem_open_creates_high_alert_intent(self):
        artifact = build_alert_policy(
            self._workflow([self._issue()]), delivery_ledger=self._delivery_ledger(), contract=self._contract()
        )
        alert = artifact["shops"]["S1"]["eligibleAlerts"][0]
        self.assertEqual(alert["severity"], "HIGH")
        self.assertEqual(alert["recommendedChannelClasses"], ["COMMAND_CENTER", "OPERATOR_NOTIFICATION"])
        self.assertTrue(alert["policyEligible"])
        self.assertFalse(alert["deliveryEnabled"])
        self.assertEqual(alert["triggerAction"], "PROMOTE")

    def test_medium_problem_routes_to_command_center_only(self):
        artifact = build_alert_policy(
            self._workflow([self._issue(tier="MEDIUM", score=61)]),
            delivery_ledger=self._delivery_ledger(), contract=self._contract()
        )
        alert = artifact["shops"]["S1"]["eligibleAlerts"][0]
        self.assertEqual(alert["severity"], "MEDIUM")
        self.assertEqual(alert["recommendedChannelClasses"], ["COMMAND_CENTER"])

    def test_opportunity_is_non_interruptive(self):
        artifact = build_alert_policy(
            self._workflow([self._issue(kind="OPPORTUNITY")]),
            delivery_ledger=self._delivery_ledger(), contract=self._contract()
        )
        self.assertEqual(artifact["eligibleAlertCount"], 0)
        row = artifact["shops"]["S1"]["suppressedIssues"][0]
        self.assertEqual(row["suppressionReason"], "NON_INTERRUPTIVE_OPPORTUNITY")

    def test_ack_monitor_resolved_are_suppressed(self):
        for state in ("ACKNOWLEDGED", "MONITORING", "RESOLVED"):
            artifact = build_alert_policy(
                self._workflow([self._issue(state=state)]),
                delivery_ledger=self._delivery_ledger(), contract=self._contract()
            )
            self.assertEqual(artifact["eligibleAlertCount"], 0)
            self.assertEqual(
                artifact["shops"]["S1"]["suppressedIssues"][0]["suppressionReason"],
                "ISSUE_STATE_SUPPRESSED",
            )

    def test_same_alert_delivery_suppresses_only_external_channel_retry(self):
        first = build_alert_policy(
            self._workflow([self._issue()]), delivery_ledger=self._delivery_ledger(), contract=self._contract()
        )
        alert_key = first["shops"]["S1"]["eligibleAlerts"][0]["alertKey"]
        ledger = self._delivery_ledger([{
            "eventId": "delivery-1",
            "alertKey": alert_key,
            "shopId": "S1",
            "issueId": "ads_issue_1",
            "channelClass": "OPERATOR_NOTIFICATION",
            "status": "DELIVERED",
            "deliveredAt": "2026-09-30T10:30:00+07:00",
        }])
        artifact = build_alert_policy(
            self._workflow([self._issue()]), delivery_ledger=ledger, contract=self._contract(),
            evaluation_at="2026-09-30T12:00:00+07:00",
        )
        decisions = {x["channelClass"]: x for x in artifact["shops"]["S1"]["eligibleAlerts"][0]["channelDecisions"]}
        self.assertEqual(decisions["COMMAND_CENTER"]["status"], "PRESENTATION_ONLY")
        self.assertEqual(decisions["OPERATOR_NOTIFICATION"]["suppressionReason"], "ALREADY_DELIVERED_SAME_ALERT_KEY")

    def test_prior_delivery_starts_cooldown_for_new_external_epoch(self):
        ledger = self._delivery_ledger([{
            "eventId": "delivery-0",
            "alertKey": "older-alert-key",
            "shopId": "S1",
            "issueId": "ads_issue_1",
            "channelClass": "OPERATOR_NOTIFICATION",
            "status": "DELIVERED",
            "deliveredAt": "2026-09-30T11:00:00+07:00",
        }])
        artifact = build_alert_policy(
            self._workflow([self._issue()]), delivery_ledger=ledger, contract=self._contract(),
            evaluation_at="2026-09-30T12:00:00+07:00",
        )
        decisions = {x["channelClass"]: x for x in artifact["shops"]["S1"]["eligibleAlerts"][0]["channelDecisions"]}
        self.assertEqual(decisions["OPERATOR_NOTIFICATION"]["suppressionReason"], "COOLDOWN_ACTIVE")
        self.assertFalse(decisions["OPERATOR_NOTIFICATION"]["policyEligible"])

    def test_reopen_bypasses_previous_epoch_cooldown(self):
        ledger = self._delivery_ledger([{
            "eventId": "delivery-old",
            "alertKey": "older-alert-key",
            "shopId": "S1",
            "issueId": "ads_issue_1",
            "channelClass": "OPERATOR_NOTIFICATION",
            "status": "DELIVERED",
            "deliveredAt": "2026-09-30T11:30:00+07:00",
        }])
        artifact = build_alert_policy(
            self._workflow([self._issue(trigger="REOPEN")]), delivery_ledger=ledger,
            contract=self._contract(), evaluation_at="2026-09-30T12:30:00+07:00",
        )
        alert = artifact["shops"]["S1"]["eligibleAlerts"][0]
        decisions = {x["channelClass"]: x for x in alert["channelDecisions"]}
        self.assertEqual(alert["triggerAction"], "REOPEN")
        self.assertEqual(decisions["OPERATOR_NOTIFICATION"]["status"], "DELIVERY_DISABLED")
        self.assertEqual(decisions["OPERATOR_NOTIFICATION"]["suppressionReason"], "")

    def test_non_human_promoted_issue_fails_closed(self):
        issue = self._issue()
        issue["humanPromoted"] = False
        with self.assertRaises(ValueError):
            build_alert_policy(
                self._workflow([issue]), delivery_ledger=self._delivery_ledger(), contract=self._contract()
            )

    def test_sidecar_binding_preserves_locked_ads_fingerprint(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ads = root / "ads"
            ads.mkdir()
            workflow = self._workflow()
            (ads / "ads_smart_issue_review_workflow.json").write_text(json.dumps(workflow), encoding="utf-8")
            (ads / "ads_intelligence.json").write_text(json.dumps({
                "meta": {"adsIntelligenceFingerprint": "ads-fp", "adsSmartIssueRegistryFingerprint": "ads-fp"}
            }), encoding="utf-8")
            (ads / "ads_intelligence_qa_report.json").write_text(json.dumps({
                "status": "PASS", "adsIntelligenceFingerprint": "ads-fp"
            }), encoding="utf-8")
            (ads / "ads_intelligence_manifest.json").write_text(json.dumps({
                "files": [], "adsIntelligenceFingerprint": "ads-fp"
            }), encoding="utf-8")
            contract_path = root / "contract.json"
            ledger_path = root / "delivery.json"
            contract_path.write_text(json.dumps(self._contract()), encoding="utf-8")
            ledger_path.write_text(json.dumps(self._delivery_ledger()), encoding="utf-8")

            result = bind_ads_alert_policy_artifact(
                ads_output_dir=ads,
                contract_path=contract_path,
                delivery_events_path=ledger_path,
            )
            self.assertEqual(result["adsIntelligenceFingerprint"], "ads-fp")
            self.assertFalse(result["deliveryEnabled"])
            artifact = json.loads((ads / "ads_alert_policy.json").read_text(encoding="utf-8"))
            self.assertTrue(artifact["doesNotModifyAdsIntelligenceFingerprint"])
            self.assertEqual(artifact["adsIntelligenceFingerprint"], "ads-fp")
            manifest = json.loads((ads / "ads_intelligence_manifest.json").read_text(encoding="utf-8"))
            self.assertIn("ads_alert_policy.json", manifest["files"])


if __name__ == "__main__":
    unittest.main()
