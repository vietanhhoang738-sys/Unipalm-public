import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from modules.ads_action_authorization import (
    apply_authorization_event_command,
    authorization_ledger_fingerprint,
    bind_ads_action_authorization_artifact,
    build_action_authorization,
    build_authorization_event_command,
    validate_action_authorization,
)


ROOT = Path(__file__).resolve().parents[2]


class AdsActionAuthorizationTest(unittest.TestCase):
    def _contract(self):
        return json.loads((ROOT / "config/ads_action_authorization_contract.json").read_text(encoding="utf-8"))

    def _ledger(self, events=None):
        return {"version": "1.0", "ledger_name": "ads_action_authorization_events", "events": list(events or [])}

    def _issue(self, state="OPEN", attribution=None):
        issue = {
            "issueId": "ads_issue_1",
            "issueKey": "candidate-key-1",
            "sourceCandidateId": "ads_sic_1",
            "shopId": "S1",
            "candidateType": "RISK",
            "kind": "PROBLEM",
            "productId": "P1",
            "productName": "Găng tay Air S5 Plus",
            "productSku": "GL005",
            "scope": "day",
            "headline": "Hiệu quả Ads giảm",
            "summary": "Evidence đã qua human review.",
            "reviewFocus": "Kiểm tra evidence trước khi thay đổi.",
            "priorityTier": "HIGH",
            "priorityScoreAtPromotion": 82.0,
            "state": state,
            "humanPromoted": True,
            "source": "EXPLICIT_HUMAN_REVIEW_LEDGER",
            "evidenceOnly": True,
            "causalClaim": False,
            "eventHistory": [{
                "eventId": "evt-promote",
                "action": "PROMOTE",
                "reviewedAt": "2026-09-30T10:00:00+07:00",
                "reviewedBy": "operator@test",
                "note": "",
            }],
        }
        if state == "ACKNOWLEDGED":
            issue["eventHistory"].append({
                "eventId": "evt-ack", "action": "ACKNOWLEDGE",
                "reviewedAt": "2026-09-30T11:00:00+07:00", "reviewedBy": "operator@test", "note": "",
            })
        elif state == "MONITORING":
            issue["eventHistory"].append({
                "eventId": "evt-monitor", "action": "MONITOR",
                "reviewedAt": "2026-09-30T11:00:00+07:00", "reviewedBy": "operator@test", "note": "",
            })
        elif state == "RESOLVED":
            issue["eventHistory"].append({
                "eventId": "evt-resolve", "action": "RESOLVE",
                "reviewedAt": "2026-09-30T11:00:00+07:00", "reviewedBy": "operator@test", "note": "",
            })
        if attribution is not None:
            issue["driverAttribution"] = attribution
        return issue

    def _workflow(self, issues=None):
        return {
            "status": "READY" if issues else "READY_EMPTY",
            "workflowFingerprint": "workflow-fp",
            "sourceRegistryFingerprint": "ads-fp",
            "operatorLedgerFingerprint": "operator-ledger-fp",
            "adsIntelligenceFingerprint": "ads-fp",
            "shops": {
                "S1": {
                    "displayName": "SYT+",
                    "reviewQueue": [],
                    "issues": list(issues or []),
                    "reviewQueueCount": 0,
                    "issueCount": len(issues or []),
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

    def _ads(self):
        return {
            "meta": {
                "adsIntelligenceFingerprint": "ads-fp",
                "adsSmartIssueRegistryFingerprint": "ads-fp",
            },
            "shops": {"S1": {"displayName": "SYT+", "periods": {}}},
        }

    def _alert(self):
        return {
            "status": "READY_EMPTY",
            "alertPolicyFingerprint": "alert-fp",
            "sourceReviewWorkflowFingerprint": "workflow-fp",
            "sourceRegistryFingerprint": "ads-fp",
            "sourceOperatorLedgerFingerprint": "operator-ledger-fp",
            "adsIntelligenceFingerprint": "ads-fp",
            "adsSmartIssueRegistryFingerprint": "ads-fp",
        }

    def _build(self, issue, ledger=None):
        return build_action_authorization(
            self._workflow([issue]),
            ads_payload=self._ads(),
            alert_policy=self._alert(),
            authorization_ledger=ledger or self._ledger(),
            contract=self._contract(),
        )

    def test_active_human_promoted_issue_gets_generic_review_proposal_only_without_attribution(self):
        value = self._build(self._issue())
        self.assertEqual(value["status"], "READY")
        self.assertEqual(value["proposalCount"], 1)
        proposal = value["shops"]["S1"]["proposals"][0]
        self.assertEqual(proposal["actionType"], "VALIDATE_EVIDENCE_BEFORE_CHANGE")
        self.assertEqual(proposal["attributionStatus"], "NOT_AVAILABLE")
        self.assertTrue(proposal["requiresHumanReview"])
        self.assertFalse(proposal["platformMutationAllowed"])
        self.assertFalse(proposal["automaticExecutionEligible"])
        self.assertEqual(proposal["authorization"]["state"], "PENDING_AUTHORIZATION")
        self.assertEqual(proposal["authorization"]["availableActions"], ["APPROVE", "REJECT"])
        self.assertFalse(proposal["executionBoundary"]["executionEnabled"])
        self.assertFalse(proposal["executionBoundary"]["authenticatedExecutorBound"])
        qa = validate_action_authorization(value, contract=self._contract())
        self.assertEqual(qa["status"], "PASS")

    def test_targeted_review_requires_explicit_attributed_quantified_top_driver(self):
        attribution = {
            "status": "ATTRIBUTED",
            "topDriver": {
                "metric": "placedAov",
                "label": "AOV",
                "contributionValue": -125000.0,
                "contributionShare": 0.61,
                "direction": "DOWN",
            },
        }
        value = self._build(self._issue(attribution=attribution))
        actions = [x["actionType"] for x in value["shops"]["S1"]["proposals"]]
        self.assertEqual(len(actions), 2)
        self.assertIn("VALIDATE_EVIDENCE_BEFORE_CHANGE", actions)
        self.assertIn("REVIEW_AOV_PRICE_PROMOTION_MIX", actions)
        targeted = next(x for x in value["shops"]["S1"]["proposals"] if x["actionType"] != "VALIDATE_EVIDENCE_BEFORE_CHANGE")
        self.assertEqual(targeted["attributionStatus"], "ATTRIBUTED")
        self.assertEqual(targeted["topDriver"]["metric"], "placedAov")
        self.assertFalse(targeted["prescriptiveRecommendation"])
        self.assertFalse(targeted["platformMutationAllowed"])

    def test_association_or_unquantified_driver_never_creates_targeted_review(self):
        association = {"status": "ASSOCIATION_ONLY", "topDriver": {"metric": "adsSpend", "contributionValue": 10}}
        unquantified = {"status": "ATTRIBUTED", "topDriver": {"metric": "adsSpend"}}
        for attribution in (association, unquantified):
            with self.subTest(attribution=attribution):
                value = self._build(self._issue(attribution=attribution))
                self.assertEqual(value["proposalCount"], 1)
                self.assertEqual(value["shops"]["S1"]["proposals"][0]["actionType"], "VALIDATE_EVIDENCE_BEFORE_CHANGE")

    def test_resolved_issue_is_suppressed_not_recommended(self):
        value = self._build(self._issue(state="RESOLVED"))
        self.assertEqual(value["status"], "READY_EMPTY")
        self.assertEqual(value["proposalCount"], 0)
        self.assertEqual(value["suppressedIssueCount"], 1)
        self.assertEqual(value["shops"]["S1"]["suppressedIssues"][0]["suppressionReason"], "ISSUE_STATE_SUPPRESSED")

    def test_approve_is_review_only_and_authenticated_execution_remains_blocked(self):
        initial = self._build(self._issue())
        proposal = initial["shops"]["S1"]["proposals"][0]
        ledger = self._ledger()
        command = build_authorization_event_command(
            initial,
            action="APPROVE",
            proposal_id=proposal["proposalId"],
            authorized_by="operator@test",
            authorized_at="2026-10-01T09:00:00+07:00",
            note="Reviewed evidence; approve review only.",
        )
        dry = apply_authorization_event_command(
            ledger,
            command=command,
            expected_ledger_fingerprint=authorization_ledger_fingerprint(ledger),
            apply=False,
        )
        self.assertEqual(dry["status"], "DRY_RUN")
        approved = self._build(self._issue(), ledger=dry["proposedLedger"])
        current = approved["shops"]["S1"]["proposals"][0]
        self.assertEqual(current["authorization"]["state"], "APPROVED_REVIEW_ONLY")
        self.assertEqual(current["authorization"]["availableActions"], ["REVOKE"])
        self.assertTrue(current["authorization"]["authorizationSatisfiedForManualReview"])
        self.assertEqual(current["executionBoundary"]["status"], "BLOCKED_AUTHENTICATED_EXECUTOR_NOT_BOUND")
        self.assertFalse(current["executionBoundary"]["authorizationPermitIssued"])
        self.assertFalse(current["executionBoundary"]["executionEnabled"])
        self.assertFalse(current["executionBoundary"]["platformMutationAllowed"])
        self.assertTrue(current["executionBoundary"]["idempotencyKey"].startswith("ads_exec_"))

    def test_revoke_is_terminal_and_stale_ledger_fingerprint_fails_closed(self):
        initial = self._build(self._issue())
        proposal = initial["shops"]["S1"]["proposals"][0]
        ledger = self._ledger()
        approve = build_authorization_event_command(
            initial, action="APPROVE", proposal_id=proposal["proposalId"],
            authorized_by="operator@test", authorized_at="2026-10-01T09:00:00+07:00",
        )
        applied = apply_authorization_event_command(
            ledger, command=approve,
            expected_ledger_fingerprint=authorization_ledger_fingerprint(ledger), apply=False,
        )
        approved = self._build(self._issue(), ledger=applied["proposedLedger"])
        revoke = build_authorization_event_command(
            approved, action="REVOKE", proposal_id=proposal["proposalId"],
            authorized_by="operator@test", authorized_at="2026-10-01T10:00:00+07:00",
        )
        with self.assertRaisesRegex(ValueError, "stale Action Authorization ledger fingerprint"):
            apply_authorization_event_command(
                applied["proposedLedger"], command=revoke,
                expected_ledger_fingerprint="stale-fingerprint", apply=False,
            )
        revoked_ledger = apply_authorization_event_command(
            applied["proposedLedger"], command=revoke,
            expected_ledger_fingerprint=authorization_ledger_fingerprint(applied["proposedLedger"]), apply=False,
        )["proposedLedger"]
        revoked = self._build(self._issue(), ledger=revoked_ledger)
        current = revoked["shops"]["S1"]["proposals"][0]
        self.assertEqual(current["authorization"]["state"], "REVOKED")
        self.assertEqual(current["authorization"]["availableActions"], [])
        self.assertEqual(current["executionBoundary"]["status"], "BLOCKED_AUTHORIZATION_REVOKED")

    def test_old_approval_cannot_bind_to_changed_issue_epoch(self):
        initial = self._build(self._issue())
        proposal = initial["shops"]["S1"]["proposals"][0]
        command = build_authorization_event_command(
            initial, action="APPROVE", proposal_id=proposal["proposalId"],
            authorized_by="operator@test", authorized_at="2026-10-01T09:00:00+07:00",
        )
        ledger = apply_authorization_event_command(
            self._ledger(), command=command,
            expected_ledger_fingerprint=authorization_ledger_fingerprint(self._ledger()), apply=False,
        )["proposedLedger"]
        changed = self._issue(state="ACKNOWLEDGED")
        value = self._build(changed, ledger=ledger)
        current = value["shops"]["S1"]["proposals"][0]
        self.assertNotEqual(current["proposalId"], proposal["proposalId"])
        self.assertEqual(current["authorization"]["state"], "PENDING_AUTHORIZATION")

    def test_unsafe_execution_contract_is_rejected(self):
        contract = deepcopy(self._contract())
        contract["action_authorization"]["execution_boundary"]["execution_enabled"] = True
        with self.assertRaisesRegex(ValueError, "unsafe execution boundary flag"):
            build_action_authorization(
                self._workflow([self._issue()]), ads_payload=self._ads(), alert_policy=self._alert(),
                authorization_ledger=self._ledger(), contract=contract,
            )

    def test_bind_sidecar_preserves_locked_ads_registry_fingerprint(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ads = root / "ads"
            ads.mkdir()
            (ads / "ads_smart_issue_review_workflow.json").write_text(json.dumps(self._workflow([self._issue()])), encoding="utf-8")
            (ads / "ads_alert_policy.json").write_text(json.dumps(self._alert()), encoding="utf-8")
            (ads / "ads_intelligence.json").write_text(json.dumps(self._ads()), encoding="utf-8")
            (ads / "ads_intelligence_qa_report.json").write_text(json.dumps({"status": "PASS", "adsIntelligenceFingerprint": "ads-fp"}), encoding="utf-8")
            (ads / "ads_intelligence_manifest.json").write_text(json.dumps({"adsIntelligenceFingerprint": "ads-fp", "files": []}), encoding="utf-8")
            ledger_path = root / "ledger.json"
            ledger_path.write_text(json.dumps(self._ledger()), encoding="utf-8")
            result = bind_ads_action_authorization_artifact(
                ads_output_dir=ads,
                contract_path=ROOT / "config/ads_action_authorization_contract.json",
                authorization_events_path=ledger_path,
            )
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["adsIntelligenceFingerprint"], "ads-fp")
            self.assertEqual(result["adsSmartIssueRegistryFingerprint"], "ads-fp")
            self.assertFalse(result["executionEnabled"])
            self.assertFalse(result["platformMutationAllowed"])
            artifact = json.loads((ads / "ads_action_authorization.json").read_text(encoding="utf-8"))
            self.assertTrue(artifact["doesNotModifyAdsIntelligenceFingerprint"])
            manifest = json.loads((ads / "ads_intelligence_manifest.json").read_text(encoding="utf-8"))
            self.assertIn("ads_action_authorization.json", manifest["files"])
            self.assertEqual(manifest["adsIntelligenceFingerprint"], "ads-fp")


if __name__ == "__main__":
    unittest.main()
