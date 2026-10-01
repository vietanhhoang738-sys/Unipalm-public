import json
import tempfile
import unittest
from pathlib import Path

from modules.product_intelligence import build_product_intelligence


class ProductIntelligenceFoundationTest(unittest.TestCase):
    def _contract(self, root: Path) -> Path:
        contract = {
            "version": "1.1",
            "layer_name": "multi_shop_product_intelligence_v1",
            "status": "PREPRODUCTION",
            "source_policy": {
                "trusted_history_sources": [
                    "PUBLISHED_SEMANTIC_QA_PASS",
                    "PUBLISHED_PROCESSED_QA_PASS_THROUGH_PRODUCT_SEMANTIC_ADAPTER",
                ],
                "canonical_mart": "dm_product_monthly",
                "daily_or_weekly_product_scope_forbidden": True,
            },
            "scope_policy": {"single_shop_only": True, "cross_shop_compare_allowed": False},
            "horizons": {"order": ["oneMonth", "threeMonths", "sixMonths", "year"]},
            "intelligence_policy": {
                "minimum_complete_months_for_structural_signal": 6,
                "current_partial_month_role": "CORROBORATING_ONLY",
            },
            "safety": {
                "write_production_data_mart": False,
                "modify_production_ui": False,
                "publish_legacy_payload": False,
                "platform_mutation_allowed": False,
                "production_activation_enabled": False,
            },
        }
        path = root / "contract.json"
        path.write_text(json.dumps(contract), encoding="utf-8")
        return path

    def _rows(self, shop_id, months, scale=1.0):
        rows = []
        for idx, month in enumerate(months, 1):
            for pid, mult in (("P1", 1.0), ("P2", 0.4)):
                gmv = (1000 + idx * 120) * mult * scale
                orders = max(1, int(gmv / 100))
                views = orders * 30
                clicks = orders * 8
                visits = orders * 6
                rows.append({
                    "shop_id": shop_id,
                    "data_month": month,
                    "product_id": pid,
                    "product_name": f"Product {pid}",
                    "resolved_parent_sku": pid,
                    "product_status": "active",
                    "current_listing_present": True,
                    "placed_gmv": gmv,
                    "placed_orders": orders,
                    "confirmed_gmv": gmv * .9,
                    "confirmed_orders": max(1, orders - 1),
                    "product_views": views,
                    "product_clicks": clicks,
                    "product_visits": visits,
                    "product_page_views": visits * 2,
                    "page_bounces": visits // 5,
                    "add_to_cart_visits": orders * 2,
                    "add_to_cart_units": orders * 2,
                    "confirmed_units": orders,
                    "confirmed_buyers": orders,
                    "repeat_order_rate": .2,
                    "avg_days_to_repeat": 30,
                    "ads_impressions": views * 2,
                    "ads_clicks": clicks,
                    "ads_conversions": orders,
                    "ads_units_sold": orders,
                    "ads_attributed_sales": gmv * .4,
                    "ads_spend": gmv * .05,
                })
        return rows

    def test_three_month_ready_six_month_blocked(self):
        months = ["2026-07", "2026-08", "2026-09"]
        shops = [
            {"shop_id": "S1", "shop_key": "a", "display_name": "A", "history_lifecycle": {"origin": "PREEXISTING_BEFORE_TRUSTED_WINDOW"}},
            {"shop_id": "S2", "shop_key": "b", "display_name": "B", "history_lifecycle": {"origin": "SHOP_LAUNCH", "start_policy": "FIRST_TRUSTED_SEMANTIC_DATE"}},
        ]
        rows = self._rows("S1", months) + self._rows("S2", months, .7)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = build_product_intelligence(
                product_rows=rows,
                shops=shops,
                trusted_months=months,
                trusted_fingerprints=["a", "b", "c"],
                as_of_period="2026-09",
                contract_path=self._contract(root),
                output_dir=root / "out",
            )
            payload = json.loads((root / "out/product_intelligence.json").read_text())
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(payload["shops"]["S1"]["horizons"]["threeMonths"]["status"], "READY")
        self.assertEqual(payload["shops"]["S1"]["horizons"]["sixMonths"]["status"], "INSUFFICIENT_HISTORY")
        self.assertEqual(payload["shops"]["S1"]["horizons"]["year"]["status"], "INSUFFICIENT_HISTORY")
        self.assertEqual(payload["shops"]["S2"]["horizons"]["year"]["status"], "READY")
        self.assertEqual(payload["shops"]["S1"]["structuralIntelligence"]["status"], "INSUFFICIENT_HISTORY")
        self.assertEqual(payload["shops"]["S2"]["structuralIntelligence"]["status"], "INSUFFICIENT_OPERATING_HISTORY")
        self.assertTrue(payload["scopePolicy"]["dayWeekForbidden"])
        self.assertFalse(payload["scopePolicy"]["compareAllowed"])

    def test_structural_intelligence_uses_six_complete_months_before_mtd(self):
        months = ["2026-03", "2026-04", "2026-05", "2026-06", "2026-07", "2026-08", "2026-09"]
        shops = [{"shop_id": "S1", "shop_key": "a", "display_name": "A", "history_lifecycle": {"origin": "PREEXISTING_BEFORE_TRUSTED_WINDOW"}}]
        rows = self._rows("S1", months)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build_product_intelligence(
                product_rows=rows,
                shops=shops,
                trusted_months=months,
                trusted_fingerprints=[str(i) for i in range(len(months))],
                as_of_period="2026-09",
                contract_path=self._contract(root),
                output_dir=root / "out",
            )
            payload = json.loads((root / "out/product_intelligence.json").read_text())
        scope = payload["shops"]["S1"]
        intel = scope["structuralIntelligence"]
        self.assertEqual(scope["horizons"]["sixMonths"]["status"], "READY")
        self.assertEqual(intel["status"], "READY")
        self.assertEqual(intel["requiredMonths"], ["2026-03", "2026-04", "2026-05", "2026-06", "2026-07", "2026-08"])
        self.assertEqual(intel["baselineEndMonth"], "2026-08")
        self.assertEqual(intel["currentPartialMonth"], "2026-09")
        self.assertEqual(intel["currentPartialMonthRole"], "CORROBORATING_ONLY_NOT_SCORED")
        self.assertTrue(intel["signals"])
        first = intel["signals"][0]
        self.assertFalse(first["causalClaim"])
        self.assertEqual(first["driverAttribution"]["status"], "ATTRIBUTED")
        self.assertIn(first["driverAttribution"]["topDriverMetric"], {"productClicks", "cvr", "aov"})
        summary = scope["horizons"]["sixMonths"]["summary"]
        self.assertAlmostEqual(summary["placedAov"], summary["placedGmv"] / summary["placedOrders"])
        self.assertAlmostEqual(summary["roas"], summary["adsAttributedSales"] / summary["adsSpend"])

    def test_multi_month_non_additive_metrics_stay_latest_month_context(self):
        months = ["2026-07", "2026-08", "2026-09"]
        shops = [{"shop_id": "S1", "shop_key": "a", "display_name": "A", "history_lifecycle": {"origin": "PREEXISTING_BEFORE_TRUSTED_WINDOW"}}]
        rows = self._rows("S1", months)
        for row in rows:
            if row["data_month"] == "2026-09" and row["product_id"] == "P1":
                row["confirmed_buyers"] = 17
                row["repeat_order_rate"] = .33
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build_product_intelligence(
                product_rows=rows,
                shops=shops,
                trusted_months=months,
                trusted_fingerprints=["1", "2", "3"],
                as_of_period="2026-09",
                contract_path=self._contract(root),
                output_dir=root / "out",
            )
            payload = json.loads((root / "out/product_intelligence.json").read_text())
        p1 = next(x for x in payload["shops"]["S1"]["horizons"]["threeMonths"]["products"] if x["productId"] == "P1")
        self.assertEqual(p1["latestMonthContext"]["confirmedBuyers"], 17)
        self.assertAlmostEqual(p1["latestMonthContext"]["repeatOrderRate"], .33)
        self.assertNotIn("confirmedBuyers", payload["shops"]["S1"]["horizons"]["threeMonths"]["summary"])


if __name__ == "__main__":
    unittest.main()
