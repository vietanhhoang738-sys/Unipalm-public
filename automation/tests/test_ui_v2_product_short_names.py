import unittest

from modules.ui_v2_product_short_names import (
    PRODUCT_SHORT_NAME_PATCH_VERSION,
    SHORT_NAME_STYLE,
    _runtime_for_map,
    build_short_name_map,
)


class UiV2ProductShortNamesTest(unittest.TestCase):
    def test_patch_version_and_factor_pill_wrap(self):
        self.assertEqual(PRODUCT_SHORT_NAME_PATCH_VERSION, "native-product-intelligence-v36-short-names")
        self.assertIn("white-space:normal", SHORT_NAME_STYLE)
        self.assertIn("overflow-wrap:anywhere", SHORT_NAME_STYLE)
        self.assertNotIn("text-overflow:ellipsis", SHORT_NAME_STYLE)

    def test_bi_order_aov_lineage_is_visible(self):
        runtime = _runtime_for_map({})
        self.assertIn('summary.orderSemantics==="UNIQUE_SHOP_ORDERS"', runtime)
        self.assertIn("· BI", runtime)
        self.assertIn("Số đơn và AOV lấy từ Business Insights ở cấp shop", runtime)

    def test_map_uses_short_names_without_mutating_full_name(self):
        payload = {
            "destinations": {
                "product": {
                    "shops": {
                        "S1": {
                            "horizons": {
                                "oneMonth": {
                                    "products": [{
                                        "productId": "P1",
                                        "productName": "Găng tay chống nắng chống tia UV 99% UPF 50+ Unipalm Air S2 cho nữ chạy xe hở đầu ngón tay cảm ứng",
                                        "resolvedParentSku": "GL002",
                                    }]
                                }
                            },
                            "structuralIntelligence": {"signals": []},
                        }
                    }
                }
            }
        }
        result = build_short_name_map(payload)["S1"]["P1"]
        self.assertEqual(result["displayName"], "Găng tay Air S2")
        self.assertIn("Găng tay chống nắng", result["fullName"])

    def test_collision_guard_disambiguates_same_alias(self):
        payload = {
            "destinations": {
                "product": {
                    "shops": {
                        "S1": {
                            "horizons": {
                                "year": {
                                    "products": [
                                        {"productId": "100001", "productName": "Thẻ kiểm tra tia UVA UVB Unipalm", "resolvedParentSku": "PK001"},
                                        {"productId": "100002", "productName": "[Quà tặng] Thẻ test tia UVA UVB Unipalm", "resolvedParentSku": "PK001"},
                                    ]
                                }
                            },
                            "structuralIntelligence": {"signals": []},
                        }
                    }
                }
            }
        }
        result = build_short_name_map(payload)["S1"]
        self.assertNotEqual(result["100001"]["displayName"], result["100002"]["displayName"])
        self.assertTrue(result["100001"].get("collisionGuardApplied"))
        self.assertTrue(result["100002"].get("collisionGuardApplied"))


if __name__ == "__main__":
    unittest.main()
