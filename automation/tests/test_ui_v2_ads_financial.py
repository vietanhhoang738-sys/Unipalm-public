import json
import unittest
from pathlib import Path

from modules import ui_v2_ads_financial as financial
from modules import ui_v2_ads_financial_polish as polish


class AdsFinancialUiV38Test(unittest.TestCase):
    def _effective_runtime(self):
        return polish.effective_financial_runtime({})

    def test_patch_version_and_financial_tokens(self):
        self.assertEqual(financial.ADS_FINANCIAL_PATCH_VERSION, "native-ads-financial-v38")
        self.assertEqual(financial.ADS_GROUP_RULE_VERSION, "ads-product-group-v1")
        self.assertEqual(polish.ADS_FINANCIAL_POLISH_VERSION, "ads-financial-polish-v2")
        style = polish.effective_financial_style()
        runtime = self._effective_runtime()
        for token in (
            "Phương trình hiệu quả Ads", "GMV Ads", "Chi tiêu Ads", "AOV",
            "Chuyển đổi", "Hiển thị", "CTR", "CR", "CPC", "Click",
            "Diễn biến trong kỳ", "Funnel Ads", "Áp lực chi phí",
            "1W", "1M", "3M", "6M", "Phân bổ hiệu quả",
            "Bản đồ CPC × ROAS", "Ads Intelligence Desk", "Nhóm SP",
            "dữ liệu Ads đã xác thực", "THAM KHẢO",
        ):
            self.assertIn(token, runtime)
        for css_token in (
            ".ads-equation{", ".ads-fin-kpis{", ".ads-cost-grid{",
            ".ads-intelligence-desk{", ".ads-fin-entity-tabs{",
        ):
            self.assertIn(css_token, style)
        self.assertNotIn("font-family:", style)
        self.assertNotIn("var(--green-soft)", style)
        self.assertIn("font:inherit", style)

    def test_effective_runtime_passes_hard_language_contract(self):
        contract_path = Path(__file__).resolve().parents[2] / "config" / "ui_v2_presentation_contract.json"
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        forbidden = list((contract.get("language_system") or {}).get("forbidden_visible_phrases") or [])
        runtime = self._effective_runtime()
        hits = [phrase for phrase in forbidden if phrase in runtime]
        self.assertEqual(hits, [])
        for legacy_copy in ("Ads Spend", "trusted history", "Spend share", "EVIDENCE ONLY"):
            self.assertNotIn(legacy_copy, runtime)

    def test_group_resolver(self):
        cases = [
            ("Khẩu trang chống tia UV Unipalm Cool S2 UPF50+", "Khẩu trang"),
            ("Găng tay chống nắng Unipalm Air S4", "Găng tay"),
            ("Ống tay chống nắng Unipalm Air F2", "Ống tay"),
            ("Cặp đôi yêu kiều Khẩu trang Cool S2 & Găng tay Air S4", "Cặp đôi / Combo"),
            ("Combo 2 Khẩu trang chống tia UV Unipalm Cool S3", "Cặp đôi / Combo"),
            ("Thẻ kiểm tra tia UV Unipalm", "Khác"),
        ]
        for name, expected in cases:
            with self.subTest(name=name):
                self.assertEqual(financial._ads_group({"productName": name}), expected)

    def test_entity_map_preserves_short_name_and_adds_group(self):
        payload = {
            "destinations": {
                "ads": {
                    "shops": {
                        "S1": {
                            "periods": {
                                "day": {
                                    "snapshots": {
                                        "2026-09-27": {
                                            "products": [
                                                {
                                                    "productId": "P1",
                                                    "productName": "Găng tay chống nắng chống tia UV Unipalm Air S2",
                                                    "productSku": "GL002",
                                                }
                                            ]
                                        }
                                    }
                                },
                                "week": {"snapshots": {}},
                                "month": {"snapshots": {}},
                                "year": {"snapshots": {}},
                            }
                        }
                    }
                }
            }
        }
        mapped = financial.build_ads_entity_map(payload)
        self.assertEqual(mapped["S1"]["P1"]["group"], "Găng tay")
        self.assertIn("Air S2", mapped["S1"]["P1"]["displayName"])
        self.assertEqual(mapped["S1"]["P1"]["groupRuleVersion"], "ads-product-group-v1")

    def test_intelligence_is_after_data_sections(self):
        runtime = self._effective_runtime()
        self.assertLess(runtime.index("Phương trình hiệu quả Ads"), runtime.index("Ads Intelligence Desk"))
        self.assertLess(runtime.index("Funnel Ads"), runtime.index("Ads Intelligence Desk"))
        self.assertLess(runtime.index("Áp lực chi phí"), runtime.index("Ads Intelligence Desk"))
        self.assertIn("không phải kết luận quan hệ nhân quả", runtime)
        self.assertIn("Chưa đủ dữ liệu", runtime)

    def test_benchmark_windows_are_fail_closed(self):
        runtime = self._effective_runtime()
        self.assertIn("windowSummary(7)", runtime)
        self.assertIn("windowSummary(30)", runtime)
        self.assertIn("windowSummary(90)", runtime)
        self.assertIn("windowSummary(180)", runtime)
        self.assertIn("allTrusted.has(cursor)", runtime)
        self.assertIn("Chưa đủ dữ liệu", runtime)


if __name__ == "__main__":
    unittest.main()
