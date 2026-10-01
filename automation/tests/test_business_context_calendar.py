import json
import tempfile
import unittest
from pathlib import Path

from modules.business_context_calendar import build_business_context


class BusinessContextCalendarTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.contract=self.root/"contract.json"
        self.calendar=self.root/"calendar.json"
        self.contract.write_text(json.dumps({
            "version":"1.0",
            "layer_name":"multi_shop_business_context_v1",
            "status":"PREPRODUCTION",
            "source_policy":{
                "explicit_source_only":True,
                "allowed_source_tiers":[
                    "A1_PLATFORM_SELLER_OFFICIAL",
                    "A2_PLATFORM_CONSUMER_OFFICIAL",
                    "B1_GOVERNMENT_OFFICIAL",
                    "C1_INDUSTRY_ANALYTICS",
                ],
                "exact_date_matching_tiers":[
                    "A1_PLATFORM_SELLER_OFFICIAL",
                    "A2_PLATFORM_CONSUMER_OFFICIAL",
                    "B1_GOVERNMENT_OFFICIAL",
                ],
                "search_snippet_only_forbidden":True,
                "inferred_from_metric_movement_forbidden":True,
            },
            "scope_types":["PLATFORM","MARKET","SHOP"],
            "context_types":["MEGA_SALE","MARKET_SEASON"],
            "context_families":["DOUBLE_DAY_MEGA_SALE","BACK_TO_SCHOOL"],
            "refresh_policy":{
                "monthly_review_required":True,
                "calendar_review_date_field":"checked_at",
                "block_if_review_month_precedes_as_of_period":True,
                "official_platform_sources_first":True,
                "stale_calendar_behavior":"FAIL_CLOSED",
            },
            "safety":{
                "enable_alerts":False,
                "enable_diagnosis":False,
                "infer_campaign_from_metrics":False,
                "write_production_data_mart":False,
                "modify_production_ui":False,
            }
        }),encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def _calendar(self,analytics_matching=False):
        return {
            "version":"TEST",
            "market":"VN",
            "checked_at":"2026-09-25",
            "sources":[
                {
                    "source_id":"official","source_tier":"A1_PLATFORM_SELLER_OFFICIAL",
                    "publisher":"Platform","platform":"shopee","title":"9.9",
                    "url":"https://example.com/official","checked_at":"2026-09-25",
                    "machine_readability":"TEXT",
                },
                {
                    "source_id":"metric","source_tier":"C1_INDUSTRY_ANALYTICS",
                    "publisher":"Metric","platform":"market","title":"Season",
                    "url":"https://example.com/metric","checked_at":"2026-09-25",
                    "machine_readability":"TEXT",
                },
            ],
            "events":[
                {
                    "context_id":"sale","label":"9.9","platform":"shopee",
                    "scope_type":"PLATFORM","shop_id":"",
                    "context_type":"MEGA_SALE","context_family":"DOUBLE_DAY_MEGA_SALE",
                    "start_date":"2026-09-07","end_date":"2026-09-09",
                    "peak_dates":["2026-09-09"],"window_type":"CAMPAIGN",
                    "source_id":"official","verification_status":"VERIFIED_OFFICIAL",
                    "exact_date_verified":True,"matching_eligible":True,
                },
                {
                    "context_id":"season","label":"Back to school","platform":"market",
                    "scope_type":"MARKET","shop_id":"",
                    "context_type":"MARKET_SEASON","context_family":"BACK_TO_SCHOOL",
                    "start_date":"2026-08-01","end_date":"2026-09-30",
                    "peak_dates":[],"window_type":"MONTH_LEVEL_MARKET_SEASON",
                    "source_id":"metric","verification_status":"VERIFIED_ANALYTICS",
                    "exact_date_verified":False,"matching_eligible":analytics_matching,
                },
            ],
            "reference_only":[],
        }

    def test_official_exact_dates_expand_to_daily_context(self):
        self.calendar.write_text(json.dumps(self._calendar()),encoding="utf-8")
        result=build_business_context(
            contract_path=self.contract,calendar_path=self.calendar,
            as_of_period="2026-09",output_dir=self.root/"out"
        )
        rows=[
            json.loads(x) for x in (self.root/"out"/"context_days.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        sale=[x for x in rows if x["context_id"]=="sale"]
        self.assertEqual([x["data_date"] for x in sale],["2026-09-07","2026-09-08","2026-09-09"])
        self.assertTrue(sale[-1]["is_peak_date"])
        self.assertTrue(all(x["matching_eligible"] for x in sale))
        self.assertFalse(result["safety"]["alertsEnabled"])

    def test_analytics_source_cannot_manufacture_exact_matching_context(self):
        self.calendar.write_text(json.dumps(self._calendar(analytics_matching=True)),encoding="utf-8")
        with self.assertRaisesRegex(ValueError,"business context QA failed"):
            build_business_context(
                contract_path=self.contract,calendar_path=self.calendar,
                as_of_period="2026-09",output_dir=self.root/"bad"
            )

    def test_context_fingerprint_is_deterministic(self):
        self.calendar.write_text(json.dumps(self._calendar()),encoding="utf-8")
        r1=build_business_context(
            contract_path=self.contract,calendar_path=self.calendar,
            as_of_period="2026-09",output_dir=self.root/"a"
        )
        r2=build_business_context(
            contract_path=self.contract,calendar_path=self.calendar,
            as_of_period="2026-09",output_dir=self.root/"b"
        )
        self.assertEqual(r1["contextBuildFingerprint"],r2["contextBuildFingerprint"])

    def test_stale_calendar_blocks_future_month(self):
        self.calendar.write_text(json.dumps(self._calendar()),encoding="utf-8")
        with self.assertRaisesRegex(ValueError,"business context QA failed"):
            build_business_context(
                contract_path=self.contract,calendar_path=self.calendar,
                as_of_period="2026-10",output_dir=self.root/"stale"
            )


if __name__=="__main__":
    unittest.main()
