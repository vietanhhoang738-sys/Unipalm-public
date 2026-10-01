# PROJECT HANDOFF — Product Intelligence V2

Date: 2026-09-28  
Repository: `vietanhhoang738-sys/Unipalm`  
Branch: `multi-shop-catalog-resolver`  
Status: **BATCH COMPLETE — VALIDATED PREPRODUCTION**

## Canonical checkpoint

Final validation:
- workflow run: **#456 / 36373421120**
- conclusion: **SUCCESS**
- commit validated: `39b44c5910e63f3c1157e9fc96c66ebc4dfe2c51`
- Native patch: `native-product-intelligence-v34`
- Product Intelligence fingerprint: `cc9cc0602225ad686d75d9730e8897460885d5dcb6e59e8736195268d723489f`
- Product history lineage fingerprint: `a28d5aa555cd916249b9be120de28076a3c7a61997bcf22b33a7c8ae87191747`
- Payload fingerprint: `5c552ed11ef214da090f2893ea616773eeae5aafb99b0cec0341437ef9daede2`
- Native fingerprint: `03042755926380a7f2895dcfe73f536376c0811a3f7a7417f24068337ea77c9a`
- Native HTML SHA256: `1b884714a3eb3228e164e1e02dfede094492fdb5517c053a6f7acd49bb5da56c`
- Native QA: **33/33 PASS**
- Product Intelligence QA: **42 checks / 0 failed**

## Product scope contract

Product is a single-Shop destination.

Allowed global horizons:
- 1 tháng
- 3 tháng
- 6 tháng
- Năm

Forbidden:
- cross-shop compare inside Product;
- day/week Product scope;
- synthetic finer-grain Product views created from supporting Ads data.

## Historical state

### SYT+

Trusted Product history is Jan–Sep 2026:
- Jan–Jun: durable `product_history_semantic_v1` backfill, QA-passed independently;
- Jul–Sep: canonical Semantic v2;
- canonical Semantic has precedence on overlap.

Horizon status:
- 1M READY
- 3M READY
- 6M READY
- Year READY
- Structural Product Intelligence READY

Structural baseline for Sep as-of:
- required complete months: Mar–Aug 2026
- previous window: Mar–May
- recent window: Jun–Aug
- Sep MTD: corroborating only, not scored

### Mall

Trusted Product history is Jul–Sep 2026, matching Shop launch lifecycle.

Horizon status:
- 1M READY
- 3M READY
- 6M INSUFFICIENT_HISTORY
- Year READY lifecycle-aware
- Structural Product Intelligence INSUFFICIENT_OPERATING_HISTORY

Do not manufacture pre-launch history or structural signals for Mall.

## Product Intelligence semantics

Structural method:
`recent 3 complete months vs prior 3 complete months`

Driver identity:
`GMV = Product Clicks × CVR × AOV` internally.

Operator-facing label:
`GMV = Lượt nhấp sản phẩm × CVR × AOV`.

Attribution method:
- exact Shapley contribution on the identity;
- contributions reconcile to modeled GMV difference;
- attribution is non-causal;
- `causalClaim=false` is enforced.

## BI layout compatibility fix

September full validation exposed a Shopee Business Insights workbook reorder for SYT+.

The final design preserves the validated staging core and changes only layout discovery:
- `automation/modules/bi_workbook_layout.py` resolves worksheet roles by content;
- cover / overview / spacer worksheets may move without changing metric semantics;
- exactly three daily KPI, traffic summary and traffic daily roles are required;
- ambiguous/missing roles fail closed;
- stage order inside each role remains placed -> confirmed -> paid;
- validated legacy staging logic is preserved in `automation/multi_shop_staging_runner_legacy.py`;
- public `automation/multi_shop_staging_runner.py` is a thin compatibility wrapper.

All old staging tests plus new reordered-workbook regression tests pass.

## Native v34 language and visual boundary

The final Native v34 operator surface passes UI V2 Language System:
- no forbidden visible copy;
- Product name remains primary label;
- SKU remains secondary;
- internal terms such as `Product Clicks`, raw `trusted history`, raw Semantic/QA wording and `Driver chính` are not exposed as primary operator copy;
- structural driver rows use `Yếu tố chính` and Vietnamese-first wording.

## Production safety

Still false / disabled:
- production cutover authorization;
- production Data Mart writes;
- production deployment;
- production index modification;
- production V2 template modification;
- platform mutation;
- automatic Product alerts/actions;
- causal claims.

## Canonical detailed milestone

Read:
`docs/product-intelligence-v2-foundation.md`

## Next project step

Do **not** rebuild Product foundation unless a regression is found.

Next destination should inherit the same domain doctrine. Recommended next batch:
**Ads Intelligence V2 Foundation**, starting from source-grain audit and scope contract before UI implementation.
