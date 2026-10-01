# Unipalm Automation

`automation/` contains both the registry-driven N-shop PREPRODUCTION core and the quarantined legacy production path. They are intentionally separate until an explicit production cutover.

Canonical ownership/dependencies are machine-readable in `../config/system_module_registry.json`.

## Registry-driven N-shop core

Current PREPRODUCTION flow:

```text
Shop Registry / Source Schema Guard
  -> Multi-Shop Staging
  -> Processed v2
  -> durable Processed Drive
  -> Semantic v2
  -> durable Semantic Drive
  -> Business Context
  -> Historical Intelligence
  -> Product Intelligence
  -> Ads Intelligence + Context Qualification
  -> Dynamic Diagnosis
  -> Diagnosis Persistence
  -> Smart Issue Candidate
  -> Human Review Registry
  -> Operator Review Workflow
  -> canonical UI Payload
  -> Native V2
```

Key runners:
- `multi_shop_staging_runner.py`
- `multi_shop_processed_runner.py`
- `multi_shop_drive_writer.py`
- `multi_shop_semantic_runner.py`
- `multi_shop_semantic_drive_writer.py`
- `multi_shop_context_runner.py`
- `multi_shop_history_runner.py`
- `multi_shop_product_intelligence_runner.py`
- `multi_shop_ads_intelligence_runner.py`
- `multi_shop_payload_runner.py`
- `multi_shop_native_v2_runner.py`

Human Smart Issue review command:
- `ads_smart_issue_review_command.py`

The review command defaults to the canonical mutable operator ledger at:
- `../ops/ads_smart_issue_review_events.json`

## Core properties

- arbitrary enabled shop count;
- concrete identities only through Shop Registry;
- every shop-grain business fact is shop-scoped;
- per-shop staging/Processed failure isolation;
- all-shop Semantic portfolio rules remain explicit;
- deterministic fingerprints and idempotent/NOOP persistence where applicable;
- evidence/context gates before intelligence claims;
- Smart Issue creation/state transition requires explicit human review;
- no automatic production/platform mutation;
- PREPRODUCTION writers are isolated from production roots.

## Current legacy production path

Active for production continuity:
- `source_processor.py`
- `run_pipeline.py`
- `backfill_product_ads.py` (recovery only)
- `frozen_v14_template.html`
- `modules/ui_artifact.py`
- `pipeline_state.json`

These components are deliberately guarded single-shop/legacy surfaces and have `DO_NOT_CLONE` roles in the system module registry.

Do not generalize the future system by cloning this legacy stack per shop.

## Architecture validation

Run structural validation from repository root:

```bash
python -m compileall -q automation
python automation/validate_architecture.py
```

Run full unit suite:

```bash
cd automation
python -m unittest discover -s tests -p "test_*.py" -v
```

GitHub workflows:
- `Architecture & Contract Guard` — broad compile/architecture/unit-test coverage for automation/config/ops changes;
- `Multi-Shop Core CI & Staging QA` — PREPRODUCTION end-to-end staging/evidence chain;
- `Unipalm Production Pipeline` — active guarded legacy production;
- Product Ads maintenance workflow — legacy production recovery only.

## Storage/authentication

RAW/staging reads use the configured service-account path where applicable.

Processed/Semantic durable PREPRODUCTION publication uses OAuth through:
- `GOOGLE_DRIVE_OAUTH_JSON`
- `modules/drive_auth.py`

Storage namespaces/policies are in `../config/storage_registry.json`.

Never embed credentials in code or repository files.

## Large-module refactor policy

Some validated modules are intentionally still physically large. Do not split them in the same batch as business-rule changes.

For a locked-module split:
1. keep the current module as the public compatibility facade;
2. extract one responsibility at a time;
3. preserve contracts/output/fingerprints where applicable;
4. run equivalence/regression tests;
5. full-stage before marking the structural refactor complete.

Current high-value refactor candidates are listed in `../config/system_module_registry.json`.

## Further reading

- `../docs/CURRENT_SYSTEM_STATE.md`
- `../docs/architecture/SYSTEM_OVERVIEW.md`
- `../docs/architecture/CHANGE_GUIDE.md`
- `../docs/architecture/FAILURE_AND_RECOVERY.md`
- `../docs/architecture/AI_HANDOFF_GUIDE.md`
