import json
import tempfile
import unittest
from pathlib import Path

from modules.ads_context_qualification import (
    bind_ads_business_context_artifacts,
    bind_snapshot_context,
    build_candidate_preview,
    qualify_context_pair,
    resolve_window_context,
)


class AdsBusinessContextQualificationTest(unittest.TestCase):
    def _policy(self):
        return {
            "mode": "DYNAMIC_ADS_CONTEXT_QUALIFICATION_V1",
            "qualifying_platforms": ["shopee"],
            "qualifying_context_families": ["DOUBLE_DAY_MEGA_SALE", "PAYDAY"],
        }

    def _row(self, date, family="PAYDAY", platform="shopee", context_id="ctx", peak=True):
        return {
            "data_date": date,
            "context_id": context_id,
            "platform": platform,
            "scope_type": "PLATFORM",
            "shop_id": "",
            "context_family": family,
            "is_peak_date": peak,
            "source_tier": "A2_PLATFORM_CONSUMER_OFFICIAL",
            "matching_eligible": True,
        }

    def test_resolver_and_qualification_three_states(self):
        policy = self._policy()
        rows = [
            self._row("2026-08-25", context_id="payday_aug"),
            self._row("2026-09-25", context_id="payday_sep"),
        ]
        aug = resolve_window_context(rows, ["2026-08-25"], shop_id="S1", policy=policy)
        sep = resolve_window_context(rows, ["2026-09-25"], shop_id="S1", policy=policy)
        compatible = qualify_context_pair(sep, aug, comparison_status="READY")
        self.assertEqual(compatible["status"], "CONTEXT_COMPATIBLE")
        self.assertEqual(compatible["reason"], "EXACT_MATCHING_PROFILE_EQUAL")
        self.assertTrue(compatible["strongDirectionalDiagnosisEligible"])

        plain = resolve_window_context(rows, ["2026-09-24"], shop_id="S1", policy=policy)
        different = qualify_context_pair(sep, plain, comparison_status="READY")
        self.assertEqual(different["status"], "CONTEXT_DIFFERENT")
        self.assertEqual(different["reason"], "EXACT_EVENT_ON_ONE_SIDE_ONLY")
        self.assertFalse(different["strongDirectionalDiagnosisEligible"])

        no_event = qualify_context_pair(plain, plain, comparison_status="READY")
        self.assertEqual(no_event["status"], "CONTEXT_UNKNOWN")
        self.assertEqual(no_event["reason"], "NO_EXACT_MATCHING_EVENT_ON_EITHER_SIDE")
        self.assertFalse(no_event["strongDirectionalDiagnosisEligible"])

    def test_non_shopee_context_is_not_qualifying_ads_context(self):
        policy = self._policy()
        rows = [self._row("2026-09-25", platform="tiktok_shop", context_id="tiktok")]
        summary = resolve_window_context(rows, ["2026-09-25"], shop_id="S1", policy=policy)
        self.assertEqual(summary["eventCount"], 0)
        self.assertEqual(summary["matchingSignature"], [])

    def test_binding_preserves_base_evidence_and_fail_closes_qualified_signals(self):
        policy = self._policy()
        signal = {"type": "Vấn đề", "productId": "P1", "causalClaim": False}
        different_snapshot = {
            "status": "READY",
            "coverageStart": "2026-09-25",
            "coverageEnd": "2026-09-25",
            "comparisonStatus": "READY",
            "comparisonStart": "2026-09-24",
            "comparisonEnd": "2026-09-24",
            "signals": [signal],
        }
        rows = [self._row("2026-09-25", context_id="payday_sep")]
        bind_snapshot_context(different_snapshot, context_rows=rows, shop_id="S1", policy=policy)
        self.assertEqual(different_snapshot["businessContext"]["matchEvaluation"], "CONTEXT_DIFFERENT")
        self.assertEqual(different_snapshot["signals"], [signal])
        self.assertEqual(different_snapshot["qualifiedSignals"], [])
        self.assertFalse(different_snapshot["strongDirectionalDiagnosisEligible"])

        compatible_snapshot = {
            "status": "READY",
            "coverageStart": "2026-09-25",
            "coverageEnd": "2026-09-25",
            "comparisonStatus": "READY",
            "comparisonStart": "2026-08-25",
            "comparisonEnd": "2026-08-25",
            "signals": [signal],
        }
        rows.append(self._row("2026-08-25", context_id="payday_aug"))
        bind_snapshot_context(compatible_snapshot, context_rows=rows, shop_id="S1", policy=policy)
        self.assertEqual(compatible_snapshot["businessContext"]["matchEvaluation"], "CONTEXT_COMPATIBLE")
        self.assertEqual(compatible_snapshot["qualifiedSignals"], [signal])
        self.assertTrue(compatible_snapshot["strongDirectionalDiagnosisEligible"])

    def test_artifact_binding_and_candidate_preview(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ads_dir = root / "ads"
            context_dir = root / "context"
            ads_dir.mkdir()
            context_dir.mkdir()
            contract = {
                "business_context_qualification": {
                    "enabled": True,
                    "mode": "DYNAMIC_ADS_CONTEXT_QUALIFICATION_V1",
                    "qualifying_platforms": ["shopee"],
                    "qualifying_context_families": ["PAYDAY"],
                    "strong_directional_diagnosis_rule": "CONTEXT_COMPATIBLE_ONLY",
                }
            }
            contract_path = root / "contract.json"
            contract_path.write_text(json.dumps(contract), encoding="utf-8")
            payload = {
                "meta": {
                    "asOfPeriod": "2026-09",
                    "adsIntelligenceFingerprint": "base-fp",
                },
                "capabilities": {},
                "shops": {
                    "S1": {
                        "displayName": "SYT+",
                        "periods": {
                            "day": {
                                "options": ["2026-09-25"],
                                "snapshots": {
                                    "2026-09-25": {
                                        "status": "READY",
                                        "coverageStart": "2026-09-25",
                                        "coverageEnd": "2026-09-25",
                                        "comparisonStatus": "READY",
                                        "comparisonStart": "2026-08-25",
                                        "comparisonEnd": "2026-08-25",
                                        "signals": [{"type": "Cơ hội", "productId": "P1", "causalClaim": False}],
                                    }
                                },
                            },
                            "week": {"options": [], "snapshots": {}},
                            "month": {"options": [], "snapshots": {}},
                            "year": {"options": [], "snapshots": {}},
                        },
                    }
                },
            }
            (ads_dir / "ads_intelligence.json").write_text(json.dumps(payload), encoding="utf-8")
            (ads_dir / "ads_intelligence_qa_report.json").write_text(json.dumps({"status": "PASS", "adsIntelligenceFingerprint": "base-fp"}), encoding="utf-8")
            (ads_dir / "ads_intelligence_manifest.json").write_text(json.dumps({"adsIntelligenceFingerprint": "base-fp", "files": ["ads_intelligence.json", "ads_intelligence_qa_report.json"]}), encoding="utf-8")
            rows = [
                self._row("2026-08-25", context_id="payday_aug"),
                self._row("2026-09-25", context_id="payday_sep"),
            ]
            (context_dir / "context_days.jsonl").write_text("\n".join(json.dumps(x) for x in rows) + "\n", encoding="utf-8")
            (context_dir / "context_manifest.json").write_text(json.dumps({
                "asOfPeriod": "2026-09",
                "contextBuildFingerprint": "context-fp",
            }), encoding="utf-8")

            result = bind_ads_business_context_artifacts(
                ads_output_dir=ads_dir,
                context_dir=context_dir,
                contract_path=contract_path,
            )
            rebound = json.loads((ads_dir / "ads_intelligence.json").read_text(encoding="utf-8"))
            preview = json.loads((ads_dir / "ads_context_candidate_preview.json").read_text(encoding="utf-8"))

        self.assertEqual(result["status"], "PASS")
        self.assertNotEqual(result["adsIntelligenceFingerprint"], "base-fp")
        snap = rebound["shops"]["S1"]["periods"]["day"]["snapshots"]["2026-09-25"]
        self.assertTrue(snap["strongDirectionalDiagnosisEligible"])
        self.assertEqual(len(snap["qualifiedSignals"]), 1)
        self.assertEqual(preview["shops"]["S1"]["scopes"]["day"]["matchEvaluation"], "CONTEXT_COMPATIBLE")
        self.assertFalse(preview["safety"]["productionActivationEnabled"])


if __name__ == "__main__":
    unittest.main()
