import json
import tempfile
import unittest
from pathlib import Path

from modules.ads_smart_issue_candidates import (
    bind_ads_smart_issue_candidate_artifacts,
    bind_smart_issue_candidates,
    validate_smart_issue_candidates,
)


class AdsSmartIssueCandidatesTest(unittest.TestCase):
    def _policy(self):
        return {
            "enabled": True,
            "mode": "SMART_ISSUE_CANDIDATE_V1",
            "input_source": "dynamicDiagnosis.items.persistence",
            "required_persistence_state": "CONFIRMED",
            "candidate_kinds": ["PROBLEM", "OPPORTUNITY"],
            "materiality": {"minimum_priority_score": 55, "minimum_abs_roas_delta": 0.25},
            "economic_exposure": {
                "mode": "RELATIVE_AND_SCOPE_ABSOLUTE_OR_HIGH_SHARE_OVERRIDE",
                "minimum_spend_share": 0.05,
                "high_share_override": 0.10,
                "scope_current_spend_floor_vnd": {"day": 100000, "week": 500000, "month": 2000000, "year": 5000000},
            },
            "recency": {
                "anchor": "SHOP_LATEST_READY_DAY_COVERAGE_END",
                "scope_max_age_days": {"day": 3, "week": 10, "month": 45, "year": 400},
            },
            "deduplication": {"one_active_candidate_per_key": True, "latest_material_occurrence_wins": True},
            "lifecycle": {
                "scope_continuity_gap_days": {"day": 3, "week": 10, "month": 45, "year": 400},
                "scope_reopen_cooldown_days": {"day": 7, "week": 21, "month": 60, "year": 450},
                "cooldown_suppresses_reopen_candidate": True,
            },
            "smart_issue_creation_enabled": False,
            "causal_claims_enabled": False,
            "automatic_alerts_enabled": False,
            "automatic_actions_enabled": False,
        }

    def _item(self, *, pid="P1", priority=80, spend=500000, share=0.12, roas_delta=-0.5, state="CONFIRMED"):
        return {
            "diagnosisId": f"diag-{pid}",
            "kind": "PROBLEM",
            "operatorType": "Vấn đề",
            "priorityTier": "HIGH" if priority >= 75 else "MEDIUM",
            "priorityScore": priority,
            "productId": pid,
            "productName": "Găng tay Air S5 Plus",
            "productSku": "GL005",
            "headline": "Hiệu quả Ads giảm",
            "summary": "ROAS giảm trong kỳ tương đồng.",
            "reviewFocus": "Kiểm tra CPC, CVR và AOV.",
            "evidence": {
                "currentSpend": spend,
                "currentAttributedSales": 1000000,
                "currentRoas": 2.0,
                "spendShare": share,
                "roasDelta": roas_delta,
                "salesDelta": -0.2,
                "spendDelta": 0.1,
            },
            "persistence": {
                "state": state,
                "contextSignature": ["PLATFORM|shopee|DOUBLE_DAY_MEGA_SALE|1|0"],
                "supportWindowCount": 3,
                "eligibleIndependentWindowCount": 3,
                "supportRatio": 1.0,
                "oppositeDirectionWindowCount": 0,
                "confirmationEligible": state == "CONFIRMED",
            },
        }

    def _snapshot(self, date, items=None):
        return {
            "status": "READY",
            "scope": "day",
            "optionKey": date,
            "coverageStart": date,
            "coverageEnd": date,
            "dynamicDiagnosis": {"status": "READY" if items else "NO_MATERIAL_DIAGNOSIS", "items": list(items or [])},
        }

    def _payload(self, snapshots):
        return {
            "capabilities": {},
            "shops": {
                "S1": {
                    "displayName": "SYT+",
                    "periods": {
                        "day": {"options": sorted(snapshots), "snapshots": snapshots},
                        "week": {"options": [], "snapshots": {}},
                        "month": {"options": [], "snapshots": {}},
                        "year": {"options": [], "snapshots": {}},
                    },
                }
            },
        }

    def test_confirmed_material_recent_diagnosis_becomes_candidate(self):
        item = self._item()
        payload = self._payload({"2026-09-27": self._snapshot("2026-09-27", [item])})
        bind_smart_issue_candidates(payload, contract={"smart_issue_candidate_policy": self._policy()})
        candidate = payload["shops"]["S1"]["smartIssueCandidates"][0]
        ev = item["smartIssueCandidate"]
        self.assertEqual(ev["status"], "ELIGIBLE")
        self.assertEqual(ev["lifecycleState"], "NEW")
        self.assertTrue(ev["eligible"])
        self.assertEqual(candidate["candidateType"], "RISK")
        self.assertFalse(candidate["smartIssueCreated"])
        self.assertFalse(candidate["economicExposure"]["economicExposureIsLossEstimate"])

    def test_low_materiality_and_low_exposure_do_not_become_candidate(self):
        item = self._item(priority=50, spend=21000, share=0.051, roas_delta=-1.0)
        payload = self._payload({"2026-09-27": self._snapshot("2026-09-27", [item])})
        bind_smart_issue_candidates(payload, contract={"smart_issue_candidate_policy": self._policy()})
        self.assertEqual(payload["shops"]["S1"]["smartIssueCandidates"], [])
        ev = item["smartIssueCandidate"]
        self.assertEqual(ev["status"], "BLOCKED_MATERIALITY")
        self.assertIn("PRIORITY_BELOW_MINIMUM", ev["economicExposure"]["blockers"])
        self.assertIn("SPEND_EXPOSURE_BELOW_SCOPE_FLOOR", ev["economicExposure"]["blockers"])

    def test_stale_confirmed_diagnosis_is_blocked_by_recency(self):
        item = self._item()
        payload = self._payload({
            "2026-09-11": self._snapshot("2026-09-11", [item]),
            "2026-09-27": self._snapshot("2026-09-27", []),
        })
        bind_smart_issue_candidates(payload, contract={"smart_issue_candidate_policy": self._policy()})
        self.assertEqual(payload["shops"]["S1"]["smartIssueCandidates"], [])
        ev = item["smartIssueCandidate"]
        self.assertEqual(ev["status"], "BLOCKED_RECENCY")
        self.assertEqual(ev["evidenceAgeDays"], 16)
        self.assertFalse(ev["recencyPassed"])

    def test_duplicate_occurrences_collapse_to_latest_candidate(self):
        first = self._item()
        latest = self._item()
        payload = self._payload({
            "2026-09-25": self._snapshot("2026-09-25", [first]),
            "2026-09-27": self._snapshot("2026-09-27", [latest]),
        })
        bind_smart_issue_candidates(payload, contract={"smart_issue_candidate_policy": self._policy()})
        candidates = payload["shops"]["S1"]["smartIssueCandidates"]
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["optionKey"], "2026-09-27")
        self.assertEqual(first["smartIssueCandidate"]["status"], "DUPLICATE_SUPPRESSED")
        self.assertEqual(latest["smartIssueCandidate"]["lifecycleState"], "CONTINUING")

    def test_reopen_inside_cooldown_is_suppressed(self):
        first = self._item()
        second = self._item()
        payload = self._payload({
            "2026-09-20": self._snapshot("2026-09-20", [first]),
            "2026-09-25": self._snapshot("2026-09-25", [second]),
        })
        bind_smart_issue_candidates(payload, contract={"smart_issue_candidate_policy": self._policy()})
        self.assertEqual(payload["shops"]["S1"]["smartIssueCandidates"], [])
        self.assertEqual(second["smartIssueCandidate"]["lifecycleState"], "COOLDOWN_SUPPRESSED")
        self.assertEqual(second["smartIssueCandidate"]["status"], "COOLDOWN_SUPPRESSED")

    def test_validation_requires_candidate_to_match_eligible_item(self):
        item = self._item()
        payload = self._payload({"2026-09-27": self._snapshot("2026-09-27", [item])})
        contract = {"smart_issue_candidate_policy": self._policy()}
        bind_smart_issue_candidates(payload, contract=contract)
        qa = validate_smart_issue_candidates(payload, contract=contract)
        self.assertEqual(qa["status"], "PASS")
        payload["shops"]["S1"]["smartIssueCandidates"] = []
        qa = validate_smart_issue_candidates(payload, contract=contract)
        self.assertEqual(qa["status"], "FAIL")

    def test_artifact_binding_refingerprints_after_persistence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ads = root / "ads"
            ads.mkdir()
            contract_path = root / "contract.json"
            contract_path.write_text(json.dumps({"smart_issue_candidate_policy": self._policy()}), encoding="utf-8")
            item = self._item()
            payload = self._payload({"2026-09-27": self._snapshot("2026-09-27", [item])})
            payload["meta"] = {
                "adsIntelligenceFingerprint": "persistence-fp",
                "adsDiagnosisPersistenceFingerprint": "persistence-fp",
            }
            (ads / "ads_intelligence.json").write_text(json.dumps(payload), encoding="utf-8")
            (ads / "ads_intelligence_qa_report.json").write_text(json.dumps({"status": "PASS", "adsIntelligenceFingerprint": "persistence-fp"}), encoding="utf-8")
            (ads / "ads_intelligence_manifest.json").write_text(json.dumps({"adsIntelligenceFingerprint": "persistence-fp", "files": ["ads_intelligence.json"]}), encoding="utf-8")
            result = bind_ads_smart_issue_candidate_artifacts(ads_output_dir=ads, contract_path=contract_path)
            rebound = json.loads((ads / "ads_intelligence.json").read_text(encoding="utf-8"))
            preview = json.loads((ads / "ads_smart_issue_candidate_preview.json").read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["preSmartIssueAdsIntelligenceFingerprint"], "persistence-fp")
        self.assertNotEqual(result["adsIntelligenceFingerprint"], "persistence-fp")
        self.assertEqual(rebound["meta"]["adsSmartIssueCandidateFingerprint"], result["adsIntelligenceFingerprint"])
        self.assertEqual(preview["shops"]["S1"]["activeCandidateCount"], 1)
        self.assertFalse(preview["safety"]["smartIssueCreationEnabled"])


if __name__ == "__main__":
    unittest.main()
