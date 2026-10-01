import unittest

from modules.ads_product_mart import aggregate_product_ads_rows, validate_product_ads_rows


class ProductAdsMartTest(unittest.TestCase):
    def test_all_campaigns_are_summed_by_shop_product_day(self):
        rows=[
            {"shop_id":"SHOP_1","data_date":"2026-06-10","ad_scope":"product","product_id":"P1","ad_service_daily_key":"A","impressions":100,"clicks":10,"conversions":2,"attributed_sales":200000,"ad_spend":20000},
            {"shop_id":"SHOP_1","data_date":"2026-06-10","ad_scope":"product","product_id":"P1","ad_service_daily_key":"B","impressions":50,"clicks":5,"conversions":1,"attributed_sales":100000,"ad_spend":10000},
            {"shop_id":"SHOP_1","data_date":"2026-06-10","ad_scope":"product","product_id":"P2","ad_service_daily_key":"C","impressions":40,"clicks":4,"conversions":1,"attributed_sales":80000,"ad_spend":8000},
        ]
        out=aggregate_product_ads_rows(rows,expected_shop_id="SHOP_1")
        self.assertEqual(len(out),2)
        p1=next(x for x in out if x["product_id"]=="P1")
        self.assertEqual(p1["shop_id"],"SHOP_1")
        self.assertEqual(p1["impressions"],150)
        self.assertEqual(p1["clicks"],15)
        self.assertEqual(p1["ad_spend"],30000)
        self.assertEqual(p1["attributed_sales"],300000)
        self.assertAlmostEqual(p1["roas"],10.0)
        self.assertEqual(validate_product_ads_rows(out)["status"],"PASS")

    def test_two_shops_with_same_product_id_never_mix(self):
        rows=[
            {"shop_id":"SHOP_1","data_date":"2026-06-10","ad_scope":"product","product_id":"P1","impressions":100,"ad_spend":1000},
            {"shop_id":"SHOP_2","data_date":"2026-06-10","ad_scope":"product","product_id":"P1","impressions":200,"ad_spend":2000},
        ]
        out=aggregate_product_ads_rows(rows)
        self.assertEqual(len(out),2)
        by_shop={x["shop_id"]:x for x in out}
        self.assertEqual(by_shop["SHOP_1"]["impressions"],100)
        self.assertEqual(by_shop["SHOP_2"]["impressions"],200)
        self.assertEqual(validate_product_ads_rows(out)["status"],"PASS")

    def test_expected_shop_rejects_cross_shop_row(self):
        rows=[{"shop_id":"SHOP_2","data_date":"2026-06-10","ad_scope":"product","product_id":"P1","ad_spend":1}]
        with self.assertRaises(ValueError):
            aggregate_product_ads_rows(rows,expected_shop_id="SHOP_1")

    def test_campaign_restart_does_not_break_product_history(self):
        rows=[
            {"shop_id":"SHOP_1","data_date":"2026-05-31","ad_scope":"product","product_id":"P1","ad_service_daily_key":"OLD","impressions":10,"ad_spend":1000},
            {"shop_id":"SHOP_1","data_date":"2026-06-01","ad_scope":"product","product_id":"P1","ad_service_daily_key":"NEW","impressions":20,"ad_spend":2000},
        ]
        out=aggregate_product_ads_rows(rows)
        self.assertEqual(
            [(x["data_date"],x["product_id"]) for x in out],
            [("2026-05-31","P1"),("2026-06-01","P1")],
        )


if __name__=="__main__":
    unittest.main()
