import json
import tempfile
import unittest
from pathlib import Path

from modules.semantic_payload import build_ui_payload


class SemanticPayloadTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.semantic=self.root/"semantic"/"2026-09"
        self.semantic.mkdir(parents=True)
        self.out=self.root/"payload"
        self.contract=self.root/"contract.json"
        self.contract.write_text(json.dumps({
            "version":"1.4",
            "layer_name":"multi_shop_ui_payload_v1",
            "status":"PREPRODUCTION",
            "source_layer":"multi_shop_semantic_v1",
            "timezone":"Asia/Ho_Chi_Minh",
            "scope_semantics":{
                "portfolio":{
                    "alignment":"ALL_ENABLED_SHOPS_COMMON_RELIABLE_INTERSECTION",
                    "daily_shop_requirement":"ALL_ENABLED_SHOPS_PRESENT_EACH_DAY",
                    "forbidden_total_fields":[
                        "visits","buyers","newBuyers","existingBuyers","potentialBuyers",
                        "uniqueImpressions","uniqueClicks",
                    ],
                    "latest_complete_day_visible_label":"Ngày gần nhất",
                    "comparison_window_policy":"REQUIRE_COMPLETE_CURRENT_AND_PREVIOUS_WINDOWS",
                },
                "shop":{
                    "alignment":"SHOP_COMMON_RELIABLE_WINDOW",
                    "daily_unique_fields":[
                        "visits","buyers","newBuyers","existingBuyers","potentialBuyers",
                    ],
                    "multi_day_unique_policy":"DAILY_ONLY_DO_NOT_SUM",
                    "headline_unique_policy":"OMIT",
                    "funnel":{
                        "primary_conversion_metric":"placedCvr",
                        "numerator":"placedOrders",
                        "denominator":"productClicks",
                        "visits_bridge_policy":"DAILY_ONLY_SUPPORTING_SIGNAL",
                    },
                    "traffic":{
                        "aggregation":"ADDITIVE_FIELDS_ONLY",
                        "forbidden_multi_day_unique_fields":[
                            "buyers","uniqueImpressions","uniqueClicks",
                        ],
                        "ratio_policy":"RECOMPUTE_FROM_ADDITIVE_COMPONENTS",
                    },
                    "product":{
                        "alignment":"SOURCE_MTD_SHOP_SCOPE_ONLY",
                        "product_identity":["shop_id","product_id"],
                        "cross_shop_identity_merge":False,
                        "day_7d_derivation":False,
                    },
                    "latest_complete_day_visible_label":"Ngày gần nhất",
                    "partial_window_visible_policy":"LABEL_OBSERVED_DAYS_NOT_REQUESTED_HORIZON",
                    "comparison_window_policy":"REQUIRE_COMPLETE_CURRENT_AND_PREVIOUS_WINDOWS",
                },
            },
            "capability_defaults":{
                "multiShopSelector":True,
                "portfolioScope":True,
                "pairwiseCompare":True,
                "shopProductView":True,
                "crossShopProductAggregation":False,
                "customerLifetime":False,
                "historicalIntelligence6m":False,
                "todayMatchedHour":False,
                "productionUiBinding":False,
            },
            "safety":{
                "write_production_data_mart":False,
                "modify_production_ui":False,
                "publish_legacy_payload":False,
            },
        }),encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def _write_jsonl(self,name,rows):
        with (self.semantic/name).open("w",encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row,ensure_ascii=False,sort_keys=True)+"\n")

    def _build_semantic(self):
        shops=[
            ("SHOP_A","a","Alpha","2026-09-05",100,2,10,100,10),
            ("SHOP_B","b","Beta","2026-09-04",200,4,20,50,10),
            ("SHOP_C","c","Gamma","2026-09-03",300,6,30,30,10),
        ]
        self._write_jsonl("dim_shop.jsonl",[
            {"shop_id":sid,"shop_key":key,"display_name":name,"platform":"shopee","enabled":True}
            for sid,key,name,_,_,_,_,_,_ in shops
        ])
        daily=[]
        traffic=[]
        products=[]
        ads_products=[]
        freshness={}
        for sid,key,name,end,gmv,orders,clicks,ads_sales,ads_spend in shops:
            end_day=int(end[-2:])
            freshness[sid]={
                "common_reliable_start":"2026-09-01",
                "common_reliable_end":end,
                "source_verified_through":{
                    "orders":end,"ads":end,"business_insights":end,
                },
            }
            for day in range(1,end_day+1):
                d=f"2026-09-{day:02d}"
                daily.append({
                    "shop_id":sid,"data_date":d,
                    "placed_gmv":gmv,"placed_orders":orders,"product_clicks":clicks,
                    "placed_aov":gmv/orders,"placed_cvr":orders/clicks,
                    "visits":clicks*2,"buyers":orders,
                    "new_buyers":1,"existing_buyers":max(0,orders-1),
                    "confirmed_gmv":gmv*.9,"confirmed_orders":orders,
                    "paid_gmv":gmv*.8,"paid_orders":orders,
                    "cancelled_orders":0,"cancelled_sales":0,
                    "returned_refunded_orders":0,"returned_refunded_sales":0,
                    "net_sales_after_cancel":gmv,
                    "ads_impressions":100,"ads_clicks":10,"ads_conversions":2,
                    "ads_attributed_sales":ads_sales,"ads_spend":ads_spend,
                    "fixed_fee":1,"service_fee":2,"transaction_fee":1,"order_fees":4,
                })
                traffic.extend([
                    {
                        "shop_id":sid,"data_date":d,"order_stage":"placed",
                        "channel_group":"Product Card","traffic_source":"Product Card",
                        "sales":gmv,"impressions":100,"clicks":10,
                        "attributed_orders":orders,"attributed_units":orders,
                    },
                    {
                        "shop_id":sid,"data_date":d,"order_stage":"placed",
                        "channel_group":"Product Card","traffic_source":"Search",
                        "sales":gmv*.5,"impressions":60,"clicks":6,
                        "attributed_orders":orders*.5,"attributed_units":orders*.5,
                    },
                ])
                ads_products.extend([
                    {
                        "shop_id":sid,"data_date":d,"product_id":f"P_{key}_1",
                        "product_name":f"Hero {name}","resolved_parent_sku":f"SKU-{key}-1",
                        "impressions":60,"clicks":6,"conversions":1,"units_sold":1,
                        "attributed_sales":ads_sales*.7,"ad_spend":ads_spend*.6,
                    },
                    {
                        "shop_id":sid,"data_date":d,"product_id":f"P_{key}_2",
                        "product_name":f"Tail {name}","resolved_parent_sku":f"SKU-{key}-2",
                        "impressions":40,"clicks":4,"conversions":1,"units_sold":1,
                        "attributed_sales":ads_sales*.3,"ad_spend":ads_spend*.4,
                    },
                ])
            products.append({
                "shop_id":sid,"data_month":"2026-09","product_id":"P_SHARED",
                "product_name":f"Product {name}","product_status":"active",
                "product_sku_observed":f"SKU-{key}","resolved_parent_sku":f"SKU-{key}",
                "catalog_join_status":"MATCHED_CURRENT_CATALOG",
                "catalog_status":"DIRECT_PARENT","current_listing_present":True,
                "placed_gmv":gmv*end_day,"placed_orders":orders*end_day,
                "confirmed_gmv":gmv*.9*end_day,"confirmed_orders":orders*end_day,
                "product_views":1000,"product_clicks":100,"ctr":.1,
                "product_visits":200,"bounce_rate":.2,
                "add_to_cart_visits":30,"atc_rate":.15,
                "ads_spend":ads_spend*end_day,
                "ads_attributed_sales":ads_sales*end_day,
                "roas":ads_sales/ads_spend,
            })

        self._write_jsonl("dm_shop_daily.jsonl",daily)
        self._write_jsonl("dm_traffic_source_daily.jsonl",traffic)
        self._write_jsonl("dm_product_monthly.jsonl",products)
        self._write_jsonl("dm_ads_product_daily.jsonl",ads_products)
        manifest={
            "layer":"multi_shop_semantic_v1",
            "period":"2026-09",
            "semantic_build_fingerprint":"SEMANTIC_FP",
            "freshness":freshness,
            "safety":{
                "legacy_data_mart_written":False,
                "production_data_mart_written":False,
                "ui_modified":False,
            },
        }
        (self.semantic/"manifest.json").write_text(json.dumps(manifest),encoding="utf-8")
        qa={
            "status":"PASS","semantic_mart_ready":True,
            "semantic_build_fingerprint":"SEMANTIC_FP",
            "selected_shop_count":3,
            "selected_shop_ids":["SHOP_A","SHOP_B","SHOP_C"],
        }
        (self.semantic/"semantic_qa_report.json").write_text(json.dumps(qa),encoding="utf-8")

    def _payload(self,out=None):
        self._build_semantic()
        target=out or self.out
        result=build_ui_payload(
            semantic_dir=self.semantic,
            output_dir=target,
            contract_path=self.contract,
        )
        payload=json.loads((target/"ui_payload.json").read_text(encoding="utf-8"))
        return result,payload

    def test_three_shop_selector_and_pairwise_compare_are_n_shop_safe(self):
        result,payload=self._payload()
        self.assertEqual(result["selectedShopCount"],3)
        self.assertEqual(len(payload["selector"]["shops"]),3)
        self.assertEqual(len(payload["compare"]["pairs"]),3)
        self.assertEqual(set(payload["shops"]),{"SHOP_A","SHOP_B","SHOP_C"})

    def test_portfolio_uses_intersection_window_not_longest_shop_cutoff(self):
        _,payload=self._payload()
        self.assertEqual(payload["portfolio"]["coverage"]["windowEnd"],"2026-09-03")
        self.assertEqual(payload["shops"]["SHOP_A"]["coverage"]["windowEnd"],"2026-09-05")
        self.assertEqual(payload["shops"]["SHOP_B"]["coverage"]["windowEnd"],"2026-09-04")
        self.assertEqual(payload["shops"]["SHOP_C"]["coverage"]["windowEnd"],"2026-09-03")
        self.assertEqual(len(payload["portfolio"]["daily"]),3)

    def test_portfolio_and_compare_ratios_are_recomputed(self):
        _,payload=self._payload()
        h=payload["portfolio"]["headline"]
        # aligned 3 days: daily portfolio GMV=600, orders=12, clicks=60.
        self.assertAlmostEqual(h["placedGmv"],1800)
        self.assertEqual(h["placedOrders"],36)
        self.assertAlmostEqual(h["placedAov"],50)
        self.assertAlmostEqual(h["placedCvr"],36/180)
        # ads sales daily=180, spend=30 -> ROAS 6.
        self.assertAlmostEqual(h["roas"],6)
        # 3 days × (order fees 12/day + ads spend 30/day) / net sales 1800.
        self.assertAlmostEqual(h["totalPlatformCostRatio"],(36+90)/1800)

        pair=next(x for x in payload["compare"]["pairs"]
                  if x["scope"]["leftShopId"]=="SHOP_A"
                  and x["scope"]["rightShopId"]=="SHOP_B")
        self.assertEqual(pair["coverage"]["windowEnd"],"2026-09-04")
        metric=pair["horizons"]["mtd"]["metrics"]["placedGmv"]
        self.assertEqual(metric["leftValue"],400)
        self.assertEqual(metric["rightValue"],800)
        self.assertEqual(metric["differenceRightVsLeft"],400)
        self.assertAlmostEqual(metric["differencePctRightVsLeft"],1.0)

    def test_same_product_id_in_multiple_shops_is_not_merged(self):
        _,payload=self._payload()
        for sid in ("SHOP_A","SHOP_B","SHOP_C"):
            self.assertEqual(len(payload["shops"][sid]["products"]),1)
            self.assertEqual(payload["shops"][sid]["products"][0]["productId"],"P_SHARED")
        self.assertFalse(payload["capabilities"]["crossShopProductAggregation"])
        self.assertNotIn("products",payload["portfolio"])

    def test_non_additive_cross_shop_uniques_are_not_exposed_as_portfolio_totals(self):
        _,payload=self._payload()
        h=payload["portfolio"]["headline"]
        self.assertNotIn("visits",h)
        self.assertNotIn("buyers",h)
        self.assertNotIn("visits",payload["portfolio"]["daily"][0])
        self.assertNotIn("buyers",payload["portfolio"]["daily"][0])
        policy=payload["portfolio"]["semanticPolicy"]
        self.assertEqual(policy["alignment"],"ALL_ENABLED_SHOPS_COMMON_RELIABLE_INTERSECTION")
        self.assertEqual(policy["latestCompleteDayVisibleLabel"],"Ngày gần nhất")
        self.assertEqual(
            policy["comparisonWindowPolicy"],
            "REQUIRE_COMPLETE_CURRENT_AND_PREVIOUS_WINDOWS",
        )
        self.assertTrue(all(
            row["shopCountIncluded"]==3 for row in payload["portfolio"]["daily"]
        ))

    def test_shop_scope_keeps_daily_uniques_but_never_promotes_them_to_period_totals(self):
        _,payload=self._payload()
        shop=payload["shops"]["SHOP_A"]
        self.assertNotIn("visits",shop["headline"])
        self.assertNotIn("buyers",shop["headline"])
        self.assertIn("visits",shop["daily"][0])
        self.assertIn("buyers",shop["daily"][0])
        self.assertIn("potentialBuyers",shop["daily"][0])
        self.assertEqual(shop["semanticPolicy"]["multiDayUniquePolicy"],"DAILY_ONLY_DO_NOT_SUM")
        self.assertEqual(shop["semanticPolicy"]["funnel"]["denominator"],"productClicks")
        self.assertEqual(shop["productCoverage"]["alignment"],"SOURCE_MTD_SHOP_SCOPE_ONLY")
        self.assertFalse(shop["productCoverage"]["crossShopAggregationAllowed"])
        self.assertTrue(all(
            all(k not in row for k in ("buyers","uniqueImpressions","uniqueClicks"))
            for row in shop["traffic"]
        ))

    def test_shop_daily_ratios_are_recomputed_including_platform_cost(self):
        _,payload=self._payload()
        row=payload["shops"]["SHOP_A"]["daily"][0]
        self.assertAlmostEqual(row["placedAov"],row["placedGmv"]/row["placedOrders"])
        self.assertAlmostEqual(row["placedCvr"],row["placedOrders"]/row["productClicks"])
        self.assertAlmostEqual(row["roas"],row["adsAttributedSales"]/row["adsSpend"])
        self.assertAlmostEqual(
            row["totalPlatformCostRatio"],
            (row["orderFees"]+row["adsSpend"])/row["netSalesAfterCancel"],
        )

    def test_compare_has_aligned_multi_horizon_analysis(self):
        _,payload=self._payload()
        pair=next(x for x in payload["compare"]["pairs"]
                  if x["scope"]["leftShopId"]=="SHOP_A"
                  and x["scope"]["rightShopId"]=="SHOP_B")
        self.assertEqual(pair["defaultHorizon"],"mtd")
        self.assertEqual(pair["horizonOrder"],["latestDay","last7","mtd"])
        self.assertEqual(set(pair["horizons"]),{"latestDay","last7","mtd"})
        self.assertEqual(
            pair["horizons"]["latestDay"]["coverage"],
            {"windowStart":"2026-09-04","windowEnd":"2026-09-04","alignedShopCount":2},
        )
        # Pair only has four common days, so last7 clamps to the aligned start.
        self.assertEqual(pair["horizons"]["last7"]["coverage"]["windowStart"],"2026-09-01")
        self.assertNotIn("metrics",pair)
        self.assertNotIn("leftHeadline",pair)
        self.assertNotIn("rightHeadline",pair)

    def test_compare_gap_decomposition_reconciles_gmv_gap(self):
        _,payload=self._payload()
        pair=payload["compare"]["pairs"][0]
        for horizon in pair["horizons"].values():
            d=horizon["driverDecomposition"]
            self.assertEqual(d["status"],"READY")
            self.assertAlmostEqual(
                d["gmvGapRightVsLeft"],d["reconciledEffectTotal"],places=6
            )

    def test_compare_includes_traffic_and_ads_product_concentration(self):
        _,payload=self._payload()
        pair=payload["compare"]["pairs"][0]
        mtd=pair["horizons"]["mtd"]
        self.assertEqual(mtd["traffic"]["left"][0]["channelGroup"],"Product Card")
        left_ads=mtd["adsProducts"]["left"]
        self.assertEqual(left_ads["productCount"],2)
        self.assertAlmostEqual(left_ads["top1AdsSalesShare"],.7)
        self.assertAlmostEqual(left_ads["top3AdsSalesShare"],1.0)
        self.assertEqual(len(left_ads["topProducts"]),2)

    def test_business_product_concentration_is_explicitly_mtd_only(self):
        _,payload=self._payload()
        pair=payload["compare"]["pairs"][0]
        self.assertEqual(
            pair["productMtd"]["alignment"],
            "SOURCE_MTD_NOT_HORIZON_ALIGNED",
        )
        self.assertEqual(
            pair["productMtd"]["left"]["alignment"],
            "SOURCE_MTD_NOT_HORIZON_ALIGNED",
        )
        self.assertEqual(pair["productMtd"]["left"]["productCount"],1)

    def test_historical_context_binding_preserves_lineage_and_fail_closed_flags(self):
        self._build_semantic()
        history_path=self.root/"historical_intelligence.json"
        def scope():
            return {
                "status":"INSUFFICIENT_HISTORY",
                "historyDepthReason":"HISTORY_LENGTH_NOT_DATA_GAP",
                "latestTrustedDate":"2026-09-03",
                "coverage":{
                    "start":"2026-07-20","end":"2026-09-03","dayCount":46,
                    "historySpanDays":46,"availableMonthCount":3,
                    "calendarCompleteMonthCount":1,
                    "coverageOrigin":"SHOP_LAUNCH",
                    "startPolicy":"FIRST_TRUSTED_SEMANTIC_DATE",
                    "lifecycleStartDate":"2026-07-20",
                    "preStartDatesAreMissing":False,
                    "coverageInterpretation":"TRUSTED_HISTORY_BEGINS_AT_SHOP_LAUNCH",
                },
                "comparators":{
                    "previousDay":{"status":"READY","alertEligible":False,"diagnosisEligible":False},
                    "previous7d":{"status":"READY","alertEligible":False,"diagnosisEligible":False},
                    "previousMonthMtd":{"status":"READY","alertEligible":False,"diagnosisEligible":False},
                    "sameWeekday":{"status":"READY","sampleCount":4,"alertEligible":False,"diagnosisEligible":False},
                    "sameDayOfMonth":{"status":"INSUFFICIENT_HISTORY","alertEligible":False,"diagnosisEligible":False},
                },
                "context":{"status":"CONTEXT_UNAVAILABLE"},
                "alertEligible":False,"diagnosisEligible":False,
            }
        history={
            "meta":{
                "layer":"multi_shop_historical_intelligence_v1",
                "asOfPeriod":"2026-09",
                "historicalBuildFingerprint":"HIST_FP",
            },
            "portfolio":scope(),
            "shops":{"SHOP_A":scope(),"SHOP_B":scope(),"SHOP_C":scope()},
            "capabilities":{
                "productionCutoverShadowMode":True,
                "productionCutover":False,
            },
            "shadowModeV1":{
                "status":"SHADOW_OBSERVING",
                "mode":"PREPRODUCTION_OBSERVE_ONLY",
                "refreshId":"run-1",
                "refreshSequence":1,
                "readinessGates":[
                    {"gate":"MINIMUM_SAFE_REFRESHES","status":"PENDING"}
                ],
                "activationControls":{
                    "requiresExplicitHumanApproval":True,
                    "productionActivationAllowed":False,
                    "automaticCutoverEnabled":False,
                    "cutoverAuthorized":False,
                },
                "rollbackControls":{
                    "required":True,
                    "legacyProductionPathRetained":True,
                    "automaticRollbackEnabled":False,
                },
                "productionWritesEnabled":False,
                "platformMutationAllowed":False,
            },
            "safety":{
                "productionDataMartWritten":False,
                "productionUiModified":False,
                "legacyPayloadPublished":False,
                "historicalAlertsEnabled":False,
                "diagnosisEnabled":False,
                "productionCutoverAuthorized":False,
                "productionActivationEnabled":False,
            },
        }
        history_path.write_text(json.dumps(history),encoding="utf-8")
        result=build_ui_payload(
            semantic_dir=self.semantic,
            output_dir=self.root/"payload-history",
            contract_path=self.contract,
            historical_path=history_path,
        )
        payload=json.loads((self.root/"payload-history"/"ui_payload.json").read_text(encoding="utf-8"))
        self.assertEqual(result["sourceHistoricalFingerprint"],"HIST_FP")
        self.assertEqual(payload["meta"]["sourceHistoricalFingerprint"],"HIST_FP")
        self.assertTrue(payload["capabilities"]["historicalComparatorContext"])
        self.assertFalse(payload["capabilities"]["historicalAlerts"])
        self.assertFalse(payload["capabilities"]["historicalDiagnosis"])
        self.assertTrue(payload["capabilities"]["productionCutoverShadowMode"])
        self.assertFalse(payload["capabilities"]["productionCutover"])
        self.assertEqual(payload["shadowModeV1"]["status"],"SHADOW_OBSERVING")
        self.assertFalse(
            payload["shadowModeV1"]["activationControls"]["cutoverAuthorized"]
        )
        self.assertEqual(
            payload["portfolio"]["historicalContext"]["coverage"]["coverageOrigin"],
            "SHOP_LAUNCH",
        )
        for sid in ("SHOP_A","SHOP_B","SHOP_C"):
            ctx=payload["shops"][sid]["historicalContext"]
            self.assertEqual(ctx["sourceHistoricalFingerprint"],"HIST_FP")
            self.assertFalse(ctx["alertEligible"])
            self.assertFalse(ctx["diagnosisEligible"])

    def test_business_context_lineage_is_carried_fail_closed(self):
        self._build_semantic()
        history_path=self.root/"historical_context_bound.json"
        def scope():
            comparator_context={
                "status":"CONTEXT_AVAILABLE",
                "current":{
                    "eventIds":["sale"],"matchingEligibleEventIds":["sale"],
                    "matchingSignature":["PLATFORM|shopee|DOUBLE_DAY_MEGA_SALE|1|1"],
                },
                "reference":{
                    "eventIds":["sale_prev"],"matchingEligibleEventIds":["sale_prev"],
                    "matchingSignature":["PLATFORM|shopee|DOUBLE_DAY_MEGA_SALE|1|1"],
                },
                "matchEvaluation":"CONTEXT_COMPATIBLE",
                "qualification":{
                    "status":"CONTEXT_COMPATIBLE",
                    "reason":"EXACT_MATCHING_PROFILE_EQUAL",
                    "alertEligible":False,
                    "diagnosisEligible":False,
                    "causalClaimEligible":False,
                },
                "contextMatchedBaselineEligible":False,
                "alertEligible":False,
                "diagnosisEligible":False,
                "causalClaimEligible":False,
            }
            return {
                "status":"INSUFFICIENT_HISTORY",
                "historyDepthReason":"HISTORY_LENGTH_NOT_DATA_GAP",
                "latestTrustedDate":"2026-09-03",
                "coverage":{
                    "start":"2026-07-20","end":"2026-09-03","dayCount":46,
                    "historySpanDays":46,"availableMonthCount":3,
                    "calendarCompleteMonthCount":1,
                    "coverageOrigin":"SHOP_LAUNCH",
                    "startPolicy":"FIRST_TRUSTED_SEMANTIC_DATE",
                    "lifecycleStartDate":"2026-07-20",
                    "preStartDatesAreMissing":False,
                    "coverageInterpretation":"TRUSTED_HISTORY_BEGINS_AT_SHOP_LAUNCH",
                },
                "comparators":{
                    "previousDay":{"status":"READY","businessContext":comparator_context,"alertEligible":False,"diagnosisEligible":False},
                    "previous7d":{"status":"READY","businessContext":comparator_context,"alertEligible":False,"diagnosisEligible":False},
                    "previousMonthMtd":{"status":"READY","businessContext":comparator_context,"alertEligible":False,"diagnosisEligible":False},
                    "sameWeekday":{
                        "status":"READY","sampleCount":4,
                        "contextMatchedBaseline":{
                            "status":"INSUFFICIENT_CONTEXT_MATCHED_HISTORY",
                            "requiredSampleCount":4,"sampleCount":0,"sampleDates":[],
                            "sourceQualification":"CONTEXT_COMPATIBLE_ONLY",
                            "allHistoryBaselinePreserved":True,"silentFallbackUsed":False,
                            "alertEligible":False,"diagnosisEligible":False,"causalClaimEligible":False,
                        },
                        "businessContext":{
                            "status":"CONTEXT_AVAILABLE","samples":{"eventIds":["sale"]},
                            "matchEvaluation":"CONTEXT_COMPATIBLE",
                            "qualification":{"status":"CONTEXT_COMPATIBLE","reason":"EXACT_MATCHING_PROFILE_EQUAL","alertEligible":False,"diagnosisEligible":False,"causalClaimEligible":False},
                            "contextMatchedBaselineEligible":False,
                            "contextMatchedBaselineStatus":"INSUFFICIENT_CONTEXT_MATCHED_HISTORY",
                            "alertEligible":False,"diagnosisEligible":False,
                        },"alertEligible":False,"diagnosisEligible":False},
                    "sameDayOfMonth":{
                        "status":"INSUFFICIENT_HISTORY",
                        "contextMatchedBaseline":{
                            "status":"INSUFFICIENT_CONTEXT_MATCHED_HISTORY",
                            "requiredSampleCount":3,"sampleCount":0,"sampleDates":[],
                            "sourceQualification":"CONTEXT_COMPATIBLE_ONLY",
                            "allHistoryBaselinePreserved":True,"silentFallbackUsed":False,
                            "alertEligible":False,"diagnosisEligible":False,"causalClaimEligible":False,
                        },
                        "businessContext":{
                            "status":"CONTEXT_AVAILABLE","samples":{"eventIds":[]},
                            "matchEvaluation":"CONTEXT_UNKNOWN",
                            "qualification":{"status":"CONTEXT_UNKNOWN","reason":"COMPARATOR_NOT_READY","alertEligible":False,"diagnosisEligible":False,"causalClaimEligible":False},
                            "contextMatchedBaselineEligible":False,
                            "contextMatchedBaselineStatus":"INSUFFICIENT_CONTEXT_MATCHED_HISTORY",
                            "alertEligible":False,"diagnosisEligible":False,
                        },"alertEligible":False,"diagnosisEligible":False},
                },
                "context":{
                    "status":"CONTEXT_AVAILABLE",
                    "sourceLayer":"multi_shop_business_context_v1",
                    "sourceFingerprint":"CTX_FP",
                    "availableDimensions":["context_id","context_family"],
                    "coverage":{"eventIds":["sale"]},
                    "contextMatchedBaselineEnabled":False,
                    "alertEligible":False,
                },
                "alertEligible":False,"diagnosisEligible":False,
            }
        history={
            "meta":{
                "layer":"multi_shop_historical_intelligence_v1",
                "asOfPeriod":"2026-09",
                "historicalBuildFingerprint":"HIST_CTX_FP",
            },
            "historySources":{"businessContextFingerprint":"CTX_FP"},
            "portfolio":scope(),
            "shops":{"SHOP_A":scope(),"SHOP_B":scope(),"SHOP_C":scope()},
            "safety":{
                "productionDataMartWritten":False,
                "productionUiModified":False,
                "legacyPayloadPublished":False,
                "historicalAlertsEnabled":False,
                "diagnosisEnabled":False,
            },
        }
        history_path.write_text(json.dumps(history),encoding="utf-8")
        result=build_ui_payload(
            semantic_dir=self.semantic,
            output_dir=self.root/"payload-context",
            contract_path=self.contract,
            historical_path=history_path,
        )
        payload=json.loads((self.root/"payload-context"/"ui_payload.json").read_text(encoding="utf-8"))
        self.assertEqual(result["sourceHistoricalFingerprint"],"HIST_CTX_FP")
        self.assertTrue(payload["capabilities"]["businessContextCalendar"])
        self.assertFalse(payload["capabilities"]["contextMatchedBaseline"])
        contexts=[payload["portfolio"]["historicalContext"]]
        contexts.extend(payload["shops"][sid]["historicalContext"] for sid in ("SHOP_A","SHOP_B","SHOP_C"))
        for ctx in contexts:
            bc=ctx["businessContext"]
            self.assertEqual(bc["status"],"CONTEXT_AVAILABLE")
            self.assertEqual(bc["sourceFingerprint"],"CTX_FP")
            self.assertFalse(bc["contextMatchedBaselineEnabled"])
            self.assertFalse(bc["alertEligible"])
            self.assertFalse(bc["diagnosisEligible"])
            self.assertEqual(
                ctx["comparators"]["previousDay"]["businessContext"]["matchEvaluation"],
                "CONTEXT_COMPATIBLE",
            )

    def test_payload_fingerprint_is_deterministic(self):
        r1,_=self._payload(self.root/"out1")
        # Rebuild the same semantic facts into a separate output directory.
        r2=build_ui_payload(
            semantic_dir=self.semantic,
            output_dir=self.root/"out2",
            contract_path=self.contract,
        )
        self.assertEqual(r1["payloadBuildFingerprint"],r2["payloadBuildFingerprint"])


if __name__=="__main__":
    unittest.main()
