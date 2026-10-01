import tempfile
import unittest
from pathlib import Path

from modules import ui_v2_ads_smart_issue_review_console as console


ADS_FP = "a" * 64
REGISTRY_FP = "b" * 64
WORKFLOW_FP = "c" * 64
LEDGER_FP = "d" * 64


def payload():
    return {
        "destinations": {
            "ads": {
                "meta": {
                    "adsIntelligenceFingerprint": ADS_FP,
                    "adsSmartIssueRegistryFingerprint": REGISTRY_FP,
                },
                "shops": {"SHP_TEST": {}},
            }
        }
    }


def contract():
    return {
        "status": "PREPRODUCTION_UI_CONTRACT",
        "review_console_policy": {
            "enabled": True,
            "input_source": "ads_smart_issue_review_workflow.json",
            "presentation_only": True,
            "read_only": True,
            "command_preview_only": True,
            "explicit_human_review_required": True,
            "available_actions_from_workflow_only": True,
            "selected_shop_only": True,
            "workflow_fingerprint_required": True,
            "registry_fingerprint_match_required": True,
            "operator_ledger_fingerprint_required": True,
            "ui_writes_review_ledger": False,
            "automatic_promotion_enabled": False,
            "automatic_state_transition_enabled": False,
            "automatic_issue_resolution_enabled": False,
            "automatic_alerts_enabled": False,
            "automatic_actions_enabled": False,
            "production_activation_enabled": False,
        },
    }


def workflow(*, nonempty=True):
    queue = []
    issues = []
    if nonempty:
        queue = [{
            "candidateKey": "candidate-1",
            "headline": "ROAS giảm đáng kể",
            "reviewState": "PENDING_REVIEW",
            "availableActions": ["PROMOTE", "DEFER", "DISMISS"],
            "humanDecisionRequired": True,
            "automaticPromotion": False,
        }]
        issues = [{
            "issueId": "issue-1",
            "headline": "Theo dõi hiệu quả Ads",
            "state": "OPEN",
            "availableActions": ["ACKNOWLEDGE", "MONITOR", "RESOLVE"],
            "explicitOperatorEventRequired": True,
            "automaticStateTransition": False,
        }]
    return {
        "status": "READY" if nonempty else "READY_EMPTY",
        "mode": "HUMAN_REVIEW_ONLY",
        "workflowFingerprint": WORKFLOW_FP,
        "sourceRegistryFingerprint": REGISTRY_FP,
        "operatorLedgerFingerprint": LEDGER_FP,
        "candidateActionCount": sum(len(x["availableActions"]) for x in queue),
        "issueActionCount": sum(len(x["availableActions"]) for x in issues),
        "shops": {
            "SHP_TEST": {
                "displayName": "Test Shop",
                "reviewQueue": queue,
                "issues": issues,
                "reviewQueueCount": len(queue),
                "issueCount": len(issues),
            }
        },
        "commandContract": {
            "reviewedByRequired": True,
            "reviewedAtTimezoneRequired": True,
            "expectedLedgerFingerprintRequired": True,
            "ledgerApplyRequiresExplicitFlag": True,
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
        "adsIntelligenceFingerprint": ADS_FP,
        "adsSmartIssueRegistryFingerprint": REGISTRY_FP,
        "doesNotModifyAdsIntelligenceFingerprint": True,
    }


class ReviewConsoleTest(unittest.TestCase):
    def test_nonempty_workflow_is_sanitized_without_business_redefinition(self):
        out = console.validate_review_workflow_for_console(workflow(), payload=payload(), contract=contract())
        self.assertTrue(out["readOnly"])
        self.assertTrue(out["commandPreviewOnly"])
        self.assertEqual(out["reviewQueueCount"], 1)
        self.assertEqual(out["issueCount"], 1)
        self.assertEqual(out["candidateActionCount"], 3)
        self.assertEqual(out["issueActionCount"], 3)

    def test_ready_empty_is_valid(self):
        out = console.validate_review_workflow_for_console(workflow(nonempty=False), payload=payload(), contract=contract())
        self.assertEqual(out["status"], "READY_EMPTY")
        self.assertEqual(out["reviewQueueCount"], 0)
        self.assertEqual(out["issueCount"], 0)

    def test_fingerprint_mismatch_fails_closed(self):
        bad = workflow(); bad["adsIntelligenceFingerprint"] = "x" * 64
        with self.assertRaisesRegex(ValueError, "Ads fingerprint mismatch"):
            console.validate_review_workflow_for_console(bad, payload=payload(), contract=contract())

    def test_unknown_or_state_invalid_action_fails_closed(self):
        bad = workflow(); bad["shops"]["SHP_TEST"]["reviewQueue"][0]["availableActions"] = ["PROMOTE", "AUTO_FIX"]
        bad["candidateActionCount"] = 2
        with self.assertRaisesRegex(ValueError, "invalid candidate review state/actions"):
            console.validate_review_workflow_for_console(bad, payload=payload(), contract=contract())

    def test_automatic_actions_fail_closed(self):
        bad = workflow(); bad["safety"]["automaticActionsEnabled"] = True
        with self.assertRaisesRegex(ValueError, "unsafe operator workflow safety flag"):
            console.validate_review_workflow_for_console(bad, payload=payload(), contract=contract())

    def test_runtime_is_read_only_and_contains_empty_state(self):
        runtime = console.REVIEW_CONSOLE_RUNTIME
        self.assertIn("Smart Issue Review Console", runtime)
        self.assertIn("Command preview", runtime)
        self.assertIn("Console không tự tạo issue và không tự ghi review event.", runtime)
        self.assertNotIn("fetch(", runtime)
        self.assertNotIn("XMLHttpRequest", runtime)
        self.assertNotIn("--apply", runtime)

    def test_artifact_validator_accepts_console_marker(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "command_center_v2_multi_shop_native_template.html"
            p.write_text(console.REVIEW_CONSOLE_STYLE + "\n" + console.REVIEW_CONSOLE_RUNTIME, encoding="utf-8")
            console._validate_review_console_artifact(td)


if __name__ == "__main__":
    unittest.main()
