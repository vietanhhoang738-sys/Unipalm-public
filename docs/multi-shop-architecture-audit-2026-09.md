# Multi-Shop Architecture Audit — 2026-09-23

## Decision

The target architecture is **N-shop**, not "SYT+ + Mall".

A new shop must be onboarded by adding one registry entry and its raw root. Core ingestion, staging, QA, catalog evidence and shop isolation must not require source-code changes for the third, fourth, or later shop.

Concrete shop identities belong only in `config/shop_registry.json` and historical audit documents.

## Non-negotiable invariants

1. Every business-grain fact/mart row carries `shop_id`.
2. Listing identity is `shop_id + product_id`; a Product ID is never globally unique.
3. Product Ads grain is `shop_id + data_date + product_id`.
4. Ratios are recomputed from additive numerators/denominators; ratios are never averaged across shops.
5. One shop's ingestion/QA failure is an independent failure domain.
6. Catalog Resolver may use evidence from any other enabled shop, but there is no permanent "reference shop" or "peer shop" role.
7. Concrete Shop IDs/names must not be embedded in generic runtime modules or multi-shop workflows.
8. Production promotion remains blocked until the intended production shops pass staging QA.
9. Legacy single-shop components must fail closed when they see zero/multiple shop identities; they must never silently merge shops.
10. UI remains unchanged until multi-shop semantic marts and staging QA are accepted.

## Registry contract

`config/shop_registry.json` is the only runtime source of shop identity/configuration.

Each enabled shop supplies:
- `shop_key`
- internal `shop_id`
- platform-native `shopee_shop_id`
- `display_name`
- `platform`
- ordered `raw_root_candidates`
- optional capabilities such as `listing_catalog_enabled`

There is no fixed shop-count field and no reference/peer role.

A root candidate can be:
- direct Drive folder ID;
- child folder under a configured parent.

The staging resolver selects the highest-priority candidate containing all required core domains. This supports zero-downtime raw-folder migrations.

## Generic multi-shop core

### Shop Registry

`automation/modules/shop_registry.py`

Responsibilities:
- validate registry identity uniqueness;
- select one, many, or all enabled shops;
- support arbitrary shop count;
- validate generic raw-root candidate definitions.

### Raw ingestion and staging

`automation/multi_shop_staging_runner.py`

Responsibilities:
- run one or many shops from the registry;
- resolve raw root per shop;
- normalize each shop independently;
- write separate staging artifacts per `shop_key/month`;
- build cross-shop catalog evidence from all *other* enabled shops;
- collect independent per-shop QA;
- return global FAIL if any selected shop fails, without merging their data.

It has no production Data Mart or UI writer.

### Catalog Resolver

`automation/modules/catalog_resolver.py`

The resolver is N-shop aware:
- target listing never uses same-shop listing as cross-shop evidence;
- all other enabled shops may contribute reference evidence;
- multiple shops supporting the same Parent SKU strengthen/retain the candidate instead of reducing a pairwise margin;
- competing different Parent SKUs remain a conflict;
- exact SKU Master evidence remains independent of shop count.

### Product Ads

`automation/modules/ads_product_mart.py`

Canonical aggregation key:
`shop_id + data_date + product_id`

Two shops using the same Product ID can never be aggregated together.

## Production legacy quarantine

The current production publisher has not been redesigned during this milestone.

### `automation/source_processor.py`

Status: **legacy single-shop-per-run, shop-agnostic**.

Changes:
- no concrete shop ID fallback;
- every source row must contain `shop_id`;
- exactly one shop must be present in a run;
- mixed-shop sources fail closed.

This prevents the old processor from becoming an accidental multi-shop aggregator.

### `automation/run_pipeline.py`

Status: **legacy single-shop publisher, guarded**.

The existing payload/UI code still contains date/product dictionaries that are not yet multi-shop semantic structures. It therefore:
- accepts any one shop identity;
- requires exactly one shop across payload source marts;
- fails if a mart contains multiple shops;
- carries `shopId` forward in payload records for future compatibility.

A true multi-shop payload/UI is deferred until staging and multi-shop marts are accepted.

### Product Ads maintenance

`automation/backfill_product_ads.py` and `product-ads-mart-maintenance.yml` remain only as a recovery path for the current production mart.

The script:
- has no default processed Ads folder;
- requires its deployment folder through environment configuration;
- requires exactly one source shop;
- refuses to apply if the legacy destination belongs to another shop.

Retire this tool after multi-shop product Ads mart promotion.

## Removed redundancy

Deleted because their responsibilities are now covered by the consolidated core CI or production pipeline:

- `.github/workflows/multi-shop-catalog-ci.yml`
- `.github/workflows/data-v2-integration-dry-run.yml`
- `.github/workflows/data-v2-module-ci.yml`
- `.github/workflows/ui-v2-production-adapter-canary.yml`
- `automation/build_ui_v2_canary.py`

Do **not** delete:
- `frozen_v14_template.html`: production V1 fallback.
- `command_center_v2_template.html`: current V2 template.
- `pipeline_state.json`: generated deployment state committed by production workflow.
- `product-ads-mart-maintenance.yml`: current production recovery tool until multi-shop cutover.

## CI architecture guard

