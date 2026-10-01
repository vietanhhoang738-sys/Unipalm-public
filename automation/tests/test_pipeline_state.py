import unittest

from modules.pipeline_state import aggregate_shop_readiness, validate_state_rows


class PipelineStateTest(unittest.TestCase):
    def test_same_domain_period_can_exist_for_many_shops(self):
        rows=[
            {"shop_id":"SHOP_1","source_domain":"orders","period":"2026-09","state":"READY","run_id":"r1","dq_error":0},
            {"shop_id":"SHOP_2","source_domain":"orders","period":"2026-09","state":"READY","run_id":"r2","dq_error":0},
            {"shop_id":"SHOP_3","source_domain":"orders","period":"2026-09","state":"READY","run_id":"r3","dq_error":0},
        ]
        qa=validate_state_rows(rows)
        self.assertEqual(qa["status"],"PASS")
        self.assertEqual(qa["shop_count"],3)

    def test_duplicate_key_is_shop_scoped(self):
        rows=[
            {"shop_id":"SHOP_1","source_domain":"orders","period":"2026-09","state":"READY","run_id":"r1"},
            {"shop_id":"SHOP_1","source_domain":"orders","period":"2026-09","state":"READY","run_id":"r2"},
        ]
        qa=validate_state_rows(rows)
        self.assertEqual(qa["status"],"FAIL")
        self.assertEqual(qa["duplicate_count"],1)

    def test_one_shop_failure_does_not_block_another_shop(self):
        rows=[
            {"shop_id":"SHOP_1","source_domain":"orders","period":"2026-09","state":"READY","run_id":"a"},
            {"shop_id":"SHOP_1","source_domain":"ads","period":"2026-09","state":"READY","run_id":"b"},
            {"shop_id":"SHOP_2","source_domain":"orders","period":"2026-09","state":"READY","run_id":"c"},
            {"shop_id":"SHOP_2","source_domain":"ads","period":"2026-09","state":"FAILED","run_id":"d"},
        ]
        out=aggregate_shop_readiness(rows,["orders","ads"])
        by={x["shop_id"]:x for x in out}
        self.assertEqual(by["SHOP_1"]["status"],"READY")
        self.assertEqual(by["SHOP_2"]["status"],"BLOCKED")
        self.assertEqual(by["SHOP_2"]["blocking_domains"],["ads"])

    def test_missing_domain_blocks_only_that_shop_period(self):
        rows=[
            {"shop_id":"SHOP_1","source_domain":"orders","period":"2026-09","state":"READY","run_id":"a"},
            {"shop_id":"SHOP_2","source_domain":"orders","period":"2026-09","state":"READY","run_id":"b"},
            {"shop_id":"SHOP_2","source_domain":"ads","period":"2026-09","state":"READY","run_id":"c"},
        ]
        out=aggregate_shop_readiness(rows,["orders","ads"])
        by={x["shop_id"]:x for x in out}
        self.assertEqual(by["SHOP_1"]["status"],"BLOCKED")
        self.assertEqual(by["SHOP_1"]["domain_status"]["ads"],"MISSING")
        self.assertEqual(by["SHOP_2"]["status"],"READY")


if __name__=="__main__":
    unittest.main()
