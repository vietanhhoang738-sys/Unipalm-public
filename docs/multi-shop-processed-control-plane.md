# Multi-Shop Processed & Control Plane Contract — 2026-09-23

## Current finding

The active `03_processed_data` tree is still organized by domain first:

```
03_processed_data/
  orders/
  returns_refunds/
  ads/
  product_performance/
  business_insights/
  data_mart/
```

The processed spreadsheets themselves already carry `shop_id` in their fact rows, which is good.

However, the active processed folder namespace and control state were designed for the original single-shop production pipeline:
- filenames such as `orders_processed_2026_09` contain no shop namespace;
- `orders_pipeline_control` has run grain `period + pipeline`, not `shop_id + period + pipeline`;
- `returns_pipeline_control` has the same issue;
- the root `shopee_data_control_center` reports one state per pipeline/domain and one Data Mart state, without shop scope.

Therefore this layer must be treated as **legacy production state**, not extended for new shops.

## What stays active for now

Do not move, rename, or rewrite these production dependencies until multi-shop staging is accepted:
- `03_processed_data/orders`
- `03_processed_data/returns_refunds`
- `03_processed_data/ads`
- `03_processed_data/product_performance`
- `03_processed_data/business_insights`
- current `shopee_data_control_center`
- current production Data Mart

They may continue serving the existing production path.

## What must not happen

For a new shop, do not:
- create another set of hard-coded Apps Scripts;
- append its output into the current flat processed folders without an explicit shop namespace;
- reuse current Control Center rows that identify only `pipeline + period`;
- create filenames whose identity is only `<domain>_processed_<YYYY_MM>`;
- use one shop's READY state as evidence another shop is READY.

## Target processed identity

Future processed artifacts must have shop identity in both data grain and storage namespace.

Recommended logical path:

```
03_processed_data_v2/
  <shop_key>/
    orders/
      YYYY/
        MM/
    returns_refunds/
    ads/
    product_performance/
    business_insights/
    listing_catalog/
```

or an equivalent object/table store where `shop_id` is an explicit partition key.

The exact physical store can change later; the identity contract cannot.

## Target control-plane grain

Canonical readiness key:

```
shop_id + source_domain + period
```

Minimum state fields:
- shop_id
- source_domain
- period
- state
- run_id
- pipeline_version
- source_version
- verified_through
- dq_error
- dq_warning
- production_updated
- output_location
- started_at
- finished_at
- error_stage
- error_message

Implemented storage-agnostic contract:
- `automation/modules/pipeline_state.py`

This module intentionally does not write the current Control Center.

## Failure-domain rule

Readiness is evaluated independently per shop.

Example:

```
SHOP_A / orders / 2026-09 = READY
SHOP_A / ads    / 2026-09 = READY
=> SHOP_A 2026-09 READY

SHOP_B / orders / 2026-09 = READY
SHOP_B / ads    / 2026-09 = FAILED
=> SHOP_B 2026-09 BLOCKED
```

SHOP_B failure must not downgrade or overwrite SHOP_A state.

## Why processed files cannot simply be shared in one flat folder

The rows can technically coexist because they carry `shop_id`, but operational identity becomes ambiguous:
- two shops can both produce `orders_processed_2026_09`;
- a pipeline control row cannot identify which shop produced an output;
- rebuild/retry actions can overwrite another shop's state;
- lineage from Control Center to output file is no longer unique.

Therefore multi-shop correctness requires storage namespace + control state to be shop-scoped, not only row-level `shop_id`.

## Migration strategy

1. Keep legacy processed/control production unchanged.
2. Use registry-driven RAW -> staging as the new source of truth for multi-shop development.
3. Prove full staging QA per enabled shop.
4. Introduce the new shop-scoped processed/control namespace.
5. Backfill/cut over one domain at a time.
6. Only then retire old domain pipeline controls and the flat Control Center.
7. Build multi-shop semantic marts after processed/control identity is stable.

## Drive cleanup completed before this contract

Active master/data-mart folders were already cleaned:
- obsolete master backups and the old Google Sheet shop registry moved to `99_archive_legacy`;
- old Data Mart variants moved to `data_mart/99_archive_legacy`;
- legacy single-shop README/dataset registry moved to documentation archive;
- production files themselves were not deleted.

## Production boundary

No production Data Mart row and no UI component is changed by this contract.

The current production processor/publisher remains guarded single-shop-per-run.


## Implemented v1 candidate

The contract is now implemented in:
- `automation/modules/processed_layer.py`
- `automation/multi_shop_processed_runner.py`
- `config/processed_layer_contract.json`

The CI workflow builds processed/control candidates only after staging succeeds.

Candidate layout:

```
processed_artifacts/
  <shop_key>/
    <YYYY-MM>/
      orders/
      ads/
      product_performance/
      business_insights/
      catalog/
      listing_catalog/
      control/
        pipeline_state.jsonl
      manifest.json
      processed_qa_report.json
```

Required checks:
- input staging QA PASS;
- schema guard not FAIL;
- source rows contain only expected `shop_id`;
- deterministic declared transforms preserve row count;
- processed output contains no foreign shop rows;
- control state keys are unique/valid;
- all required domains are READY.

### Volatile metadata rule

Run-specific ingestion fields are not business facts.

Orders staging includes `loaded_at`, but processed v1 drops it from:
- `fact_orders`
- `fact_order_items`

Run lineage remains in:
- `run_id`
- manifest metadata
- control state

Therefore identical RAW/business facts produce the same processed `build_fingerprint` across rebuilds.

This was verified with two consecutive real all-shop runs on September 2026 data.

### Drive namespace

Pre-production root:
`03_processed_data_v2`

Physical namespace target:
`<shop_key>/<YYYY-MM>/<domain>/...`

This period-first partition is intentional: one shop/month is the atomic rebuild scope.

`config/storage_registry.json` owns the storage root and write policy. It does not enumerate shops.

The legacy `03_processed_data` remains unchanged.


## Durable Drive writer authentication

The atomic Drive writer is implemented, but Google My Drive cannot accept file uploads owned by a service account because the service account has no personal storage quota.

Therefore:
- staging/raw read continues with service-account credentials;
- durable `03_processed_data_v2` writes use user OAuth;
- runtime secret name is `GOOGLE_DRIVE_OAUTH_JSON`;
- auth mode is declared in `config/storage_registry.json`.

The writer does not fall back silently from user OAuth to service account.

If OAuth is missing, the Drive persistence gate must fail clearly rather than creating a misleading partial success.

See `docs/processed-v2-drive-oauth-setup.md`.


## Durable persistence validation

User-OAuth Drive publishing is live and validated.

First publish:
- run `PUBLIC_SNAPSHOT_NOT_CONFIGURED`
- both enabled shops = `PUBLISHED`
- 15 files per partition
- uploaded bytes verified by MD5 + size

Immediate rerun with unchanged business facts:
- run `PUBLIC_SNAPSHOT_NOT_CONFIGURED`
- both enabled shops = `NOOP`
- 0 files uploaded
- same `build_fingerprint`

Direct Drive verification found exactly one active period partition per shop and no leftover temporary/backup folders.

This proves:
1. durable persistence;
2. shop/period isolation;
3. atomic publish;
4. idempotent rebuild;
5. control-run audit persistence.

Processed v2 remains PREPRODUCTION and is now actively consumed by the validated Semantic v2 → UI Payload → Native V2 chain. Production cutover remains a separate explicit gate.
