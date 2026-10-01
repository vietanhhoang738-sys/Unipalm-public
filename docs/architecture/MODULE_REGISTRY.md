# Module Registry & Ownership Model

The canonical machine-readable registry is `config/system_module_registry.json`.

This document explains how to use it. Do not maintain a second manual dependency graph here.

## Every module must declare

- **id** — stable logical module identifier;
- **lane** — `core` or `legacy`;
- **layer** — architecture layer;
- **status** — lifecycle state such as `LOCKED_V1` or `ACTIVE_LEGACY`;
- **replication_role** — whether the module is reusable core, instance config, operator state or non-clonable legacy;
- **dependencies** — direct logical upstream modules;
- **implementation_paths** — code owned by the module;
- **runner_paths** — executable entrypoints;
- **contract_paths** — normative machine contracts;
- **config_paths** — non-contract configuration/registries;
- **doc_paths** — canonical design/rationale;
- **test_paths** — regression protection;
- **failure_boundary** — what fails and what must remain untouched;
- **change_entrypoints** — first files to inspect/edit;
- **do_not_change** — common boundary violations to avoid.

## Status semantics

### `LOCKED_V1`

The declared v1 scope is complete. Downstream convenience is not a reason to rewrite it. Changes require one of:
- a bug fix that preserves the existing contract;
- a compatibility-preserving internal refactor with equivalence proof;
- an explicit new contract/version.

### `ACTIVE_LEGACY`

Still required for production/recovery continuity but not a template for new development. Do not clone or deepen this dependency unless needed for safety before cutover.

### `PREPRODUCTION_ACTIVE`

Actively evolving capability whose contract has not yet been locked.

### `DEFERRED_BY_DESIGN`

Intentionally postponed because another milestone owns the prerequisite. This is not an incomplete hidden task.

## Dependency direction

Core dependencies must point upstream or laterally only where explicitly justified. The architecture validator blocks a registered core module from depending on a later layer.

This prevents circular architecture such as:

```text
Semantic -> UI -> Semantic
```

or:

```text
Candidate -> Registry -> Candidate
```

## Registering a new module

Before a new domain/capability is considered architecturally complete:
1. choose its owning layer;
2. define direct dependencies only;
3. create/identify its contract;
4. register implementation, tests and docs;
5. define its failure boundary;
6. define change entrypoints;
7. run `python automation/validate_architecture.py`;
8. run unit/integration/staging validation as appropriate.

A new page or feature must not become an unregistered mini-system.

## Refactoring a locked module

For a structural split, keep the existing public module/runner as a compatibility facade first.

Example target pattern:

```text
historical_intelligence.py  # stable facade / public contract
    -> history_inventory.py
    -> comparator.py
    -> context_baseline.py
    -> anomaly.py
```

The split is accepted only after:
- identical contract behavior;
- regression suite PASS;
- fingerprint/output equivalence where deterministic identity is part of the contract;
- full staging PASS when the module is in the production-like chain.

Do not combine path moves, business-rule changes and contract changes in one refactor batch.
