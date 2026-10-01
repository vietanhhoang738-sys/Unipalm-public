# Legacy Upstream Dependency Audit — SYT+ Raw Migration

Date: 2026-09-23

## Goal

Move the original shop RAW domains from the flat `01_raw_data` root into its own shop root without breaking the current production Apps Script pipelines.

Target root has been created:

`01_raw_data/unipalm_syt_plus`

Drive folder ID:

`PUBLIC_RESOURCE_SHOP_01`

It is deliberately empty until cutover.

## Cutover rule

Do not move one core RAW domain at a time.

The registry-driven staging resolver selects one root that contains all required core domains:
- orders
- ads
- product_performance
- business_insights

Therefore the physical migration unit is **all core RAW domains together**.

Moving only Orders would preserve the Orders folder ID for Apps Script, but it would make the legacy root incomplete while the new root is also incomplete.

## Dependency status

### Orders

Status: `VERIFIED_FOLDER_ID`

Evidence from legacy Apps Script `01_Config.txt`:

- `RAW_ORDERS_ROOT_FOLDER_ID = 1eqK0gfnlclhaisLDplzsWxqC-znxsIyN`
- `PROCESSED_ORDERS_ROOT_FOLDER_ID = 1ayBlA92ue2QX8r_qkP9UEFQoYJ1WImNO`

Google Drive preserves a folder's ID when its parent changes.

Operational conclusion:
- Orders is technically move-safe from the verified config perspective;
- it still waits for atomic cutover with the other core domains.

### Ads

Status: `UNVERIFIED_LEGACY_CONFIG`

No reliable source copy has yet proven whether the legacy processor resolves RAW by:
- fixed folder ID; or
- traversal/name under `01_raw_data`.

Physical move remains blocked.

### Product Performance

Status: `UNVERIFIED_LEGACY_CONFIG`

Physical move remains blocked.

### Business Insights

Status: `UNVERIFIED_LEGACY_CONFIG`

Physical move remains blocked.

### Returns & Refunds

Status: `UNVERIFIED_LEGACY_CONFIG`

This domain is not required by staging v1 core-root selection, but it is still a production legacy domain and should migrate with the shop root only after its legacy dependency is verified or retired.

### Listing Catalog

Status: `REGISTRY_DRIVEN_ONLY`

This domain was added for the new multi-shop architecture and is not part of the old Apps Script production stack.

Do not move it ahead of the core domains because the current fallback root needs to keep seeing the latest authoritative listing snapshot until raw-root cutover.

## Machine-readable source

`config/legacy_pipeline_dependencies.json`

CI test:

`automation/tests/test_legacy_dependency_inventory.py`

Safety rules enforced:
- all core domains must be classified;
- unverified dependencies cannot be marked move-ready;
- Orders remains `WAIT_ATOMIC_CUTOVER`;
- migration root must be explicitly configured.

## Cleanup performed

The obsolete `orders_pipeline_controller` spreadsheet in `00_documentation` was archived as:

`orders_pipeline_controller_LEGACY_NOT_STARTED`

It was a stale validate/test controller:
- last modified 2026-08-08;
- `status=NOT_STARTED`;
- pointed to an old July output;
- no active repo/library dependency was found.

Current production Orders control remains `orders_pipeline_control` under the active processed Orders domain.

## Recommended route

Do not spend effort cloning/refactoring all historical Apps Script processors for N shops.

Preferred route:
1. keep legacy SYT+ production running unchanged;
2. finish registry-driven Python staging equivalence;
3. obtain full staging QA for current shops;
4. either verify remaining legacy folder dependencies and perform one atomic folder move, or retire legacy upstream processors before moving;
5. all future shops use registry-driven ingestion rather than new Apps Script copies.

No production Data Mart or UI is changed by this migration preparation.


## Active production state outside the main system folder

`unipalm_pipeline_state_v1` is **not redundant**.

It is actively updated by the current production automation and contains:
- scheduler controls;
- source manifest fingerprints;
- production reliable window;
- QA/publish gate state;
- publish/run history;
- current production build metadata.

Latest observed run history extends through 2026-09-22.

Therefore:
- do not archive or move it during the staging migration;
- classify it as `ACTIVE_LEGACY_PRODUCTION_STATE`;
- future N-shop control-plane work should replace its single-shop source manifest/state semantics before retirement.

The root `04_reports` folder is currently empty. It has no active artifact dependency and may remain as a reserved reporting namespace; no migration decision depends on it.
