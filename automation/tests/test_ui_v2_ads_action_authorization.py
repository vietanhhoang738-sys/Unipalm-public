import json
import tempfile
import unittest
from pathlib import Path

from modules.ui_v2_ads_action_authorization import (
    ACTION_AUTHORIZATION_RUNTIME,
    ADS_ACTION_AUTHORIZATION_UI_VERSION,
    _validate_action_authorization_artifact,
    load_action_authorization_for_ui,
    validate_action_authorization_for_ui,
)


class ActionAuthorizationUiTest(unittest.TestCase):
    def _contract(self):
        return {
            "version": "1.0",
            "status": "PREPRODUCTION_UI_CONTRACT",
            "layer_name": "ads_action_authorization_ui_v1",
            "action_authorization_ui": {
                "enabled": True,
                "input_source": "ads_action_authorization.json",
                "presentation_only": True,
                "read_only": True,
                "selected_shop_only": True,
                "action_authorization_fingerprint_required": True,
                "review_workflow_fingerprint_match_required": True,
                "alert_policy_fingerprint_match_required": True,
                "registry_fingerprint_match_required": True,
                "ads_intelligence_fingerprint_match_required": True,
                "authorization_ledger_fingerprint_required": True,
                "issue_epoch_binding_required": True,
                "proposal_fingerprint_required": True,
                "attributed_driver_required_for_targeted_review": True,
                "authenticated_executor_bound": False,
                "execution_enabled": False,
                "ui_execution_enabled": False,
                "provider_binding_enabled": False,
                "platform_mutation_allowed": False,
                "automatic_execution_enabled": False,
                "automatic_issue_transition_enabled": False,
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

    def _alert(self):
        return {
            "alertPolicyFingerprint": "alert-fp",
            "shops": {"S1": {"displayName": "SYT+"}},
        }

    def _proposal(self, action_type="VALIDATE_EVIDENCE_BEFORE_CHANGE", auth_state="PENDING_AUTHORIZATION"):
        targeted = action_type != "VALIDATE_EVIDENCE_BEFORE_CHANGE"
        available = ["APPROVE", "REJECT"] if auth_state == "PENDING_AUTHORIZATION" else (["REVOKE"] if auth_state == "APPROVED_REVIEW_ONLY" else [])
        status = {
            "PENDING_AUTHORIZATION": "BLOCKED_HUMAN_AUTHORIZATION_REQUIRED",
            "APPROVED_REVIEW_ONLY": "BLOCKED_AUTHENTICATED_EXECUTOR_NOT_BOUND",
            "REJECTED": "BLOCKED_OPERATOR_REJECTED",
            "REVOKED": "BLOCKED_AUTHORIZATION_REVOKED",
        }[auth_state]
        return {
            "proposalId": "ads_action_1" + ("t" if targeted else ""),
            "proposalFingerprint": "proposal-fp" + ("t" if targeted else ""),
            "shopId": "S1",
            "issueId": "ads_issue_1",
            "issueEpoch": "evt-promote",
            "issueState": "OPEN",
            "actionType": action_type,
            "title": "Review option",
            "whyRelevant": "Evidence cần được kiểm tra trước khi thay đổi.",
            "prerequisites": ["Check lineage"],
            "kpisToMonitor": ["roas"],
            "verificationChecks": ["Refresh evidence"],
            "stopOrReversalChecks": ["Stop if evidence changes"],
            "uncertainty": ["CAUSALITY_NOT_ESTABLISHED"],
            "status": "REVIEW_OPTION",
            "executionMode": "HUMAN_REVIEW_ONLY",
            "requiresHumanReview": True,
            "prescriptiveRecommendation": False,
            "platformMutationAllowed": False,
            "automaticExecutionEligible": False,
            "automaticAlertEligible": False,
            "causalClaimEligible": False,
            "attributionStatus": "ATTRIBUTED" if targeted else "NOT_AVAILABLE",
            "topDriver": {"metric": "placedAov", "label": "AOV", "contributionValue": -1.0} if targeted else {},
            "authorization": {
                "state": auth_state,
                "availableActions": available,
            },
            "executionBoundary": {
                "status": status,
                "authenticatedExecutorRequired": True,
                "authenticatedExecutorBound": False,
                "executionEnabled": False,
                "dryRunOnly": True,
                "providerBindingEnabled": False,
                "platformMutationAllowed": False,
                "productionActivationEnabled": False,
                "authorizationPermitIssued": False,
                "idempotencyKey": "ads_exec_1",
            },
        }

    def _artifact(self, proposals=None):
        proposals = list(proposals or [])
        counts = {"PENDING_AUTHORIZATION": 0, "APPROVED_REVIEW_ONLY": 0, "REJECTED": 0, "REVOKED": 0}
        for p in proposals:
            counts[p["authorization"]["state"]] += 1
        return {
            "status": "READY" if proposals else "READY_EMPTY",
            "mode": "SMART_ISSUE_ACTION_AUTHORIZATION_V1",
            "actionAuthorizationFingerprint": "action-auth-fp",
            "authorizationLedgerFingerprint": "auth-ledger-fp",
            "sourceReviewWorkflowFingerprint": "workflow-fp",
            "sourceAlertPolicyFingerprint": "alert-fp",
            "sourceRegistryFingerprint": "ads-fp",
            "sourceOperatorLedgerFingerprint": "operator-ledger-fp",
            "adsIntelligenceFingerprint": "ads-fp",
            "adsSmartIssueRegistryFingerprint": "ads-fp",
            "doesNotModifyAdsIntelligenceFingerprint": True,
            "proposalCount": len(proposals),
            "suppressedIssueCount": 0,
            "authorizationStateCounts": counts,
            "shops": {
                "S1": {
                    "displayName": "SYT+",
                    "proposals": proposals,
                    "proposalCount": len(proposals),
                    "suppressedIssues": [],
                    "suppressedIssueCount": 0,
                }
            },
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

    def test_empty_artifact_is_valid_and_read_only(self):
        view = validate_action_authorization_for_ui(
            self._artifact(), payload=self._payload(), review_workflow=self._workflow(),
            alert_policy=self._alert(), contract=self._contract(),
        )
        self.assertEqual(view["status"], "READY_EMPTY")
        self.assertEqual(view["proposalCount"], 0)
        self.assertTrue(view["readOnly"])
        self.assertFalse(view["executionBoundary"]["executionEnabled"])

    def test_targeted_proposal_requires_attribution(self):
        proposal = self._proposal("REVIEW_AOV_PRICE_PROMOTION_MIX")
        view = validate_action_authorization_for_ui(
            self._artifact([proposal]), payload=self._payload(), review_workflow=self._workflow(),
            alert_policy=self._alert(), contract=self._contract(),
        )
        self.assertEqual(view["proposalCount"], 1)
        proposal["attributionStatus"] = "ASSOCIATION_ONLY"
        with self.assertRaises(ValueError):
            validate_action_authorization_for_ui(
                self._artifact([proposal]), payload=self._payload(), review_workflow=self._workflow(),
                alert_policy=self._alert(), contract=self._contract(),
            )

    def test_approved_review_only_still_cannot_execute(self):
        proposal = self._proposal(auth_state="APPROVED_REVIEW_ONLY")
        view = validate_action_authorization_for_ui(
            self._artifact([proposal]), payload=self._payload(), review_workflow=self._workflow(),
            alert_policy=self._alert(), contract=self._contract(),
        )
        current = view["shops"]["S1"]["proposals"][0]
        self.assertEqual(current["authorization"]["state"], "APPROVED_REVIEW_ONLY")
        self.assertFalse(current["executionBoundary"]["executionEnabled"])
        self.assertFalse(current["executionBoundary"]["authorizationPermitIssued"])

    def test_lineage_mismatch_fails_closed(self):
        artifact = self._artifact()
        artifact["sourceAlertPolicyFingerprint"] = "wrong"
        with self.assertRaises(ValueError):
            validate_action_authorization_for_ui(
                artifact, payload=self._payload(), review_workflow=self._workflow(),
                alert_policy=self._alert(), contract=self._contract(),
            )

    def test_execution_enable_fails_closed(self):
        artifact = self._artifact()
        artifact["executionBoundary"]["executionEnabled"] = True
        with self.assertRaises(ValueError):
            validate_action_authorization_for_ui(
                artifact, payload=self._payload(), review_workflow=self._workflow(),
                alert_policy=self._alert(), contract=self._contract(),
            )

    def test_loader_reads_sidecar_and_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact_path = root / "ads_action_authorization.json"
            contract_path = root / "contract.json"
            artifact_path.write_text(json.dumps(self._artifact()), encoding="utf-8")
            contract_path.write_text(json.dumps(self._contract()), encoding="utf-8")
            view = load_action_authorization_for_ui(
                action_authorization_path=artifact_path,
                payload=self._payload(), review_workflow=self._workflow(),
                alert_policy=self._alert(), contract_path=contract_path,
            )
            self.assertEqual(view["actionAuthorizationFingerprint"], "action-auth-fp")

    def test_runtime_has_no_execution_or_raw_signal_primitives(self):
        self.assertIn(ADS_ACTION_AUTHORIZATION_UI_VERSION, ACTION_AUTHORIZATION_RUNTIME)
        for token in ("fetch(", "XMLHttpRequest", "--apply", "executeAction(", "runAction(", "sendAction(", "const rawSignals=snap.signals||[]"):
            self.assertNotIn(token, ACTION_AUTHORIZATION_RUNTIME)

    def test_artifact_validator(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "command_center_v2_multi_shop_native_template.html"
            path.write_text("\n".join([
                ADS_ACTION_AUTHORIZATION_UI_VERSION,
                "Recommendation / Action Authorization", "READ ONLY", "EXECUTION OFF",
                "HUMAN APPROVAL REQUIRED", "APPROVE ở v1 vẫn không cấp quyền execution",
                "smartIssueActionAuthorization",
                "Chưa có action proposal nào cần authorization ở shop này.",
                "UI không ghi authorization ledger và không gọi executor",
            ]), encoding="utf-8")
            _validate_action_authorization_artifact(tmp)


if __name__ == "__main__":
    unittest.main()
