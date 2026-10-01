import json
import tempfile
import unittest
from pathlib import Path

from modules.semantic_drive_writer import (
    load_semantic_storage_registry,
    validate_local_semantic_partition,
)


class SemanticDriveWriterTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _semantic(self):
        p=self.root/"2026-09"
        p.mkdir(parents=True,exist_ok=True)
        mart=p/"dm_shop_monthly.jsonl"
        mart.write_text(
            json.dumps({"shop_id":"SHOP_A","data_month":"2026-09","placed_gmv":100},sort_keys=True)+"\n"+
            json.dumps({"shop_id":"SHOP_B","data_month":"2026-09","placed_gmv":200},sort_keys=True)+"\n",
            encoding="utf-8",
        )
        import hashlib
        sha=hashlib.sha256(mart.read_bytes()).hexdigest()
        fp="semantic-fingerprint"
        (p/"manifest.json").write_text(json.dumps({
            "layer":"multi_shop_semantic_v1",
            "period":"2026-09",
            "semantic_build_fingerprint":fp,
            "source_partitions":[
                {"shop_id":"SHOP_A","shop_key":"a","processed_build_fingerprint":"pa"},
                {"shop_id":"SHOP_B","shop_key":"b","processed_build_fingerprint":"pb"},
            ],
            "files":[
                {"name":"dm_shop_monthly","file":"dm_shop_monthly.jsonl","rows":2,"sha256":sha,
                 "grain":["shop_id","data_month"]}
            ],
            "safety":{
                "legacy_data_mart_written":False,
                "production_data_mart_written":False,
                "ui_modified":False,
            },
        }),encoding="utf-8")
        (p/"semantic_qa_report.json").write_text(json.dumps({
            "status":"PASS","period":"2026-09","semantic_mart_ready":True,
            "semantic_build_fingerprint":fp,
            "selected_shop_count":2,
            "selected_shop_ids":["SHOP_A","SHOP_B"],
            "checks":[],
        }),encoding="utf-8")
        return p

    def test_storage_registry_semantic_root_is_preproduction_and_isolated(self):
        root=Path(__file__).resolve().parents[2]
        cfg=load_semantic_storage_registry(root/"config"/"storage_registry.json")["semantic_v2"]
        self.assertEqual(cfg["status"],"PREPRODUCTION")
        self.assertNotIn(cfg["drive_root_id"],cfg["forbidden_drive_root_ids"])
        self.assertTrue(cfg["writer_policy"]["requires_all_enabled_shops"])
        self.assertFalse(cfg["writer_policy"]["write_legacy_data_mart"])
        self.assertFalse(cfg["writer_policy"]["write_production_data_mart"])
        self.assertFalse(cfg["writer_policy"]["write_ui"])

    def test_valid_semantic_portfolio_passes_preflight(self):
        p=self._semantic()
        audit=validate_local_semantic_partition(
            p,expected_period="2026-09",expected_shop_ids={"SHOP_A","SHOP_B"})
        self.assertEqual(audit["selected_shop_count"],2)
        self.assertEqual(audit["semantic_build_fingerprint"],"semantic-fingerprint")
        self.assertGreaterEqual(len(audit["files"]),3)

    def test_partial_shop_scope_is_rejected(self):
        p=self._semantic()
        with self.assertRaises(ValueError):
            validate_local_semantic_partition(
                p,expected_period="2026-09",expected_shop_ids={"SHOP_A","SHOP_B","SHOP_C"})

    def test_tampered_mart_is_rejected(self):
        p=self._semantic()
        with (p/"dm_shop_monthly.jsonl").open("a",encoding="utf-8") as f:
            f.write(json.dumps({"shop_id":"SHOP_A","data_month":"2026-09","placed_gmv":999})+"\n")
        with self.assertRaises(ValueError):
            validate_local_semantic_partition(
                p,expected_period="2026-09",expected_shop_ids={"SHOP_A","SHOP_B"})


if __name__=="__main__":
    unittest.main()
