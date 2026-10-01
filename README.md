# Unipalm Business OS

Unipalm is an e-commerce **Business Operating System** being migrated from the original guarded single-shop production pipeline to a registry-driven **N-shop architecture**.

## Start here

A new engineer, AI agent or reviewer should read in this order:

1. `UNIPALM_PROJECT_CONSTITUTION.md` — non-negotiable project rules;
2. `docs/CURRENT_SYSTEM_STATE.md` — concise current validated state;
3. `docs/architecture/SYSTEM_OVERVIEW.md` — end-to-end architecture;
4. `config/system_module_registry.json` — machine-readable ownership/dependencies;
5. `docs/architecture/CHANGE_GUIDE.md` — where to make common changes;
6. the relevant `config/*_contract.json`, canonical domain doc, implementation and tests.

`docs/PROJECT_HANDOFF_MULTI_SHOP.md` remains the detailed milestone chronology and provenance record. It is not the fastest current-state onboarding entrypoint.

## Governance hierarchy

1. `UNIPALM_PROJECT_CONSTITUTION.md`
2. machine-readable contracts and architecture registry in `config/`
3. canonical architecture/domain documentation
4. implementation/workflows
5. tests and QA gates
6. dated audits/handoff/run evidence

A lower layer must not silently override a higher one.

## Canonical target flow

```text
RAW / Platform Exports
  -> Source Schema Drift Guard
  -> Shop-scoped Staging
  -> Shop-scoped Processed v2
  -> Durable Storage
  -> Semantic v2
  -> Historical + Business Context
  -> Product Intelligence / Ads Intelligence
  -> Context-qualified Diagnosis
  -> Diagnosis Persistence
  -> Smart Issue Candidate
  -> Human Review Registry
  -> Operator Review Workflow
  -> Canonical UI Payload
  -> Native V2 Destinations
  -> Human Operator
```

## Current boundary

Production UI and production Data Mart remain on the guarded legacy path. The N-shop chain above is validated in PREPRODUCTION; production cutover has **not** occurred.

PREPRODUCTION readiness, Shadow Mode readiness, a Smart Issue Candidate, a human-reviewed Smart Issue or an Operator Action/Review option does **not** authorize production/platform mutation.

Current production/legacy components are quarantined and must not be cloned as the architecture for a new shop.

## N-shop invariants

- concrete shop identities come from `config/shop_registry.json`;
- every shop-grain fact carries `shop_id`;
- listing identity is `shop_id + product_id`;
- generic core must not hard-code current Shop IDs/names or shop count;
- one shop's ingestion/QA is an independent failure domain;
- cross-shop ratios are recomputed from additive components, never averaged;
- a new shop should be onboarded primarily through registry/configuration and source availability.

## Configuration vs operational state

`config/` owns contracts, registries and curated evidence/configuration.

`ops/` is the canonical location for new mutable human/operator control state such as staging requests and Smart Issue review events.

The active legacy production state file remains at `automation/pipeline_state.json` until an approved production cutover migration.

## Architecture enforcement

Machine-readable module ownership lives in:

`config/system_module_registry.json`

Validate locally with:

```bash
python -m compileall -q automation
python automation/validate_public_repository.py
python automation/run_public_tests.py
```

GitHub runs `Public Repository Guard` for every pull request and every update to
`main`. The workflow is read-only, uses immutable action revisions, receives no
secrets and performs no deployment. It verifies that the repository still
descends from the audited public root, remains operations-empty and contains
only pseudonymized identifiers before running the public-compatible unit suite.

The private production workflows and production UI artifact are intentionally
absent from this repository. Their private-only validators are therefore not
part of the public CI suite; their absence is itself enforced by the public
repository validator.

## Production safety

The current legacy publisher remains single-shop-per-run and fails closed if it sees mixed-shop marts. This prevents accidental cross-shop corruption during migration.

The production dashboard payload in `index.html` remains encrypted with AES-256-GCM. Its access key is not stored in the repository.

Do not modify or retire the production UI, legacy Data Mart, legacy pipeline or recovery tooling until an explicit cutover milestone includes equivalent N-shop production persistence, rollback/recovery, production binding and human approval.

## Maintenance and cloning

For maintenance:
- `docs/architecture/MODULE_REGISTRY.md`
- `docs/architecture/CHANGE_GUIDE.md`
- `docs/architecture/FAILURE_AND_RECOVERY.md`
- `docs/architecture/AI_HANDOFF_GUIDE.md`

For future standardized instances:
- `docs/architecture/CLONE_AND_BOOTSTRAP.md`

A module is not considered truly complete only because it runs. It must also have clear ownership, dependencies, contract, failure boundary, tests, change entrypoints and recovery/compatibility guidance.
