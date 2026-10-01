# Multi-Shop Semantic Mart v1

Date: 2026-09-23  
Status: **PREPRODUCTION — durable persistence validated**

## Purpose

This layer converts shop-scoped processed v2 facts into business-ready marts consumed by the current multi-shop UI Payload v1.x / Native V2 PREPRODUCTION path without inheriting assumptions from the legacy single-shop Data Mart.

Source:

`03_processed_data_v2/<shop_key>/<YYYY-MM>/...`

Durable semantic output:

`04_semantic_data_v2/<YYYY-MM>/...`

The semantic portfolio partition is period-scoped, not shop-scoped, because every row already contains `shop_id` and the layer intentionally supports cross-shop benchmark calculations.

Production Data Mart and production UI are not written by this layer.

## Core identity rules

- Shop grain always includes `shop_id`.
- Product joins use `shop_id + product_id`.
- A Product ID from one shop is never used to enrich a row from another shop.
- Parent SKU is observed/resolved evidence, not a global Product ID.
- SKU-prefix inference is forbidden.
- There is no permanent reference shop, peer shop, or fake all-shop entity.

Synthetic 3-shop tests verify that the same Product ID can exist in three shops without collision.

## KPI policy

Ratios are never averaged. They are recomputed from additive numerators and denominators:

```
AOV  = SUM(GMV) / SUM(Orders)
CVR  = SUM(Orders) / SUM(Product Clicks)
ROAS = SUM(Attributed Ads Sales) / SUM(Ads Spend)
CTR  = SUM(Clicks) / SUM(Impressions)
```

Daily Visitors and Buyers are not summed into monthly unique metrics because they are not additive across days.

## Common reliable window

Cross-domain daily marts use a common reliable window per shop:

`common_reliable_end = MIN(source verified-through dates)`

September 2026 validation:

### SYT+

- common start: 2026-09-01
- common end: 2026-09-17
- Orders verified through: 2026-09-18
- Ads verified through: 2026-09-18
- BI verified through: 2026-09-17

### Mall

- common start: 2026-09-01
- common end: 2026-09-21
- Orders verified through: 2026-09-21
- Ads verified through: 2026-09-22
- BI verified through: 2026-09-21

Source-specific marts may retain later source dates; only cross-domain combined metrics are constrained to the common reliable window.

## Current marts and grains

| Mart | Grain |
| --- | --- |
| `dim_shop` | `shop_id` |
| `dm_shop_daily` | `shop_id + data_date` |
| `dm_commercial_stage_daily` | `shop_id + data_date + order_stage` |
| `dm_ads_daily` | `shop_id + data_date` |
| `dm_ads_product_daily` | `shop_id + data_date + product_id` |
| `dm_product_monthly` | `shop_id + data_month + product_id` |
| `dm_traffic_source_daily` | `shop_id + data_date + order_stage + channel_group + traffic_source` |
| `dm_order_quality_daily` | `shop_id + data_date` |

### Lean semantic output policy

Semantic v1.2 no longer persists monthly marts that can be deterministically derived from daily facts and have no current consumer. This reduces duplicated storage, contract surface, Drive artifacts and QA maintenance without losing business information.

## Current real validation

Cleanup checkpoint: GitHub Actions run #244 / `35992225052` — PASS.

Semantic contract: `1.2`

Semantic build fingerprint:

`fb862a21b281d3b33611e35c060d5dfbbe19a3bdbb455fc9f9c034b755a3c162`

Observed persisted rows:
- `dim_shop`: 2
- `dm_shop_daily`: 40
- `dm_commercial_stage_daily`: 120
- `dm_ads_daily`: 41
- `dm_ads_product_daily`: 912
- `dm_product_monthly`: 71
- `dm_traffic_source_daily`: 3,582
- `dm_order_quality_daily`: 40

QA: 17 checks PASS, 0 failures.

Drive publish replaced the prior semantic period partition atomically with exactly 10 files: 8 marts + `manifest.json` + `semantic_qa_report.json`. The removed monthly marts are not present in the active partition.

