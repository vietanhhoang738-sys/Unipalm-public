# AI / Engineer Handoff Guide

This guide is for a new AI agent or engineer with repository access and no prior conversation context.

## First 15 minutes

Read in order:
1. `UNIPALM_PROJECT_CONSTITUTION.md` — non-negotiable rules;
2. `README.md` — repo boundary and production status;
3. `docs/CURRENT_SYSTEM_STATE.md` — what is validated now;
4. `docs/architecture/SYSTEM_OVERVIEW.md` — system map;
5. `config/system_module_registry.json` — machine-readable owners/dependencies;
6. the relevant module contract;
7. the relevant canonical domain doc;
8. implementation + tests registered for that module.

Do not begin by reading `PROJECT_HANDOFF_MULTI_SHOP.md` from top to bottom. It is a detailed historical chronology, useful after current ownership is clear.

## Before changing anything

Answer these questions:
- Which module owns this behavior?
- Is the module `LOCKED_V1`, active legacy, or still evolving?
- What is its direct upstream input?
- What directly consumes its output?
- Which contract governs the behavior?
- What is its failure boundary?
- Which fingerprint/checkpoint should remain unchanged?
- Is production permission involved?

If you cannot answer these, do not edit yet.

## Mandatory local/CI checks

Structural validation:

```bash
python -m compileall -q automation
python automation/validate_architecture.py
```

Full repository unit tests:

```bash
cd automation
python -m unittest discover -s tests -p "test_*.py" -v
```

A change in the PREPRODUCTION chain may also require full GitHub staging validation and artifact/fingerprint review.

## Safety rules

Never:
- hard-code current shop identities in generic core logic;
- average ratios across shops when additive numerators/denominators exist;
- turn association/contribution into causal language;
- invent a fallback when the contract requires `UNKNOWN` or `INSUFFICIENT_*`;
- treat PREPRODUCTION readiness as production authorization;
- let UI redefine business facts;
- let presentation write operator review state directly;
- change a locked upstream module solely because a downstream feature is inconvenient;
- clone the legacy production stack for a new shop.

## How to extend the system

Prefer:
1. consume an existing stable contract;
2. add a new downstream sidecar/module;
3. register it in `system_module_registry.json`;
4. add a focused contract if behavior is new;
5. add tests and docs;
6. prove compatibility;
7. stage it;
8. only then consider changing an upstream contract.

## How to refactor

For a large locked module:
- keep its current import/API facade;
- extract one responsibility at a time;
- add equivalence tests;
- avoid changing business rules in the same commit/batch;
- compare deterministic outputs/fingerprints;
- full-stage before declaring the split complete.

## When you discover stale documentation

Classify it before editing:
- current state -> update `CURRENT_SYSTEM_STATE.md`;
- stable project law -> Constitution / architecture docs;
- domain behavior -> canonical domain doc;
- historical evidence -> leave history intact and add a newer checkpoint/reference.

Do not rewrite history to look current.

## Production changes

The current production path is still legacy and guarded. Any production cutover, deployment, platform mutation or retirement of legacy recovery requires explicit human approval and a dedicated cutover/rollback milestone.

## Definition of a successful handoff

A new maintainer should be able to state:
- where data enters;
- where each business fact becomes canonical;
- which module owns each decision layer;
- what is locked;
- how failure propagates;
- where mutable operator state lives;
- how to validate a change;
- how to recover/rollback;
- which parts are reusable when cloning another instance.
