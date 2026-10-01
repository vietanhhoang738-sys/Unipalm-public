# Product Intelligence V2

Status: **VALIDATED PREPRODUCTION MILESTONE**  
Foundation visual direction: **human-accepted**  
Final structural-history validation: **run #456 / 36373421120 — SUCCESS**  
Native patch: **`native-product-intelligence-v34`**  
Production cutover: **not authorized**

## Mission

Product is the first domain-level Intelligence workspace after Command Center. It is designed to answer, for one selected Shop:

`Danh mục đang vận hành thế nào -> sản phẩm nào đang tăng/giảm đáng chú ý -> yếu tố nào đóng góp vào thay đổi GMV -> mức bằng chứng lịch sử có đủ hay không -> đi xuống KPI/funnel/Ads/chi tiết sản phẩm.`

Product is not a cross-shop comparison surface. Cross-shop orchestration remains a Command Center / Compare responsibility.

## Destination Scope Doctrine

Canonical rules:
- exactly one Shop at a time;
- no `So sánh Shop` inside Product;
- canonical Product Performance grain is **MONTHLY**;
- allowed global horizons are **1 tháng / 3 tháng / 6 tháng / Năm**;
- Product day/week scopes are forbidden;
- daily Product Ads facts may support Product analysis only after aggregation into the selected monthly-family horizon;
- unavailable horizons must remain disabled rather than silently using incomplete history;
- product identity remains `shop_id + product_id`; no cross-shop merge by name/SKU similarity.

Canonical contracts:
- `config/destination_scope_contract.json`
- `config/ui_v2_presentation_contract.json`
- `config/product_intelligence_contract.json`

## Product history architecture

### Why Product has its own historical failure domain

Full-shop historical months can fail a shop-wide reconciliation for an unrelated domain while Product Performance itself remains structurally valid. Product history therefore must not weaken the shop-wide Processed/Semantic gate, but it also must not discard valid Product facts solely because Orders or another domain failed.

The durable Product-history path is:

`historical RAW -> read-only Staging -> Product-domain QA -> product_history_semantic_v1 -> Product Intelligence`

It does **not** imply:
- full-shop Processed promotion;
- canonical portfolio Semantic promotion;
- production Data Mart writes;
- production UI writes.

Durable namespace:

`04_semantic_data_v2/_product_history_backfill/<shop_key>/<YYYY-MM>/...`

Canonical Semantic v2 always wins for overlapping months. Product-history semantic partitions are used only for missing historical Shop-months.

Relevant components:
- `config/product_history_backfill_contract.json`
- `automation/modules/product_history_semantic.py`
- `automation/modules/product_history_drive_writer.py`
- `automation/multi_shop_product_history_backfill_runner.py`
- `config/storage_registry.json`

## Validated Product history — September 2026

### SYT+

Trusted Product months: **2026-01 through 2026-09**.

Lineage:
- Jan–Jun: `PRODUCT_HISTORY_SEMANTIC_V1`, each month independently QA-passed and fingerprinted;
- Jul–Sep: canonical `SEMANTIC_V2`;
- precedence: `CANONICAL_SEMANTIC_V2_OVER_PRODUCT_HISTORY_SEMANTIC_V1`.

Horizon state:
- 1 tháng: **READY**
- 3 tháng: **READY**
- 6 tháng: **READY**
- Năm: **READY**
- Structural Product Intelligence: **READY**

### Mall

Trusted Product months: **2026-07 through 2026-09**, matching its validated Shop lifecycle.

Horizon state:
- 1 tháng: **READY**
- 3 tháng: **READY**
- 6 tháng: **INSUFFICIENT_HISTORY**
- Năm: **READY** using lifecycle-aware current-year start at Shop launch
- Structural Product Intelligence: **INSUFFICIENT_OPERATING_HISTORY**

Pre-launch months are not treated as missing business data and no structural problem/opportunity is fabricated for Mall.

## Structural Product Intelligence

Structural comparison uses **six completed months immediately before the as-of month**.

For as-of `2026-09`:
- required complete-month baseline: **2026-03 through 2026-08**;
- previous window: **Mar–May**;
- recent window: **Jun–Aug**;
- Sep MTD role: **`CORROBORATING_ONLY_NOT_SCORED`**.

This intentionally separates structural trend scoring from an incomplete current month.

### Driver attribution

For each eligible Product signal, GMV movement is decomposed using:

`GMV = Lượt nhấp sản phẩm × CVR × AOV`

Method: exact Shapley contribution on this business identity.

The contribution is explanatory, **not causal**. Product Intelligence and Native UI both enforce `causalClaim=false`.