Catalog QA still treats historical deleted listings without a current Listing Catalog record as valid when they satisfy `HISTORICAL_DELETED_NO_CURRENT_LISTING`.

## BI traffic-source correction

The first semantic QA run exposed a real upstream modeling bug: Shopee BI traffic exports contain hierarchical sections such as Product Card, Seller Live, Seller Video and Shopee Affiliate.

The old normalizer flattened those sections and created duplicate semantic grains.

The staging normalizer now preserves:
- `channel_group`
- canonical `traffic_source`
- `traffic_source_raw`
- `is_group_total`
- `exposure_metric`

English and Vietnamese labels are canonicalized while preserving raw evidence. Staging now blocks duplicate traffic grains before processed/semantic promotion.

Shopee Ads traffic section inside BI is intentionally not merged into the traffic mart because its metric schema differs and canonical Ads facts already come from the Ads export.

## Durable Drive persistence

Drive root:

`04_semantic_data_v2`

Drive folder ID:

`PUBLIC_RESOURCE_012`

Current partition:

`04_semantic_data_v2/2026-09`

First durable publish:
- GitHub run `PUBLIC_SNAPSHOT_NOT_CONFIGURED`
- status: `PUBLISHED`
- semantic partition published atomically
- MD5 + size verified

Immediate identical rebuild:
- GitHub run `PUBLIC_SNAPSHOT_NOT_CONFIGURED`
- status: `NOOP`
- 0 files uploaded
- same semantic fingerprint

Drive inspection confirmed exactly one active `2026-09` partition, no leftover temp/backup, and persisted run audits.

Reviewed baseline artifact:

`_control/baselines/semantic_v2_baseline_all_2026_09_run_114.zip`

## Persistence safety

Canonical semantic persistence requires:
- semantic QA PASS;
- all enabled shops included;
- exact source-shop scope match;
- manifest hashes valid;
- atomic temporary upload + swap;
- same fingerprint => NOOP;
- unmanaged existing partition => FAIL;
- user OAuth for My Drive writes.

Partial one-shop runs may build semantic QA artifacts, but they may not overwrite the canonical portfolio partition.

## Production boundary

Current state:

```
RAW
  -> Staging + Schema Guard
  -> Processed v2
  -> Durable Processed Drive
  -> Semantic v2
  -> Durable Semantic Drive
  -> UI Payload v1.x
  -> Native V2 PREPRODUCTION
```

The current downstream contract is UI Payload v1.x. Redundant monthly semantic outputs are intentionally not persisted: `dm_shop_monthly`, `dm_shop_benchmark_monthly`, and `dm_traffic_source_monthly` are all derivable from authoritative daily marts and had no active downstream consumer. Semantic contract v1.2 therefore keeps only marts that are directly consumed or provide non-derivable product grain. Production Data Mart and production UI remain untouched.


## Traffic-source grain

Business Insights traffic is a sectioned source. A source name such as `Search` may appear under more than one channel group and must not be flattened.

Canonical persisted traffic grain:
- daily: `shop_id + data_date + order_stage + channel_group + traffic_source`

Monthly traffic views, when needed, are derived from the daily mart rather than persisted as a second semantic mart.

The parser preserves `traffic_source_raw` for audit and canonicalizes supported EN/VI source names.

Exposure labels differ by channel (for example Product Impressions, Live Views, Video Views, Content Views). These are normalized into the additive `impressions` field together with `exposure_metric`, which preserves the original semantic type.

Shopee Ads is not duplicated into this BI traffic mart because the dedicated Ads fact is authoritative for Ads metrics.

## Historical deleted product semantics

Current Listing Catalog is current-state metadata, while Product Performance can retain a listing that Shopee has already deleted.

Therefore a missing current catalog join is not automatically an error.

Allowed product join states:
- `MATCHED_CURRENT_CATALOG`
- `HISTORICAL_DELETED_NO_CURRENT_LISTING`

Any other missing current catalog identity remains blocking as `MISSING_CURRENT_CATALOG`.

A historical deleted row never receives an inferred Parent SKU simply to satisfy the join.
