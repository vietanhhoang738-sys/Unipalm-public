import unittest

from modules.ui_v2_ads_destination import (
    ADS_NATIVE_PATCH_VERSION,
    ADS_STYLE,
    build_ads_short_name_map,
    _validate_ads_payload,
)


class UiV2AdsDestinationTest(unittest.TestCase):
    def _payload(self):
        return {
            "destinations": {
                "ads": {
                    "scopePolicy": {
                        "singleShopOnly": True,
                        "compareAllowed": False,
                        "canonicalSourceGrain": "DAILY",
                        "allowedTimeScopes": ["day", "week", "month", "year"],
                    },
                    "shops": {
                        "S1": {
                            "sourceGrain": "DAILY",
                            "compareAllowed": False,
                            "timeScopeOrder": ["day", "week", "month", "year"],
                            "periods": {
                                "week": {
                                    "options": ["2026-09-27"],
                                    "snapshots": {
                                        "2026-09-27": {
                                            "status": "READY",
                                            "causalClaim": False,
                                            "driverAttribution": {"status": "ATTRIBUTED", "causalClaim": False},
                                            "signals": [{
                                                "productId": "P1",
                                                "productName": "Găng tay chống nắng chống tia UV 99% UPF 50+ Unipalm Air S2 cho nữ",
                                                "productSku": "GL002",
                                                "causalClaim": False,
                                            }],
                                            "products": [{
                                                "productId": "P1",
                                                "productName": "Găng tay chống nắng chống tia UV 99% UPF 50+ Unipalm Air S2 cho nữ",
                                                "productSku": "GL002",
                                            }],
                                        }
                                    },
                                }
                            },
                        }
                    },
                }
            }
        }

    def test_ads_native_tokens_and_responsive_layout(self):
        self.assertEqual(ADS_NATIVE_PATCH_VERSION, "native-ads-intelligence-v37")
        self.assertIn(".ads-destination{", ADS_STYLE)
        self.assertIn(".ads-signal-strip{", ADS_STYLE)
        self.assertIn("@media(max-width:680px)", ADS_STYLE)
        self.assertNotIn("font-family", ADS_STYLE)

    def test_ads_payload_is_single_shop_daily_only(self):
        _validate_ads_payload(self._payload())

    def test_ads_payload_rejects_compare(self):
        payload = self._payload()
        payload["destinations"]["ads"]["scopePolicy"]["compareAllowed"] = True
        with self.assertRaises(ValueError):
            _validate_ads_payload(payload)

    def test_ads_payload_rejects_causal_claim(self):
        payload = self._payload()
        payload["destinations"]["ads"]["shops"]["S1"]["periods"]["week"]["snapshots"]["2026-09-27"]["signals"][0]["causalClaim"] = True
        with self.assertRaises(ValueError):
            _validate_ads_payload(payload)

    def test_ads_reuses_product_short_name_system(self):
        result = build_ads_short_name_map(self._payload())
        self.assertEqual(result["S1"]["P1"]["displayName"], "Găng tay Air S2")
        self.assertIn("Găng tay chống nắng", result["S1"]["P1"]["fullName"])


if __name__ == "__main__":
    unittest.main()
