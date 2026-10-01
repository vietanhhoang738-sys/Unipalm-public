import json
import unittest
from pathlib import Path

from modules import ui_v2_ads_diagnosis_persistence as persistence_ui
from modules import ui_v2_ads_dynamic_diagnosis as diagnosis_ui
from modules import ui_v2_ads_financial as financial


class AdsDiagnosisPersistenceUiTest(unittest.TestCase):
    def test_wrapper_keeps_locked_layers_intact(self):
        self.assertEqual(financial.ADS_FINANCIAL_PATCH_VERSION, "native-ads-financial-v38")
        self.assertEqual(diagnosis_ui.ADS_DYNAMIC_DIAGNOSIS_UI_VERSION, "ads-dynamic-diagnosis-ui-v1")
        self.assertEqual(persistence_ui.ADS_DIAGNOSIS_PERSISTENCE_UI_VERSION, "ads-diagnosis-persistence-ui-v1")
        self.assertIn(".ads-desk-persistence{", persistence_ui.PERSISTENCE_STYLE)
        self.assertNotIn("font-family:", persistence_ui.PERSISTENCE_STYLE)

    def test_runtime_adds_persistence_without_reopening_raw_signals(self):
        runtime = persistence_ui.effective_persistence_runtime({})
        self.assertIn("snap.dynamicDiagnosis||{}", runtime)
        self.assertIn("diag.items||[]", runtime)
        self.assertNotIn("const rawSignals=snap.signals||[]", runtime)
        self.assertIn("supportWindowCount", runtime)
        self.assertIn("eligibleIndependentWindowCount", runtime)
        self.assertIn("Đã xác nhận", runtime)
        self.assertIn("Mâu thuẫn", runtime)
        self.assertIn("Một lần", runtime)
        self.assertIn("Lần đầu", runtime)
        self.assertIn("các cửa sổ độc lập cùng scope và cùng bối cảnh", runtime)

    def test_operator_language_contract_still_passes(self):
        contract_path = Path(__file__).resolve().parents[2] / "config" / "ui_v2_presentation_contract.json"
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        forbidden = list((contract.get("language_system") or {}).get("forbidden_visible_phrases") or [])
        runtime = persistence_ui.effective_persistence_runtime({})
        hits = [phrase for phrase in forbidden if phrase in runtime]
        self.assertEqual(hits, [])
        for legacy_copy in ("Ads Spend", "trusted history", "Spend share", "EVIDENCE ONLY"):
            self.assertNotIn(legacy_copy, runtime)

    def test_data_first_order_and_safety_copy_remain(self):
        runtime = persistence_ui.effective_persistence_runtime({})
        self.assertLess(runtime.index("Phương trình hiệu quả Ads"), runtime.index("Ads Intelligence Desk"))
        self.assertLess(runtime.index("Funnel Ads"), runtime.index("Ads Intelligence Desk"))
        self.assertLess(runtime.index("Áp lực chi phí"), runtime.index("Ads Intelligence Desk"))
        self.assertIn("không phải kết luận quan hệ nhân quả", runtime)
        self.assertNotIn("Smart Issue candidate", runtime)


if __name__ == "__main__":
    unittest.main()
