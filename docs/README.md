# Unipalm Documentation Map

This directory contains three different kinds of information. They must not be treated as interchangeable.

## 1. Current system state

Start with `CURRENT_SYSTEM_STATE.md` when you need to know **what is active and validated now**.

It records:
- current development/production boundary;
- latest validated functional checkpoints;
- locked modules;
- known migration debt;
- the next architectural milestone.

Do not search the historical handoff chronicle first for current state.

## 2. Canonical architecture and maintenance guidance

Start with `architecture/SYSTEM_OVERVIEW.md` when you need to understand **how the system works**.

Canonical architecture set:
- `architecture/SYSTEM_OVERVIEW.md`
- `architecture/MODULE_REGISTRY.md`
- `architecture/CHANGE_GUIDE.md`
- `architecture/FAILURE_AND_RECOVERY.md`
- `architecture/AI_HANDOFF_GUIDE.md`
- `architecture/CLONE_AND_BOOTSTRAP.md`

Machine-readable ownership is in `../config/system_module_registry.json` and is validated by `../automation/validate_architecture.py`.

## 3. Domain design documents

Existing domain documents such as multi-shop staging, Semantic, Historical Intelligence, Product Intelligence, Ads Intelligence and Smart Issue documents remain canonical for the detailed behavior of their domains.

A domain document explains **why and how a module behaves**. The system architecture documents explain **how modules fit together**.

## 4. Audits and historical evidence

Files with audit/checkpoint/run history are evidence, not system law.

`PROJECT_HANDOFF_MULTI_SHOP.md` is retained as the detailed milestone chronology. Because it is intentionally long, it is no longer the fastest onboarding entrypoint.

Historical documents must not override:
1. `UNIPALM_PROJECT_CONSTITUTION.md`;
2. current machine-readable contracts;
3. `config/system_module_registry.json`;
4. current canonical architecture/domain docs.

## Documentation lifecycle

New documents should be classified before creation:
- **architecture** — stable system-wide ownership/maintenance rules;
- **domain** — detailed behavior of one business/technical capability;
- **runbook** — repeatable operator/recovery procedure;
- **audit/checkpoint** — dated evidence;
- **handoff/current state** — concise current operating state.

Do not create a second document that owns the same rule. Link to the existing owner instead.
