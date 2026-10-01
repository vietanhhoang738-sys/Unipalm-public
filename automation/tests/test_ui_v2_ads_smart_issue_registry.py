import unittest

from modules import ui_v2_ads_financial as financial
from modules import ui_v2_ads_dynamic_diagnosis as diagnosis_ui
from modules import ui_v2_ads_diagnosis_persistence as persistence_ui
from modules import ui_v2_ads_smart_issue_candidates as candidate_ui
from modules import ui_v2_ads_smart_issue_registry as registry_ui


class AdsSmartIssueRegistryUiTest(unittest.TestCase):
    def test_locked_lower_layers_remain_unchanged(self):
        self.assertEqual(financial.ADS_FINANCIAL_PATCH_VERSION, "native-ads-financial-v38")
        self.assertEqual(diagnosis_ui.ADS_DYNAMIC_DIAGNOSIS_UI_VERSION, "ads-dynamic-diagnosis-ui-v1")
        self.assertEqual(persistence_ui.ADS_DIAGNOSIS_PERSISTENCE_UI_VERSION, "ads-diagnosis-persistence-ui-v1")
        self.assertEqual(candidate_ui.ADS_SMART_ISSUE_CANDIDATE_UI_VERSION, "ads-smart-issue-candidate-ui-v1")
        self.assertEqual(registry_ui.ADS_SMART_ISSUE_REGISTRY_UI_VERSION, "ads-smart-issue-registry-ui-v1")

    def test_registry_wraps_current_candidate_card_shape(self):
        candidate_card = candidate_ui._enhanced_candidate_card()
        self.assertEqual(candidate_card.count("+'</div>').join('')"), 1)
        registry_card = registry_ui._enhanced_registry_card()
        self.assertIn("Ứng viên Smart Issue", registry_card)
        self.assertIn("humanReview", registry_card)
        self.assertIn("Chờ review", registry_card)
        self.assertIn("Cần review mở lại", registry_card)
        self.assertIn("Đã hoãn", registry_card)
        self.assertIn("Đã bỏ qua", registry_card)

    def test_effective_runtime_preserves_all_upstream_gates(self):
        runtime = registry_ui.effective_smart_issue_registry_runtime({})
        self.assertIn("snap.dynamicDiagnosis||{}", runtime)
        self.assertIn("diag.items||[]", runtime)
        self.assertNotIn("const rawSignals=snap.signals||[]", runtime)
        self.assertIn("Chẩn đoán chỉ xuất hiện khi hai kỳ có bối cảnh bán hàng tương đồng.", runtime)
        self.assertIn("Độ bền chỉ được xác nhận bằng các cửa sổ độc lập cùng scope và cùng bối cảnh.", runtime)
        self.assertIn("Ứng viên Smart Issue chỉ được đánh dấu", runtime)
        self.assertIn("Smart Issue chỉ được mở hoặc đổi trạng thái sau một review event rõ ràng của operator", runtime)
        self.assertIn("smartIssueCandidate", runtime)
        self.assertIn("humanReview", runtime)

    def test_review_badge_is_read_only_and_candidate_gated(self):
        runtime = registry_ui.effective_smart_issue_registry_runtime({})
        self.assertIn("(sig.smartIssueCandidate||{}).eligible", runtime)
        self.assertIn("LINKED_ISSUE", runtime)
        self.assertIn("REOPEN_REVIEW_REQUIRED", runtime)
        self.assertIn("DEFERRED", runtime)
        self.assertIn("DISMISSED", runtime)
        self.assertNotIn("autoPromoteSmartIssue", runtime)
        self.assertNotIn("Tự động mở Smart Issue", runtime)
        self.assertNotIn("Tự động xử lý", runtime)
        self.assertNotIn("Tự động cảnh báo", runtime)

    def test_data_first_order_remains_unchanged(self):
        runtime = registry_ui.effective_smart_issue_registry_runtime({})
        self.assertLess(runtime.index("Phương trình hiệu quả Ads"), runtime.index("Ads Intelligence Desk"))
        self.assertLess(runtime.index("Funnel Ads"), runtime.index("Ads Intelligence Desk"))
        self.assertLess(runtime.index("Áp lực chi phí"), runtime.index("Ads Intelligence Desk"))
        self.assertIn("không phải kết luận quan hệ nhân quả", runtime)


if __name__ == "__main__":
    unittest.main()
