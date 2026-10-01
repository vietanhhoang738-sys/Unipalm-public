import unittest

from modules import ui_v2_ads_financial as financial
from modules import ui_v2_ads_dynamic_diagnosis as diagnosis_ui
from modules import ui_v2_ads_diagnosis_persistence as persistence_ui
from modules import ui_v2_ads_smart_issue_candidates as candidate_ui


class AdsSmartIssueCandidateUiTest(unittest.TestCase):
    def test_locked_lower_layers_remain_unchanged(self):
        self.assertEqual(financial.ADS_FINANCIAL_PATCH_VERSION, "native-ads-financial-v38")
        self.assertEqual(diagnosis_ui.ADS_DYNAMIC_DIAGNOSIS_UI_VERSION, "ads-dynamic-diagnosis-ui-v1")
        self.assertEqual(persistence_ui.ADS_DIAGNOSIS_PERSISTENCE_UI_VERSION, "ads-diagnosis-persistence-ui-v1")
        self.assertEqual(candidate_ui.ADS_SMART_ISSUE_CANDIDATE_UI_VERSION, "ads-smart-issue-candidate-ui-v1")

    def test_effective_runtime_keeps_diagnosis_and_persistence_gates(self):
        runtime = candidate_ui.effective_smart_issue_candidate_runtime({})
        self.assertIn("snap.dynamicDiagnosis||{}", runtime)
        self.assertIn("diag.items||[]", runtime)
        self.assertNotIn("const rawSignals=snap.signals||[]", runtime)
        self.assertIn("Chẩn đoán chỉ xuất hiện khi hai kỳ có bối cảnh bán hàng tương đồng.", runtime)
        self.assertIn("Độ bền chỉ được xác nhận bằng các cửa sổ độc lập cùng scope và cùng bối cảnh.", runtime)
        self.assertIn("Ứng viên Smart Issue chỉ được đánh dấu", runtime)
        self.assertIn("smartIssueCandidate", runtime)
        self.assertIn("evidenceAgeDays", runtime)
        self.assertIn("lifecycleState", runtime)

    def test_candidate_badge_is_conditional_not_automatic_issue(self):
        runtime = candidate_ui.effective_smart_issue_candidate_runtime({})
        self.assertIn("(sig.smartIssueCandidate||{}).eligible", runtime)
        self.assertIn("Ứng viên Smart Issue", runtime)
        self.assertNotIn("Tự động xử lý", runtime)
        self.assertNotIn("Tự động cảnh báo", runtime)
        self.assertIn("Đã xác nhận", runtime)

    def test_data_first_order_remains_unchanged(self):
        runtime = candidate_ui.effective_smart_issue_candidate_runtime({})
        self.assertLess(runtime.index("Phương trình hiệu quả Ads"), runtime.index("Ads Intelligence Desk"))
        self.assertLess(runtime.index("Funnel Ads"), runtime.index("Ads Intelligence Desk"))
        self.assertLess(runtime.index("Áp lực chi phí"), runtime.index("Ads Intelligence Desk"))
        self.assertIn("không phải kết luận quan hệ nhân quả", runtime)


if __name__ == "__main__":
    unittest.main()
