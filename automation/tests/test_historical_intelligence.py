import json
import tempfile
import unittest
from pathlib import Path

from modules.historical_intelligence import build_historical_intelligence


class HistoricalIntelligenceTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.contract=self.root/"contract.json"
        self.contract.write_text(json.dumps({
            "version":"1.0",
            "layer_name":"multi_shop_historical_intelligence_v1",
            "status":"PREPRODUCTION",
            "inventory_policy":{
                "trusted_history_source":"PUBLISHED_SEMANTIC_QA_PASS",
                "raw_source_presence_role":"BACKFILL_CANDIDATE_ONLY"
            },
            "comparator_policy":{
                "same_weekday":{"lookback_weeks":8,"min_samples":4},
                "same_day_of_month":{"lookback_months":6,"min_samples":3}
            },
            "minimum_history":{
                "history_ready_min_complete_months":3,
                "six_month_intelligence_min_complete_months":6,
                "same_weekday_min_samples":4,
                "same_day_of_month_min_samples":3
            },
            "baseline_policy":{
                "statistics":["median","mean","min","max","mad"]
            },
            "context_policy":{"source_policy":"EXPLICIT_ONLY"},
            "anomaly_eligibility_policy":{
                "enabled":True,
                "statuses":["ANOMALY_ELIGIBLE","ANOMALY_BLOCKED"],
                "metric_scope":"PER_COMPARATOR_PER_KPI",
                "metric_names":[
                    "placedGmv","placedOrders","productClicks","placedAov","placedCvr",
                    "adsSpend","adsAttributedSales","roas","cancelledSales",
                    "netSalesAfterCancel","orderFees","totalPlatformCostRatio"
                ],
                "statistical_baseline_comparators":["sameWeekday","sameDayOfMonth"],
                "factual_window_comparators":["previousDay","previous7d","previousMonthMtd"],
                "reason_codes":[
                    "COMPARATOR_NOT_READY","DATA_WINDOW_INCOMPLETE",
                    "INSUFFICIENT_HISTORY_DEPTH","SHOP_LIFECYCLE_HISTORY_TOO_SHORT",
                    "PORTFOLIO_LIFECYCLE_HISTORY_TOO_SHORT","CONTEXT_LINEAGE_UNAVAILABLE",
                    "CONTEXT_DIFFERENT","CONTEXT_UNKNOWN","INSUFFICIENT_CONTEXT_MATCHED_HISTORY",
                    "NO_STATISTICAL_BASELINE_METHOD","METRIC_BASELINE_UNAVAILABLE"
                ],
                "anomaly_detection_enabled":False,
                "severity_enabled":False,
                "alerts_enabled":False,
                "diagnosis_enabled":False,
                "causal_claims_enabled":False
            },
            "anomaly_detection_foundation":{
                "enabled":True,
                "mode":"PREPRODUCTION_EVIDENCE_ONLY",
                "operational_anomaly_detection_enabled":False,
                "statuses":["NORMAL","DEVIATION_CANDIDATE","NOT_EVALUATED"],
                "statistical_method":"MODIFIED_Z_SCORE_MAD",
                "modified_z_constant":0.67448975,
                "absolute_z_threshold":3.5,
                "zero_mad_behavior":"NOT_EVALUATED",
                "zero_median_effect_behavior":"NOT_EVALUATED",
                "baseline_source":"CONTEXT_MATCHED_BASELINE_ONLY",
                "current_observation":"LATEST_TRUSTED_DAY",
                "eligibility_source":"ANOMALY_ELIGIBILITY_PER_KPI",
                "minimum_effect_pct":{
                    "placedGmv":0.15,"placedOrders":0.15,"productClicks":0.15,
                    "placedAov":0.10,"placedCvr":0.10,"adsSpend":0.20,
                    "adsAttributedSales":0.15,"roas":0.15,"cancelledSales":0.25,
                    "netSalesAfterCancel":0.15,"orderFees":0.20,
                    "totalPlatformCostRatio":0.15
                },
                "directionality":{
                    "placedGmv":"LOWER_ONLY","placedOrders":"LOWER_ONLY",
                    "productClicks":"LOWER_ONLY","placedAov":"LOWER_ONLY",
                    "placedCvr":"LOWER_ONLY","adsSpend":"TWO_SIDED",
                    "adsAttributedSales":"LOWER_ONLY","roas":"LOWER_ONLY",
                    "cancelledSales":"HIGHER_ONLY","netSalesAfterCancel":"LOWER_ONLY",
                    "orderFees":"TWO_SIDED","totalPlatformCostRatio":"HIGHER_ONLY"
                },
                "not_evaluated_reasons":[
                    "ANOMALY_ELIGIBILITY_BLOCKED","BASELINE_STATISTICS_UNAVAILABLE",
                    "ROBUST_SCALE_ZERO","RELATIVE_EFFECT_UNDEFINED"
                ],
                "deviation_candidate_is_not_alert":True,
                "severity_enabled":False,"alerts_enabled":False,
                "diagnosis_enabled":False,"causal_claims_enabled":False
            },
            "anomaly_severity_confidence":{
                "enabled":True,
                "mode":"PREPRODUCTION_EVIDENCE_ONLY",
                "source_state":"DEVIATION_CANDIDATE_ONLY",
                "non_candidate_status":"NOT_ASSESSED",
                "severity_meaning":"STATISTICAL_AND_RELATIVE_MAGNITUDE_ONLY_NOT_BUSINESS_IMPACT",
                "severity_levels":["LOW","MEDIUM","HIGH"],
                "severity_score":{
                    "method":"WEIGHTED_SIGNAL_STRENGTH",
                    "statistical_weight":0.5,"effect_weight":0.5,
                    "low_max_exclusive":0.55,"high_min_inclusive":0.8
                },
                "confidence_levels":["LOW","MEDIUM","HIGH"],
                "confidence_score":{
                    "method":"WEIGHTED_EVIDENCE_QUALITY",
                    "sample_depth_weight":0.5,"context_lineage_weight":0.2,
                    "history_readiness_weight":0.15,"robust_scale_weight":0.15,
                    "low_max_exclusive":0.6,"high_min_inclusive":0.85
                },
                "no_severity_for":["NORMAL","NOT_EVALUATED"],
                "automatic_alerts_enabled":False,
                "diagnosis_enabled":False,
                "causal_claims_enabled":False
            },
            "driver_attribution_foundation":{
                "enabled":True,
                "mode":"PREPRODUCTION_EVIDENCE_ONLY",
                "source_detector_state":"DEVIATION_CANDIDATE_ONLY",
                "minimum_confidence_level":"MEDIUM",
                "statuses":["ATTRIBUTED","ASSOCIATION_ONLY","NOT_DIAGNOSED"],
                "supported_identities":{
                    "placedGmv":{
                        "identity":"GMV = Product Clicks × CVR × AOV",
                        "drivers":["productClicks","placedCvr","placedAov"]
                    },
                    "placedOrders":{
                        "identity":"Orders = Product Clicks × CVR",
                        "drivers":["productClicks","placedCvr"]
                    },
                    "roas":{
                        "identity":"ROAS = Ads Attributed Sales / Ads Spend",
                        "drivers":["adsAttributedSales","adsSpend"]
                    },
                    "netSalesAfterCancel":{
                        "identity":"Net Sales = Placed GMV - Cancelled Sales",
                        "drivers":["placedGmv","cancelledSales"]
                    },
                    "totalPlatformCostRatio":{
                        "identity":"Platform Cost Ratio = (Order Fees + Ads Spend) / Net Sales After Cancel",
                        "drivers":["orderFees","adsSpend","netSalesAfterCancel"]
                    }
                },
                "attribution_method":"EXACT_SHAPLEY_ON_BUSINESS_IDENTITY",
                "reference_source":"CONTEXT_MATCHED_BASELINE_MEDIANS",
                "max_baseline_alignment_residual_pct":0.25,
                "association_source":"CO_MOVING_DEVIATION_CANDIDATES_ONLY",
                "identity_contribution_is_causal_claim":False,
                "operational_diagnosis_enabled":False,
                "automatic_alerts_enabled":False,
                "causal_claims_enabled":False
            },
            "smart_issues_foundation":{
                "enabled":True,
                "mode":"PREPRODUCTION_EVIDENCE_ONLY",
                "issue_type":"PERFORMANCE_DEVIATION",
                "statuses":["ISSUE_READY","NO_ISSUE"],
                "source_detector_state":"DEVIATION_CANDIDATE_ONLY",
                "minimum_severity_level":"MEDIUM",
                "minimum_confidence_level":"MEDIUM",
                "allowed_attribution_statuses":["ATTRIBUTED","ASSOCIATION_ONLY"],
                "max_issues_per_comparator":1,
                "max_issues_per_scope":5,
                "dedupe_key":"AFFECTED_METRIC",
                "ranking":[
                    "ATTRIBUTION_STATUS","BUSINESS_KPI_PRIORITY","SEVERITY_SCORE",
                    "CONFIDENCE_SCORE","ABS_EFFECT_PCT"
                ],
                "attribution_priority":{
                    "ATTRIBUTED":2,"ASSOCIATION_ONLY":1
                },
                "business_metric_priority":{
                    "placedGmv":100,"placedOrders":90,"roas":85,
                    "netSalesAfterCancel":80,"totalPlatformCostRatio":75,
                    "placedCvr":70,"placedAov":65,"productClicks":60,
                    "adsAttributedSales":55,"cancelledSales":50,
                    "adsSpend":45,"orderFees":40
                },
                "issue_surface":"LATEST_TRUSTED_OBSERVATION",
                "required_uncertainty":[
                    "CAUSALITY_NOT_ESTABLISHED",
                    "AUTOMATIC_ALERTS_DISABLED",
                    "HUMAN_REVIEW_REQUIRED",
                    "PLATFORM_MUTATION_DISABLED"
                ],
                "operational_alerts_enabled":False,
                "action_recommendations_enabled":False,
                "operational_diagnosis_enabled":False,
                "causal_claims_enabled":False
            },
            "operator_action_policy_foundation":{
                "enabled":True,
                "mode":"PREPRODUCTION_REVIEW_OPTIONS_ONLY",
                "source_issue_state":"ISSUE_READY_ONLY",
                "statuses":["ACTION_OPTIONS_READY","NO_ACTION_OPTIONS"],
                "option_status":"REVIEW_OPTION",
                "max_options_per_issue":2,
                "max_options_per_scope":6,
                "generic_validation_option":True,
                "targeted_review_requires_attributed_driver":True,
                "targeted_driver_rules":{
                    "productClicks":"REVIEW_TRAFFIC_AND_LISTING_VISIBILITY",
                    "placedCvr":"REVIEW_CONVERSION_FUNNEL_AND_OFFER",
                    "placedAov":"REVIEW_AOV_PRICE_PROMOTION_MIX",
                    "adsSpend":"REVIEW_ADS_SPEND_EFFICIENCY",
                    "adsAttributedSales":"REVIEW_ADS_ATTRIBUTED_SALES",
                    "cancelledSales":"REVIEW_CANCELLATION_AND_FULFILLMENT",
                    "orderFees":"REVIEW_FEE_AND_PROMOTION_COST",
                    "netSalesAfterCancel":"REVIEW_NET_SALES_QUALITY"
                },
                "forbidden_directives":[
                    "CHANGE_BID","CHANGE_BUDGET","CHANGE_PRICE","CHANGE_PROMOTION",
                    "PAUSE_CAMPAIGN","PUBLISH_LISTING_CHANGE","CONTACT_CUSTOMER_AUTOMATICALLY"
                ],
                "requires_human_review":True,
                "platform_mutation_allowed":False,
                "automatic_execution_enabled":False,
                "automatic_alerts_enabled":False,
                "causal_claims_enabled":False
            },
            "production_cutover_shadow_mode_v1":{
                "enabled":True,
                "mode":"PREPRODUCTION_OBSERVE_ONLY",
                "statuses":[
                    "SHADOW_OBSERVING","READY_FOR_HUMAN_CUTOVER_REVIEW",
                    "CUTOVER_BLOCKED"
                ],
                "minimum_consecutive_safe_refreshes":3,
                "minimum_consecutive_stable_refreshes":3,
                "max_retained_refresh_records":10,
                "required_readiness_gates":[
                    "TRUSTED_LINEAGE_COMPLETE","LINEAGE_CONTINUITY",
                    "ALL_ENABLED_SCOPES_PRESENT","FAIL_CLOSED_SAFETY",
                    "ISSUE_ACTION_TRANSITIONS_VALID","MINIMUM_SAFE_REFRESHES",
                    "MINIMUM_STABLE_REFRESHES","HUMAN_VISUAL_BASELINE_RETAINED"
                ],
                "approved_visual_baseline_run":216,
                "cutover_requires_explicit_human_approval":True,
                "automatic_cutover_enabled":False,
                "production_activation_enabled":False,
                "production_writes_enabled":False,
                "platform_mutation_allowed":False,
                "automatic_alerts_enabled":False,
                "rollback_required":True
            },
            "safety":{
                "write_production_data_mart":False,
                "modify_production_ui":False,
                "publish_legacy_payload":False,
                "enable_historical_alerts":False,
                "enable_diagnosis":False
            }
        }),encoding="utf-8")
        self.shops=[
            {"shop_id":"SHOP_A","shop_key":"a"},
            {"shop_id":"SHOP_B","shop_key":"b"}
        ]

    def tearDown(self):
        self.tmp.cleanup()

    def _row(self,sid,date,gmv=100,orders=2,clicks=10):
        return {
            "shop_id":sid,"data_date":date,
            "placed_gmv":gmv,"placed_orders":orders,"product_clicks":clicks,
            "ads_spend":10,"ads_attributed_sales":50,
            "cancelled_sales":0,"net_sales_after_cancel":gmv,"order_fees":4
        }

    def _inventory(self,months):
        return {
            "semantic":{
                "trustedMonths":months,
                "trustedFingerprints":[f"FP_{x}" for x in months]
            },
            "raw":{
                "SHOP_A":{"coreDailyBackfillCandidateMonths":["2026-07","2026-08","2026-09"]},
                "SHOP_B":{"coreDailyBackfillCandidateMonths":["2026-07","2026-08","2026-09"]}
            }
        }

    def test_one_partial_month_is_explicitly_insufficient(self):
        rows=[]
        for day in range(1,18):
            d=f"2026-09-{day:02d}"
            rows.extend([self._row("SHOP_A",d),self._row("SHOP_B",d,200,4,20)])
        out=self.root/"one"
        result=build_historical_intelligence(
            semantic_daily_rows=rows,inventory=self._inventory(["2026-09"]),
            shops=self.shops,as_of_period="2026-09",
            contract_path=self.contract,output_dir=out
        )
        payload=json.loads((out/"historical_intelligence.json").read_text(encoding="utf-8"))
        self.assertEqual(result["status"],"PASS")
        self.assertEqual(payload["portfolio"]["status"],"INSUFFICIENT_HISTORY")
        self.assertEqual(payload["portfolio"]["sixMonthStatus"],"INSUFFICIENT_HISTORY")
        self.assertFalse(payload["portfolio"]["alertEligible"])
        self.assertFalse(payload["capabilities"]["historicalAlerts"])
        self.assertEqual(
            payload["portfolio"]["comparators"]["sameWeekday"]["status"],
            "INSUFFICIENT_HISTORY"
        )

    def test_same_weekday_requires_four_real_samples(self):
        import datetime as dt
        rows=[]
        start=dt.date(2026,8,15)
        for offset in range(35):
            d=(start+dt.timedelta(days=offset)).isoformat()
            rows.extend([self._row("SHOP_A",d),self._row("SHOP_B",d)])
        out=self.root/"weekday"
        build_historical_intelligence(
            semantic_daily_rows=rows,inventory=self._inventory(["2026-08","2026-09"]),
            shops=self.shops,as_of_period="2026-09",
            contract_path=self.contract,output_dir=out
        )
        payload=json.loads((out/"historical_intelligence.json").read_text(encoding="utf-8"))
        sw=payload["shops"]["SHOP_A"]["comparators"]["sameWeekday"]
        self.assertEqual(sw["status"],"READY")
        self.assertGreaterEqual(sw["sampleCount"],4)
        self.assertFalse(sw["alertEligible"])

    def test_previous_7d_recomputes_ratios(self):
        rows=[]
        for day in range(1,18):
            d=f"2026-09-{day:02d}"
            rows.append(self._row("SHOP_A",d,100+day,2,10))
            rows.append(self._row("SHOP_B",d,200+day,4,20))
        out=self.root/"prev7"
        build_historical_intelligence(
            semantic_daily_rows=rows,inventory=self._inventory(["2026-09"]),
            shops=self.shops,as_of_period="2026-09",
            contract_path=self.contract,output_dir=out
        )
        payload=json.loads((out/"historical_intelligence.json").read_text(encoding="utf-8"))
        p=payload["shops"]["SHOP_A"]["comparators"]["previous7d"]
        self.assertEqual(p["status"],"READY")
        self.assertAlmostEqual(
            p["current"]["placedAov"],
            p["current"]["placedGmv"]/p["current"]["placedOrders"]
        )
        self.assertAlmostEqual(
            p["current"]["roas"],
            p["current"]["adsAttributedSales"]/p["current"]["adsSpend"]
        )

    def test_historical_fingerprint_is_deterministic(self):
        rows=[]
        for day in range(1,18):
            d=f"2026-09-{day:02d}"
            rows.extend([self._row("SHOP_A",d),self._row("SHOP_B",d)])
        r1=build_historical_intelligence(
            semantic_daily_rows=rows,inventory=self._inventory(["2026-09"]),
            shops=self.shops,as_of_period="2026-09",
            contract_path=self.contract,output_dir=self.root/"det1"
        )
        r2=build_historical_intelligence(
            semantic_daily_rows=rows,inventory=self._inventory(["2026-09"]),
            shops=self.shops,as_of_period="2026-09",
            contract_path=self.contract,output_dir=self.root/"det2"
        )
        self.assertEqual(
            r1["historicalBuildFingerprint"],
            r2["historicalBuildFingerprint"]
        )

    def test_portfolio_requires_same_date_from_every_shop(self):
        rows=[
            self._row("SHOP_A","2026-09-01"),
            self._row("SHOP_B","2026-09-01"),
            self._row("SHOP_A","2026-09-02")
        ]
        out=self.root/"aligned"
        build_historical_intelligence(
            semantic_daily_rows=rows,inventory=self._inventory(["2026-09"]),
            shops=self.shops,as_of_period="2026-09",
            contract_path=self.contract,output_dir=out
        )
        payload=json.loads((out/"historical_intelligence.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["portfolio"]["coverage"]["dayCount"],1)
        self.assertEqual(payload["portfolio"]["latestTrustedDate"],"2026-09-01")

    def test_launch_origin_is_not_reported_as_prelaunch_missing_data(self):
        import datetime as dt
        shops=[
            {"shop_id":"SHOP_A","shop_key":"a","history_lifecycle":{
                "origin":"PREEXISTING_BEFORE_TRUSTED_WINDOW",
                "start_policy":"UNKNOWN_BEFORE_TRUSTED_WINDOW",
                "pre_start_dates_are_missing":None,
            }},
            {"shop_id":"SHOP_B","shop_key":"b","history_lifecycle":{
                "origin":"SHOP_LAUNCH",
                "start_policy":"FIRST_TRUSTED_SEMANTIC_DATE",
                "pre_start_dates_are_missing":False,
            }},
        ]
        rows=[]
        start=dt.date(2026,7,20)
        end=dt.date(2026,9,17)
        for offset in range((end-start).days+1):
            d=(start+dt.timedelta(days=offset)).isoformat()
            rows.extend([self._row("SHOP_A",d),self._row("SHOP_B",d)])
        out=self.root/"launch"
        build_historical_intelligence(
            semantic_daily_rows=rows,inventory=self._inventory(["2026-07","2026-08","2026-09"]),
            shops=shops,as_of_period="2026-09",
            contract_path=self.contract,output_dir=out
        )
        payload=json.loads((out/"historical_intelligence.json").read_text(encoding="utf-8"))
        mall=payload["shops"]["SHOP_B"]
        portfolio=payload["portfolio"]
        self.assertEqual(mall["coverage"]["coverageOrigin"],"SHOP_LAUNCH")
        self.assertEqual(mall["coverage"]["lifecycleStartDate"],"2026-07-20")
        self.assertFalse(mall["coverage"]["preStartDatesAreMissing"])
        self.assertEqual(mall["historyDepthReason"],"HISTORY_LENGTH_NOT_DATA_GAP")
        self.assertEqual(portfolio["coverage"]["coverageOrigin"],"ALL_ENABLED_SHOPS_ACTIVE")
        self.assertFalse(portfolio["coverage"]["preStartDatesAreMissing"])

    def test_explicit_business_context_binds_to_comparators_fail_closed(self):
        import datetime as dt
        shops=[
            {"shop_id":"SHOP_A","shop_key":"a","platform":"shopee"},
            {"shop_id":"SHOP_B","shop_key":"b","platform":"shopee"},
        ]
        rows=[]
        start=dt.date(2026,7,20)
        end=dt.date(2026,9,17)
        for offset in range((end-start).days+1):
            d=(start+dt.timedelta(days=offset)).isoformat()
            rows.extend([self._row("SHOP_A",d),self._row("SHOP_B",d)])
        context_rows=[
            {
                "data_date":"2026-09-17",
                "context_id":"shopee_mid_autumn",
                "label":"Siêu Hội Trăng Rằm",
                "platform":"shopee",
                "scope_type":"PLATFORM",
                "shop_id":"",
                "context_type":"PLATFORM_PROGRAM",
                "context_family":"FESTIVAL_CAMPAIGN",
                "window_type":"CONSUMER_CAMPAIGN",
                "is_peak_date":False,
                "source_id":"official",
                "source_tier":"A2_PLATFORM_CONSUMER_OFFICIAL",
                "verification_status":"VERIFIED_OFFICIAL",
                "exact_date_verified":True,
                "matching_eligible":True,
            },
            {
                "data_date":"2026-09-02",
                "context_id":"national_day",
                "label":"Quốc khánh",
                "platform":"market",
                "scope_type":"MARKET",
                "shop_id":"",
                "context_type":"HOLIDAY",
                "context_family":"PUBLIC_HOLIDAY",
                "window_type":"PUBLIC_HOLIDAY_WINDOW",
                "is_peak_date":True,
                "source_id":"gov",
                "source_tier":"B1_GOVERNMENT_OFFICIAL",
                "verification_status":"VERIFIED_OFFICIAL",
                "exact_date_verified":True,
                "matching_eligible":True,
            },
        ]
        out=self.root/"context"
        result=build_historical_intelligence(
            semantic_daily_rows=rows,
            inventory=self._inventory(["2026-07","2026-08","2026-09"]),
            shops=shops,
            as_of_period="2026-09",
            contract_path=self.contract,
            output_dir=out,
            context_rows=context_rows,
            context_fingerprint="CTX_FP",
        )
        payload=json.loads((out/"historical_intelligence.json").read_text(encoding="utf-8"))
        self.assertEqual(result["businessContextFingerprint"],"CTX_FP")
        self.assertEqual(
            payload["historySources"]["businessContextFingerprint"],"CTX_FP"
        )
        for scope in [payload["portfolio"],*payload["shops"].values()]:
            self.assertEqual(scope["context"]["status"],"CONTEXT_AVAILABLE")
            self.assertEqual(scope["context"]["sourceFingerprint"],"CTX_FP")
            self.assertFalse(scope["context"]["contextMatchedBaselineEnabled"])
            self.assertFalse(scope["context"]["alertEligible"])
            for comparator in scope["comparators"].values():
                bc=comparator["businessContext"]
                self.assertEqual(bc["status"],"CONTEXT_AVAILABLE")
                self.assertFalse(bc["alertEligible"])
                self.assertFalse(bc["diagnosisEligible"])
        latest=payload["shops"]["SHOP_A"]["comparators"]["previousDay"]["businessContext"]
        self.assertIn("shopee_mid_autumn",latest["current"]["eventIds"])
        self.assertIn(
            "shopee_mid_autumn",
            latest["current"]["matchingEligibleEventIds"],
        )

        self.assertEqual(latest["matchEvaluation"],"CONTEXT_DIFFERENT")
        self.assertEqual(
            latest["qualification"]["reason"],
            "EXACT_MATCHING_EVENT_PRESENT_ON_ONE_SIDE_ONLY",
        )
        self.assertFalse(latest["qualification"]["causalClaimEligible"])

    def test_context_qualification_uses_family_profile_not_event_id(self):
        rows=[]
        for day in range(1,5):
            d=f"2026-09-{day:02d}"
            rows.extend([self._row("SHOP_A",d),self._row("SHOP_B",d)])
        context_rows=[
            {
                "data_date":"2026-09-03","context_id":"campaign_prev",
                "platform":"market","scope_type":"MARKET","shop_id":"",
                "context_type":"MEGA_SALE","context_family":"DOUBLE_DAY_MEGA_SALE",
                "is_peak_date":True,"matching_eligible":True,
                "source_tier":"B1_GOVERNMENT_OFFICIAL",
            },
            {
                "data_date":"2026-09-04","context_id":"campaign_current",
                "platform":"market","scope_type":"MARKET","shop_id":"",
                "context_type":"MEGA_SALE","context_family":"DOUBLE_DAY_MEGA_SALE",
                "is_peak_date":True,"matching_eligible":True,
                "source_tier":"B1_GOVERNMENT_OFFICIAL",
            },
        ]
        out=self.root/"context-compatible"
        build_historical_intelligence(
            semantic_daily_rows=rows,inventory=self._inventory(["2026-09"]),
            shops=self.shops,as_of_period="2026-09",
            contract_path=self.contract,output_dir=out,
            context_rows=context_rows,context_fingerprint="CTX_COMPAT",
        )
        payload=json.loads((out/"historical_intelligence.json").read_text(encoding="utf-8"))
        bc=payload["portfolio"]["comparators"]["previousDay"]["businessContext"]
        self.assertEqual(bc["matchEvaluation"],"CONTEXT_COMPATIBLE")
        self.assertEqual(
            bc["qualification"]["reason"],
            "EXACT_MATCHING_PROFILE_EQUAL",
        )
        self.assertNotEqual(
            bc["current"]["matchingEligibleEventIds"],
            bc["reference"]["matchingEligibleEventIds"],
        )

    def test_context_qualification_is_unknown_when_both_sides_have_no_exact_event(self):
        rows=[]
        for day in range(1,5):
            d=f"2026-09-{day:02d}"
            rows.extend([self._row("SHOP_A",d),self._row("SHOP_B",d)])
        context_rows=[
            {
                "data_date":"2026-09-03","context_id":"season_prev",
                "platform":"market","scope_type":"MARKET","shop_id":"",
                "context_type":"MARKET_SEASON","context_family":"BACK_TO_SCHOOL",
                "is_peak_date":False,"matching_eligible":False,
                "source_tier":"C1_INDUSTRY_ANALYTICS",
            },
            {
                "data_date":"2026-09-04","context_id":"season_current",
                "platform":"market","scope_type":"MARKET","shop_id":"",
                "context_type":"MARKET_SEASON","context_family":"BACK_TO_SCHOOL",
                "is_peak_date":False,"matching_eligible":False,
                "source_tier":"C1_INDUSTRY_ANALYTICS",
            },
        ]
        out=self.root/"context-unknown"
        build_historical_intelligence(
            semantic_daily_rows=rows,inventory=self._inventory(["2026-09"]),
            shops=self.shops,as_of_period="2026-09",
            contract_path=self.contract,output_dir=out,
            context_rows=context_rows,context_fingerprint="CTX_UNKNOWN",
        )
        payload=json.loads((out/"historical_intelligence.json").read_text(encoding="utf-8"))
        bc=payload["portfolio"]["comparators"]["previousDay"]["businessContext"]
        self.assertEqual(bc["matchEvaluation"],"CONTEXT_UNKNOWN")
        self.assertEqual(
            bc["qualification"]["reason"],
            "NO_EXACT_MATCHING_EVENT_ON_EITHER_SIDE",
        )
        self.assertFalse(bc["contextMatchedBaselineEligible"])

    def test_context_matched_baseline_is_insufficient_without_silent_fallback(self):
        import datetime as dt
        rows=[]
        start=dt.date(2026,7,20); end=dt.date(2026,9,17)
        for offset in range((end-start).days+1):
            d=(start+dt.timedelta(days=offset)).isoformat()
            rows.extend([self._row("SHOP_A",d),self._row("SHOP_B",d)])
        context_rows=[{
            "data_date":"2026-09-17","context_id":"festival_now",
            "platform":"shopee","scope_type":"PLATFORM","shop_id":"",
            "context_type":"PLATFORM_PROGRAM","context_family":"FESTIVAL_CAMPAIGN",
            "is_peak_date":False,"matching_eligible":True,
            "source_tier":"A2_PLATFORM_CONSUMER_OFFICIAL",
        }]
        out=self.root/"matched-insufficient"
        build_historical_intelligence(
            semantic_daily_rows=rows,
            inventory=self._inventory(["2026-07","2026-08","2026-09"]),
            shops=[
                {"shop_id":"SHOP_A","shop_key":"a","platform":"shopee"},
                {"shop_id":"SHOP_B","shop_key":"b","platform":"shopee"},
            ],
            as_of_period="2026-09",contract_path=self.contract,output_dir=out,
            context_rows=context_rows,context_fingerprint="CTX_MATCHED_INSUFFICIENT",
        )
        payload=json.loads((out/"historical_intelligence.json").read_text(encoding="utf-8"))
        sw=payload["portfolio"]["comparators"]["sameWeekday"]
        self.assertEqual(sw["status"],"READY")
        self.assertIn("baseline",sw)
        matched=sw["contextMatchedBaseline"]
        self.assertEqual(matched["status"],"INSUFFICIENT_CONTEXT_MATCHED_HISTORY")
        self.assertEqual(matched["requiredSampleCount"],4)
        self.assertEqual(matched["sampleCount"],0)
        self.assertNotIn("baseline",matched)
        self.assertFalse(matched["silentFallbackUsed"])
        self.assertFalse(payload["portfolio"]["context"]["contextMatchedBaselineEnabled"])

    def test_context_matched_baseline_ready_preserves_all_history_baseline(self):
        import datetime as dt
        rows=[]
        start=dt.date(2026,7,20); end=dt.date(2026,9,17)
        for offset in range((end-start).days+1):
            d=(start+dt.timedelta(days=offset)).isoformat()
            rows.extend([self._row("SHOP_A",d),self._row("SHOP_B",d)])
        compatible_dates=["2026-09-17","2026-09-10","2026-09-03","2026-08-27","2026-08-20"]
        context_rows=[]
        for i,d in enumerate(compatible_dates):
            context_rows.append({
                "data_date":d,"context_id":f"member_{i}",
                "platform":"shopee","scope_type":"PLATFORM","shop_id":"",
                "context_type":"PLATFORM_PROGRAM","context_family":"MEMBER_DAY",
                "is_peak_date":False,"matching_eligible":True,
                "source_tier":"A1_PLATFORM_SELLER_OFFICIAL",
            })
        out=self.root/"matched-ready"
        build_historical_intelligence(
            semantic_daily_rows=rows,
            inventory=self._inventory(["2026-07","2026-08","2026-09"]),
            shops=[
                {"shop_id":"SHOP_A","shop_key":"a","platform":"shopee"},
                {"shop_id":"SHOP_B","shop_key":"b","platform":"shopee"},
            ],
            as_of_period="2026-09",contract_path=self.contract,output_dir=out,
            context_rows=context_rows,context_fingerprint="CTX_MATCHED_READY",
        )
        payload=json.loads((out/"historical_intelligence.json").read_text(encoding="utf-8"))
        sw=payload["portfolio"]["comparators"]["sameWeekday"]
        self.assertEqual(sw["sampleCount"],8)
        self.assertIn("baseline",sw)
        matched=sw["contextMatchedBaseline"]
        self.assertEqual(matched["status"],"READY")
        self.assertEqual(matched["requiredSampleCount"],4)
        self.assertEqual(matched["sampleCount"],4)
        self.assertEqual(
            matched["sampleDates"],
            ["2026-09-10","2026-09-03","2026-08-27","2026-08-20"],
        )
        self.assertIn("baseline",matched)
        self.assertTrue(payload["portfolio"]["context"]["contextMatchedBaselineEnabled"])
        self.assertTrue(payload["capabilities"]["contextMatchedBaseline"])
        self.assertFalse(matched["silentFallbackUsed"])

    def test_anomaly_eligibility_requires_ready_history_and_matched_baseline(self):
        import datetime as dt
        rows=[]
        start=dt.date(2026,7,1); end=dt.date(2026,9,30)
        for offset in range((end-start).days+1):
            d=(start+dt.timedelta(days=offset)).isoformat()
            rows.extend([self._row("SHOP_A",d),self._row("SHOP_B",d)])
        latest="2026-09-30"
        compatible=[latest]
        for k in range(1,6):
            compatible.append((dt.date(2026,9,30)-dt.timedelta(days=7*k)).isoformat())
        context_rows=[]
        for i,d in enumerate(compatible):
            context_rows.append({
                "data_date":d,"context_id":f"member_{i}",
                "platform":"market","scope_type":"MARKET","shop_id":"",
                "context_type":"PLATFORM_PROGRAM","context_family":"MEMBER_DAY",
                "is_peak_date":False,"matching_eligible":True,
                "source_tier":"B1_GOVERNMENT_OFFICIAL",
            })
        out=self.root/"elig-ready"
        build_historical_intelligence(
            semantic_daily_rows=rows,
            inventory=self._inventory(["2026-07","2026-08","2026-09"]),
            shops=self.shops,as_of_period="2026-09",
            contract_path=self.contract,output_dir=out,
            context_rows=context_rows,context_fingerprint="CTX_ELIG",
        )
        payload=json.loads((out/"historical_intelligence.json").read_text(encoding="utf-8"))
        portfolio=payload["portfolio"]
        self.assertEqual(portfolio["status"],"READY")
        sw=portfolio["comparators"]["sameWeekday"]
        self.assertEqual(sw["contextMatchedBaseline"]["status"],"READY")
        self.assertEqual(sw["anomalyEligibility"]["status"],"ANOMALY_ELIGIBLE")
        self.assertEqual(sw["anomalyEligibility"]["reasonCodes"],[])
        self.assertTrue(all(
            x["status"]=="ANOMALY_ELIGIBLE"
            for x in sw["anomalyEligibility"]["metricEligibility"].values()
        ))
        self.assertEqual(
            portfolio["comparators"]["previousDay"]["anomalyEligibility"]["status"],
            "ANOMALY_BLOCKED",
        )
        self.assertIn(
            "NO_STATISTICAL_BASELINE_METHOD",
            portfolio["comparators"]["previousDay"]["anomalyEligibility"]["reasonCodes"],
        )
        self.assertFalse(payload["capabilities"]["anomalyDetection"])

    def test_anomaly_eligibility_reports_fail_closed_block_reasons(self):
        rows=[]
        for day in range(1,18):
            d=f"2026-09-{day:02d}"
            rows.extend([self._row("SHOP_A",d),self._row("SHOP_B",d)])
        out=self.root/"elig-blocked"
        build_historical_intelligence(
            semantic_daily_rows=rows,
            inventory=self._inventory(["2026-09"]),
            shops=self.shops,as_of_period="2026-09",
            contract_path=self.contract,output_dir=out,
        )
        payload=json.loads((out/"historical_intelligence.json").read_text(encoding="utf-8"))
        sw=payload["portfolio"]["comparators"]["sameWeekday"]["anomalyEligibility"]
        self.assertEqual(sw["status"],"ANOMALY_BLOCKED")
        self.assertIn("PORTFOLIO_LIFECYCLE_HISTORY_TOO_SHORT",sw["reasonCodes"])
        self.assertIn("CONTEXT_LINEAGE_UNAVAILABLE",sw["reasonCodes"])
        self.assertIn("INSUFFICIENT_CONTEXT_MATCHED_HISTORY",sw["reasonCodes"])
        self.assertFalse(sw["anomalyDetectionEnabled"])
        self.assertEqual(payload["portfolio"]["anomalyEligibility"]["eligibleMetricCount"],0)

    def _detector_ready_case(
        self,current_gmv,output_name,current_orders=2,current_clicks=10,
        refresh_id="",previous_shadow_state=None,
    ):
        import datetime as dt
        latest="2026-09-30"
        same_weekday_values={
            "2026-09-23":100,
            "2026-09-16":110,
            "2026-09-09":90,
            "2026-09-02":105,
            "2026-08-26":95,
            "2026-08-19":102,
            "2026-08-12":98,
            "2026-08-05":107,
        }
        rows=[]
        start=dt.date(2026,7,1); end=dt.date(2026,9,30)
        for offset in range((end-start).days+1):
            d=(start+dt.timedelta(days=offset)).isoformat()
            gmv=current_gmv if d==latest else same_weekday_values.get(d,100)
            orders=current_orders if d==latest else 2
            clicks=current_clicks if d==latest else 10
            rows.extend([
                self._row("SHOP_A",d,gmv=gmv,orders=orders,clicks=clicks),
                self._row("SHOP_B",d,gmv=gmv,orders=orders,clicks=clicks),
            ])
        context_dates=[latest,*same_weekday_values.keys()]
        context_rows=[
            {
                "data_date":d,"context_id":f"ctx_{i}",
                "platform":"market","scope_type":"MARKET","shop_id":"",
                "context_type":"PLATFORM_PROGRAM","context_family":"MEMBER_DAY",
                "is_peak_date":False,"matching_eligible":True,
                "source_tier":"B1_GOVERNMENT_OFFICIAL",
            }
            for i,d in enumerate(context_dates)
        ]
        out=self.root/output_name
        build_historical_intelligence(
            semantic_daily_rows=rows,
            inventory=self._inventory(["2026-07","2026-08","2026-09"]),
            shops=self.shops,as_of_period="2026-09",
            contract_path=self.contract,output_dir=out,
            context_rows=context_rows,context_fingerprint="CTX_DETECTOR",
            refresh_id=refresh_id,
            previous_shadow_state=previous_shadow_state,
        )
        return json.loads((out/"historical_intelligence.json").read_text(encoding="utf-8"))

    def test_anomaly_detection_foundation_marks_normal_when_robust_and_effect_gates_do_not_fire(self):
        payload=self._detector_ready_case(100,"detector-normal")
        sw=payload["portfolio"]["comparators"]["sameWeekday"]
        self.assertEqual(sw["anomalyEligibility"]["metricEligibility"]["placedGmv"]["status"],"ANOMALY_ELIGIBLE")
        result=sw["anomalyDetectionFoundation"]["metricResults"]["placedGmv"]
        self.assertEqual(result["status"],"NORMAL")
        self.assertTrue(result["scorePublished"])
        self.assertIn("modifiedZScore",result)
        self.assertFalse(result["effectGatePassed"])
        self.assertFalse(result["alertEligible"])
        self.assertFalse(result["diagnosisEligible"])
        self.assertFalse(result["causalClaimEligible"])
        severity=result["severityConfidence"]
        self.assertEqual(severity["status"],"NOT_ASSESSED")
        self.assertFalse(severity["severityPublished"])
        self.assertFalse(severity["confidencePublished"])
        self.assertNotIn("severityScore",severity)
        self.assertNotIn("confidenceScore",severity)
        attribution=result["driverAttribution"]
        self.assertEqual(attribution["status"],"NOT_DIAGNOSED")
        self.assertEqual(attribution["reason"],"NOT_DEVIATION_CANDIDATE")
        self.assertFalse(attribution["causalClaimEligible"])
        self.assertEqual(payload["portfolio"]["anomalyDetectionFoundation"]["status"],"NORMAL")
        self.assertEqual(payload["portfolio"]["smartIssuesFoundation"]["status"],"NO_ISSUE")
        self.assertEqual(payload["portfolio"]["smartIssuesFoundation"]["issueCount"],0)
        self.assertEqual(payload["portfolio"]["smartIssuesFoundation"]["issues"],[])
        self.assertTrue(payload["capabilities"]["anomalyDetectionFoundation"])
        self.assertFalse(payload["capabilities"]["anomalyDetection"])

    def test_anomaly_detection_foundation_marks_lower_gmv_as_deviation_candidate_without_alert(self):
        payload=self._detector_ready_case(50,"detector-candidate")
        sw=payload["portfolio"]["comparators"]["sameWeekday"]
        result=sw["anomalyDetectionFoundation"]["metricResults"]["placedGmv"]
        self.assertEqual(result["status"],"DEVIATION_CANDIDATE")
        self.assertLess(result["modifiedZScore"],-3.5)
        self.assertTrue(result["directionGatePassed"])
        self.assertTrue(result["effectGatePassed"])
        self.assertTrue(result["scoreGatePassed"])
        self.assertEqual(result["directionalityPolicy"],"LOWER_ONLY")
        self.assertFalse(result["deviationCandidateIsAlert"])
        self.assertFalse(result["alertEligible"])
        severity=result["severityConfidence"]
        self.assertEqual(severity["status"],"ASSESSED")
        self.assertEqual(severity["severityLevel"],"HIGH")
        self.assertEqual(severity["confidenceLevel"],"HIGH")
        self.assertGreaterEqual(severity["severityScore"],0.8)
        self.assertGreaterEqual(severity["confidenceScore"],0.85)
        self.assertFalse(severity["businessImpactClaim"])
        self.assertFalse(severity["alertEligible"])
        self.assertFalse(severity["diagnosisEligible"])
        self.assertFalse(severity["causalClaimEligible"])
        self.assertEqual(
            payload["portfolio"]["anomalySeverityConfidence"]["highestSignalSeverity"],
            "HIGH",
        )
        self.assertEqual(
            payload["portfolio"]["anomalySeverityConfidence"]["lowestEvidenceConfidence"],
            "HIGH",
        )
        attribution=result["driverAttribution"]
        self.assertEqual(attribution["status"],"ATTRIBUTED")
        self.assertEqual(attribution["topDriverMetric"],"placedAov")
        self.assertEqual(attribution["identity"],"GMV = Product Clicks × CVR × AOV")
        self.assertAlmostEqual(
            sum(x["contributionValue"] for x in attribution["driverContributions"]),
            attribution["modeledDifference"],
        )
        self.assertAlmostEqual(attribution["identityClosureResidual"],0.0)
        self.assertFalse(attribution["identityContributionIsCausalClaim"])
        self.assertFalse(attribution["causalClaimEligible"])
        aov_result=sw["anomalyDetectionFoundation"]["metricResults"]["placedAov"]
        self.assertEqual(aov_result["status"],"DEVIATION_CANDIDATE")
        self.assertEqual(aov_result["driverAttribution"]["status"],"ASSOCIATION_ONLY")
        self.assertEqual(
            aov_result["driverAttribution"]["reason"],
            "NO_SUPPORTED_BUSINESS_IDENTITY",
        )
        self.assertTrue(aov_result["driverAttribution"]["associatedSignals"])
        self.assertEqual(
            payload["portfolio"]["driverAttributionFoundation"]["status"],
            "ATTRIBUTED",
        )
        smart=payload["portfolio"]["smartIssuesFoundation"]
        self.assertEqual(smart["status"],"ISSUE_READY")
        self.assertEqual(smart["issueCount"],1)
        issue=smart["issues"][0]
        self.assertTrue(issue["issueId"].startswith("SI_"))
        self.assertEqual(issue["affectedMetric"],"placedGmv")
        self.assertEqual(issue["sourceComparator"],"sameWeekday")
        self.assertEqual(issue["attributionStatus"],"ATTRIBUTED")
        self.assertEqual(issue["driverEvidence"]["topDriverMetric"],"placedAov")
        self.assertIn("CAUSALITY_NOT_ESTABLISHED",issue["unresolvedUncertainty"])
        self.assertIn("HUMAN_REVIEW_REQUIRED",issue["unresolvedUncertainty"])
        self.assertIn("PLATFORM_MUTATION_DISABLED",issue["unresolvedUncertainty"])
        self.assertFalse(issue["automaticAlertEligible"])
        self.assertFalse(issue["actionRecommendationEligible"])
        self.assertFalse(issue["operationalDiagnosisEnabled"])
        self.assertFalse(issue["causalClaimEligible"])
        action_policy=payload["portfolio"]["operatorActionPolicyFoundation"]
        self.assertEqual(action_policy["status"],"ACTION_OPTIONS_READY")
        self.assertEqual(action_policy["actionOptionCount"],2)
        options=action_policy["actionOptions"]
        self.assertEqual(options[0]["optionKey"],"VALIDATE_EVIDENCE_BEFORE_CHANGE")
        self.assertEqual(options[1]["optionKey"],"REVIEW_AOV_PRICE_PROMOTION_MIX")
        self.assertTrue(all(x["requiresHumanReview"] for x in options))
        self.assertTrue(all(x["executionMode"]=="HUMAN_REVIEW_ONLY" for x in options))
        self.assertTrue(all(not x["platformMutationAllowed"] for x in options))
        self.assertTrue(all(not x["automaticExecutionEligible"] for x in options))
        self.assertTrue(all(not x["prescriptiveRecommendation"] for x in options))
        self.assertEqual(payload["portfolio"]["anomalyDetectionFoundation"]["status"],"DEVIATION_CANDIDATE")
        self.assertFalse(payload["capabilities"]["anomalyDetection"])

    def test_shadow_mode_requires_three_distinct_safe_stable_refreshes(self):
        first=self._detector_ready_case(
            100,"shadow-refresh-1",refresh_id="run-1"
        )
        shadow1=first["shadowModeV1"]
        self.assertEqual(shadow1["status"],"SHADOW_OBSERVING")
        self.assertEqual(shadow1["consecutiveSafeRefreshes"],1)
        self.assertEqual(shadow1["consecutiveStableRefreshes"],1)

        second=self._detector_ready_case(
            100,"shadow-refresh-2",refresh_id="run-2",
            previous_shadow_state=shadow1,
        )
        shadow2=second["shadowModeV1"]
        self.assertEqual(shadow2["status"],"SHADOW_OBSERVING")
        self.assertEqual(shadow2["consecutiveSafeRefreshes"],2)
        self.assertEqual(shadow2["consecutiveStableRefreshes"],2)
        self.assertTrue(shadow2["transition"]["stateStable"])

        third=self._detector_ready_case(
            100,"shadow-refresh-3",refresh_id="run-3",
            previous_shadow_state=shadow2,
        )
        shadow3=third["shadowModeV1"]
        self.assertEqual(
            shadow3["status"],"READY_FOR_HUMAN_CUTOVER_REVIEW"
        )
        self.assertEqual(shadow3["consecutiveSafeRefreshes"],3)
        self.assertEqual(shadow3["consecutiveStableRefreshes"],3)
        self.assertTrue(all(x["status"]=="PASS" for x in shadow3["readinessGates"]))
        self.assertFalse(shadow3["activationControls"]["cutoverAuthorized"])
        self.assertFalse(shadow3["activationControls"]["productionActivationAllowed"])
        checklist={x["item"]:x["status"] for x in shadow3["cutoverChecklist"]}
        self.assertEqual(checklist["EXPLICIT_HUMAN_CUTOVER_APPROVAL"],"PENDING")
        self.assertEqual(checklist["EXPLICIT_PRODUCTION_DEPLOYMENT_APPROVAL"],"PENDING")

    def test_shadow_mode_idempotent_refresh_does_not_advance_counters(self):
        first=self._detector_ready_case(
            100,"shadow-idempotent-1",refresh_id="same-run"
        )["shadowModeV1"]
        repeated=self._detector_ready_case(
            100,"shadow-idempotent-2",refresh_id="same-run",
            previous_shadow_state=first,
        )["shadowModeV1"]
        self.assertTrue(repeated["idempotentRefresh"])
        self.assertEqual(repeated["refreshSequence"],1)
        self.assertEqual(repeated["consecutiveSafeRefreshes"],1)
        self.assertEqual(len(repeated["refreshRecords"]),1)

    def test_shadow_mode_records_issue_and_action_disappearance(self):
        candidate=self._detector_ready_case(
            50,"shadow-candidate",refresh_id="candidate-run"
        )["shadowModeV1"]
        self.assertTrue(candidate["currentState"]["issueIds"])
        self.assertTrue(candidate["currentState"]["actionOptionIds"])

        normal=self._detector_ready_case(
            100,"shadow-normal",refresh_id="normal-run",
            previous_shadow_state=candidate,
        )["shadowModeV1"]
        self.assertEqual(normal["currentState"]["issueIds"],[])
        self.assertEqual(normal["currentState"]["actionOptionIds"],[])
        self.assertEqual(
            normal["transition"]["issues"]["disappeared"],
            candidate["currentState"]["issueIds"],
        )
        self.assertEqual(
            normal["transition"]["actionOptions"]["disappeared"],
            candidate["currentState"]["actionOptionIds"],
        )
        self.assertTrue(normal["transition"]["lineageValid"])
        self.assertEqual(normal["consecutiveStableRefreshes"],1)

    def test_shadow_mode_blocks_lineage_regression(self):
        previous=self._detector_ready_case(
            100,"shadow-lineage-1",refresh_id="lineage-1"
        )["shadowModeV1"]
        previous["sourceSnapshot"]["trustedSemanticMonths"].append("2026-10")
        regressed=self._detector_ready_case(
            100,"shadow-lineage-2",refresh_id="lineage-2",
            previous_shadow_state=previous,
        )["shadowModeV1"]
        self.assertEqual(regressed["status"],"CUTOVER_BLOCKED")
        self.assertEqual(regressed["lineageStatus"],"REGRESSION_BLOCKED")
        self.assertIn("LINEAGE_CONTINUITY",regressed["failedGates"])
        self.assertFalse(regressed["activationControls"]["cutoverAuthorized"])

    def test_smart_issue_can_publish_association_only_without_fabricated_driver(self):
        payload=self._detector_ready_case(
            100,"smart-association",current_orders=4,current_clicks=20
        )
        sw=payload["portfolio"]["comparators"]["sameWeekday"]
        gmv=sw["anomalyDetectionFoundation"]["metricResults"]["placedGmv"]
        aov=sw["anomalyDetectionFoundation"]["metricResults"]["placedAov"]
        self.assertEqual(gmv["status"],"NORMAL")
        self.assertEqual(aov["status"],"DEVIATION_CANDIDATE")
        self.assertEqual(aov["driverAttribution"]["status"],"ASSOCIATION_ONLY")
        smart=payload["portfolio"]["smartIssuesFoundation"]
        self.assertEqual(smart["status"],"ISSUE_READY")
        self.assertEqual(smart["issueCount"],1)
        issue=smart["issues"][0]
        self.assertEqual(issue["affectedMetric"],"placedAov")
        self.assertEqual(issue["attributionStatus"],"ASSOCIATION_ONLY")
        self.assertEqual(issue["driverEvidence"]["topDriverMetric"],"")
        self.assertIn(
            "ASSOCIATION_ONLY_NOT_ATTRIBUTION",
            issue["unresolvedUncertainty"],
        )
        self.assertFalse(issue["causalClaimEligible"])
        self.assertFalse(issue["actionRecommendationEligible"])
        action_policy=payload["portfolio"]["operatorActionPolicyFoundation"]
        self.assertEqual(action_policy["status"],"ACTION_OPTIONS_READY")
        self.assertEqual(action_policy["actionOptionCount"],1)
        self.assertEqual(
            action_policy["actionOptions"][0]["optionKey"],
            "VALIDATE_EVIDENCE_BEFORE_CHANGE",
        )

    def test_anomaly_detection_foundation_publishes_no_score_when_eligibility_is_blocked(self):
        rows=[]
        for day in range(1,18):
            d=f"2026-09-{day:02d}"
            rows.extend([self._row("SHOP_A",d),self._row("SHOP_B",d)])
        out=self.root/"detector-blocked"
        build_historical_intelligence(
            semantic_daily_rows=rows,
            inventory=self._inventory(["2026-09"]),
            shops=self.shops,as_of_period="2026-09",
            contract_path=self.contract,output_dir=out,
        )
        payload=json.loads((out/"historical_intelligence.json").read_text(encoding="utf-8"))
        sw=payload["portfolio"]["comparators"]["sameWeekday"]
        result=sw["anomalyDetectionFoundation"]["metricResults"]["placedGmv"]
        self.assertEqual(result["status"],"NOT_EVALUATED")
        self.assertEqual(result["reason"],"ANOMALY_ELIGIBILITY_BLOCKED")
        self.assertFalse(result["scorePublished"])
        self.assertNotIn("modifiedZScore",result)
        severity=result["severityConfidence"]
        self.assertEqual(severity["status"],"NOT_ASSESSED")
        self.assertFalse(severity["severityPublished"])
        self.assertFalse(severity["confidencePublished"])
        self.assertNotIn("severityScore",severity)
        self.assertNotIn("confidenceScore",severity)
        attribution=result["driverAttribution"]
        self.assertEqual(attribution["status"],"NOT_DIAGNOSED")
        self.assertEqual(attribution["reason"],"NOT_DEVIATION_CANDIDATE")
        self.assertFalse(attribution["causalClaimEligible"])
        self.assertEqual(payload["portfolio"]["driverAttributionFoundation"]["status"],"NOT_DIAGNOSED")
        self.assertEqual(payload["portfolio"]["smartIssuesFoundation"]["status"],"NO_ISSUE")
        self.assertEqual(payload["portfolio"]["smartIssuesFoundation"]["issueCount"],0)
        action_policy=payload["portfolio"]["operatorActionPolicyFoundation"]
        self.assertEqual(action_policy["status"],"NO_ACTION_OPTIONS")
        self.assertEqual(action_policy["actionOptionCount"],0)
        self.assertEqual(action_policy["actionOptions"],[])
        self.assertEqual(payload["portfolio"]["anomalyDetectionFoundation"]["status"],"NOT_EVALUATED")
        self.assertFalse(payload["capabilities"]["anomalyDetection"])

    def test_context_does_not_enable_alerts_or_diagnosis(self):
        rows=[]
        for day in range(1,18):
            d=f"2026-09-{day:02d}"
            rows.extend([self._row("SHOP_A",d),self._row("SHOP_B",d)])
        context_rows=[{
            "data_date":"2026-09-17",
            "context_id":"sale",
            "platform":"market",
            "scope_type":"MARKET",
            "shop_id":"",
            "context_type":"MARKET_SEASON",
            "context_family":"BACK_TO_SCHOOL",
            "matching_eligible":False,
            "source_tier":"C1_INDUSTRY_ANALYTICS",
            "is_peak_date":False,
        }]
        out=self.root/"context-safe"
        build_historical_intelligence(
            semantic_daily_rows=rows,
            inventory=self._inventory(["2026-09"]),
            shops=self.shops,
            as_of_period="2026-09",
            contract_path=self.contract,
            output_dir=out,
            context_rows=context_rows,
            context_fingerprint="CTX_SAFE",
        )
        payload=json.loads((out/"historical_intelligence.json").read_text(encoding="utf-8"))
        self.assertFalse(payload["capabilities"]["historicalAlerts"])
        self.assertFalse(payload["capabilities"]["historicalDiagnosis"])
        self.assertFalse(payload["capabilities"]["contextMatchedBaseline"])
        self.assertFalse(payload["safety"]["historicalAlertsEnabled"])
        self.assertFalse(payload["safety"]["diagnosisEnabled"])


if __name__=="__main__":
    unittest.main()
