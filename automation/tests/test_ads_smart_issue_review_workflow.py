import json
import tempfile
import unittest
from pathlib import Path

from modules.ads_smart_issue_review_workflow import (
    append_review_event,
    bind_ads_smart_issue_review_workflow_artifact,
    build_operator_review_workflow,
    build_review_event_command,
    operator_ledger_fingerprint,
    validate_operator_review_workflow,
)


class AdsSmartIssueReviewWorkflowTest(unittest.TestCase):
    def _policy(self):
        return {
            "enabled": True,
            "mode": "SMART_ISSUE_OPERATOR_REVIEW_WORKFLOW_V1",
            "input_source": "ads_smart_issue_registry.json",
            "review_ledger_source": "ads_smart_issue_review_events.json",
            "append_only": True,
            "explicit_human_review_required": True,
            "expected_ledger_fingerprint_required": True,
            "deterministic_event_id": True,
            "reviewed_at_timezone_required": True,
            "reviewed_by_required": True,
            "ledger_apply_requires_explicit_flag": True,
            "candidate_actions_by_review_state": {
                "PENDING_REVIEW": ["PROMOTE", "DEFER", "DISMISS"],
                "DEFERRED": ["PROMOTE", "DEFER", "DISMISS"],
                "DISMISSED": ["PROMOTE", "DEFER", "DISMISS"],
                "REOPEN_REVIEW_REQUIRED": ["REOPEN"],
            },
            "issue_actions_by_state": {
                "OPEN": ["ACKNOWLEDGE", "MONITOR", "RESOLVE"],
                "ACKNOWLEDGED": ["MONITOR", "RESOLVE"],
                "MONITORING": ["MONITOR", "RESOLVE"],
                "RESOLVED": ["REOPEN"],
            },
            "automatic_promotion_enabled": False,
            "automatic_state_transition_enabled": False,
            "automatic_issue_resolution_enabled": False,
            "automatic_alerts_enabled": False,
            "automatic_actions_enabled": False,
            "causal_claims_enabled": False,
        }

    def _contract(self):
        return {"operator_review_workflow_policy": self._policy()}

    def _ledger(self, events=None):
        return {"version": "1.0", "ledger_name": "ads_smart_issue_review_events", "events": list(events or [])}

    def _candidate_row(self, *, state="PENDING_REVIEW", key="candidate-key-1", linked_issue_id=""):
        return {
            "shopId": "S1",
            "candidateId": "ads_sic_1",
            "candidateKey": key,
            "candidateType": "RISK",
            "kind": "PROBLEM",
            "productId": "P1",
            "productName": "Găng tay Air S5 Plus",
            "productSku": "GL005",
            "scope": "day",
            "contextSignature": ["PLATFORM|shopee|DOUBLE_DAY_MEGA_SALE|1|0"],
            "headline": "Hiệu quả Ads giảm",
            "summary": "ROAS giảm trong kỳ tương đồng.",
            "reviewFocus": "Kiểm tra CPC, CVR và AOV.",
            "priorityTier": "HIGH",
            "priorityScore": 82.0,
            "coverageEnd": "2026-09-27",
            "latestEvidenceDate": "2026-09-27",
            "reviewState": state,
            "linkedIssueId": linked_issue_id,
            "linkedIssueState": "RESOLVED" if linked_issue_id else "",
            "explicitHumanReviewRequired": True,
            "automaticPromotion": False,
        }

    def _issue(self, *, state="OPEN", issue_id="ads_issue_1"):
        return {
            "issueId": issue_id,
            "issueKey": "candidate-key-1",
            "shopId": "S1",
            "kind": "PROBLEM",
            "productId": "P1",
            "productName": "Găng tay Air S5 Plus",
            "scope": "day",
            "state": state,
            "humanPromoted": True,
            "evidenceOnly": True,
            "causalClaim": False,
            "automaticAlertEligible": False,
            "automaticActionEligible": False,
        }

    def _registry(self, *, queue=None, issues=None):
        return {
            "status": "PREPRODUCTION_REGISTRY",
            "reviewLedgerFingerprint": "registry-ledger-fp",
            "adsSmartIssueRegistryFingerprint": "registry-fp",
            "shops": {
                "S1": {
                    "displayName": "SYT+",
                    "reviewQueue": list(queue or []),
                    "issues": list(issues or []),
                    "lineage": {},
                }
            },
            "safety": {
                "explicitHumanReviewRequired": True,
                "automaticPromotionEnabled": False,
            },
        }

    def test_pending_candidate_exposes_only_human_review_actions(self):
        workflow = build_operator_review_workflow(
            self._registry(queue=[self._candidate_row()]),
            review_ledger=self._ledger(),
            contract=self._contract(),
        )
        row = workflow["shops"]["S1"]["reviewQueue"][0]
        self.assertEqual(row["availableActions"], ["PROMOTE", "DEFER", "DISMISS"])
        self.assertTrue(row["humanDecisionRequired"])
        self.assertFalse(row["automaticPromotion"])
        self.assertEqual(validate_operator_review_workflow(workflow, contract=self._contract())["status"], "PASS")

    def test_issue_state_exposes_valid_transition_actions_only(self):
        expected = {
            "OPEN": ["ACKNOWLEDGE", "MONITOR", "RESOLVE"],
            "ACKNOWLEDGED": ["MONITOR", "RESOLVE"],
            "MONITORING": ["MONITOR", "RESOLVE"],
            "RESOLVED": ["REOPEN"],
        }
        for state, actions in expected.items():
            workflow = build_operator_review_workflow(
                self._registry(issues=[self._issue(state=state)]),
                review_ledger=self._ledger(),
                contract=self._contract(),
            )
            self.assertEqual(workflow["shops"]["S1"]["issues"][0]["availableActions"], actions)

    def test_promote_command_captures_candidate_snapshot_and_is_deterministic(self):
        workflow = build_operator_review_workflow(
            self._registry(queue=[self._candidate_row()]),
            review_ledger=self._ledger(),
            contract=self._contract(),
        )
        kwargs = dict(
            action="PROMOTE",
            candidate_key="candidate-key-1",
            reviewed_by="operator@test",
            reviewed_at="2026-09-30T12:30:00+07:00",
            note="Đã kiểm tra evidence.",
        )
        first = build_review_event_command(workflow, **kwargs)
        second = build_review_event_command(workflow, **kwargs)
        self.assertEqual(first["event"]["eventId"], second["event"]["eventId"])
        self.assertEqual(first["event"]["candidateSnapshot"]["candidateKey"], "candidate-key-1")
        self.assertEqual(first["event"]["action"], "PROMOTE")
        self.assertTrue(first["applyRequiresExplicitFlag"])

    def test_reopen_review_candidate_builds_issue_transition_event(self):
        workflow = build_operator_review_workflow(
            self._registry(queue=[self._candidate_row(state="REOPEN_REVIEW_REQUIRED", linked_issue_id="ads_issue_1")], issues=[self._issue(state="RESOLVED")]),
            review_ledger=self._ledger(),
            contract=self._contract(),
        )
        command = build_review_event_command(
            workflow,
            action="REOPEN",
            candidate_key="candidate-key-1",
            reviewed_by="operator@test",
            reviewed_at="2026-09-30T12:30:00+07:00",
        )
        self.assertEqual(command["event"]["issueId"], "ads_issue_1")
        self.assertNotIn("candidateKey", command["event"])

    def test_invalid_action_and_timezone_fail_closed(self):
        workflow = build_operator_review_workflow(
            self._registry(queue=[self._candidate_row()]),
            review_ledger=self._ledger(),
            contract=self._contract(),
        )
        with self.assertRaises(ValueError):
            build_review_event_command(
                workflow,
                action="RESOLVE",
                candidate_key="candidate-key-1",
                reviewed_by="operator@test",
                reviewed_at="2026-09-30T12:30:00+07:00",
            )
        with self.assertRaises(ValueError):
            build_review_event_command(
                workflow,
                action="PROMOTE",
                candidate_key="candidate-key-1",
                reviewed_by="operator@test",
                reviewed_at="2026-09-30T12:30:00",
            )

    def test_dry_run_does_not_write_and_apply_is_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.json"
            ledger = self._ledger()
            path.write_text(json.dumps(ledger), encoding="utf-8")
            workflow = build_operator_review_workflow(
                self._registry(queue=[self._candidate_row()]),
                review_ledger=ledger,
                contract=self._contract(),
            )
            command = build_review_event_command(
                workflow,
                action="DEFER",
                candidate_key="candidate-key-1",
                reviewed_by="operator@test",
                reviewed_at="2026-09-30T12:30:00+07:00",
            )
            dry = append_review_event(review_ledger_path=path, command=command, apply=False)
            self.assertEqual(dry["status"], "DRY_RUN")
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["events"], [])
            applied = append_review_event(review_ledger_path=path, command=command, apply=True)
            self.assertEqual(applied["status"], "APPLIED")
            self.assertEqual(len(json.loads(path.read_text(encoding="utf-8"))["events"]), 1)

    def test_stale_ledger_fingerprint_blocks_apply(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.json"
            ledger = self._ledger()
            path.write_text(json.dumps(ledger), encoding="utf-8")
            workflow = build_operator_review_workflow(
                self._registry(queue=[self._candidate_row()]),
                review_ledger=ledger,
                contract=self._contract(),
            )
            command = build_review_event_command(
                workflow,
                action="DISMISS",
                candidate_key="candidate-key-1",
                reviewed_by="operator@test",
                reviewed_at="2026-09-30T12:30:00+07:00",
            )
            changed = self._ledger([{"eventId": "other", "action": "DEFER"}])
            path.write_text(json.dumps(changed), encoding="utf-8")
            with self.assertRaises(ValueError):
                append_review_event(review_ledger_path=path, command=command, apply=True)

    def test_sidecar_binding_preserves_locked_registry_ads_fingerprint(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ads = root / "ads"
            ads.mkdir()
            registry = self._registry(queue=[])
            ledger = self._ledger()
            contract_path = root / "contract.json"
            ledger_path = root / "ledger.json"
            contract_path.write_text(json.dumps(self._contract()), encoding="utf-8")
            ledger_path.write_text(json.dumps(ledger), encoding="utf-8")
            (ads / "ads_smart_issue_registry.json").write_text(json.dumps(registry), encoding="utf-8")
            payload = {"meta": {"adsIntelligenceFingerprint": "registry-fp", "adsSmartIssueRegistryFingerprint": "registry-fp"}}
            (ads / "ads_intelligence.json").write_text(json.dumps(payload), encoding="utf-8")
            (ads / "ads_intelligence_qa_report.json").write_text(json.dumps({"status": "PASS", "adsIntelligenceFingerprint": "registry-fp"}), encoding="utf-8")
            (ads / "ads_intelligence_manifest.json").write_text(json.dumps({"adsIntelligenceFingerprint": "registry-fp", "files": []}), encoding="utf-8")
            result = bind_ads_smart_issue_review_workflow_artifact(
                ads_output_dir=ads,
                contract_path=contract_path,
                review_events_path=ledger_path,
            )
            rebound = json.loads((ads / "ads_intelligence.json").read_text(encoding="utf-8"))
            workflow = json.loads((ads / "ads_smart_issue_review_workflow.json").read_text(encoding="utf-8"))
            qa = json.loads((ads / "ads_intelligence_qa_report.json").read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["adsIntelligenceFingerprint"], "registry-fp")
        self.assertEqual(rebound["meta"]["adsIntelligenceFingerprint"], "registry-fp")
        self.assertTrue(workflow["doesNotModifyAdsIntelligenceFingerprint"])
        self.assertEqual(qa["smartIssueOperatorReviewWorkflow"]["status"], "PASS")

    def test_operator_ledger_fingerprint_changes_when_event_appends(self):
        base = self._ledger()
        changed = self._ledger([{"eventId": "e1", "action": "DEFER"}])
        self.assertNotEqual(operator_ledger_fingerprint(base), operator_ledger_fingerprint(changed))


if __name__ == "__main__":
    unittest.main()
