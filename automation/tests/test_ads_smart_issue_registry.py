import json
import tempfile
import unittest
from pathlib import Path

from modules.ads_smart_issue_registry import (
    bind_ads_smart_issue_registry_artifacts,
    bind_smart_issue_registry,
    validate_smart_issue_registry,
)


class AdsSmartIssueRegistryTest(unittest.TestCase):
    def _policy(self):
        return {
            "enabled": True,
            "mode": "SMART_ISSUE_REGISTRY_HUMAN_REVIEW_V1",
            "input_source": "smartIssueCandidates",
            "review_event_source": "EXPLICIT_APPEND_ONLY_JSON_LEDGER",
            "explicit_human_review_required": True,
            "candidate_default_review_state": "PENDING_REVIEW",
            "candidate_review_actions": ["PROMOTE", "DEFER", "DISMISS"],
            "issue_transition_actions": ["ACKNOWLEDGE", "MONITOR", "RESOLVE", "REOPEN"],
            "issue_states": ["OPEN", "ACKNOWLEDGED", "MONITORING", "RESOLVED"],
            "promotion_initial_state": "OPEN",
            "issue_id_mode": "DETERMINISTIC_FROM_CANDIDATE_KEY",
            "event_order": ["reviewedAt", "eventId"],
            "review_actor_required": True,
            "promotion_snapshot_required": True,
            "candidate_disappearance_auto_resolve": False,
            "automatic_promotion_enabled": False,
            "automatic_state_transition_enabled": False,
            "automatic_issue_resolution_enabled": False,
            "automatic_alerts_enabled": False,
            "automatic_actions_enabled": False,
            "causal_claims_enabled": False,
        }

    def _candidate(self, key="candidate-key-1", cid="ads_sic_1"):
        return {
            "candidateId": cid,
            "candidateKey": key,
            "candidateType": "RISK",
            "kind": "PROBLEM",
            "operatorType": "Vấn đề",
            "productId": "P1",
            "productName": "Găng tay Air S5 Plus",
            "productSku": "GL005",
            "scope": "day",
            "optionKey": "2026-09-27",
            "coverageEnd": "2026-09-27",
            "latestEvidenceDate": "2026-09-27",
            "evidenceAgeDays": 0,
            "lifecycleState": "NEW",
            "priorityTier": "HIGH",
            "priorityScore": 82.0,
            "headline": "Hiệu quả Ads giảm",
            "summary": "ROAS giảm trong kỳ tương đồng.",
            "reviewFocus": "Kiểm tra CPC, CVR và AOV.",
            "persistence": {
                "state": "CONFIRMED",
                "contextSignature": ["PLATFORM|shopee|DOUBLE_DAY_MEGA_SALE|1|0"],
            },
            "economicExposure": {"spendShare": 0.12, "currentSpend": 500000},
            "evidenceOnly": True,
            "causalClaim": False,
            "smartIssueCreated": False,
            "automaticAlertEligible": False,
            "automaticActionEligible": False,
        }

    def _payload(self, candidates=None):
        return {
            "capabilities": {},
            "shops": {
                "S1": {
                    "displayName": "SYT+",
                    "smartIssueCandidates": list(candidates or []),
                    "periods": {
                        "day": {"options": [], "snapshots": {}},
                        "week": {"options": [], "snapshots": {}},
                        "month": {"options": [], "snapshots": {}},
                        "year": {"options": [], "snapshots": {}},
                    },
                }
            },
        }

    def _snapshot(self, candidate):
        return {
            "shopId": "S1",
            "candidateId": candidate["candidateId"],
            "candidateKey": candidate["candidateKey"],
            "candidateType": candidate["candidateType"],
            "kind": candidate["kind"],
            "productId": candidate["productId"],
            "productName": candidate["productName"],
            "productSku": candidate["productSku"],
            "scope": candidate["scope"],
            "contextSignature": candidate["persistence"]["contextSignature"],
            "headline": candidate["headline"],
            "summary": candidate["summary"],
            "reviewFocus": candidate["reviewFocus"],
            "priorityTier": candidate["priorityTier"],
            "priorityScore": candidate["priorityScore"],
            "coverageEnd": candidate["coverageEnd"],
            "latestEvidenceDate": candidate["latestEvidenceDate"],
        }

    def _ledger(self, events=None):
        return {"version": "1.0", "ledger_name": "ads_smart_issue_review_events", "events": list(events or [])}

    def _promote(self, candidate, *, event_id="e1", at="2026-09-27T10:00:00+07:00"):
        return {
            "eventId": event_id,
            "action": "PROMOTE",
            "reviewedAt": at,
            "reviewedBy": "operator@test",
            "note": "Đã kiểm tra evidence và quyết định mở issue.",
            "candidateKey": candidate["candidateKey"],
            "candidateSnapshot": self._snapshot(candidate),
        }

    def _issue_id(self, key):
        import hashlib
        return "ads_issue_" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]

    def test_unreviewed_candidate_stays_pending_and_never_auto_promotes(self):
        candidate = self._candidate()
        payload = self._payload([candidate])
        contract = {"smart_issue_registry_policy": self._policy()}
        bind_smart_issue_registry(payload, contract=contract, review_ledger=self._ledger())
        shop = payload["shops"]["S1"]
        self.assertEqual(shop["smartIssues"], [])
        self.assertEqual(shop["smartIssueReviewQueue"][0]["reviewState"], "PENDING_REVIEW")
        self.assertFalse(candidate["humanReview"]["automaticPromotion"])
        self.assertEqual(validate_smart_issue_registry(payload, contract=contract, review_ledger=self._ledger())["status"], "PASS")

    def test_promote_event_creates_open_issue_with_stable_id(self):
        candidate = self._candidate()
        ledger = self._ledger([self._promote(candidate)])
        payload = self._payload([candidate])
        contract = {"smart_issue_registry_policy": self._policy()}
        bind_smart_issue_registry(payload, contract=contract, review_ledger=ledger)
        issue = payload["shops"]["S1"]["smartIssues"][0]
        self.assertEqual(issue["state"], "OPEN")
        self.assertEqual(issue["issueId"], self._issue_id(candidate["candidateKey"]))
        self.assertTrue(issue["humanPromoted"])
        self.assertEqual(payload["shops"]["S1"]["smartIssueReviewQueue"], [])
        self.assertEqual(candidate["humanReview"]["state"], "LINKED_ISSUE")

    def test_defer_and_dismiss_never_create_issue(self):
        candidate = self._candidate()
        for action, expected in (("DEFER", "DEFERRED"), ("DISMISS", "DISMISSED")):
            payload = self._payload([dict(candidate)])
            ledger = self._ledger([{
                "eventId": f"e-{action}", "action": action,
                "reviewedAt": "2026-09-27T10:00:00+07:00", "reviewedBy": "operator@test",
                "candidateKey": candidate["candidateKey"], "note": "reviewed"
            }])
            bind_smart_issue_registry(payload, contract={"smart_issue_registry_policy": self._policy()}, review_ledger=ledger)
            self.assertEqual(payload["shops"]["S1"]["smartIssues"], [])
            self.assertEqual(payload["shops"]["S1"]["smartIssueReviewQueue"][0]["reviewState"], expected)

    def test_issue_lifecycle_requires_explicit_events(self):
        candidate = self._candidate()
        issue_id = self._issue_id(candidate["candidateKey"])
        events = [
            self._promote(candidate, event_id="e1", at="2026-09-27T10:00:00+07:00"),
            {"eventId": "e2", "action": "ACKNOWLEDGE", "issueId": issue_id, "reviewedAt": "2026-09-27T11:00:00+07:00", "reviewedBy": "operator@test", "note": "Đã nhận xử lý"},
            {"eventId": "e3", "action": "MONITOR", "issueId": issue_id, "reviewedAt": "2026-09-27T12:00:00+07:00", "reviewedBy": "operator@test", "note": "Theo dõi thêm"},
            {"eventId": "e4", "action": "RESOLVE", "issueId": issue_id, "reviewedAt": "2026-09-27T13:00:00+07:00", "reviewedBy": "operator@test", "note": "Evidence đã bình thường"},
            {"eventId": "e5", "action": "REOPEN", "issueId": issue_id, "reviewedAt": "2026-09-28T09:00:00+07:00", "reviewedBy": "operator@test", "note": "Evidence tái xuất hiện"},
        ]
        payload = self._payload([candidate])
        bind_smart_issue_registry(payload, contract={"smart_issue_registry_policy": self._policy()}, review_ledger=self._ledger(events))
        issue = payload["shops"]["S1"]["smartIssues"][0]
        self.assertEqual(issue["state"], "OPEN")
        self.assertEqual(issue["reopenCount"], 1)
        self.assertEqual(len(issue["eventHistory"]), 5)

    def test_resolved_issue_persists_when_candidate_disappears(self):
        candidate = self._candidate()
        issue_id = self._issue_id(candidate["candidateKey"])
        events = [
            self._promote(candidate),
            {"eventId": "e2", "action": "RESOLVE", "issueId": issue_id, "reviewedAt": "2026-09-28T10:00:00+07:00", "reviewedBy": "operator@test", "note": "Resolved"},
        ]
        payload = self._payload([])
        bind_smart_issue_registry(payload, contract={"smart_issue_registry_policy": self._policy()}, review_ledger=self._ledger(events))
        issue = payload["shops"]["S1"]["smartIssues"][0]
        self.assertEqual(issue["state"], "RESOLVED")
        self.assertEqual(payload["shops"]["S1"]["smartIssueReviewQueue"], [])

    def test_resolved_issue_with_current_candidate_requires_explicit_reopen_review(self):
        candidate = self._candidate()
        issue_id = self._issue_id(candidate["candidateKey"])
        events = [
            self._promote(candidate),
            {"eventId": "e2", "action": "RESOLVE", "issueId": issue_id, "reviewedAt": "2026-09-28T10:00:00+07:00", "reviewedBy": "operator@test", "note": "Resolved"},
        ]
        payload = self._payload([candidate])
        bind_smart_issue_registry(payload, contract={"smart_issue_registry_policy": self._policy()}, review_ledger=self._ledger(events))
        self.assertEqual(candidate["humanReview"]["state"], "REOPEN_REVIEW_REQUIRED")
        self.assertEqual(payload["shops"]["S1"]["smartIssues"][0]["state"], "RESOLVED")

    def test_invalid_transition_fails_closed(self):
        candidate = self._candidate()
        issue_id = self._issue_id(candidate["candidateKey"])
        events = [
            self._promote(candidate),
            {"eventId": "e2", "action": "REOPEN", "issueId": issue_id, "reviewedAt": "2026-09-28T10:00:00+07:00", "reviewedBy": "operator@test"},
        ]
        with self.assertRaises(ValueError):
            bind_smart_issue_registry(self._payload([candidate]), contract={"smart_issue_registry_policy": self._policy()}, review_ledger=self._ledger(events))

    def test_duplicate_event_id_fails_closed(self):
        candidate = self._candidate()
        events = [self._promote(candidate), {"eventId": "e1", "action": "DEFER", "candidateKey": "other", "reviewedAt": "2026-09-28T10:00:00+07:00", "reviewedBy": "operator@test"}]
        with self.assertRaises(ValueError):
            bind_smart_issue_registry(self._payload([candidate]), contract={"smart_issue_registry_policy": self._policy()}, review_ledger=self._ledger(events))

    def test_artifact_binding_refingerprints_after_candidate_layer(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ads = root / "ads"
            ads.mkdir()
            contract_path = root / "contract.json"
            ledger_path = root / "ledger.json"
            contract_path.write_text(json.dumps({"smart_issue_registry_policy": self._policy()}), encoding="utf-8")
            ledger_path.write_text(json.dumps(self._ledger()), encoding="utf-8")
            payload = self._payload([])
            payload["meta"] = {
                "adsIntelligenceFingerprint": "candidate-fp",
                "adsSmartIssueCandidateFingerprint": "candidate-fp",
            }
            (ads / "ads_intelligence.json").write_text(json.dumps(payload), encoding="utf-8")
            (ads / "ads_intelligence_qa_report.json").write_text(json.dumps({"status": "PASS", "adsIntelligenceFingerprint": "candidate-fp"}), encoding="utf-8")
            (ads / "ads_intelligence_manifest.json").write_text(json.dumps({"adsIntelligenceFingerprint": "candidate-fp", "files": ["ads_intelligence.json"]}), encoding="utf-8")
            result = bind_ads_smart_issue_registry_artifacts(ads_output_dir=ads, contract_path=contract_path, review_events_path=ledger_path)
            rebound = json.loads((ads / "ads_intelligence.json").read_text(encoding="utf-8"))
            preview = json.loads((ads / "ads_smart_issue_registry_preview.json").read_text(encoding="utf-8"))
            registry = json.loads((ads / "ads_smart_issue_registry.json").read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["preSmartIssueRegistryAdsIntelligenceFingerprint"], "candidate-fp")
        self.assertNotEqual(result["adsIntelligenceFingerprint"], "candidate-fp")
        self.assertEqual(rebound["meta"]["adsSmartIssueRegistryFingerprint"], result["adsIntelligenceFingerprint"])
        self.assertEqual(preview["shops"]["S1"]["issueCount"], 0)
        self.assertEqual(registry["status"], "PREPRODUCTION_REGISTRY")
        self.assertFalse(registry["safety"]["automaticAlertsEnabled"])


if __name__ == "__main__":
    unittest.main()
