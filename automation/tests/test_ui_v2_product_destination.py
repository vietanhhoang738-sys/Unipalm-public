import unittest

from modules import ui_v2_product_destination as product_ui


class UiV2ProductDestinationTest(unittest.TestCase):
    def test_product_native_contract_tokens(self):
        self.assertEqual(product_ui.PRODUCT_NATIVE_PATCH_VERSION, "native-product-intelligence-v34")
        self.assertIn('q.get("destination")!=="product"', product_ui.PRODUCT_RUNTIME)
        self.assertIn('productHorizon', product_ui.PRODUCT_RUNTIME)
        for label in (
            "1 tháng", "3 tháng", "6 tháng", "Năm", "Sản phẩm", "Tóm tắt sản phẩm",
            "Cơ cấu danh mục", "Hiệu quả funnel sản phẩm", "Chi tiết sản phẩm",
            "So sánh 3 tháng hoàn tất gần nhất", "tháng hiện tại chỉ dùng đối chiếu bổ sung",
            "Shop chưa đủ tuổi dữ liệu cho phân tích cấu trúc", "Yếu tố chính:",
            "GMV = Lượt nhấp sản phẩm × CVR × AOV", "không phải kết luận quan hệ nhân quả",
        ):
            self.assertIn(label, product_ui.PRODUCT_RUNTIME)
        self.assertNotIn("Product Clicks", product_ui.PRODUCT_RUNTIME)
        self.assertNotIn("Driver chính:", product_ui.PRODUCT_RUNTIME)
        self.assertNotIn("trusted history", product_ui.PRODUCT_RUNTIME)
        self.assertIn(".product-signal-driver{", product_ui.PRODUCT_STYLE)
        self.assertNotIn("font-family", product_ui.PRODUCT_STYLE)
        self.assertNotIn("data-native-scope=\"compare\"", product_ui.PRODUCT_RUNTIME)

    def _base_payload(self):
        return {
            "destinations": {
                "product": {
                    "scopePolicy": {
                        "singleShopOnly": True,
                        "compareAllowed": False,
                        "canonicalSourceGrain": "MONTHLY",
                        "allowedTimeScopes": ["oneMonth", "threeMonths", "sixMonths", "year"],
                        "dayWeekForbidden": True,
                    },
                    "shops": {
                        "S1": {
                            "compareAllowed": False,
                            "sourceGrain": "MONTHLY",
                            "horizons": {
                                "oneMonth": {"status": "READY", "products": []},
                                "threeMonths": {"status": "READY", "products": []},
                                "sixMonths": {"status": "INSUFFICIENT_HISTORY", "products": []},
                                "year": {"status": "INSUFFICIENT_HISTORY", "products": []},
                            },
                            "structuralIntelligence": {"status": "INSUFFICIENT_HISTORY"},
                        }
                    },
                }
            }
        }

    def test_product_payload_is_single_shop_monthly_family_only(self):
        product_ui._validate_product_payload(self._base_payload())

    def test_unavailable_horizon_cannot_contain_products(self):
        payload = self._base_payload()
        payload["destinations"]["product"]["shops"]["S1"]["horizons"]["sixMonths"] = {
            "status": "INSUFFICIENT_HISTORY",
            "products": [{"productId": "P1"}],
        }
        with self.assertRaises(ValueError):
            product_ui._validate_product_payload(payload)

    def test_structural_ready_requires_mtd_corroborating_only(self):
        payload = self._base_payload()
        payload["destinations"]["product"]["shops"]["S1"]["structuralIntelligence"] = {
            "status": "READY",
            "currentPartialMonthRole": "IN_SCORE",
            "signals": [],
        }
        with self.assertRaises(ValueError):
            product_ui._validate_product_payload(payload)

    def test_structural_ready_rejects_causal_claims(self):
        payload = self._base_payload()
        payload["destinations"]["product"]["shops"]["S1"]["structuralIntelligence"] = {
            "status": "READY",
            "currentPartialMonthRole": "CORROBORATING_ONLY_NOT_SCORED",
            "signals": [{
                "productId": "P1",
                "causalClaim": False,
                "driverAttribution": {"status": "ATTRIBUTED", "causalClaim": True},
            }],
        }
        with self.assertRaises(ValueError):
            product_ui._validate_product_payload(payload)

    def test_structural_ready_accepts_noncausal_driver_attribution(self):
        payload = self._base_payload()
        payload["destinations"]["product"]["shops"]["S1"]["structuralIntelligence"] = {
            "status": "READY",
            "currentPartialMonthRole": "CORROBORATING_ONLY_NOT_SCORED",
            "signals": [{
                "productId": "P1",
                "causalClaim": False,
                "driverAttribution": {
                    "status": "ATTRIBUTED",
                    "causalClaim": False,
                    "topDriverMetric": "cvr",
                },
            }],
        }
        product_ui._validate_product_payload(payload)


if __name__ == "__main__":
    unittest.main()
