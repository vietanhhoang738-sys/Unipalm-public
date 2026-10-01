import json
import tempfile
import unittest
from pathlib import Path

from modules.ui_v2_ads_alert_policy import (
    ALERT_POLICY_RUNTIME,
    ADS_SMART_ISSUE_ALERT_POLICY_UI_VERSION,
    _validate_alert_policy_artifact,
    load_alert_policy_for_ui,
    validate_alert_policy_for_ui,
)


class AlertPolicyUiTest(unittest.TestCase):
    def _contract(self):
        return {
            "version": "1.0",
            "status": "PREPRODUCTION_UI_CONTRACT",
            "alert_policy_ui": {
                "enabled": True,
                "input_source": "ads_alert_policy.json",
                "presentation_only": True,
                "read_only": True,
                "selected_shop_only": True,
                "alert_policy_fingerprint_required": True,
                "review_workflow_fingerprint_match_required": True,
                "registry_fingerprint_match_required": True,
                "operator_ledger_fingerprint_match_required": True,
                "delivery_ledger_fingerprint_required": True,
                "provider_binding_enabled": False,
                "ui_delivery_enabled": False,
                "automatic_delivery_enabled": False,
                "automatic_promotion_enabled": False,
                "automatic_state_transition_enabled": False,
                "automatic_issue_resolution_enabled": False,
                "automatic_actions_enabled": False,
                "causal_claims_enabled": False,
                "production_activation_enabled": False,
                "raw_ads_signal_binding_enabled": False,
            },
        }

    def _payload(self):
        return {
            "destinations": {
                "ads": {
                    "meta": {
                        "adsIntelligenceFingerprint": "ads-fp",
                        "adsSmartIssueRegistryFingerprint": "ads-fp",
                    },
                    "shops": {"S1": {}},
                }
            }
        }

    def _workflow(self):
        return {
            "workflowFingerprint": "workflow-fp",
            "sourceRegistryFingerprint": "ads-fp",
            "operatorLedgerFingerprint": "operator-ledger-fp",
            "shops": {"S1": {"displayName": "SYT+"}},
        }

    def _policy(self, alerts=None, suppressed=None):
        alerts = list(alerts or [])
        suppressed = list(suppressed or [])
        high = len([x for x in alerts if x.get("severity") == "HIGH"])
        medium = len([x for x in alerts if x.get("severity") == "MEDIUM"])
        return {
            "status": "READY" if alerts else "READY_EMPTY",
            "mode": "SMART_ISSUE_ALERT_POLICY_V1",
            "alertPolicyFingerprint": "alert-fp",
            "sourceReviewWorkflowFingerprint": "workflow-fp",
            "sourceRegistryFingerprint": "ads-fp",
            "sourceOperatorLedgerFingerprint": "operator-ledger-fp",
            "deliveryLedgerFingerprint": "delivery-ledger-fp",
            "adsIntelligenceFingerprint": "ads-fp",
            "adsSmartIssueRegistryFingerprint": "ads-fp",
            "doesNotModifyAdsIntelligenceFingerprint": True,
            "eligibleAlertCount": len(alerts),
            "suppressedIssueCount": len(suppressed),
            "severityCounts": {"HIGH": high, "MEDIUM": medium},
            "shops": {
                "S1": {
                    "displayName": "SYT+",
                    "eligibleAlerts": alerts,
                    "suppressedIssues": suppressed,
                    "eligibleAlertCount": len(alerts),
                    "suppressedIssueCount": len(suppressed),
                }
            },
            "routingPolicy": {},
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

    def _alert(self, severity="HIGH"):
        return {
            "alertId": "ads_alert_1",
            "alertKey": "alert-key-1",
            "shopId": "S1",
            "issueId": "ads_issue_1",
            "issueKey": "candidate-key-1",
            "kind": "PROBLEM",
            "productId": "P1",
            "productName": "Găng tay Air S5 Plus",
            "productSku": "GL005",
            "scope": "day",
            "headline": "Hiệu quả Ads giảm",
            "summary": "Evidence đã qua human review.",
            "severity": severity,
            "priorityTier": severity,
            "priorityScoreAtPromotion": 82 if severity == "HIGH" else 61,
            "triggerAction": "PROMOTE",
            "triggerEventId": "evt-promote",
            "triggeredAt": "2026-09-30T10:00:00+07:00",
            "triggeredBy": "operator@test",
            "recommendedChannelClasses": ["COMMAND_CENTER", "OPERATOR_NOTIFICATION"] if severity == "HIGH" else ["COMMAND_CENTER"],
            "channelDecisions": [],
            "policyEligible": True,
            "deliveryEnabled": False,
            "automaticDelivery": False,
            "evidenceOnly": True,
            "causalClaim": False,
        }

    def test_empty_alert_policy_is_valid(self):
        view = validate_alert_policy_for_ui(
            self._policy(), payload=self._payload(), review_workflow=self._workflow(), contract=self._contract()
        )
        self.assertEqual(view["status"], "READY_EMPTY")
        self.assertEqual(view["eligibleAlertCount"], 0)
        self.assertTrue(view["readOnly"])

    def test_nonempty_alert_policy_is_sanitized(self):
        view = validate_alert_policy_for_ui(
            self._policy([self._alert()]), payload=self._payload(), review_workflow=self._workflow(), contract=self._contract()
        )
        self.assertEqual(view["eligibleAlertCount"], 1)
        self.assertEqual(view["severityCounts"]["HIGH"], 1)
        self.assertFalse(view["delivery"]["enabled"])

    def test_lineage_mismatch_fails_closed(self):
        policy = self._policy()
        policy["sourceReviewWorkflowFingerprint"] = "wrong"
        with self.assertRaises(ValueError):
            validate_alert_policy_for_ui(
                policy, payload=self._payload(), review_workflow=self._workflow(), contract=self._contract()
            )

    def test_delivery_enable_fails_closed(self):
        policy = self._policy()
        policy["delivery"]["enabled"] = True
        with self.assertRaises(ValueError):
            validate_alert_policy_for_ui(
                policy, payload=self._payload(), review_workflow=self._workflow(), contract=self._contract()
            )

    def test_opportunity_in_eligible_alerts_fails_closed(self):
        alert = self._alert()
        alert["kind"] = "OPPORTUNITY"
        with self.assertRaises(ValueError):
            validate_alert_policy_for_ui(
                self._policy([alert]), payload=self._payload(), review_workflow=self._workflow(), contract=self._contract()
            )

    def test_loader_reads_sidecar_and_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            policy_path = root / "ads_alert_policy.json"
            contract_path = root / "contract.json"
            policy_path.write_text(json.dumps(self._policy()), encoding="utf-8")
            contract_path.write_text(json.dumps(self._contract()), encoding="utf-8")
            view = load_alert_policy_for_ui(
                alert_policy_path=policy_path,
                payload=self._payload(),
                review_workflow=self._workflow(),
                contract_path=contract_path,
            )
            self.assertEqual(view["alertPolicyFingerprint"], "alert-fp")

    def test_runtime_has_no_delivery_or_raw_signal_primitives(self):
        self.assertIn(ADS_SMART_ISSUE_ALERT_POLICY_UI_VERSION, ALERT_POLICY_RUNTIME)
        for token in ("fetch(", "XMLHttpRequest", "--apply", "sendNotification(", "sendAlert(", "const rawSignals=snap.signals||[]"):
            self.assertNotIn(token, ALERT_POLICY_RUNTIME)

    def test_artifact_validator(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "command_center_v2_multi_shop_native_template.html"
            path.write_text(
                "\n".join([
                    ADS_SMART_ISSUE_ALERT_POLICY_UI_VERSION,
                    "Alert Policy", "DELIVERY OFF", "HUMAN-PROMOTED ONLY",
                    "Không có Smart Issue nào đủ điều kiện cảnh báo ở shop này.",
                    "smartIssueAlertPolicy", "Notification delivery/provider binding chưa được bật",
                ]), encoding="utf-8"
            )
            _validate_alert_policy_artifact(tmp)


if __name__ == "__main__":
    unittest.main()