`.github/workflows/multi-shop-staging.yml` is now the consolidated `Multi-Shop Core CI & Staging QA` workflow.

On code changes it:
- compiles all multi-shop core modules plus guarded legacy adapters;
- runs the full repository unit-test suite;
- runs an architecture guard that rejects concrete current Shop IDs embedded in generic runtime code;
- rejects a multi-shop workflow default tied to one named shop.

Manual staging defaults to `all`; a specific registry shop key can still be supplied.

## Remaining technical debt outside the new core

### Legacy Apps Script upstream

Historical/current Orders Apps Script evidence still contains explicit SYT+ `shop_id` in its processing context.

This layer is not in the GitHub Python core and has not been generalized here.

Recommended direction:
- do not clone the old Apps Script stack once per new shop;
- keep it temporarily for existing production continuity;
- prove equivalence of the registry-driven Python RAW ingestion;
- then retire Apps Script upstream domain-by-domain.

This is materially cleaner than maintaining N copies of shop-specific Apps Script pipelines.

### Control Center / production processed outputs

The current production Control Center and processed-output path were built for the original shop workflow. Before multi-shop production promotion, readiness/control state must become shop-scoped, for example:

`shop_id + source_domain + period + run/status`

A domain should be able to fail for one shop without making another shop's production history ambiguous.

## Drive target

Desired steady-state raw layout:

```
01_raw_data/
  <shop-root-1>/
    orders/
    ads/
    product_performance/
    business_insights/
    returns_refunds/
    listing_catalog/
  <shop-root-2>/
    ...
  <shop-root-N>/
    ...
```

Folder names are operational labels only. The registry maps them to canonical `shop_id`.

The current SYT+ legacy root remains a lower-priority candidate until its domain folders are safely moved under `unipalm_syt_plus`.

## Gate to the next phase

Do not build or write production multi-shop marts yet.

Required sequence:
1. finish upstream dependency/migration checks;
2. run registry-driven staging for each enabled production shop;
3. resolve source gaps and QA failures;
4. accept per-shop staging QA;
5. design/write multi-shop semantic marts;
6. validate additive and ratio aggregation across 3+ synthetic/real shop scenarios;
7. only then add multi-shop payload/UI scope.

The architecture must be tested with at least a synthetic third shop even while only two real shops are registered.


## Processed/control-plane audit

Drive inspection confirms current processed facts already carry `shop_id`, but the physical namespace and operational controls are still legacy single-shop.

Observed active layout:
- `03_processed_data/<domain>/<year>/<month>/<domain>_processed_<YYYY_MM>`
- `orders_pipeline_control`
- `returns_pipeline_control`
- root `shopee_data_control_center`

Current controls do not use `shop_id + domain + period` as their key. They must therefore remain legacy production only and must not be extended to new shops.

The new storage-agnostic control-plane contract is implemented in:
- `automation/modules/pipeline_state.py`
- `docs/multi-shop-processed-control-plane.md`

Canonical future readiness grain:
`shop_id + source_domain + period`.

The active legacy processed/control folders were not moved or renamed because current Apps Script production dependencies are not yet fully retired.


## Atomic raw-root migration rule

The SYT+ migration root has been created and pinned by Drive folder ID in Shop Registry.

Do not move core domains independently. The staging raw-root resolver requires a single candidate root containing every core domain, so the cutover unit is:
- Orders
- Ads
- Product Performance
- Business Insights

Only Orders has a verified fixed-folder-ID legacy dependency today. Ads, Product Performance and Business Insights remain unverified, so the physical cutover is blocked.

See:
- `config/legacy_pipeline_dependencies.json`
- `docs/legacy-upstream-dependency-audit.md`

This explicit inventory is preferred over hidden operational assumptions.


## Source-schema boundary

Multi-shop scalability now includes a source-schema abstraction. Runtime parsers no longer own independent hard-coded EN/VI alias dictionaries; aliases and reviewed fingerprints are centralized in `config/source_schema_registry.json`.

This prevents three failure modes:
1. adding a new shop whose Shopee locale differs;
2. Shopee adding/reordering columns;
3. Shopee renaming a business metric while ingestion silently treats it as the old metric.

Schema FAIL is a pre-production blocker. Schema WARN is observable but non-blocking when required canonical semantics are intact.

See `docs/source-schema-drift-guard.md`.


## Durable semantic layer

The registry-driven architecture now has a durable semantic boundary:

`03_processed_data_v2 -> 04_semantic_data_v2`

Semantic rules:
- every shop-grain mart carries `shop_id`;
- product joins are `shop_id + product_id`;
- portfolio ratios are recomputed from additive numerators/denominators;
- non-additive daily unique metrics are not summed into monthly metrics;
- cross-domain daily KPIs use per-shop common reliable windows;
- canonical portfolio persistence requires all enabled shops.

The first semantic QA run exposed and caused correction of the BI traffic-source grain. Staging now preserves channel/source hierarchy and blocks duplicate traffic grains.

Durable publish/no-op validation passed on runs `PUBLIC_SNAPSHOT_NOT_CONFIGURED` and `PUBLIC_SNAPSHOT_NOT_CONFIGURED`.

See `docs/multi-shop-semantic-mart-v1.md`.
