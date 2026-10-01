import json
import tempfile
import unittest
from pathlib import Path

from modules.processed_layer import build_processed_partition, inspect_partition_fingerprint, load_processed_contract


class ProcessedLayerTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.staging=self.root/"staging"
        self.output=self.root/"processed"

    def tearDown(self):
        self.tmp.cleanup()

    def _write_jsonl(self,path,rows):
        path.parent.mkdir(parents=True,exist_ok=True)
        with path.open("w",encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row,ensure_ascii=False,sort_keys=True)+"\n")

    def _make_staging(self,shop_key,shop_id,period="2026-09",foreign_file=None):
        p=self.staging/shop_key/period
        p.mkdir(parents=True,exist_ok=True)
        (p/"staging_qa_report.json").write_text(json.dumps({
            "status":"PASS","production_write_allowed":True,
            "target_month":period,"shop_id":shop_id,
            "schema_guard":{"status":"PASS"},
        }),encoding="utf-8")
        (p/"schema_drift_report.json").write_text(json.dumps({
            "summary":{"status":"PASS","status_counts":{"PASS":2,"WARN":0,"FAIL":0}},
            "audits":[],
        }),encoding="utf-8")

        contract=load_processed_contract()
        for domain,spec in contract["domains"].items():
            for item in spec.get("files") or []:
                source=item["source"]
                sid="OTHER" if foreign_file==source else shop_id
                row={"shop_id":sid}
                if source=="fact_orders.jsonl":
                    row.update({"order_id":"O1","order_created_at":"2026-09-20 10:00:00","loaded_at":"RUN_A"})
                elif source=="fact_order_items.jsonl":
                    row.update({"order_id":"O1","order_item_seq":1,"loaded_at":"RUN_A"})
                elif source=="fact_ads_performance_daily.jsonl":
                    row.update({"data_date":"2026-09-20","ad_service_daily_key":"A1"})
                elif source=="dm_ads_product_daily_candidate.jsonl":
                    row.update({"data_date":"2026-09-20","product_id":"P1"})
                elif source=="fact_product_performance_monthly.jsonl":
                    row.update({"data_month":"2026-09","product_id":"P1"})
                elif source=="fact_product_variations_monthly.jsonl":
                    row.update({"data_month":"2026-09","product_id":"P1","variation_sku":"V1"})
                elif source=="fact_shop_performance_daily.jsonl":
                    row.update({"data_date":"2026-09-20","order_stage":"placed"})
                elif source=="fact_traffic_source_daily.jsonl":
                    row.update({"data_date":"2026-09-20","order_stage":"placed"})
                elif source=="fact_traffic_source_monthly.jsonl":
                    row.update({"data_month":"2026-09","order_stage":"placed"})
                elif source=="catalog_resolution_staging.jsonl":
                    row.update({"product_id":"P1","status":"DIRECT_PARENT"})
                elif source=="listing_catalog_products_snapshot.jsonl":
                    row.update({"product_id":"P1"})
                elif source=="listing_catalog_variations_snapshot.jsonl":
                    row.update({"product_id":"P1","variation_id":"V1"})
                self._write_jsonl(p/source,[row])
        return p

    def test_builds_shop_scoped_partition_and_control_state(self):
        source=self._make_staging("shop_1","SHOP_1")
        result=build_processed_partition(
            staging_dir=source,output_root=self.output,shop_key="shop_1",
            period="2026-09",run_id="run-1",generated_at="2026-09-23T00:00:00+00:00")
        self.assertEqual(result["status"],"PASS")
        target=self.output/"shop_1"/"2026-09"
        self.assertTrue((target/"orders"/"fact_orders.jsonl").exists())
        self.assertTrue((target/"ads"/"fact_ads_product_daily.jsonl").exists())
        self.assertTrue((target/"control"/"pipeline_state.jsonl").exists())
        qa=json.loads((target/"processed_qa_report.json").read_text(encoding="utf-8"))
        self.assertEqual(qa["status"],"PASS")
        states=[
            json.loads(x) for x in (target/"control"/"pipeline_state.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        keys={(x["shop_id"],x["source_domain"],x["period"]) for x in states}
        self.assertEqual(len(keys),len(states))
        self.assertTrue(all(x["production_updated"] is False for x in states))

    def test_identical_source_rebuild_has_same_fingerprint(self):
        source=self._make_staging("shop_1","SHOP_1")
        first=build_processed_partition(
            staging_dir=source,output_root=self.output,shop_key="shop_1",
            period="2026-09",run_id="run-1",generated_at="2026-09-23T00:00:00+00:00")
        second=build_processed_partition(
            staging_dir=source,output_root=self.output,shop_key="shop_1",
            period="2026-09",run_id="run-2",generated_at="2026-09-23T01:00:00+00:00")
        self.assertEqual(first["build_fingerprint"],second["build_fingerprint"])
        self.assertEqual(
            inspect_partition_fingerprint(self.output/"shop_1"/"2026-09"),
            first["build_fingerprint"],
        )

    def test_volatile_loaded_at_does_not_change_processed_fingerprint(self):
        source=self._make_staging("shop_1","SHOP_1")
        first=build_processed_partition(
            staging_dir=source,output_root=self.output,shop_key="shop_1",
            period="2026-09",run_id="run-1",generated_at="2026-09-23T00:00:00+00:00")

        # Same business facts, new ingestion timestamps.
        for name in ("fact_orders.jsonl","fact_order_items.jsonl"):
            rows=[json.loads(x) for x in (source/name).read_text(encoding="utf-8").splitlines() if x.strip()]
            for row in rows:
                row["loaded_at"]="RUN_B"
            self._write_jsonl(source/name,rows)

        second=build_processed_partition(
            staging_dir=source,output_root=self.output,shop_key="shop_1",
            period="2026-09",run_id="run-2",generated_at="2026-09-23T01:00:00+00:00")
        self.assertEqual(first["build_fingerprint"],second["build_fingerprint"])

        target=self.output/"shop_1"/"2026-09"
        for name in ("orders/fact_orders.jsonl","orders/fact_order_items.jsonl"):
            rows=[json.loads(x) for x in (target/name).read_text(encoding="utf-8").splitlines() if x.strip()]
            self.assertTrue(rows)
            self.assertTrue(all("loaded_at" not in row for row in rows))

    def test_foreign_shop_row_blocks_processed_partition(self):
        source=self._make_staging(
            "shop_1","SHOP_1",foreign_file="fact_ads_performance_daily.jsonl")
        with self.assertRaises(ValueError):
            build_processed_partition(
                staging_dir=source,output_root=self.output,shop_key="shop_1",
                period="2026-09",run_id="run-1")

    def test_rebuilding_one_shop_does_not_touch_another_shop(self):
        s1=self._make_staging("shop_1","SHOP_1")
        s2=self._make_staging("shop_2","SHOP_2")
        r1=build_processed_partition(
            staging_dir=s1,output_root=self.output,shop_key="shop_1",
            period="2026-09",run_id="run-1")
        r2=build_processed_partition(
            staging_dir=s2,output_root=self.output,shop_key="shop_2",
            period="2026-09",run_id="run-1")
        shop2_before=inspect_partition_fingerprint(self.output/"shop_2"/"2026-09")
        self.assertEqual(shop2_before,r2["build_fingerprint"])

        # Change only shop 1 facts and rebuild shop 1.
        with (s1/"fact_orders.jsonl").open("a",encoding="utf-8") as f:
            f.write(json.dumps({
                "shop_id":"SHOP_1","order_id":"O2",
                "order_created_at":"2026-09-21 10:00:00",
            },sort_keys=True)+"\n")
        r1b=build_processed_partition(
            staging_dir=s1,output_root=self.output,shop_key="shop_1",
            period="2026-09",run_id="run-2")
        self.assertNotEqual(r1["build_fingerprint"],r1b["build_fingerprint"])
        self.assertEqual(
            inspect_partition_fingerprint(self.output/"shop_2"/"2026-09"),
            shop2_before,
        )


if __name__=="__main__":
    unittest.main()
