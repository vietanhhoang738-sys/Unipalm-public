import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import modules.drive_partition_writer as drive_writer
from modules.drive_partition_writer import load_storage_registry, validate_local_partition
from modules.processed_layer import build_processed_partition, load_processed_contract


class DrivePartitionWriterTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _write_jsonl(self,path,rows):
        path.parent.mkdir(parents=True,exist_ok=True)
        with path.open("w",encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row,sort_keys=True)+"\n")

    def _candidate(self):
        staging=self.root/"staging"
        staging.mkdir()
        (staging/"staging_qa_report.json").write_text(json.dumps({
            "status":"PASS",
            "production_write_allowed":True,
            "target_month":"2026-09",
            "shop_id":"SHOP_X",
            "schema_guard":{"status":"PASS"},
        }),encoding="utf-8")
        (staging/"schema_drift_report.json").write_text(json.dumps({
            "summary":{"status":"PASS","status_counts":{"PASS":1,"WARN":0,"FAIL":0}},
            "audits":[],
        }),encoding="utf-8")

        contract=load_processed_contract()
        for domain,spec in contract["domains"].items():
            for file_spec in spec.get("files") or []:
                source=file_spec["source"]
                row={"shop_id":"SHOP_X"}
                if source=="fact_orders.jsonl":
                    row.update({"order_id":"O1","order_created_at":"2026-09-20 10:00:00","loaded_at":"volatile"})
                elif source=="fact_order_items.jsonl":
                    row.update({"order_id":"O1","order_item_seq":1,"loaded_at":"volatile"})
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
                    row.update({"product_id":"P1"})
                elif source=="listing_catalog_products_snapshot.jsonl":
                    row.update({"product_id":"P1"})
                elif source=="listing_catalog_variations_snapshot.jsonl":
                    row.update({"product_id":"P1","variation_id":"V1"})
                self._write_jsonl(staging/source,[row])

        out=self.root/"processed"
        build_processed_partition(
            staging_dir=staging,
            output_root=out,
            shop_key="shop_x",
            period="2026-09",
            run_id="run-1",
        )
        return out/"shop_x"/"2026-09"

    def test_storage_registry_is_preproduction_and_forbids_legacy_root(self):
        root=Path(__file__).resolve().parents[2]
        cfg=load_storage_registry(root/"config"/"storage_registry.json")["processed_v2"]
        self.assertEqual(cfg["status"],"PREPRODUCTION")
        self.assertNotIn(cfg["drive_root_id"],cfg["forbidden_drive_root_ids"])
        self.assertFalse(cfg["writer_policy"]["write_legacy_processed"])
        self.assertFalse(cfg["writer_policy"]["write_production_data_mart"])
        self.assertFalse(cfg["writer_policy"]["write_ui"])

    def test_local_processed_partition_passes_writer_preflight(self):
        part=self._candidate()
        audit=validate_local_partition(
            part,expected_shop_key="shop_x",expected_period="2026-09")
        self.assertEqual(audit["shop_id"],"SHOP_X")
        self.assertTrue(audit["build_fingerprint"])
        self.assertGreater(len(audit["files"]),0)
        orders=[
            json.loads(x) for x in
            (part/"orders"/"fact_orders.jsonl").read_text(encoding="utf-8").splitlines()
            if x.strip()
        ]
        self.assertTrue(all("loaded_at" not in row for row in orders))

    def test_manifest_hash_tamper_blocks_writer(self):
        part=self._candidate()
        target=part/"orders"/"fact_orders.jsonl"
        with target.open("a",encoding="utf-8") as f:
            f.write(json.dumps({"shop_id":"SHOP_X","order_id":"TAMPER"})+"\n")
        with self.assertRaises(ValueError):
            validate_local_partition(
                part,expected_shop_key="shop_x",expected_period="2026-09")

    def test_control_audit_upload_retries_transient_timeout(self):
        local=self.root/"audit.json"
        local.write_text('{"status":"PASS"}',encoding="utf-8")
        calls={"count":0}

        def flaky_upload(*args,**kwargs):
            calls["count"]+=1
            if calls["count"]==1:
                raise TimeoutError("transient Drive timeout")
            return {"id":"AUDIT_OK"}

        with patch.object(
            drive_writer,"ensure_control_run_folder",return_value={"id":"RUN"}
        ), patch.object(
            drive_writer,"_list_children",return_value=[]
        ), patch.object(
            drive_writer,"_upload_file_verified",side_effect=flaky_upload
        ):
            result=drive_writer.upload_control_file(
                object(),
                control_root_id="CONTROL",
                run_id="RUN_ID",
                local_path=local,
                file_name="audit.json",
                attempts=2,
                base_delay_seconds=0,
            )
        self.assertEqual(result["id"],"AUDIT_OK")
        self.assertEqual(calls["count"],2)

    def test_scope_mismatch_blocks_writer(self):
        part=self._candidate()
        with self.assertRaises(ValueError):
            validate_local_partition(
                part,expected_shop_key="other_shop",expected_period="2026-09")


if __name__=="__main__":
    unittest.main()
