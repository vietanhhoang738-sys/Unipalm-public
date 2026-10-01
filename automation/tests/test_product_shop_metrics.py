import json
import tempfile
import unittest
from pathlib import Path

from modules.product_intelligence_shop_metrics import build_product_intelligence
from modules.product_shop_metrics import monthly_from_bi_stage, summarize


class ProductShopMetricsTest(unittest.TestCase):
    def test_monthly_bi_stage_uses_unique_shop_orders(self):
        rows = [
            {"shop_id": "S1", "data_date": "2026-09-01", "order_stage": "placed", "gross_sales": 600, "order_count": 2},
            {"shop_id": "S1", "data_date": "2026-09-02", "order_stage": "placed", "gross_sales": 400, "order_count": 3},
            {"shop_id": "S1", "data_date": "2026-09-01", "order_stage": "confirmed", "gross_sales": 500, "order_count": 2},
        ]
        row = monthly_from_bi_stage(rows, shop_id="S1", period="2026-09")
        self.assertEqual(row["placed_orders"], 5)
        self.assertEqual(row["placed_gmv"], 1000)
        self.assertEqual(row["placed_aov"], 200)
        self.assertEqual(row["order_semantics"], "UNIQUE_SHOP_ORDERS")

    def test_multi_month_summary_recomputes_aov_from_bi_totals(self):
        rows = [
            {"shop_id": "S1", "data_month": "2026-08", "placed_gmv": 1000, "placed_orders": 5, "confirmed_gmv": 900, "confirmed_orders": 4, "source": "BI"},
            {"shop_id": "S1", "data_month": "2026-09", "placed_gmv": 2000, "placed_orders": 5, "confirmed_gmv": 1800, "confirmed_orders": 5, "source": "BI"},
        ]
        result = summarize(rows, shop_id="S1", months=["2026-08", "2026-09"])
        self.assertEqual(result["status"], "READY")
        self.assertEqual(result["placedOrders"], 10)
        self.assertEqual(result["placedAov"], 300)

    def _contract(self, root: Path):
        path = root / "contract.json"
        path.write_text(json.dumps({
            "version": "1.2",
            "layer_name": "multi_shop_product_intelligence_v1",
            "status": "PREPRODUCTION",
            "source_policy": {"trusted_history_sources": ["PUBLISHED_SEMANTIC_QA_PASS"], "canonical_mart": "dm_product_monthly", "daily_or_weekly_product_scope_forbidden": True},
            "scope_policy": {"single_shop_only": True, "cross_shop_compare_allowed": False},
            "horizons": {"order": ["oneMonth", "threeMonths", "sixMonths", "year"]},
            "intelligence_policy": {"minimum_complete_months_for_structural_signal": 6, "current_partial_month_role": "CORROBORATING_ONLY"},
            "safety": {"write_production_data_mart": False, "modify_production_ui": False, "publish_legacy_payload": False, "platform_mutation_allowed": False, "production_activation_enabled": False},
        }), encoding="utf-8")
        return path

    def test_product_summary_does_not_treat_product_occurrences_as_shop_orders(self):
        product_rows = [
            {
                "shop_id": "S1", "data_month": "2026-09", "product_id": "PAID", "product_name": "Paid",
                "placed_gmv": 1000, "placed_orders": 10, "confirmed_gmv": 900, "confirmed_orders": 9,
                "product_views": 100, "product_clicks": 20, "product_visits": 20, "product_page_views": 30,
                "page_bounces": 2, "add_to_cart_visits": 10, "add_to_cart_units": 10, "confirmed_units": 9,
                "ads_impressions": 100, "ads_clicks": 10, "ads_conversions": 2, "ads_units_sold": 2,
                "ads_attributed_sales": 500, "ads_spend": 50,
            },
            {
                "shop_id": "S1", "data_month": "2026-09", "product_id": "GIFT", "product_name": "Gift 0đ",
                "placed_gmv": 0, "placed_orders": 10, "confirmed_gmv": 0, "confirmed_orders": 9,
                "product_views": 0, "product_clicks": 0, "product_visits": 0, "product_page_views": 0,
                "page_bounces": 0, "add_to_cart_visits": 0, "add_to_cart_units": 10, "confirmed_units": 9,
                "ads_impressions": 0, "ads_clicks": 0, "ads_conversions": 0, "ads_units_sold": 0,
                "ads_attributed_sales": 0, "ads_spend": 0,
            },
        ]
        shop_metrics = [{
            "shop_id": "S1", "data_month": "2026-09", "placed_gmv": 1000, "placed_orders": 5,
            "confirmed_gmv": 900, "confirmed_orders": 4, "source": "CANONICAL_SEMANTIC_V2_BUSINESS_INSIGHTS",
        }]
        shops = [{"shop_id": "S1", "shop_key": "s1", "display_name": "S1", "history_lifecycle": {"origin": "SHOP_LAUNCH", "start_policy": "FIRST_TRUSTED_SEMANTIC_DATE"}}]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build_product_intelligence(
                product_rows=product_rows, shop_metric_rows=shop_metrics, shops=shops,
                trusted_months=["2026-09"], trusted_fingerprints=["fp"], as_of_period="2026-09",
                contract_path=self._contract(root), output_dir=root / "out",
            )
            payload = json.loads((root / "out/product_intelligence.json").read_text())
        summary = payload["shops"]["S1"]["horizons"]["oneMonth"]["summary"]
        self.assertEqual(summary["productOrderOccurrences"], 20)
        self.assertEqual(summary["placedOrders"], 5)
        self.assertEqual(summary["placedAov"], 200)
        self.assertEqual(summary["orderSemantics"], "UNIQUE_SHOP_ORDERS")
        self.assertEqual(summary["shopMetricSource"], "BUSINESS_INSIGHTS_SHOP_LEVEL")


if __name__ == "__main__":
    unittest.main()
