# System Cleanup Audit — 2026-09-24

Status: **ACTIVE CLEANUP BASELINE**

This audit records what was removed, what was retained, and why. Cleanup is dependency-driven: a file/mart is removed only when its information is redundant or it has no active runtime/workflow/safety role.

## Accepted principles

- Do not delete production/legacy code merely because its name is old.
- Remove duplicated facts and dead adapters before adding new abstractions.
- Prefer one authoritative persisted grain; derive deterministic rollups when needed.
- UI must not render unavailable capabilities as empty/degraded operator surfaces.
- Historical provenance belongs in compact handoff/audit notes, not parallel runtime paths.

## Removed / simplified

### UI Payload / Compare
- removed duplicate per-pair V2 payload copies; Compare now consumes horizon-only pair data;
- removed unused Compare daily trimming helper;
- unavailable historical issue capability no longer renders a useless `Cần xử lý` card;
- when issue intelligence is unavailable, the GMV-driver card expands to use the available space;
- Business Pulse no longer advertises unavailable historical intelligence as an operator insight.

### Semantic layer
Removed redundant persisted marts:
- `dm_shop_benchmark_monthly`
- `dm_shop_monthly`
- `dm_traffic_source_monthly`

Reason:
- deterministic from authoritative daily facts;
- no active downstream consumer;
- duplicated contract, QA, Drive storage and maintenance surface.

Semantic contract v1.2 currently persists:
- `dim_shop`
- `dm_shop_daily`
- `dm_commercial_stage_daily`
- `dm_ads_daily`
- `dm_ads_product_daily`
- `dm_product_monthly`
- `dm_traffic_source_daily`
- `dm_order_quality_daily`

The semantic loader also stopped loading unused order-item facts.

### Staging
- removed dead private helper `_find_header()`; the active BI normalizer implements its required last-matching-header logic directly.

### Command Center compatibility
- removed unused top-level compatibility placeholders `commandCenter.smartIssues`, `commandCenter.productSignals` and empty `commandCenter.featureHealth`;
- retained period-level `smartIssues.status` because it is an active control signal for hiding unavailable issue intelligence.

### Legacy production source processor
- removed unused helpers `get_headers()` and `group_from_name()` after confirming no production runner, recovery module or test reference remained.
- production behavior and publisher boundaries are unchanged.

### Documentation
- removed superseded standalone `docs/multi-shop-ui-native-v2.md`;
- compacted superseded UI milestone history in the project handoff;
- refreshed stale “future/next milestone” wording in ingestion, processed, semantic, payload and automation docs.

## Explicitly retained

### Legacy production path
Keep until explicit production cutover:
- `.github/workflows/unipalm-pipeline.yml`
- `automation/run_pipeline.py`
- `automation/source_processor.py`
- `automation/frozen_v14_template.html`
- `automation/modules/ui_artifact.py`
- `automation/modules/product_ranking.py`

These remain active production dependencies.

### Recovery / migration safety
Keep:
- `.github/workflows/product-ads-mart-maintenance.yml`
- `automation/backfill_product_ads.py`
- `config/legacy_pipeline_dependencies.json`
- `automation/tests/test_legacy_dependency_inventory.py`

These provide recovery or migration guardrails and are not dead code.

### Semantic marts not currently consumed by UI, but retained
- `dm_commercial_stage_daily`: preserves stage-specific Visits/Buyers and placed/confirmed/paid detail not fully represented by `dm_shop_daily`.
- `dm_ads_daily`: preserves ATC, Units, CPC, CPM, CPA and ACOS not present in `dm_shop_daily`.
- `dm_order_quality_daily`: preserves Orders-source total orders and quality rates with a distinct source denominator.

No-current-UI-consumer is not sufficient reason to delete non-duplicated business information.

### UI compatibility layer
Keep `automation/modules/ui_v2_compat.py`.
It is actively consumed by the Native V2 builder and provides safe adaptation of the read-only production V2 renderer.

## Real cleanup checkpoint

GitHub Actions run #244 / `35992225052`: **PASS**

Semantic contract:
- version `1.2`
- 8 persisted marts
- 17 semantic QA checks PASS
- 0 failures
- semantic fingerprint: `fb862a21b281d3b33611e35c060d5dfbbe19a3bdbb455fc9f9c034b755a3c162`

Drive publish:
- status `PUBLISHED`
- previous semantic partition replaced atomically
- 10 files uploaded = 8 marts + manifest + QA
- no removed monthly mart remains in the published partition

UI Payload:
- contract `1.2`
- fingerprint `58f054911b139278ee2cf0350e76746bb77dc3e8f22c4a578721b0ca03af4f78`

Native V2:
- patch `native-sidebar-rail-v13`
- fingerprint `53c3ebae2160567f6ba6c4d9a3983eb7b8d4ef49127fb08698e3d122ccaeb44c`
- 30/30 QA checks PASS
- production V2 source SHA unchanged: `9540f23b4d9537441e3bd4cdeafd15747ab4280a87a0130d223984009d99c952`

Production safety flags remain false for Data Mart writes, production V2 modification, production index modification and deployment.

## Deferred cleanup

Do not remove the remaining legacy production path until a separately approved production cutover plan has:
1. equivalent multi-shop production persistence;
2. rollback/recovery procedure;
3. production payload/UI binding;
4. production deployment validation;
5. explicit user approval.

Future cleanup should continue in small dependency-scoped batches rather than large rewrites.
