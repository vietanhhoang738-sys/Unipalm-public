import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from modules.ui_v2_native import (
    _bundle_from_payload,
    _present_product,
    _presentation_checks,
    build_native_v2_multi_shop,
)
from modules.ui_v2_compat import _smart_issues_for_period


ROOT=Path(__file__).resolve().parents[2]
V2_TEMPLATE=ROOT/"automation"/"command_center_v2_template.html"


def sha_json(value):
    raw=json.dumps(
        value,ensure_ascii=False,sort_keys=True,separators=(",",":"),default=str
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


class UiV2NativeTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.payload_dir=self.root/"payload"
        self.payload_dir.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def _daily(self,gmv,orders,clicks,days=4):
        rows=[]
        for day in range(1,days+1):
            rows.append({
                "date":f"2026-09-{day:02d}",
                "placedGmv":gmv,
                "placedOrders":orders,
                "productClicks":clicks,
                "placedAov":gmv/orders,
                "placedCvr":orders/clicks,
                "visits":clicks*2,
                "buyers":orders,
                "newBuyers":1,
                "existingBuyers":max(0,orders-1),
                "adsSpend":10,
                "adsAttributedSales":50,
                "roas":5,
                "cancelledSales":0,
                "netSalesAfterCancel":gmv,
                "orderFees":4,
            })
        return rows

    def _decorate_pair(self,pair):
        coverage=dict(pair["coverage"])
        latest=coverage["windowEnd"]
        base={
            "metrics":dict(pair.pop("metrics")),
            "leftHeadline":dict(pair.pop("leftHeadline")),
            "rightHeadline":dict(pair.pop("rightHeadline")),
            "driverDecomposition":{"status":"UNAVAILABLE","drivers":[]},
            "traffic":{"left":[],"right":[]},
            "adsProducts":{
                "left":{"topProducts":[]},
                "right":{"topProducts":[]},
            },
        }
        pair["defaultHorizon"]="mtd"
        pair["horizonOrder"]=["latestDay","last7","mtd"]
        pair["horizons"]={
            "latestDay":{
                **base,
                "key":"latestDay",
                "label":"Ngày gần nhất",
                "coverage":{
                    "windowStart":latest,
                    "windowEnd":latest,
                    "alignedShopCount":2,
                },
            },
            "last7":{
                **base,
                "key":"last7",
                "label":"7 ngày",
                "coverage":coverage,
            },
            "mtd":{
                **base,
                "key":"mtd",
                "label":"Tháng này",
                "coverage":coverage,
            },
        }
        pair["productMtd"]={
            "alignment":"SOURCE_MTD_NOT_HORIZON_ALIGNED",
            "left":{"topProducts":[]},
            "right":{"topProducts":[]},
        }
        return pair

    def _write_payload(self):
        shops=[
            {"shopId":"SHOP_A","shopKey":"a","displayName":"Alpha","platform":"shopee",
             "freshness":{"commonReliableStart":"2026-09-01","commonReliableEnd":"2026-09-04",
                          "sourceVerifiedThrough":{"orders":"2026-09-04","ads":"2026-09-04","business_insights":"2026-09-04"}}},
            {"shopId":"SHOP_B","shopKey":"b","displayName":"Beta","platform":"shopee",
             "freshness":{"commonReliableStart":"2026-09-01","commonReliableEnd":"2026-09-04",
                          "sourceVerifiedThrough":{"orders":"2026-09-04","ads":"2026-09-04","business_insights":"2026-09-04"}}},
            {"shopId":"SHOP_C","shopKey":"c","displayName":"Gamma","platform":"shopee",
             "freshness":{"commonReliableStart":"2026-09-01","commonReliableEnd":"2026-09-04",
                          "sourceVerifiedThrough":{"orders":"2026-09-04","ads":"2026-09-04","business_insights":"2026-09-04"}}},
        ]
        values={
            "SHOP_A":(100,2,10),
            "SHOP_B":(200,4,20),
            "SHOP_C":(300,6,30),
        }
        shop_scopes={}
        for sid,(gmv,orders,clicks) in values.items():
            shop_scopes[sid]={
                "scope":{"type":"shop","shopId":sid},
                "coverage":{"windowStart":"2026-09-01","windowEnd":"2026-09-04","alignedShopCount":1},
                "headline":{
                    "placedGmv":gmv*4,"placedOrders":orders*4,"productClicks":clicks*4,
                    "placedAov":gmv/orders,"placedCvr":orders/clicks,
                    "adsSpend":40,"adsAttributedSales":200,"roas":5,
                },
                "daily":self._daily(gmv,orders,clicks),
                "traffic":[],
                "products":[],
                "productCoverage":{
                    "dataMonth":"2026-09",
                    "alignment":"SOURCE_MTD_SHOP_SCOPE_ONLY",
                    "crossShopAggregationAllowed":False,
                },
                "semanticPolicy":{
                    "alignment":"SHOP_COMMON_RELIABLE_WINDOW",
                    "dailyUniqueFields":["visits","buyers","newBuyers","existingBuyers","potentialBuyers"],
                    "multiDayUniquePolicy":"DAILY_ONLY_DO_NOT_SUM",
                    "headlineUniquePolicy":"OMIT",
                    "ratioPolicy":"RECOMPUTE_FROM_ADDITIVE_COMPONENTS",
                    "funnel":{"denominator":"productClicks"},
                    "traffic":{"aggregation":"ADDITIVE_FIELDS_ONLY"},
                    "product":{"alignment":"SOURCE_MTD_SHOP_SCOPE_ONLY","day_7d_derivation":False},
                    "latestCompleteDayVisibleLabel":"Ngày gần nhất",
                    "partialWindowVisiblePolicy":"LABEL_OBSERVED_DAYS_NOT_REQUESTED_HORIZON",
                    "comparisonWindowPolicy":"REQUIRE_COMPLETE_CURRENT_AND_PREVIOUS_WINDOWS",
                },
            }

        portfolio_daily=[]
        for day in range(1,5):
            portfolio_daily.append({
                "date":f"2026-09-{day:02d}",
                "shopCountIncluded":3,
                "placedGmv":600,
                "placedOrders":12,
                "productClicks":60,
                "placedAov":50,
                "placedCvr":.2,
                "adsSpend":30,
                "adsAttributedSales":150,
                "roas":5,
                "cancelledSales":0,
                "netSalesAfterCancel":600,
                "orderFees":12,
                "totalPlatformCostRatio":.07,
            })

        pairs=[]
        ids=["SHOP_A","SHOP_B","SHOP_C"]
        for i,left in enumerate(ids):
            for right in ids[i+1:]:
                lg,lo,lc=values[left]
                rg,ro,rc=values[right]
                l4=lg*4;r4=rg*4
                pairs.append({
                    "compareId":f"{left}__{right}",
                    "scope":{"type":"compare","leftShopId":left,"rightShopId":right},
                    "coverage":{"windowStart":"2026-09-01","windowEnd":"2026-09-04","alignedShopCount":2},
                    "leftHeadline":{"placedGmv":l4,"placedOrders":lo*4,"productClicks":lc*4,
                                    "placedAov":lg/lo,"placedCvr":lo/lc,"adsSpend":40,
                                    "adsAttributedSales":200,"roas":5},
                    "rightHeadline":{"placedGmv":r4,"placedOrders":ro*4,"productClicks":rc*4,
                                     "placedAov":rg/ro,"placedCvr":ro/rc,"adsSpend":40,
                                     "adsAttributedSales":200,"roas":5},
                    "metrics":{
                        "placedGmv":{"leftValue":l4,"rightValue":r4,
                                     "differenceRightVsLeft":r4-l4,
                                     "differencePctRightVsLeft":r4/l4-1},
                        "placedOrders":{"leftValue":lo*4,"rightValue":ro*4,
                                        "differenceRightVsLeft":(ro-lo)*4,
                                        "differencePctRightVsLeft":ro/lo-1},
                        "placedAov":{"leftValue":lg/lo,"rightValue":rg/ro,
                                     "differenceRightVsLeft":rg/ro-lg/lo,
                                     "differencePctRightVsLeft":(rg/ro)/(lg/lo)-1},
                        "placedCvr":{"leftValue":lo/lc,"rightValue":ro/rc,
                                     "differenceRightVsLeft":ro/rc-lo/lc,
                                     "differencePctRightVsLeft":(ro/rc)/(lo/lc)-1},
                        "roas":{"leftValue":5,"rightValue":5,
                                "differenceRightVsLeft":0,
                                "differencePctRightVsLeft":0},
                    },
                })

        for pair in pairs:
            self._decorate_pair(pair)

        payload={
            "meta":{
                "payloadContractVersion":"1.0",
                "sourceLayer":"multi_shop_semantic_v1",
                "sourceSemanticFingerprint":"SEMANTIC_FP",
                "period":"2026-09",
                "timezone":"Asia/Ho_Chi_Minh",
                "canonicalCommercialStage":"placed",
            },
            "selector":{
                "defaultScope":{"type":"portfolio"},
                "scopeModes":["portfolio","shop","compare"],
                "orderPolicy":"SHOP_REGISTRY_ORDER",
                "shops":shops,
            },
            "portfolio":{
                "scope":{"type":"portfolio","shopIds":ids},
                "coverage":{"windowStart":"2026-09-01","windowEnd":"2026-09-04",
                            "alignedShopCount":3,
                            "policy":"INTERSECTION_OF_SHOP_COMMON_RELIABLE_WINDOWS"},
                "headline":{"placedGmv":2400,"placedOrders":48,"productClicks":240,
                            "placedAov":50,"placedCvr":.2,"adsSpend":120,
                            "adsAttributedSales":600,"roas":5},
                "daily":portfolio_daily,
                "traffic":[],
                "shopContributions":[],
            },
            "shops":shop_scopes,
            "compare":{"policy":"PAIRWISE_ALIGNED_WINDOW_NO_RANKING","pairs":pairs},
            "capabilities":{
                "multiShopSelector":True,"portfolioScope":True,"pairwiseCompare":True,
                "shopProductView":True,"crossShopProductAggregation":False,
                "customerLifetime":False,"historicalIntelligence6m":False,
                "todayMatchedHour":False,"productionUiBinding":False,
            },
            "safety":{
                "productionDataMartWritten":False,
                "productionUiModified":False,
                "legacyPayloadPublished":False,
            },
        }
        psha=sha_json(payload)
        manifest={
            "layer":"multi_shop_ui_payload_v1",
            "contractVersion":"1.0",
            "period":"2026-09",
            "sourceSemanticFingerprint":"SEMANTIC_FP",
            "payloadBuildFingerprint":"PAYLOAD_FP",
            "payloadSha256":psha,
            "selectedShopIds":ids,
            "selectedShopCount":3,
            "files":[{"file":"ui_payload.json","sha256":psha}],
            "safety":payload["safety"],
        }
        qa={
            "status":"PASS","payloadReady":True,"period":"2026-09",
            "payloadBuildFingerprint":"PAYLOAD_FP",
            "sourceSemanticFingerprint":"SEMANTIC_FP",
            "selectedShopCount":3,"selectedShopIds":ids,
            "failedCheckCount":0,"checks":[],
            "safety":payload["safety"],
        }
        (self.payload_dir/"ui_payload.json").write_text(json.dumps(payload),encoding="utf-8")
        (self.payload_dir/"payload_manifest.json").write_text(json.dumps(manifest),encoding="utf-8")
        (self.payload_dir/"payload_qa_report.json").write_text(json.dumps(qa),encoding="utf-8")
        return payload

    def _refresh_payload_integrity(self, payload):
        psha=sha_json(payload)
        manifest=json.loads((self.payload_dir/"payload_manifest.json").read_text(encoding="utf-8"))
        qa=json.loads((self.payload_dir/"payload_qa_report.json").read_text(encoding="utf-8"))
        manifest["payloadSha256"]=psha
        (self.payload_dir/"ui_payload.json").write_text(json.dumps(payload),encoding="utf-8")
        (self.payload_dir/"payload_manifest.json").write_text(json.dumps(manifest),encoding="utf-8")
        (self.payload_dir/"payload_qa_report.json").write_text(json.dumps(qa),encoding="utf-8")

    def _extend_to_four_shops(self, payload):
        shop={
            "shopId":"SHOP_D","shopKey":"d","displayName":"Delta","platform":"shopee",
            "freshness":{"commonReliableStart":"2026-09-01","commonReliableEnd":"2026-09-04",
                         "sourceVerifiedThrough":{"orders":"2026-09-04","ads":"2026-09-04","business_insights":"2026-09-04"}},
        }
        payload["selector"]["shops"].append(shop)
        payload["portfolio"]["scope"]["shopIds"].append("SHOP_D")
        payload["portfolio"]["coverage"]["alignedShopCount"]=4
        for row in payload["portfolio"]["daily"]:
            row["shopCountIncluded"]=4
            row["placedGmv"]+=400
            row["placedOrders"]+=8
            row["productClicks"]+=40
            row["adsSpend"]+=10
            row["adsAttributedSales"]+=50
            row["placedAov"]=row["placedGmv"]/row["placedOrders"]
            row["placedCvr"]=row["placedOrders"]/row["productClicks"]
            row["roas"]=row["adsAttributedSales"]/row["adsSpend"]
        payload["shops"]["SHOP_D"]={
            "scope":{"type":"shop","shopId":"SHOP_D"},
            "coverage":{"windowStart":"2026-09-01","windowEnd":"2026-09-04","alignedShopCount":1},
            "headline":{"placedGmv":1600,"placedOrders":32,"productClicks":160,
                        "placedAov":50,"placedCvr":.2,"adsSpend":40,
                        "adsAttributedSales":200,"roas":5},
            "daily":self._daily(400,8,40),
            "traffic":[],"products":[],
            "productCoverage":{
                "dataMonth":"2026-09",
                "alignment":"SOURCE_MTD_SHOP_SCOPE_ONLY",
                "crossShopAggregationAllowed":False,
            },
            "semanticPolicy":{
                "alignment":"SHOP_COMMON_RELIABLE_WINDOW",
                "dailyUniqueFields":["visits","buyers","newBuyers","existingBuyers","potentialBuyers"],
                "multiDayUniquePolicy":"DAILY_ONLY_DO_NOT_SUM",
                "headlineUniquePolicy":"OMIT",
                "ratioPolicy":"RECOMPUTE_FROM_ADDITIVE_COMPONENTS",
                "funnel":{"denominator":"productClicks"},
                "traffic":{"aggregation":"ADDITIVE_FIELDS_ONLY"},
                "product":{"alignment":"SOURCE_MTD_SHOP_SCOPE_ONLY","day_7d_derivation":False},
                "latestCompleteDayVisibleLabel":"Ngày gần nhất",
                "partialWindowVisiblePolicy":"LABEL_OBSERVED_DAYS_NOT_REQUESTED_HORIZON",
                "comparisonWindowPolicy":"REQUIRE_COMPLETE_CURRENT_AND_PREVIOUS_WINDOWS",
            },
        }
        for left in ("SHOP_A","SHOP_B","SHOP_C"):
            lhs=payload["shops"][left]["headline"]
            rhs=payload["shops"]["SHOP_D"]["headline"]
            metrics={}
            for key in ("placedGmv","placedOrders","placedAov","placedCvr","roas"):
                lv=lhs[key]; rv=rhs[key]
                metrics[key]={
                    "leftValue":lv,"rightValue":rv,
                    "differenceRightVsLeft":rv-lv,
                    "differencePctRightVsLeft":rv/lv-1 if lv else None,
                }
            pair={
                "compareId":f"{left}__SHOP_D",
                "scope":{"type":"compare","leftShopId":left,"rightShopId":"SHOP_D"},
                "coverage":{"windowStart":"2026-09-01","windowEnd":"2026-09-04","alignedShopCount":2},
                "leftHeadline":lhs,"rightHeadline":rhs,"metrics":metrics,
            }
            payload["compare"]["pairs"].append(self._decorate_pair(pair))
        self._refresh_payload_integrity(payload)

    def test_shadow_mode_is_carried_into_native_bundle_without_activation(self):
        payload=self._write_payload()
        payload["shadowModeV1"]={
            "status":"SHADOW_OBSERVING",
            "mode":"PREPRODUCTION_OBSERVE_ONLY",
            "activationControls":{
                "requiresExplicitHumanApproval":True,
                "productionActivationAllowed":False,
                "automaticCutoverEnabled":False,
                "cutoverAuthorized":False,
            },
        }
        bundle=_bundle_from_payload(payload)
        self.assertEqual(bundle["shadowModeV1"]["status"],"SHADOW_OBSERVING")
        self.assertFalse(
            bundle["shadowModeV1"]["activationControls"]["cutoverAuthorized"]
        )

    def test_four_shop_native_v2_is_n_shop_safe(self):
        payload=self._write_payload()
        self._extend_to_four_shops(payload)
        result=build_native_v2_multi_shop(
            payload_dir=self.payload_dir,
            v2_template_path=V2_TEMPLATE,
            output_dir=self.root/"native-four",
        )
        self.assertEqual(result["selectedShopCount"],4)
        self.assertEqual(result["comparePairCount"],6)

    def test_tampered_payload_is_blocked_before_native_render(self):
        payload=self._write_payload()
        payload["portfolio"]["daily"][0]["placedGmv"]=999999
        (self.payload_dir/"ui_payload.json").write_text(
            json.dumps(payload),encoding="utf-8"
        )
        with self.assertRaisesRegex(ValueError,"canonical UI payload hash mismatch"):
            build_native_v2_multi_shop(
                payload_dir=self.payload_dir,
                v2_template_path=V2_TEMPLATE,
                output_dir=self.root/"native-tampered",
            )

    def test_native_v2_derivative_preserves_foundation_and_adds_scope_controls(self):
        payload=self._write_payload()
        source_before=V2_TEMPLATE.read_bytes()
        result=build_native_v2_multi_shop(
            payload_dir=self.payload_dir,
            v2_template_path=V2_TEMPLATE,
            output_dir=self.root/"native",
        )
        self.assertEqual(result["status"],"PASS")
        self.assertEqual(result["nativePatchVersion"],"native-production-shadow-mode-v28")
        self.assertTrue(result["nativeV2Ready"])
        self.assertEqual(result["selectedShopCount"],3)
        self.assertEqual(result["comparePairCount"],3)
        self.assertEqual(V2_TEMPLATE.read_bytes(),source_before)
        self.assertFalse(result["safety"]["productionV2TemplateModified"])
        self.assertFalse(result["safety"]["productionIndexModified"])
        self.assertFalse(result["safety"]["productionDeploymentPerformed"])

        html=(self.root/"native"/"command_center_v2_multi_shop_native_template.html").read_text(encoding="utf-8")
        self.assertIn('data-native-destination="command-center"',html)
        self.assertIn('data-native-destination="compare"',html)
        self.assertIn('data-native-scope="portfolio"',html)
        self.assertIn('data-native-scope="shop"',html)
        self.assertNotIn('data-native-scope="compare"',html)
        self.assertIn('compareNav.textContent="So sánh Shop"',html)
        self.assertIn('id="sidebarPin"',html)
        self.assertIn("transform:scale(1.25)",html)
        self.assertIn('[data-theme="dark"]',html)
        self.assertIn("PREPRODUCTION",html)
        self.assertIn("Không xếp hạng tổng thể",html)
        self.assertIn('period-grid compare-period-grid',html)
        self.assertIn('period-card compare-period-card',html)
        self.assertIn('pulse compare-pulse',html)
        self.assertIn('Diễn biến so sánh',html)
        self.assertIn('class="kpi-grid"',html)
        self.assertIn('content-grid compare-overview-grid',html)
        self.assertIn('card compare-table-card',html)
        self.assertIn('class="driver-list"',html)
        self.assertIn('class="driver-row"',html)
        self.assertIn('aria-label="Phạm vi Command Center"',html)
        self.assertIn('label for="nativeShopSelect"',html)
        self.assertIn('aria-label="Shop A"',html)
        self.assertIn('aria-label="Shop B"',html)
        self.assertIn('aria-pressed="false"',html)
        self.assertIn("Tổng hợp tất cả shop · cùng cửa sổ dữ liệu đã đối soát",html)
        self.assertIn(">Toàn hệ thống</button>",html)
        self.assertIn("nativeLeftBadge",html)
        self.assertIn("nativeRightBadge",html)
        self.assertIn(".native-shop-badge.preferred",html)
        self.assertIn(".native-shop-badge.mall",html)
        self.assertIn(".native-sidebar-rail{position:fixed",html)
        self.assertIn("top:16px",html)
        self.assertIn("height:calc(100vh - 32px)",html)
        self.assertIn(".native-sidebar-rail.unpinned",html)
        self.assertIn(".native-sidebar-rail.unpinned.peek",html)
        self.assertIn("native-sidebar-hover-active",html)
        self.assertIn("document.body.insertBefore(sidebarRail,document.body.firstChild)",html)
        self.assertIn("sidebarRail.appendChild(sidebar)",html)
        self.assertIn("syncSidebarRailMode",html)
        self.assertNotIn("window.scrollY",html)
        self.assertIn("native-table-shop-head",html)
        self.assertIn("productPanel(S.left,leftName",html)
        self.assertIn("productPanel(S.right,rightName",html)
        self.assertNotIn("compare-card-legend",html)
        self.assertIn('data-compare-horizon',html)
        self.assertIn('let horizon=p.get("horizon")||"mtd"',html)
        self.assertIn('window.UNIPALM_NATIVE_SCOPE={scope,shop,left,right,horizon}',html)
        self.assertIn("Doanh thu & chất lượng đơn hàng",html)
        self.assertIn("Funnel doanh thu",html)
        self.assertIn("Cơ cấu chi phí",html)
        self.assertIn("Hiệu quả quảng cáo",html)
        self.assertIn("Nguồn truy cập & chuyển đổi",html)
        self.assertIn("Hiệu quả quảng cáo theo sản phẩm",html)
        self.assertIn("Cơ cấu doanh số sản phẩm · Tháng này",html)
        self.assertIn("Phân tích hai shop · cùng kỳ dữ liệu",html)
        self.assertIn("<th>Chỉ số</th>",html)
        self.assertIn("Chi phí nền tảng",html)
        self.assertIn("Tỷ lệ doanh thu hủy",html)
        self.assertIn("Lượt nhấp sản phẩm",html)
        self.assertIn("Diễn biến so sánh",html)
        self.assertIn("Cơ sở phân tích",html)
        self.assertNotIn("Cảnh báo lịch sử chưa khả dụng cho phạm vi này.",html)
        self.assertIn('issueCard.hidden=true',html)
        self.assertIn('issueGrid.style.gridTemplateColumns="1fr"',html)
        self.assertIn('"So sánh cùng kỳ"',html)
        self.assertIn("Yếu tố tạo chênh lệch lớn nhất là <strong>",html)
        self.assertIn("đóng góp khoảng",html)
        self.assertIn("thấp hơn",html)
        self.assertIn('function moneyFull(v)',html)
        self.assertIn('value:moneyFull(cur.gmv)',html)
        self.assertIn('+"tr đ"',html)
        self.assertIn('fmt.moneyFull(lm)',html)
        self.assertIn('fmt.moneyFull(rm)',html)
        self.assertIn('tableRow("GMV đặt hàng","placedGmv","money")',html)
        self.assertIn('return "AOV";',html)
        self.assertNotIn('return sign+"₫"',html)
        self.assertNotIn('" triệu đồng"',html)
        self.assertNotIn('"Giá trị đơn hàng trung bình"',html)
        self.assertIn("Cơ sở phân tích",html)
        self.assertIn("Chi tiêu Ads",html)
        self.assertIn("Dữ liệu đạt chuẩn",html)
        self.assertIn('["CVR","placedCvr","high"]',html)
        self.assertIn('["ROAS","roas","high"]',html)
        self.assertIn('class="native-product-name" title="',html)
        check_names={x["name"] for x in result["checks"]}
        self.assertIn("compare_v2_visual_primitives",check_names)
        self.assertIn("compare_no_parallel_visual_shell",check_names)
        self.assertIn("compare_business_pulse",check_names)
        self.assertIn("compare_bundle_has_no_duplicate_v2_payloads",check_names)
        self.assertIn("compare_uses_contract_horizons_only",check_names)
        self.assertIn("command_center_scope_renderer_passthrough",check_names)
        self.assertIn("compare_is_separate_destination",check_names)
        self.assertIn("native_destination_architecture",check_names)
        self.assertIn("ui_v2_shared_design_language",check_names)
        self.assertIn("legacy_compare_visual_css_removed",check_names)
        self.assertIn("portfolio_is_all_shops_view",check_names)
        self.assertIn("compare_shop_identity_badges",check_names)
        self.assertIn("compare_shop_identity_propagated",check_names)
        self.assertIn("compare_no_repeated_badge_legends",check_names)
        self.assertIn("sidebar_viewport_rail",check_names)
        self.assertIn("sidebar_unpin_position_continuity",check_names)
        # The production V2 source remains read-only and may contain legacy strings.
        # Language lint applies to the native extension's visible runtime copy.

        bundle=_bundle_from_payload(payload)
        cc=bundle["portfolio"]["v2Payload"]["commandCenter"]
        self.assertNotIn("featureHealth",cc)
        self.assertNotIn("productSignals",cc)
        self.assertNotIn("smartIssues",cc)
        self.assertTrue(all(
            p["smartIssues"]["status"]=="NO_ISSUE"
            for p in cc["periods"].values()
        ))
        self.assertTrue(all(
            "leftV2Payload" not in pair and "rightV2Payload" not in pair
            for pair in bundle["comparePairs"]
        ))
        portfolio_health=bundle["portfolio"]["v2Payload"]["health"]["sources"]
        self.assertTrue(portfolio_health)
        self.assertTrue(all(x["months"]==0 for x in portfolio_health))
        self.assertEqual(portfolio_health[0]["name"],"Toàn hệ thống")
        self.assertEqual(portfolio_health[0]["note"],"Cửa sổ dữ liệu đã đối soát")
        portfolio_cc=bundle["portfolio"]["v2Payload"]["commandCenter"]
        self.assertTrue(portfolio_cc["labels"]["yesterday"].startswith("Ngày gần nhất"))
        for period in portfolio_cc["periods"].values():
            self.assertFalse(period["current"]["visitsAvailable"])
            if period["comparisonAvailable"]:
                self.assertTrue(period["comparisonCoverage"]["currentComplete"])
                self.assertTrue(period["comparisonCoverage"]["previousComplete"])
            if period["drivers"]["status"]=="READY":
                self.assertNotIn("clickBridge",period["drivers"])

        shop_cc=bundle["shopViews"]["SHOP_A"]["v2Payload"]["commandCenter"]
        self.assertTrue(shop_cc["periods"]["yesterday"]["current"]["visitsAvailable"])
        self.assertFalse(shop_cc["periods"]["last7"]["current"]["visitsAvailable"])
        self.assertFalse(shop_cc["periods"]["mtd"]["current"]["visitsAvailable"])
        self.assertTrue(shop_cc["labels"]["last7"].startswith("4 ngày khả dụng"))
        self.assertTrue(shop_cc["labels"]["mtd"].startswith("Tháng này"))
        self.assertEqual(
            bundle["shopViews"]["SHOP_A"]["v2Payload"]["meta"]["uniqueMetricPolicy"],
            "DAILY_ONLY_DO_NOT_SUM",
        )

    def test_historical_comparator_is_presented_in_operator_language(self):
        payload=self._write_payload()
        context={
            "sourceHistoricalFingerprint":"HIST_FP",
            "status":"INSUFFICIENT_HISTORY",
            "historyDepthReason":"HISTORY_LENGTH_NOT_DATA_GAP",
            "latestTrustedDate":"2026-09-04",
            "coverage":{
                "coverageOrigin":"SHOP_LAUNCH",
                "preStartDatesAreMissing":False,
                "coverageInterpretation":"TRUSTED_HISTORY_BEGINS_AT_SHOP_LAUNCH",
            },
            "comparators":{
                "previousDay":{
                    "status":"READY",
                    "currentWindow":{"start":"2026-09-04","end":"2026-09-04"},
                    "referenceWindow":{"start":"2026-09-03","end":"2026-09-03"},
                    "currentMissingDates":[],"referenceMissingDates":[],
                    "current":{"placedGmv":400,"placedOrders":8,"productClicks":40,"placedAov":50,"placedCvr":.2,"adsSpend":10,"roas":5},
                    "reference":{"placedGmv":300,"placedOrders":6,"productClicks":30,"placedAov":50,"placedCvr":.2,"adsSpend":10,"roas":4},
                    "businessContext":{
                        "status":"CONTEXT_AVAILABLE",
                        "matchEvaluation":"CONTEXT_DIFFERENT",
                        "qualification":{
                            "status":"CONTEXT_DIFFERENT",
                            "reason":"EXACT_MATCHING_PROFILE_DIFFERENT",
                            "alertEligible":False,
                            "diagnosisEligible":False,
                            "causalClaimEligible":False,
                        },
                        "contextMatchedBaselineEligible":False,
                        "alertEligible":False,
                        "diagnosisEligible":False,
                        "causalClaimEligible":False,
                    },
                    "alertEligible":False,"diagnosisEligible":False,
                },
                "previous7d":{"status":"INSUFFICIENT_HISTORY","alertEligible":False,"diagnosisEligible":False},
                "previousMonthMtd":{"status":"INSUFFICIENT_HISTORY","alertEligible":False,"diagnosisEligible":False},
                "sameWeekday":{
                    "status":"READY","sampleCount":4,
                    "sampleDates":["2026-08-28","2026-08-21","2026-08-14","2026-08-07"],
                    "baseline":{
                        "placedGmv":{"median":350,"mean":350,"min":300,"max":400},
                        "placedOrders":{"median":7,"mean":7,"min":6,"max":8},
                        "productClicks":{"median":35,"mean":35,"min":30,"max":40},
                        "placedAov":{"median":50,"mean":50,"min":50,"max":50},
                        "placedCvr":{"median":.2,"mean":.2,"min":.2,"max":.2},
                        "adsSpend":{"median":10,"mean":10,"min":10,"max":10},
                        "roas":{"median":4.5,"mean":4.5,"min":4,"max":5},
                    },
                    "contextMatchedBaseline":{
                        "status":"INSUFFICIENT_CONTEXT_MATCHED_HISTORY",
                        "requiredSampleCount":4,"sampleCount":0,"sampleDates":[],
                        "silentFallbackUsed":False,
                        "alertEligible":False,"diagnosisEligible":False,"causalClaimEligible":False,
                    },
                    "alertEligible":False,"diagnosisEligible":False,
                },
                "sameDayOfMonth":{"status":"INSUFFICIENT_HISTORY","alertEligible":False,"diagnosisEligible":False},
            },
            "contextStatus":"CONTEXT_UNAVAILABLE",
            "alertEligible":False,
            "diagnosisEligible":False,
        }
        payload["portfolio"]["historicalContext"]=context
        payload["shops"]["SHOP_A"]["historicalContext"]=context
        self._refresh_payload_integrity(payload)
        result=build_native_v2_multi_shop(
            payload_dir=self.payload_dir,
            v2_template_path=V2_TEMPLATE,
            output_dir=self.root/"native-history",
        )
        self.assertEqual(result["status"],"PASS")
        html=(self.root/"native-history"/"command_center_v2_multi_shop_native_template.html").read_text(encoding="utf-8")
        self.assertIn("Diễn biến kinh doanh",html)
        self.assertIn("Đã tham chiếu ",html)
        self.assertIn(" ngày cùng thứ trong lịch sử",html)
        self.assertIn("Chưa đủ kỳ lịch sử cùng bối cảnh",html)
        self.assertIn("không dùng kỳ khác bối cảnh để thay thế",html)
        self.assertIn("chưa đủ bằng chứng để kết luận nguyên nhân",html)
        self.assertIn("Dữ liệu lịch sử được tính từ thời điểm shop bắt đầu hoạt động",html)
        self.assertIn("Khác bối cảnh",html)
        self.assertIn("Cần thêm dữ liệu lịch sử trước khi đánh giá mức độ bất thường",html)
        self.assertIn("Bằng chứng đã tổng hợp",html)
        self.assertIn("Không có vấn đề nào đạt ngưỡng cần xử lý",html)
        for phrase in (
            "Business Pulse","Driver lớn nhất","historical baseline","factual",
            "decomposition driver","campaign chính thức","rule hiện tại",
            "Severity/Confidence","Detector nền tảng","Driver attribution",
        ):
            self.assertNotIn(phrase,html)

    def test_ui_v2_product_naming_prefers_commercial_name(self):
        row=_present_product({
            "productId":"50562805590",
            "productName":"Cặp Đôi Yêu Kiều",
            "resolvedParentSku":"CB019",
        })
        self.assertEqual(row["displayName"],"Cặp Đôi Yêu Kiều")
        self.assertEqual(row["secondarySku"],"CB019")
        self.assertEqual(row["productNamingState"],"RESOLVED_NAME")
        self.assertNotEqual(row["displayName"],row["secondarySku"])
        self.assertNotEqual(row["displayName"],row["productId"])

    def test_ui_v2_product_naming_missing_name_does_not_promote_sku_or_id(self):
        row=_present_product({
            "productId":"P123",
            "resolvedParentSku":"SKU-123",
        })
        self.assertEqual(row["displayName"],"Chưa xác định tên sản phẩm")
        self.assertEqual(row["secondarySku"],"SKU-123")
        self.assertEqual(row["productNamingState"],"MISSING_PRODUCT_NAME")

    def test_ui_v2_presentation_contract_is_enforced(self):
        payload=self._write_payload()
        bundle=_bundle_from_payload(payload)
        checks=_presentation_checks(bundle)
        self.assertTrue(checks["fontInter"])
        self.assertTrue(checks["nativeDoesNotOverrideFont"])
        self.assertTrue(checks["nativeUsesOnlyFoundationPalette"])
        self.assertTrue(checks["sharedDesignLanguageActive"])
        self.assertEqual(checks["forbiddenVisibleCopyHits"],[])
        self.assertEqual(checks["productNamingErrors"],[])
        contract=json.loads((ROOT/"config"/"ui_v2_presentation_contract.json").read_text(encoding="utf-8"))
        currency=contract["language_system"]["currency_format"]
        self.assertEqual(currency["full_example"],"2.100.000 đ")
        self.assertEqual(currency["compact_example"],"4,1tr đ")
        self.assertTrue(currency["show_full_amount"])
        self.assertTrue(currency["compact_units_allowed"])
        self.assertEqual(currency["full_amount_contexts"],["command_center_primary_period_cards","shop_compare_primary_period_cards"])

    def test_smart_issue_foundation_maps_only_to_latest_day_without_actions(self):
        context={
            "operatorActionPolicyFoundation":{
                "status":"ACTION_OPTIONS_READY",
                "actionOptionCount":2,
                "actionOptions":[
                    {
                        "actionOptionId":"AO_VALIDATE",
                        "status":"REVIEW_OPTION",
                        "optionKey":"VALIDATE_EVIDENCE_BEFORE_CHANGE",
                        "title":"Xác minh evidence trước khi thay đổi vận hành",
                        "whyRelevant":"Evidence validation",
                        "sourceIssueId":"SI_TEST",
                        "requiresHumanReview":True,
                        "executionMode":"HUMAN_REVIEW_ONLY",
                        "platformMutationAllowed":False,
                        "automaticExecutionEligible":False,
                        "automaticAlertEligible":False,
                        "prescriptiveRecommendation":False,
                        "causalClaimEligible":False,
                        "prerequisites":["Check evidence"],
                        "monitorKpis":["placedGmv"],
                        "verificationChecks":["Verify next refresh"],
                        "stopOrReversalChecks":["Stop if issue clears"],
                    },
                    {
                        "actionOptionId":"AO_AOV",
                        "status":"REVIEW_OPTION",
                        "optionKey":"REVIEW_AOV_PRICE_PROMOTION_MIX",
                        "title":"Rà soát AOV, price & promotion mix",
                        "whyRelevant":"AOV is the quantified top contribution",
                        "sourceIssueId":"SI_TEST",
                        "requiresHumanReview":True,
                        "executionMode":"HUMAN_REVIEW_ONLY",
                        "platformMutationAllowed":False,
                        "automaticExecutionEligible":False,
                        "automaticAlertEligible":False,
                        "prescriptiveRecommendation":False,
                        "causalClaimEligible":False,
                        "prerequisites":["Check product mix"],
                        "monitorKpis":["placedAov","placedGmv"],
                        "verificationChecks":["Verify AOV next refresh"],
                        "stopOrReversalChecks":["Stop if issue clears"],
                    },
                ],
            },
            "smartIssuesFoundation":{
                "status":"ISSUE_READY",
                "issueCount":1,
                "issues":[{
                    "issueId":"SI_TEST",
                    "status":"ISSUE_READY",
                    "affectedMetric":"placedGmv",
                    "severityLevel":"HIGH",
                    "severityScore":0.91,
                    "confidenceLevel":"HIGH",
                    "confidenceScore":0.93,
                    "effectPct":-0.4,
                    "modifiedZScore":-4.2,
                    "sourceComparator":"sameWeekday",
                    "attributionStatus":"ATTRIBUTED",
                    "driverEvidence":{
                        "topDriverMetric":"placedAov",
                        "identityContributionIsCausalClaim":False,
                    },
                    "contextEvidence":{
                        "matchedSampleCount":6,
                        "matchEvaluation":"CONTEXT_COMPATIBLE",
                    },
                    "unresolvedUncertainty":[
                        "CAUSALITY_NOT_ESTABLISHED",
                        "AUTOMATIC_ALERTS_DISABLED",
                        "ACTION_POLICY_NOT_DEFINED",
                    ],
                    "automaticAlertEligible":False,
                    "actionRecommendationEligible":False,
                    "operationalDiagnosisEnabled":False,
                    "causalClaimEligible":False,
                }],
            }
        }
        latest=_smart_issues_for_period(context,"yesterday")
        self.assertEqual(latest["status"],"ISSUE_READY")
        self.assertEqual(latest["count"],1)
        issue=latest["issues"][0]
        self.assertEqual(issue["label"],"GMV")
        self.assertIn("AOV",issue["summary"])
        self.assertFalse(issue["operationalDiagnosisEnabled"])
        self.assertFalse(issue["automaticAlertEligible"])
        self.assertFalse(issue["actionRecommendationEligible"])
        self.assertFalse(issue["causalClaimEligible"])
        self.assertEqual(issue["reviewOptionCount"],2)
        self.assertEqual(len(issue["reviewOptions"]),2)
        self.assertEqual(
            issue["reviewOptions"][1]["optionKey"],
            "REVIEW_AOV_PRICE_PROMOTION_MIX",
        )
        self.assertTrue(all(
            x["executionMode"]=="HUMAN_REVIEW_ONLY"
            for x in issue["reviewOptions"]
        ))
        self.assertTrue(all(
            not x["platformMutationAllowed"]
            for x in issue["reviewOptions"]
        ))
        self.assertEqual(
            _smart_issues_for_period(context,"last7")["status"],
            "NO_ISSUE",
        )
        self.assertEqual(
            _smart_issues_for_period(context,"mtd")["status"],
            "NO_ISSUE",
        )

    def test_native_v2_build_is_deterministic(self):
        self._write_payload()
        a=build_native_v2_multi_shop(
            payload_dir=self.payload_dir,
            v2_template_path=V2_TEMPLATE,
            output_dir=self.root/"native1",
        )
        b=build_native_v2_multi_shop(
            payload_dir=self.payload_dir,
            v2_template_path=V2_TEMPLATE,
            output_dir=self.root/"native2",
        )
        self.assertEqual(a["nativeBuildFingerprint"],b["nativeBuildFingerprint"])

    def test_v2_foundation_contract_remains_present(self):
        text=V2_TEMPLATE.read_text(encoding="utf-8")
        self.assertEqual(text.count("/*__UNIPALM_DATA__*/"),1)
        self.assertIn('id="sidebarPin"',text)
        self.assertIn("transform:scale(1.25)",text)
        self.assertIn('[data-theme="dark"]',text)
        self.assertIn("const LIVE_CC=",text)
        self.assertIn("function render()",text)
        # Multi-shop adapter must not introduce a second Compare visual system.
        native_text=(ROOT/"automation"/"modules"/"ui_v2_native.py").read_text(encoding="utf-8")
        for legacy in (".native-compare-card",".native-section{",".native-period-tabs",".native-two-col",".native-exec-summary",".native-driver-track"):
            self.assertNotIn(legacy,native_text[native_text.index('NATIVE_STYLE=r"""'):native_text.index('def _bootstrap')])


if __name__=="__main__":
    unittest.main()
