import json
import tempfile
import unittest
from pathlib import Path

from modules.ads_diagnosis_persistence import (
    bind_ads_diagnosis_persistence_artifacts,
    bind_diagnosis_persistence,
    validate_diagnosis_persistence,
)


class AdsDiagnosisPersistenceTest(unittest.TestCase):
    def _policy(self):
        return {
            "enabled": True,
            "mode": "DIAGNOSIS_PERSISTENCE_MULTI_WINDOW_V1",
            "input_source": "dynamicDiagnosis.items",
            "scope_mode": "SAME_SCOPE_ONLY",
            "context_signature_mode": "SAME_CURRENT_CONTEXT_SIGNATURE",
            "independence_rule": "NON_OVERLAPPING_WINDOWS_ONLY",
            "lookback_observations": 3,
            "minimum_support_windows": 2,
            "minimum_support_ratio": 2 / 3,
            "smart_issue_candidate_generation_enabled": False,
            "causal_claims_enabled": False,
            "automatic_alerts_enabled": False,
            "automatic_actions_enabled": False,
        }

    def _contract(self):
        return {"diagnosis_persistence_policy": self._policy()}

    def _item(self, kind="PROBLEM", pid="P1"):
        return {
            "diagnosisId": f"diag-{pid}-{kind}",
            "kind": kind,
            "operatorType": "Vấn đề" if kind == "PROBLEM" else "Cơ hội",
            "productId": pid,
            "productName": "Air S2",
            "priorityTier": "MEDIUM",
            "priorityScore": 62,
            "confidenceTier": "HIGH",
            "confidence": 0.9,
            "causalClaim": False,
            "automaticAlertEligible": False,
            "automaticActionEligible": False,
        }

    def _snapshot(self, option, start, end, *, items=None, diag_status="READY", signature="MEGA"):
        return {
            "status": "READY",
            "scope": "day",
            "optionKey": option,
            "coverageStart": start,
            "coverageEnd": end,
            "comparisonStatus": "READY",
            "strongDirectionalDiagnosisEligible": True,
            "businessContext": {
                "matchEvaluation": "CONTEXT_COMPATIBLE",
                "qualification": {"currentSignature": [signature]},
            },
            "dynamicDiagnosis": {
                "status": diag_status,
                "items": list(items or []),
                "causalClaim": False,
                "automaticAlertsEnabled": False,
                "automaticActionsEnabled": False,
            },
        }

    def _payload(self, snapshots, scope="day"):
        periods = {
            "day": {"options": [], "snapshots": {}},
            "week": {"options": [], "snapshots": {}},
            "month": {"options": [], "snapshots": {}},
            "year": {"options": [], "snapshots": {}},
        }
        periods[scope] = {"options": sorted(snapshots), "snapshots": snapshots}
        for snap in snapshots.values():
            snap["scope"] = scope
        return {
            "meta": {},
            "capabilities": {},
            "shops": {"S1": {"displayName": "SYT+", "periods": periods}},
        }

    def test_two_of_three_independent_same_direction_confirms(self):
        snaps = {
            "2026-09-01": self._snapshot("2026-09-01", "2026-09-01", "2026-09-01", items=[self._item()]),
            "2026-09-02": self._snapshot("2026-09-02", "2026-09-02", "2026-09-02", items=[], diag_status="NO_MATERIAL_DIAGNOSIS"),
            "2026-09-03": self._snapshot("2026-09-03", "2026-09-03", "2026-09-03", items=[self._item()]),
        }
        payload = self._payload(snaps)
        bind_diagnosis_persistence(payload, contract=self._contract())
        persistence = snaps["2026-09-03"]["dynamicDiagnosis"]["items"][0]["persistence"]
        self.assertEqual(persistence["state"], "CONFIRMED")
        self.assertEqual(persistence["supportWindowCount"], 2)
        self.assertEqual(persistence["eligibleIndependentWindowCount"], 3)
        self.assertAlmostEqual(persistence["supportRatio"], 2 / 3)
        self.assertTrue(persistence["confirmationEligible"])
        self.assertFalse(persistence["smartIssueCandidateEligible"])

    def test_opposite_direction_blocks_confirmation(self):
        snaps = {
            "2026-09-01": self._snapshot("2026-09-01", "2026-09-01", "2026-09-01", items=[self._item("PROBLEM")]),
            "2026-09-02": self._snapshot("2026-09-02", "2026-09-02", "2026-09-02", items=[self._item("OPPORTUNITY")]),
            "2026-09-03": self._snapshot("2026-09-03", "2026-09-03", "2026-09-03", items=[self._item("PROBLEM")]),
        }
        payload = self._payload(snaps)
        bind_diagnosis_persistence(payload, contract=self._contract())
        persistence = snaps["2026-09-03"]["dynamicDiagnosis"]["items"][0]["persistence"]
        self.assertEqual(persistence["state"], "CONFLICTED")
        self.assertEqual(persistence["supportWindowCount"], 2)
        self.assertEqual(persistence["oppositeDirectionWindowCount"], 1)
        self.assertFalse(persistence["confirmationEligible"])

    def test_compatible_no_material_window_counts_as_miss(self):
        snaps = {
            "2026-09-01": self._snapshot("2026-09-01", "2026-09-01", "2026-09-01", items=[], diag_status="NO_MATERIAL_DIAGNOSIS"),
            "2026-09-02": self._snapshot("2026-09-02", "2026-09-02", "2026-09-02", items=[self._item()]),
        }
        payload = self._payload(snaps)
        bind_diagnosis_persistence(payload, contract=self._contract())
        persistence = snaps["2026-09-02"]["dynamicDiagnosis"]["items"][0]["persistence"]
        self.assertEqual(persistence["state"], "ONE_OFF")
        self.assertEqual(persistence["eligibleIndependentWindowCount"], 2)
        self.assertEqual(persistence["supportWindowCount"], 1)

    def test_different_context_signature_is_not_confirmation_evidence(self):
        snaps = {
            "2026-09-01": self._snapshot("2026-09-01", "2026-09-01", "2026-09-01", items=[self._item()], signature="PAYDAY"),
            "2026-09-02": self._snapshot("2026-09-02", "2026-09-02", "2026-09-02", items=[self._item()], signature="MEGA"),
        }
        payload = self._payload(snaps)
        bind_diagnosis_persistence(payload, contract=self._contract())
        persistence = snaps["2026-09-02"]["dynamicDiagnosis"]["items"][0]["persistence"]
        self.assertEqual(persistence["state"], "FIRST_OBSERVATION")
        self.assertEqual(persistence["eligibleIndependentWindowCount"], 1)

    def test_overlapping_rolling_windows_do_not_double_confirm(self):
        snaps = {
            "2026-09-07": self._snapshot("2026-09-07", "2026-09-01", "2026-09-07", items=[self._item()]),
            "2026-09-08": self._snapshot("2026-09-08", "2026-09-02", "2026-09-08", items=[self._item()]),
        }
        payload = self._payload(snaps, scope="week")
        bind_diagnosis_persistence(payload, contract=self._contract())
        persistence = snaps["2026-09-08"]["dynamicDiagnosis"]["items"][0]["persistence"]
        self.assertEqual(persistence["state"], "FIRST_OBSERVATION")
        self.assertEqual(persistence["eligibleIndependentWindowCount"], 1)
        self.assertEqual(persistence["supportWindowKeys"], ["2026-09-08"])

    def test_blocked_context_window_is_excluded_not_counted_as_miss(self):
        blocked = self._snapshot("2026-09-02", "2026-09-02", "2026-09-02", items=[])
        blocked["businessContext"]["matchEvaluation"] = "CONTEXT_DIFFERENT"
        blocked["strongDirectionalDiagnosisEligible"] = False
        blocked["dynamicDiagnosis"]["status"] = "BLOCKED_CONTEXT_DIFFERENT"
        snaps = {
            "2026-09-01": self._snapshot("2026-09-01", "2026-09-01", "2026-09-01", items=[self._item()]),
            "2026-09-02": blocked,
            "2026-09-03": self._snapshot("2026-09-03", "2026-09-03", "2026-09-03", items=[self._item()]),
        }
        payload = self._payload(snaps)
        bind_diagnosis_persistence(payload, contract=self._contract())
        persistence = snaps["2026-09-03"]["dynamicDiagnosis"]["items"][0]["persistence"]
        self.assertEqual(persistence["state"], "CONFIRMED")
        self.assertEqual(persistence["eligibleIndependentWindowCount"], 2)
        self.assertNotIn("2026-09-02", persistence["supportWindowKeys"])

    def test_validation_enforces_noncausal_nonautomation_boundary(self):
        snaps = {
            "2026-09-01": self._snapshot("2026-09-01", "2026-09-01", "2026-09-01", items=[self._item()]),
            "2026-09-02": self._snapshot("2026-09-02", "2026-09-02", "2026-09-02", items=[self._item()]),
        }
        payload = self._payload(snaps)
        bind_diagnosis_persistence(payload, contract=self._contract())
        qa = validate_diagnosis_persistence(payload, contract=self._contract())
        self.assertEqual(qa["status"], "PASS")
        p = snaps["2026-09-02"]["dynamicDiagnosis"]["items"][0]["persistence"]
        p["smartIssueCandidateEligible"] = True
        qa = validate_diagnosis_persistence(payload, contract=self._contract())
        self.assertEqual(qa["status"], "FAIL")

    def test_artifact_binding_preserves_dynamic_fingerprint_and_adds_new_layer(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ads_dir = root / "ads"
            ads_dir.mkdir()
            contract_path = root / "persistence.json"
            contract_path.write_text(json.dumps(self._contract()), encoding="utf-8")
            snaps = {
                "2026-09-01": self._snapshot("2026-09-01", "2026-09-01", "2026-09-01", items=[self._item()]),
                "2026-09-02": self._snapshot("2026-09-02", "2026-09-02", "2026-09-02", items=[self._item()]),
            }
            payload = self._payload(snaps)
            payload["meta"] = {
                "adsIntelligenceFingerprint": "diagnosis-fp",
                "adsDynamicDiagnosisFingerprint": "diagnosis-fp",
            }
            (ads_dir / "ads_intelligence.json").write_text(json.dumps(payload), encoding="utf-8")
            (ads_dir / "ads_intelligence_qa_report.json").write_text(json.dumps({
                "status": "PASS", "adsIntelligenceFingerprint": "diagnosis-fp"
            }), encoding="utf-8")
            (ads_dir / "ads_intelligence_manifest.json").write_text(json.dumps({
                "adsIntelligenceFingerprint": "diagnosis-fp", "files": ["ads_intelligence.json"]
            }), encoding="utf-8")

            result = bind_ads_diagnosis_persistence_artifacts(
                ads_output_dir=ads_dir,
                contract_path=contract_path,
            )
            rebound = json.loads((ads_dir / "ads_intelligence.json").read_text(encoding="utf-8"))
            preview = json.loads((ads_dir / "ads_persistence_candidate_preview.json").read_text(encoding="utf-8"))

        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["adsDynamicDiagnosisFingerprint"], "diagnosis-fp")
        self.assertEqual(result["prePersistenceAdsIntelligenceFingerprint"], "diagnosis-fp")
        self.assertNotEqual(result["adsDiagnosisPersistenceFingerprint"], "diagnosis-fp")
        self.assertEqual(rebound["meta"]["adsDynamicDiagnosisFingerprint"], "diagnosis-fp")
        self.assertEqual(
            rebound["shops"]["S1"]["periods"]["day"]["snapshots"]["2026-09-02"]
            ["dynamicDiagnosis"]["items"][0]["persistence"]["state"],
            "CONFIRMED",
        )
        self.assertEqual(preview["shops"]["S1"]["confirmedDiagnosisItemCount"], 1)
        self.assertFalse(preview["safety"]["smartIssueCandidatesEnabled"])


if __name__ == "__main__":
    unittest.main()
