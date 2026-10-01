import json
import tempfile
import unittest
from pathlib import Path

from modules.semantic_mart import build_semantic_marts, load_contract


class SemanticMartTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.processed=self.root/"processed"
        self.output=self.root/"semantic"

    def tearDown(self):
        self.tmp.cleanup()

    def _write_jsonl(self,path,rows):
        path.parent.mkdir(parents=True,exist_ok=True)
        with path.open("w",encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row,ensure_ascii=False,sort_keys=True)+"\n")

    def _make_shop(self,shop_key,shop_id,*,gmv,orders,clicks,ads_sales,ads_spend,ads_end="2026-09-02"):
        p=self.processed/shop_key/"2026-09"
        p.mkdir(parents=True,exist_ok=True)
        (p/"manifest.json").write_text(json.dumps({
            "shop_key":shop_key,"shop_id":shop_id,"period":"2026-09",
            "build_fingerprint":f"fp-{shop_key}",
        }),encoding="utf-8")
        (p/"processed_qa_report.json").write_text(json.dumps({
            "status":"PASS","processed_partition_ready":True,
            "shop_key":shop_key,"shop_id":shop_id,"period":"2026-09",
            "build_fingerprint":f"fp-{shop_key}",
        }),encoding="utf-8")

        states=[
            {"shop_id":shop_id,"source_domain":"orders","period":"2026-09","state":"READY","verified_through":"2026-09-03"},
            {"shop_id":shop_id,"source_domain":"ads","period":"2026-09","state":"READY","verified_through":ads_end},
            {"shop_id":shop_id,"source_domain":"business_insights","period":"2026-09","state":"READY","verified_through":"2026-09-03"},
            {"shop_id":shop_id,"source_domain":"product_performance","period":"2026-09","state":"READY","verified_through":"2026-09"},
        ]
        self._write_jsonl(p/"control"/"pipeline_state.jsonl",states)

        bi=[]
        for day in ("01","02","03"):
            for stage,mult in (("placed",1.0),("confirmed",0.9),("paid",0.8)):
                bi.append({
                    "shop_id":shop_id,"data_date":f"2026-09-{day}","order_stage":stage,
                    "gross_sales":gmv*mult,"order_count":orders,
                    "product_clicks":clicks,"visits":clicks*2,
                    "cancelled_orders":1 if stage=="placed" else 0,
                    "cancelled_sales":10 if stage=="placed" else 0,
                    "returned_refunded_orders":0,"returned_refunded_sales":0,
                    "buyers":orders,"new_buyers":max(0,orders-1),"existing_buyers":1,
                    "potential_buyers":clicks//2,
                })
        self._write_jsonl(p/"business_insights"/"fact_shop_performance_daily.jsonl",bi)

        traffic_daily=[]
        traffic_monthly=[]
        for stage in ("placed","confirmed","paid"):
            for day in ("01","02","03"):
                traffic_daily.append({
                    "shop_id":shop_id,"data_date":f"2026-09-{day}","order_stage":stage,
                    "channel_group":"Product Card","traffic_source":"Product Card",
                    "sales_ratio":1,"sales":gmv,"impressions":1000,"clicks":100,
                    "orders":10,"units":11,"buyers":9,"unique_impressions":800,"unique_clicks":80,
                })
            traffic_monthly.append({
                "shop_id":shop_id,"data_month":"2026-09","order_stage":stage,
                "channel_group":"Product Card","traffic_source":"Search",
                "sales_ratio":0.5,"sales":gmv*3,"impressions":3000,"clicks":300,
                "orders":30,"units":33,"buyers":20,"unique_impressions":2000,"unique_clicks":200,
            })
        self._write_jsonl(p/"business_insights"/"fact_traffic_source_daily.jsonl",traffic_daily)
        self._write_jsonl(p/"business_insights"/"fact_traffic_source_monthly.jsonl",traffic_monthly)

        order_rows=[]
        item_rows=[]
        for idx,day in enumerate(("01","02","03"),1):
            order_rows.append({
                "shop_id":shop_id,"order_id":f"{shop_key}-O{idx}",
                "order_created_at":f"2026-09-{day} 10:00:00","order_status":"Completed",
                "fixed_fee":2,"service_fee":3,"transaction_fee":1,
                "shop_voucher":0,"order_total_value":gmv,
            })
            item_rows.append({
                "shop_id":shop_id,"order_id":f"{shop_key}-O{idx}",
                "order_item_seq":1,"item_buyer_payment":gmv,
            })
        self._write_jsonl(p/"orders"/"fact_orders.jsonl",order_rows)
        self._write_jsonl(p/"orders"/"fact_order_items.jsonl",item_rows)

        ads=[]
        ads_product=[]
        for idx,day in enumerate(("01","02"),1):
            ads.append({
                "shop_id":shop_id,"data_date":f"2026-09-{day}",
                "ad_service_daily_key":f"{shop_key}-A{idx}","ad_scope":"product",
                "product_id":"P_SHARED","impressions":100,"clicks":10,
                "add_to_cart":2,"conversions":2,"units_sold":2,
                "attributed_sales":ads_sales,"ad_spend":ads_spend,
            })
            ads_product.append({
                "shop_id":shop_id,"data_date":f"2026-09-{day}",
                "product_id":"P_SHARED","impressions":100,"clicks":10,
                "add_to_cart":2,"conversions":2,"units_sold":2,
                "attributed_sales":ads_sales,"ad_spend":ads_spend,
            })
        self._write_jsonl(p/"ads"/"fact_ads_performance_daily.jsonl",ads)
        self._write_jsonl(p/"ads"/"fact_ads_product_daily.jsonl",ads_product)

        self._write_jsonl(p/"product_performance"/"fact_product_performance_monthly.jsonl",[{
            "shop_id":shop_id,"data_month":"2026-09","product_id":"P_SHARED",
            "product_name":f"Product {shop_key}","product_sku":"SKU-"+shop_key,
            "product_status":"active","placed_gmv_vnd":gmv*3,"confirmed_gmv_vnd":gmv*2.7,
            "placed_orders":orders*3,"confirmed_orders":orders*3-1,
            "product_views":1000,"product_clicks":100,
            "unique_product_impressions":800,"unique_product_clicks":80,
            "product_visits":200,"product_page_views":300,"product_page_bounces":20,
            "add_to_cart_visits":40,"add_to_cart_units":50,
            "confirmed_units":orders*3,"confirmed_buyers":orders*2,
            "confirmed_repeat_order_rate":0.1,"confirmed_avg_days_to_repeat_order":3,
        }])
        self._write_jsonl(p/"catalog"/"catalog_resolution.jsonl",[{
            "shop_id":shop_id,"product_id":"P_SHARED","status":"DIRECT_PARENT",
            "resolved_parent_sku":"PARENT-"+shop_key,"canonical_family_key":"",
            "confidence":1.0,
        }])
        self._write_jsonl(p/"listing_catalog"/"products_snapshot.jsonl",[{
            "shop_id":shop_id,"product_id":"P_SHARED","product_name":f"Product {shop_key}",
            "observed_parent_sku":"PARENT-"+shop_key,
        }])
        return {
            "shop_key":shop_key,"shop_id":shop_id,"shopee_shop_id":shop_id,
            "display_name":shop_key,"platform":"shopee","enabled":True,
        }

    def test_three_shops_build_without_cross_shop_product_collision(self):
        shops=[
            self._make_shop("a","SHOP_A",gmv=100,orders=2,clicks=20,ads_sales=50,ads_spend=10),
            self._make_shop("b","SHOP_B",gmv=200,orders=4,clicks=40,ads_sales=80,ads_spend=20),
            self._make_shop("c","SHOP_C",gmv=300,orders=6,clicks=60,ads_sales=120,ads_spend=30),
        ]
        result=build_semantic_marts(
            processed_root=self.processed,output_dir=self.output,
            period="2026-09",shops=shops,generated_at="x")
        self.assertEqual(result["status"],"PASS")
        rows=[json.loads(x) for x in (self.output/"dm_product_monthly.jsonl").read_text().splitlines()]
        self.assertEqual(len(rows),3)
        self.assertEqual({r["shop_id"] for r in rows},{"SHOP_A","SHOP_B","SHOP_C"})
        self.assertEqual({r["product_id"] for r in rows},{"P_SHARED"})
        parents={r["shop_id"]:r["resolved_parent_sku"] for r in rows}
        self.assertEqual(parents["SHOP_A"],"PARENT-a")
        self.assertEqual(parents["SHOP_B"],"PARENT-b")
        self.assertEqual(parents["SHOP_C"],"PARENT-c")

    def test_common_reliable_end_is_minimum_of_core_daily_domains(self):
        shop=self._make_shop("a","SHOP_A",gmv=100,orders=2,clicks=20,ads_sales=50,ads_spend=10,ads_end="2026-09-02")
        build_semantic_marts(
            processed_root=self.processed,output_dir=self.output,
            period="2026-09",shops=[shop])
        daily=[json.loads(x) for x in (self.output/"dm_shop_daily.jsonl").read_text().splitlines()]
        self.assertEqual([r["data_date"] for r in daily],["2026-09-01","2026-09-02"])
        self.assertTrue(all(r["common_reliable_end"]=="2026-09-02" for r in daily))

    def test_daily_ratios_are_recomputed_from_additive_fields_not_averaged(self):
        shops=[
            self._make_shop("a","SHOP_A",gmv=100,orders=1,clicks=10,ads_sales=100,ads_spend=10),
            self._make_shop("b","SHOP_B",gmv=1000,orders=2,clicks=100,ads_sales=10,ads_spend=10),
        ]
        build_semantic_marts(
            processed_root=self.processed,output_dir=self.output,
            period="2026-09",shops=shops)
        daily=[json.loads(x) for x in (self.output/"dm_shop_daily.jsonl").read_text().splitlines()]
        a=next(r for r in daily if r["shop_id"]=="SHOP_A")
        self.assertAlmostEqual(a["placed_aov"],100.0)
        self.assertAlmostEqual(a["placed_cvr"],0.1)
        self.assertAlmostEqual(a["roas"],10.0)

    def test_redundant_monthly_semantic_marts_are_not_emitted(self):
        shop=self._make_shop("a","SHOP_A",gmv=100,orders=2,clicks=20,ads_sales=50,ads_spend=10)
        result=build_semantic_marts(
            processed_root=self.processed,output_dir=self.output,
            period="2026-09",shops=[shop])
        names={x["name"] for x in result["files"]}
        self.assertNotIn("dm_shop_monthly",names)
        self.assertNotIn("dm_traffic_source_monthly",names)
        self.assertFalse((self.output/"dm_shop_monthly.jsonl").exists())
        self.assertFalse((self.output/"dm_traffic_source_monthly.jsonl").exists())
        self.assertFalse((self.output/"dm_shop_benchmark_monthly.jsonl").exists())

    def test_deleted_historical_product_without_current_listing_is_valid(self):
        shop=self._make_shop("a","SHOP_A",gmv=100,orders=2,clicks=20,ads_sales=50,ads_spend=10)
        p=self.processed/"a"/"2026-09"
        self._write_jsonl(p/"product_performance"/"fact_product_performance_monthly.jsonl",[{
            "shop_id":"SHOP_A","data_month":"2026-09","product_id":"P_DELETED",
            "product_name":"Deleted historical listing","product_sku":"OLD-SKU",
            "product_status":"Đã xóa","placed_gmv_vnd":0,"confirmed_gmv_vnd":0,
            "placed_orders":0,"confirmed_orders":0,"product_views":1,"product_clicks":0,
            "unique_product_impressions":1,"unique_product_clicks":0,
            "product_visits":0,"product_page_views":0,"product_page_bounces":0,
            "add_to_cart_visits":0,"add_to_cart_units":0,"confirmed_units":0,
            "confirmed_buyers":0,"confirmed_repeat_order_rate":0,
            "confirmed_avg_days_to_repeat_order":0,
        }])
        self._write_jsonl(p/"catalog"/"catalog_resolution.jsonl",[{
            "shop_id":"SHOP_A","product_id":"P_NEW","status":"DIRECT_PARENT",
            "resolved_parent_sku":"NEW-PARENT","confidence":1.0,
        }])
        self._write_jsonl(p/"listing_catalog"/"products_snapshot.jsonl",[{
            "shop_id":"SHOP_A","product_id":"P_NEW","product_name":"Current replacement listing",
            "observed_parent_sku":"NEW-PARENT",
        }])

        result=build_semantic_marts(
            processed_root=self.processed,output_dir=self.output,
            period="2026-09",shops=[shop])
        self.assertEqual(result["status"],"PASS")
        row=json.loads((self.output/"dm_product_monthly.jsonl").read_text().splitlines()[0])
        self.assertEqual(row["product_id"],"P_DELETED")
        self.assertEqual(row["catalog_join_status"],"HISTORICAL_DELETED_NO_CURRENT_LISTING")
        self.assertFalse(row["current_listing_present"])
        self.assertEqual(row["catalog_status"],"NOT_IN_CURRENT_CATALOG")

if __name__=="__main__":
    unittest.main()
