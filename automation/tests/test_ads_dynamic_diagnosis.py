import json
import tempfile
import unittest
from pathlib import Path

from modules.ads_dynamic_diagnosis import (
    bind_ads_dynamic_diagnosis_artifacts,
    build_snapshot_diagnosis,
    validate_dynamic_diagnosis,
)


class AdsDynamicDiagnosisTest(unittest.TestCase):
    def _policy(self):
        return {
            "enabled": True,
            "mode": "DYNAMIC_ADS_DIAGNOSIS_V1",
            "input_signal_source": "qualifiedSignals",
            "context_gate": "CONTEXT_COMPATIBLE_ONLY",
            "max_diagnosis_items": 6,
            "priority_high_min": 75,
            "priority_medium_min": 55,
            "causal_claims_enabled": False,
            "automatic_alerts_enabled": False,
            "automatic_actions_enabled": False,
        }

    def _signal(self, *, kind="Vấn đề", pid="P1", priority=82, confidence=0.9):
        return {
            "type": kind,
            "productId": pid,
            "productName": "Găng tay Air S2" if pid == "P1" else "Khẩu trang Cool S3",
            "productSku": "GL002" if pid == "P1" else "KT003",
            "currentSpend": 1200000,
            "currentAttributedSales": 3600000,
            "currentRoas": 3.0,
            "currentCpa": 60000,
            "currentCvr": 0.05,
            "spendShare": 0.22,
            "roasDelta": -0.32 if kind == "Vấn đề" else 0.41,
            "salesDelta": -0.08 if kind == "Vấn đề" else 0.28,
            "spendDelta": 0.18,
            "priorityScore": priority,
            "confidence": confidence,
            "relationType": "PERIOD_OVER_PERIOD_EVIDENCE",
            "causalClaim": False,
        }

    def _snapshot(self, evaluation="CONTEXT_COMPATIBLE", eligible=True, signals=None):
        signals = list(signals or [])
        return {
            "status": "READY",
            "scope": "week",
            "optionKey": "2026-09-08",
            "comparisonStatus": "READY",
            "businessContext": {"matchEvaluation": evaluation},
            "strongDirectionalDiagnosisEligible": eligible,
            "qualifiedSignals": signals if eligible else [],
            "signals": signals,
        }

    def test_compatible_qualified_signal_becomes_noncausal_diagnosis(self):
        snap = self._snapshot(signals=[self._signal()])
        diagnosis = build_snapshot_diagnosis(snap, policy=self._policy())
        self.assertEqual(diagnosis["status"], "READY")
        self.assertEqual(diagnosis["problemCount"], 1)
        self.assertEqual(len(diagnosis["items"]), 1)
        item = diagnosis["items"][0]
        self.assertEqual(item["kind"], "PROBLEM")
        self.assertEqual(item["priorityTier"], "HIGH")
        self.assertEqual(item["confidenceTier"], "HIGH")
        self.assertTrue(item["contextQualified"])
        self.assertTrue(item["evidenceOnly"])
        self.assertFalse(item["causalClaim"])
        self.assertFalse(item["automaticAlertEligible"])
        self.assertFalse(item["automaticActionEligible"])
        self.assertIn("bối cảnh so sánh tương đồng", item["headline"])
        self.assertIn("ROAS", item["summary"])

    def test_context_different_and_unknown_fail_closed(self):
        for evaluation, expected in (
            ("CONTEXT_DIFFERENT", "BLOCKED_CONTEXT_DIFFERENT"),
            ("CONTEXT_UNKNOWN", "BLOCKED_CONTEXT_UNKNOWN"),
        ):
            with self.subTest(evaluation=evaluation):
                snap = self._snapshot(evaluation=evaluation, eligible=False, signals=[self._signal()])
                diagnosis = build_snapshot_diagnosis(snap, policy=self._policy())
                self.assertEqual(diagnosis["status"], expected)
                self.assertEqual(diagnosis["items"], [])
                self.assertEqual(len(snap["signals"]), 1)
                self.assertEqual(snap["qualifiedSignals"], [])
                self.assertFalse(diagnosis["automaticAlertsEnabled"])
                self.assertFalse(diagnosis["automaticActionsEnabled"])

    def test_compatible_without_material_signal_is_not_forced_into_diagnosis(self):
        snap = self._snapshot(signals=[])
        diagnosis = build_snapshot_diagnosis(snap, policy=self._policy())
        self.assertEqual(diagnosis["status"], "NO_MATERIAL_DIAGNOSIS")
        self.assertEqual(diagnosis["items"], [])
        self.assertIn("chưa có tín hiệu", diagnosis["reason"])

    def test_diagnosis_priority_is_deterministic_and_bounded(self):
        signals = [
            self._signal(kind="Cơ hội", pid="P2", priority=61, confidence=0.8),
            self._signal(kind="Vấn đề", pid="P1", priority=91, confidence=0.9),
        ]
        snap = self._snapshot(signals=signals)
        diagnosis = build_snapshot_diagnosis(snap, policy=self._policy())
        self.assertEqual([x["productId"] for x in diagnosis["items"]], ["P1", "P2"])
        self.assertEqual(diagnosis["items"][0]["priorityTier"], "HIGH")
        self.assertEqual(diagnosis["items"][1]["priorityTier"], "MEDIUM")
        self.assertEqual(diagnosis["opportunityCount"], 1)
        self.assertEqual(diagnosis["problemCount"], 1)

    def test_validation_rejects_unqualified_diagnosis_leak(self):
        snap = self._snapshot(evaluation="CONTEXT_DIFFERENT", eligible=False, signals=[self._signal()])
        snap["dynamicDiagnosis"] = {
            "status": "READY",
            "items": [{"productId": "P1", "causalClaim": False}],
            "causalClaim": False,
            "automaticAlertsEnabled": False,
            "automaticActionsEnabled": False,
        }
        payload = {
            "capabilities": {"adsDynamicDiagnosis": True, "adsDiagnosisContextQualifiedOnly": True},
            "shops": {
                "S1": {
                    "dynamicDiagnosisLineage": {"inputSignalSource": "qualifiedSignals"},
                    "periods": {
                        "day": {"snapshots": {}},
                        "week": {"snapshots": {"2026-09-08": snap}},
                        "month": {"snapshots": {}},
                        "year": {"snapshots": {}},
                    },
                }
            },
        }
        qa = validate_dynamic_diagnosis(payload)
        self.assertEqual(qa["status"], "FAIL")
        failed = [x["name"] for x in qa["checks"] if x["status"] == "FAIL"]
        self.assertTrue(any("diagnosis_gate" in x for x in failed))
        self.assertTrue(any("diagnosis_from_qualified_only" in x for x in failed))

    def test_artifact_binding_refingerprints_and_writes_preview(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ads_dir = root / "ads"
            ads_dir.mkdir()
            contract_path = root / "contract.json"
            contract_path.write_text(json.dumps({"dynamic_diagnosis_policy": self._policy()}), encoding="utf-8")
            signal = self._signal()
            snapshot = self._snapshot(signals=[signal])
            payload = {
                "meta": {
                    "adsIntelligenceFingerprint": "context-fp",
                    "adsContextQualificationFingerprint": "context-fp",
                },
                "capabilities": {},
                "shops": {
                    "S1": {
                        "displayName": "SYT+",
                        "periods": {
                            "day": {"options": [], "snapshots": {}},
                            "week": {"options": ["2026-09-08"], "snapshots": {"2026-09-08": snapshot}},
                            "month": {"options": [], "snapshots": {}},
                            "year": {"options": [], "snapshots": {}},
                        },
                    }
                },
            }
            (ads_dir / "ads_intelligence.json").write_text(json.dumps(payload), encoding="utf-8")
            (ads_dir / "ads_intelligence_qa_report.json").write_text(json.dumps({
                "status": "PASS", "adsIntelligenceFingerprint": "context-fp"
            }), encoding="utf-8")
            (ads_dir / "ads_intelligence_manifest.json").write_text(json.dumps({
                "adsIntelligenceFingerprint": "context-fp", "files": ["ads_intelligence.json"]
            }), encoding="utf-8")

            result = bind_ads_dynamic_diagnosis_artifacts(
                ads_output_dir=ads_dir,
                contract_path=contract_path,
            )
            rebound = json.loads((ads_dir / "ads_intelligence.json").read_text(encoding="utf-8"))
            preview = json.loads((ads_dir / "ads_diagnosis_candidate_preview.json").read_text(encoding="utf-8"))

        self.assertEqual(result["status"], "PASS")
        self.assertNotEqual(result["adsIntelligenceFingerprint"], "context-fp")
        self.assertEqual(result["adsContextQualificationFingerprint"], "context-fp")
        self.assertEqual(result["dynamicDiagnosisStatus"], "PASS")
        diagnosis = rebound["shops"]["S1"]["periods"]["week"]["snapshots"]["2026-09-08"]["dynamicDiagnosis"]
        self.assertEqual(diagnosis["status"], "READY")
        self.assertEqual(len(diagnosis["items"]), 1)
        self.assertEqual(preview["shops"]["S1"]["scopes"]["week"]["diagnosisStatus"], "READY")
        self.assertFalse(preview["safety"]["productionActivationEnabled"])


if __name__ == "__main__":
    unittest.main()