Run #456 artifact inspection confirmed:
- SYT+ structural status: **READY**;
- baseline end month: **2026-08**;
- required structural months: **Mar–Aug**;
- Sep MTD excluded from structural scoring;
- all attributed driver contributions reconcile to their modeled GMV gap;
- no causal claim leaked into Product signals.

## Aggregation discipline

Across Product horizons:
- additive measures are summed;
- AOV, CTR, add-to-cart rate and ROAS are recomputed from additive components;
- ratios are never averaged across months;
- non-additive monthly fields such as buyer counts, repeat-order rate and average days to repeat remain latest-month context unless a dedicated cohort/lifetime contract exists.

## Native Product v34

Native v34 uses the shared V2 Design Language and remains a single-Shop Product diagnostic workspace.

Information hierarchy:
1. Tóm tắt sản phẩm;
2. history/evidence state;
3. structural problems/opportunities when evidence is sufficient;
4. top contributing factor to the modeled GMV movement;
5. primary Product KPIs;
6. Cơ cấu danh mục;
7. Hiệu quả funnel sản phẩm;
8. Product-level Ads support;
9. searchable Product table.

Product name is the primary visible identifier. SKU is secondary. Product ID remains technical metadata.

Visible operator copy follows UI V2 Language System. Internal phrases such as `Product Clicks`, `Driver chính`, `trusted history`, raw Semantic/QA jargon are not surfaced as operator-facing labels.

## Shopee Business Insights layout hardening

Final September validation exposed a real Shopee export-layout change: SYT+ Business Insights no longer matched the historical absolute worksheet positions.

The fix deliberately does not rewrite business metric semantics.

`automation/modules/bi_workbook_layout.py` now resolves required BI worksheet roles by content:
- 3 Shop daily KPI sheets;
- 3 traffic summary sheets;
- 3 traffic daily sheets;
- cover/overview/spacer sheets are ignored;
- stage order inside each role remains placed -> confirmed -> paid;
- missing/ambiguous roles fail closed.

The validated staging core is preserved in `automation/multi_shop_staging_runner_legacy.py`; the public runner is a thin compatibility wrapper that replaces only BI layout discovery.

Regression coverage includes reordered workbooks with inserted cover/overview sheets and legacy runner compatibility.

## Final validation — run #456

Workflow: `Multi-Shop Core CI & Staging QA`  
Run number: **456**  
Run ID: **36373421120**  
Commit: `39b44c5910e63f3c1157e9fc96c66ebc4dfe2c51`  
Conclusion: **SUCCESS**

Full chain passed:

`RAW -> Staging -> Processed v2 -> durable Drive -> Semantic v2 -> Business Context -> Historical -> Product Intelligence -> Canonical Payload -> Native V2`

Validated fingerprints:
- Semantic: `38e12e9552fd81571b85e37f977bfbeb8feda9a1d3b7e301663f56fa28cad7f6`
- Product Intelligence: `cc9cc0602225ad686d75d9730e8897460885d5dcb6e59e8736195268d723489f`
- Product history lineage: `a28d5aa555cd916249b9be120de28076a3c7a61997bcf22b33a7c8ae87191747`
- Payload: `5c552ed11ef214da090f2893ea616773eeae5aafb99b0cec0341437ef9daede2`
- Native: `03042755926380a7f2895dcfe73f536376c0811a3f7a7417f24068337ea77c9a`
- Native HTML SHA256: `1b884714a3eb3228e164e1e02dfede094492fdb5517c053a6f7acd49bb5da56c`

Native QA:
- **PASS**
- 33 checks / 0 failed
- `ui_v2_language_system`: PASS, zero forbidden visible-copy hits
- `ui_v2_product_naming_system`: PASS
- Product destination ready: true

Product Intelligence QA:
- **PASS**
- 42 checks / 0 failed

## Safety

Run #456 confirms:
- production cutover is not authorized;
- production Data Mart was not written;
- production deployment was not performed;
- production index was not modified;
- production V2 template was not modified;
- platform mutation is not allowed;
- automatic Product alerts/actions remain disabled;
- causal claims remain disabled.

## Milestone decision

**Product Intelligence V2 structural-history batch is complete.**

The Product destination is now a validated PREPRODUCTION milestone with real structural Intelligence for SYT+ and lifecycle-aware fail-closed behavior for Mall. Future Product work should be incremental capability improvement, not a rebuild of this foundation.

The next domain destination should inherit the same doctrine:
- one Shop at a time;
- source-grain-constrained time scope;
- Intelligence before raw metric inspection;
- explicit evidence boundaries;
- shared V2 visual/language contracts;
- production remains separately gated.
