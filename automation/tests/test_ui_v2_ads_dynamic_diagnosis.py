import json
import unittest
from pathlib import Path

from modules import ui_v2_ads_dynamic_diagnosis as diagnosis_ui
from modules import ui_v2_ads_financial as financial


class AdsDynamicDiagnosisUiTest(unittest.TestCase):
    def test_additive_wrapper_keeps_financial_v38_locked(self):
        self.assertEqual(financial.ADS_FINANCIAL_PATCH_VERSION, "native-ads-financial-v38")
        self.assertEqual(diagnosis_ui.ADS_DYNAMIC_DIAGNOSIS_UI_VERSION, "ads-dynamic-diagnosis-ui-v1")
        self.assertIn(".ads-desk-gate{", diagnosis_ui.DIAGNOSIS_STYLE)
        self.assertIn(".ads-desk-priority{", diagnosis_ui.DIAGNOSIS_STYLE)
        self.assertNotIn("font-family:", diagnosis_ui.DIAGNOSIS_STYLE)

    def test_effective_runtime_consumes_dynamic_diagnosis_not_raw_signals(self):
        runtime = diagnosis_ui.effective_dynamic_diagnosis_runtime({})
        self.assertIn("snap.dynamicDiagnosis||{}", runtime)
        self.assertIn("diag.items||[]", runtime)
        self.assertNotIn("const rawSignals=snap.signals||[]", runtime)
        self.assertIn("Chẩn đoán chỉ xuất hiện khi hai kỳ có bối cảnh bán hàng tương đồng.", runtime)
        self.assertIn("Chẩn đoán đang được khóa", runtime)
        self.assertIn("Chưa có chẩn đoán nổi bật", runtime)
        self.assertIn("reviewFocus", runtime)
        self.assertIn("priorityTier", runtime)
        self.assertIn("confidenceTier", runtime)

    def test_operator_language_contract_still_passes(self):
        contract_path = Path(__file__).resolve().parents[2] / "config" / "ui_v2_presentation_contract.json"
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        forbidden = list((contract.get("language_system") or {}).get("forbidden_visible_phrases") or [])
        runtime = diagnosis_ui.effective_dynamic_diagnosis_runtime({})
        hits = [phrase for phrase in forbidden if phrase in runtime]
        self.assertEqual(hits, [])
        for legacy_copy in ("Ads Spend", "trusted history", "Spend share", "EVIDENCE ONLY"):
            self.assertNotIn(legacy_copy, runtime)

    def test_data_first_order_is_unchanged(self):
        runtime = diagnosis_ui.effective_dynamic_diagnosis_runtime({})
        self.assertLess(runtime.index("Phương trình hiệu quả Ads"), runtime.index("Ads Intelligence Desk"))
        self.assertLess(runtime.index("Funnel Ads"), runtime.index("Ads Intelligence Desk"))
        self.assertLess(runtime.index("Áp lực chi phí"), runtime.index("Ads Intelligence Desk"))
        self.assertIn("không phải kết luận quan hệ nhân quả", runtime)


if __name__ == "__main__":
    unittest.main()
