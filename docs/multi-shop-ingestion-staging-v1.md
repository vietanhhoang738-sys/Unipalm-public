# Multi-Shop Ingestion & Staging v1

## Scope

This is the pre-production RAW -> standardized staging layer for **any enabled shop in Shop Registry**.

Safety boundary:
- no production Data Mart writes;
- no UI mutation;
- independent shop failure domains;
- staging artifacts only;
- failed QA blocks promotion.

## Registry-driven onboarding

A shop is onboarded by adding one entry to `config/shop_registry.json` with:
- `shop_key`
- `shop_id`
- platform-native Shop ID
- display name
- platform
- enabled flag
- ordered raw-root candidates

There is no fixed shop count and no reference/peer role.

Manual examples:

```bash
# all enabled shops
python automation/multi_shop_staging_runner.py --month 2026-09

# one shop
python automation/multi_shop_staging_runner.py --shop-key <shop_key> --month 2026-09

# selected shops
python automation/multi_shop_staging_runner.py \
  --shop-key <shop_1> \
  --shop-key <shop_3> \
  --month 2026-09
```

## Required raw domains

Core:
- orders
- ads
- product_performance
- business_insights

Optional/pre-production:
- returns_refunds
- listing_catalog

Expected domain shape:

```
<shop raw root>/
  <domain>/
    YYYY/
      YYYY-MM/
        ...
```

The runner evaluates raw-root candidates by priority and selects the first candidate containing all core domains.

## Listing Catalog Snapshot

Shopee Seller Center `mass_update_sales_info` is the preferred authority for observed listing metadata.

It provides current:
- Product ID/name
- Variation ID/name
- Parent SKU
- Variation SKU
- price
- seller stock
- GTIN when present

The export can contain non-standard workbook-view metadata, so listing ingestion reads worksheet cells without depending on those view properties.

Parent SKU is propagated within the same `product_id` when Shopee writes it only on one variation row.

No Parent SKU is inferred from a variation-SKU prefix.

## Normalized outputs per shop/month

- `fact_orders.jsonl`
- `fact_order_items.jsonl`
- `fact_product_performance_monthly.jsonl`
- `fact_product_variations_monthly.jsonl`
- `fact_shop_performance_daily.jsonl`
- `fact_traffic_source_daily.jsonl`
- `fact_traffic_source_monthly.jsonl`
- `fact_ads_performance_daily.jsonl`
- `dm_ads_product_daily_candidate.jsonl`
- `catalog_resolution_staging.jsonl`
- `listing_catalog_products_snapshot.jsonl`
- `listing_catalog_variations_snapshot.jsonl`
- `staging_qa_report.json`

Global run:
- `multi_shop_staging_summary_<YYYY-MM>.json`

Every business-grain row contains `shop_id`.

## Source normalization rules

### Orders

Shopee Orders export is item-grain while order-level amounts/fees repeat on item rows.

The adapter creates:
- one order row per `shop_id + order_id`;
- item rows separately.

Repeated order-level values are validated, never summed across item rows.

### Business Insights

Placed, Confirmed and Paid remain distinct commercial stages.

Traffic is normalized separately.

Ratios remain source-level; any later cross-shop aggregate must recompute ratios from additive components.

### Product Performance

Product summary and variation rows are separated.

Product Performance remains the KPI/performance source even when Listing Catalog supplies better identity metadata.

### Ads

Every daily file is checked against the registry platform Shop ID.

All campaigns are retained.

Product Ads candidate grain:
`shop_id + data_date + product_id`

Campaign restarts therefore do not fragment product history, and identical Product IDs in different shops cannot mix.

## Cross-shop Catalog Resolver evidence

For a target shop, the runner can load catalog evidence from **all other enabled registry shops**.

There is no permanent reference shop.

Reference loading is fail-soft:
- unavailable other-shop catalog evidence is recorded;
- target-shop ingestion can still proceed;
- resolver confidence/status exposes evidence quality.

Optional external reference JSON and SKU-family map remain supported.

## Blocking QA

Checks include:
1. shop identity isolation;
2. duplicate business keys;
3. BI stage coverage/alignment;
4. target-month Orders presence;
5. target-month Ads presence/contiguity;
6. duplicate Ads source-day files;
7. cancelled-order fee invariant;
8. product/variation referential consistency;
9. Product Ads all-campaign aggregation;
10. Placed Orders/GMV reconciliation;
11. Catalog Resolver observability.

`production_write_allowed=true` only when all blocking checks pass for that shop.

A multi-shop run returns overall PASS only when every selected shop passes.

## Current source-state rule

Source coverage is not documented here as a static blocker because it changes continuously. The authoritative state is the latest staging/processed manifest and pipeline-state evidence for each shop.

Listing Catalog snapshots remain authoritative for current listing metadata, including the corrected `CB019-*` Cặp Đôi Yêu Kiều variations.

## Raw-folder migration

Desired steady state is one root per shop under `01_raw_data`.

SYT+ currently has:
- a high-priority future child root `unipalm_syt_plus`;
- its existing root as lower-priority fallback.

The runner switches automatically only when the higher-priority root contains every core domain.

Physical folder migration should wait until legacy upstream dependencies are verified.

## Production boundary

The current production processor/publisher is still a guarded one-shop-per-run legacy path.

It must not receive multi-shop marts.

The separate Semantic v2 layer is now implemented and validated. Keep the legacy production guard until an explicit production cutover replaces it.


## Mixed-locale files within one period

Supported and validated.

The same shop/month may contain a mixture of English and Vietnamese Shopee exports. Parsing is performed independently per file and resolves locale-specific labels to canonical fields before concatenation.

Real validation on Mall Ads 2026-09:
- 01-18 Sep: English
- 19-20 Sep: Vietnamese
- 20 contiguous source days
- full staging QA PASS

Therefore the ingestion contract does **not** bind locale to `shop_id`, folder, or month.

Unknown/unrecognized schemas must still fail closed rather than returning silent zero rows.


## Source Schema Drift Guard

Before any source is normalized, its header contract is checked against `config/source_schema_registry.json`.

Policy:
- known EN/VI aliases are normalized to canonical fields;
- column order is irrelevant;
- added columns create non-blocking WARN evidence;
- a missing required canonical field blocks the file;
- semantic guesses/fuzzy matching are forbidden.

Current reviewed EN/VI fingerprints are baselined from September 2026 source files for both enabled shops.

Successful shop staging emits `schema_drift_report.json`. Schema warnings are surfaced in the multi-shop summary. A blocking drift is stored in `staging_error.json` and cannot promote to production.

See `docs/source-schema-drift-guard.md`.
