# Source Schema Drift Guard

Date: 2026-09-23

## Purpose

Protect registry-driven multi-shop ingestion from silent Shopee export-template changes.

The guard sits between RAW files and canonical staging normalization. It does not write the production Data Mart or UI.

## Core rule

Source-language labels are not the internal data contract.

Each source field resolves to a canonical field through a deterministic alias registry:

`config/source_schema_registry.json`

Examples:

```
Ads canonical field: gmv
Known aliases:
- GMV
- Doanh số

Ads canonical field: expense
Known aliases:
- Expense
- Chi phí
```

A label such as `Doanh thu` is **not** assumed to mean `gmv` until the business meaning is checked and that exact alias is explicitly approved.

No fuzzy matching is used for financial/business fields.

## Drift behavior

### Known alias

Example:

`GMV -> Doanh số`

when both are approved aliases for `gmv`.

Result:
- canonical mapping succeeds;
- data is normalized to the same internal field;
- an already baselined schema fingerprint is PASS;
- production eligibility still depends on all other staging QA.

### New extra column

Example:

Shopee adds `Campaign Objective`.

Result:
- existing required fields still resolve;
- new raw fingerprint is detected;
- unknown column is recorded;
- schema status = WARN;
- staging may continue;
- warning is written to `schema_drift_report.json`.

This avoids breaking ingestion just because Shopee added information we do not consume.

### Unknown rename of a required field

Example:

Current:
`GMV`

Shopee changes it to:
`Doanh thu`

and `Doanh thu` is not an approved alias.

Result:
- canonical `gmv` becomes missing;
- `Doanh thu` appears as an unknown column;
- schema status = FAIL;
- staging is blocked before production promotion;
- `staging_error.json` preserves the blocking schema audit.

The system must never infer that the two metrics are equivalent based on wording.

### Removed required field

Result:
- FAIL;
- staging blocked.

### Column reorder

Header fingerprints are order-independent.

Pure column reordering does not create schema drift.

### Header capitalization

Exact source alias matching is preferred.

A case-insensitive fallback is allowed only when the result is unambiguous.

This matters because Shopee Orders currently contains two different financial columns whose Vietnamese labels differ only by capitalization:

- `Tổng số tiền Người mua thanh toán`
- `Tổng số tiền người mua thanh toán`

They must remain separate canonical fields.

## Contracts currently guarded

- Listing Catalog machine fields
- Product Performance
- Business Insights daily
- Business Insights traffic
- Orders
- Ads metadata
- Ads rows

Contracts are shop-neutral and locale-neutral.

A shop does not have a configured language. Each file is recognized independently.

## Schema fingerprints

A fingerprint is the SHA-256 hash of the normalized set of raw headers.

Properties:
- header order does not matter;
- whitespace normalization does not create false drift;
- raw label changes do change the fingerprint;
- added/removed columns change the fingerprint.

The registry contains the currently observed and reviewed EN/VI fingerprints from September 2026.

Current baseline validation:
- SYT+: 48/48 source-schema audits PASS
- Mall: 52/52 source-schema audits PASS
- unknown columns: 0 after known-unused columns were baselined
- new fingerprints: 0
- both shops full staging QA: PASS

Historical/unused Shopee fields are recorded as `known_ignored_headers`; they remain part of the fingerprint but do not produce recurring false warnings.

## Runtime artifacts

Each successful shop staging run produces:

- `staging_qa_report.json`
- `schema_drift_report.json`

`schema_drift_report.json` contains:
- contract name/version;
- source file;
- fingerprint;
- fingerprint status;
- resolved canonical fields;
- missing required/optional fields;
- unknown columns;
- warnings/failures.

The multi-shop run summary also exposes:
- `schema_status`
- `schema_warn_count`
- `schema_new_fingerprint_count`
- `schema_unknown_column_groups`

## Review workflow for a future Shopee change

When schema status is WARN or FAIL:

1. Inspect the source file and `schema_drift_report.json` / `staging_error.json`.
2. Determine whether the change is merely structural or changes metric semantics.
3. For a new optional column:
   - leave it unused, or define a canonical field if needed;
   - review and baseline the new fingerprint.
4. For a renamed existing metric:
   - verify Shopee's actual definition;
   - only then add the exact label as an alias.
5. Rerun staging.
6. Add the newly reviewed fingerprint only after staging/reconciliation succeeds.

Do not approve a fingerprint merely to make CI green.

## Safety boundary

A schema FAIL can never become `production_write_allowed=true`.

Schema WARN is intentionally non-blocking when all required semantics remain intact, but it is visible in artifacts and the run summary.

The production Data Mart and UI remain unchanged during this milestone.
