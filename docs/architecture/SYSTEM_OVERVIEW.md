# Unipalm System Overview

Status: **Canonical architecture overview — PREPRODUCTION migration**

## 1. What Unipalm is

Unipalm is an e-commerce Business Operating System. It converts fragmented source exports into trusted business facts, context-aware intelligence and human-reviewed operating decisions.

The project deliberately separates facts, interpretation, issue state, operator state and presentation so that one layer cannot silently redefine another.

## 2. Architecture map

```text
                    GOVERNANCE
        Constitution + contracts + module registry
                         |
                         v
INSTANCE CONFIG -> SOURCE BOUNDARY -> STAGING -> PROCESSED -> DURABLE STORAGE
 shop registry      schema guard       |          |              |
      |                                 +----------+--------------+
      |                                                    |
      +----------------------------------------------------v
                                                        SEMANTIC
                                                           |
                        +----------------------------------+------------------+
                        |                                                     |
                        v                                                     v
                 BUSINESS CONTEXT                                   HISTORICAL INTELLIGENCE
                        |                                                     |
                        +------------------+------------------+---------------+
                                           |                  |
                                           v                  v
                                 PRODUCT INTELLIGENCE    ADS INTELLIGENCE
                                                              |
                                                              v
                                                   CONTEXT QUALIFICATION
                                                              |
                                                              v
                                                    DYNAMIC DIAGNOSIS
                                                              |
                                                              v
                                              DIAGNOSIS PERSISTENCE
                                                              |
                                                              v
                                                SMART ISSUE CANDIDATE
                                                              |
                                                              v
                                          HUMAN REVIEW / ISSUE REGISTRY
                                                              |
                                                              v
                                           OPERATOR REVIEW WORKFLOW
                                                              |
                         +------------------------------------+----------------+
                         |                                                     |
                         v                                                     v
                 CANONICAL UI PAYLOAD                                   OPERATOR STATE
                         |
                         v
                    NATIVE V2 UI
                         |
                         v
                  HUMAN OPERATOR
```

The active legacy production lane exists beside this PREPRODUCTION core and is quarantined rather than treated as a reusable architecture.

## 3. Boundary rules

### Upstream ownership

A downstream module consumes an upstream contract. It may not rewrite upstream facts because its own UI or feature is inconvenient.

Example:
- presentation may rename a label;
- presentation may not redefine ROAS;
- Registry may consume a Smart Issue Candidate;
- Registry may not lower Candidate thresholds to create more issues.

### Contract evolution

A locked contract is not edited casually in place. When semantic behavior changes materially, create a deliberate new contract version or an explicit compatible migration.

### Failure isolation

Each layer should fail at its own boundary:

```text
Upstream PASS -> Module FAIL -> downstream BLOCKED
```

not:

```text
Module FAIL -> silently mutate upstream -> continue with plausible output
```

A failure must not corrupt a previously valid upstream artifact.

### Production isolation

PREPRODUCTION validation never means permission to mutate production. Production activation is a separate human-approved milestone.

## 4. Sources of truth

| Concern | Source of truth |
|---|---|
| Project-wide principles | `UNIPALM_PROJECT_CONSTITUTION.md` |
| Module ownership/dependencies | `config/system_module_registry.json` |
| Shop identity | `config/shop_registry.json` |
| Source schemas | `config/source_schema_registry.json` |
| Domain behavior | relevant `config/*_contract.json` |
| Storage namespaces | `config/storage_registry.json` |
| Business Context evidence | `config/business_context_calendar.json` |
| Mutable operator state | `ops/` |
| Current validated state | `docs/CURRENT_SYSTEM_STATE.md` |
| Domain rationale | relevant canonical document in `docs/` |
| Executable behavior | `automation/` + tests |

No historical audit/run note supersedes the current contract or module registry.

## 5. Core, instance and legacy separation

### Core reusable logic

Reusable across another seller/brand when the same platform/domain contract applies:
- schema guard;
- staging engine;
- Processed/Semantic logic;
- persistence writers;
- historical/context framework;
- intelligence/diagnosis framework;
- Smart Issue lifecycle framework;
- canonical payload and shared presentation foundation.

### Instance-specific configuration

Expected to change when cloning an instance:
- Shop Registry;
- raw/storage resource IDs;
- credentials/secrets;
- platform evidence/calendar;
- branding/presentation values explicitly designed as instance config;
- optional policy thresholds only where the owning contract permits configuration.

### Legacy

Legacy production exists for continuity, not as the template for future shops or cloned deployments.

## 6. Validation model

A meaningful change should pass the relevant sequence:

```text
compile/static checks
  -> architecture registry validation
  -> module unit tests
  -> compatibility/regression tests
  -> synthetic edge cases
  -> full PREPRODUCTION staging where required
  -> artifact/fingerprint audit
  -> documentation checkpoint
```

Only then should a module/milestone be marked `LOCKED`.

## 7. Completion definition

A module reaches 100% only when both are true:

**Functional DONE**
- implementation complete for its declared version;
- contracts/tests pass;
- real-data or relevant integration validation passes.

**Maintainability DONE**
- owner and dependencies registered;
- source of truth clear;
- failure boundary documented;
- change entrypoints documented;
- regression tests identified;
- rollback/migration impact understood;
- another engineer/AI can locate and modify it without relying on undocumented project memory.

## 8. Physical reorganization policy

The current repo already contains validated paths referenced by workflows, docs and tests. Therefore logical standardization precedes physical file moves.

Do not perform a mass folder rewrite merely for aesthetics. Physical moves should be one dependency-scoped migration at a time, with compatibility tests and a full staging checkpoint when runtime paths change.
