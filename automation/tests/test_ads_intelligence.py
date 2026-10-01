import json
import tempfile
import unittest
from pathlib import Path

from modules.ads_intelligence import build_ads_intelligence


class AdsIntelligenceFoundationTest(unittest.TestCase):
    def _contract(self, root: Path) -> Path:
        contract = {
            "version": "1.0",
            "layer_name": "multi_shop_ads_intelligence_v1",
            "status": "PREPRODUCTION",
            "source_policy": {
                "trusted_history_source": "PUBLISHED_SEMANTIC_QA_PASS",
                "canonical_grain": "DAILY",
            },
            "scope_policy": {
                "single_shop_only": True,
                "cross_shop_compare_allowed": False,
                "allowed_time_scopes": ["day", "week", "month", "year"],
            },
            "intelligence_policy": {
                "product_signal_min_spend_share": 0.03,
                "product_signal_min_abs_roas_delta": 0.15,
                "product_signal_max_count": 8,
            },
            "safety": {
                "write_production_data_mart": False,
                "modify_production_ui": False,
                "publish_legacy_payload": False,
                "platform_mutation_allowed": False,
                "production_activation_enabled": False,
            },
        }
        path = root / "ads_contract.json"
        path.write_text(json.dumps(contract), encoding="utf-8")
        return path

    def _dates(self, start: str, count: int):
        import datetime as dt
        cur = dt.datetime.strptime(start, "%Y-%m-%d").date()
        return [(cur + dt.timedelta(days=x)).isoformat() for x in range(count)]

    def _rows(self, shop_id: str, dates, scale=1.0):
        shop = []
        products = []
        final_week_start = max(1, len(dates) - 6)
        for idx, date in enumerate(dates, 1):
            # Shop-level CVR improves in the later history so the ROAS identity
            # itself has a measurable period-over-period change.
            conv = 10 if idx <= len(dates) // 2 else 16
            clicks = 100
            spend = 200000 * scale
            sales = conv * 100000 * scale
            shop.append({
                "shop_id": shop_id, "data_date": date,
                "impressions": 4000, "clicks": clicks, "add_to_cart": 20,
                "conversions": conv, "units_sold": conv,
                "attributed_sales": sales, "ad_spend": spend,
            })
            # P2 deteriorates only in the final seven days. This deliberately
            # makes the latest 7D window differ from the immediately prior 7D,
            # so the test crosses the 15% product-signal threshold without
            # weakening production policy.
            p2_roas_mult = .45 if idx >= final_week_start else 1.0
            for pid, share, roas_mult in (("P1", .7, 1.0), ("P2", .3, p2_roas_mult)):
                pspend = spend * share
                pconv = max(1, int(conv * share))
                psales = pconv * 100000 * scale * roas_mult
                products.append({
                    "shop_id": shop_id, "data_date": date, "product_id": pid,
                    "product_name": f"Product {pid}", "product_sku": pid,
                    "impressions": int(4000 * share), "clicks": int(clicks * share),
                    "add_to_cart": int(20 * share), "conversions": pconv,
                    "units_sold": pconv, "attributed_sales": psales,
                    "ad_spend": pspend,
                })
        return shop, products

    def test_ads_daily_scopes_and_lifecycle_year_availability(self):
        dates = self._dates("2026-07-01", 89)  # through 2026-09-27
        s1, p1 = self._rows("S1", dates)
        s2, p2 = self._rows("S2", dates, .7)
        shops = [
            {"shop_id": "S1", "shop_key": "syt", "display_name": "SYT+", "history_lifecycle": {"origin": "PREEXISTING_BEFORE_TRUSTED_WINDOW"}},
            {"shop_id": "S2", "shop_key": "mall", "display_name": "Mall", "history_lifecycle": {"origin": "SHOP_LAUNCH", "start_policy": "FIRST_TRUSTED_SEMANTIC_DATE"}},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = build_ads_intelligence(
                ads_rows=s1 + s2,
                ads_product_rows=p1 + p2,
                shops=shops,
                trusted_months=["2026-07", "2026-08", "2026-09"],
                trusted_fingerprints=["a", "b", "c"],
                as_of_period="2026-09",
                contract_path=self._contract(root),
                output_dir=root / "out",
            )
            payload = json.loads((root / "out/ads_intelligence.json").read_text())
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(payload["scopePolicy"]["allowedTimeScopes"], ["day", "week", "month", "year"])
        syt = payload["shops"]["S1"]["periods"]
        mall = payload["shops"]["S2"]["periods"]
        self.assertEqual(syt["asOfDate"], "2026-09-27")
        self.assertEqual(syt["month"]["snapshots"]["2026-09"]["status"], "READY")
        self.assertEqual(syt["year"]["snapshots"]["2026"]["status"], "INSUFFICIENT_HISTORY")
        self.assertEqual(mall["year"]["snapshots"]["2026"]["status"], "READY")
        week = syt["week"]["snapshots"]["2026-09-27"]
        self.assertEqual(week["status"], "READY")
        self.assertEqual(week["comparisonStatus"], "READY")
        self.assertFalse(week["causalClaim"])
        self.assertFalse(week["driverAttribution"]["causalClaim"])

    def test_ratios_recomputed_and_signals_noncausal(self):
        dates = self._dates("2026-08-20", 39)
        s1, p1 = self._rows("S1", dates)
        shops = [{"shop_id": "S1", "shop_key": "syt", "display_name": "SYT+", "history_lifecycle": {"origin": "PREEXISTING_BEFORE_TRUSTED_WINDOW"}}]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build_ads_intelligence(
                ads_rows=s1, ads_product_rows=p1, shops=shops,
                trusted_months=["2026-08", "2026-09"], trusted_fingerprints=["a", "b"],
                as_of_period="2026-09", contract_path=self._contract(root), output_dir=root / "out",
            )
            payload = json.loads((root / "out/ads_intelligence.json").read_text())
        snap = payload["shops"]["S1"]["periods"]["week"]["snapshots"]["2026-09-27"]
        sm = snap["summary"]
        self.assertAlmostEqual(sm["roas"], sm["attributedSales"] / sm["adSpend"])
        self.assertAlmostEqual(sm["ctr"], sm["clicks"] / sm["impressions"])
        self.assertAlmostEqual(sm["cvr"], sm["conversions"] / sm["clicks"])
        self.assertAlmostEqual(sm["cpc"], sm["adSpend"] / sm["clicks"])
        self.assertTrue(snap["signals"])
        self.assertTrue(all(not x["causalClaim"] for x in snap["signals"]))
        self.assertEqual(snap["driverAttribution"]["status"], "ATTRIBUTED")
        self.assertIn(snap["driverAttribution"]["topDriverMetric"], {"cvr", "adsAov", "cpc"})


if __name__ == "__main__":
    unittest.main()
