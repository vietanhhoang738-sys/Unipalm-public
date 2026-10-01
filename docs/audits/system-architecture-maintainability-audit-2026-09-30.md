# System Architecture & Maintainability Audit — 2026-09-30

Status: **VALIDATED / LOCKED v1**  
Scope: repository-wide architecture, maintainability, handoff, cloneability and anti-chain-failure foundations.  
Production activation: **NOT INCLUDED / REMAINS DISABLED**.

## Executive conclusion

The project did **not** require a rewrite. Its core N-shop/Data/Semantic/Intelligence architecture was already strong and fail-closed. The main standardization risk was around repository governance and maintainability: flat/fragmented docs, mixed config vs mutable state, stale/manual CI coverage, large validated modules, legacy/current code sharing one physical tree, and brittle chained Native V2 runtime-string patches.

The chosen solution was deliberately low-risk:

1. standardize logical ownership first;
2. make ownership/dependencies machine-readable and machine-validated;
3. separate new mutable operator state from normative contracts/config;
4. create a concise onboarding/maintenance documentation spine;
5. add a broad architecture/contract CI guard;
6. preserve locked business contracts/fingerprints;
7. defer risky physical moves/splits to isolated compatibility migrations.

This avoids the exact failure mode the project is trying to prevent: a large aesthetic refactor creating a cross-system regression.

## Audit findings and decisions

### 1. Strong existing foundations — retained

Already healthy:
- registry-driven N-shop identity;
- shop-scoped grains and independent staging failure domains;
- schema drift guard;
- Processed/Semantic contracts and deterministic publication;
- evidence/context-aware Intelligence;
- fail-closed diagnosis/persistence/candidate/issue gates;
- human-reviewed Smart Issue lifecycle;
- locked fingerprints and PREPRODUCTION safety;
- explicit legacy production isolation.

Decision: preserve these contracts rather than reorganize them for aesthetics.

### 2. Repository ownership was understandable to the original project context but not sufficiently machine-readable

Risk: a new maintainer could find the code but still have to infer which module owns a rule, which downstream consumer depends on it, or which files must not be changed.

Action:
- added `config/system_module_registry.json`;
- added `automation/validate_architecture.py`;
- added `automation/tests/test_system_architecture_registry.py`.

The registry records module layer, lane, status, dependencies, implementation, runners, contracts/config, docs, tests, failure boundary, change entrypoints, replication role and common prohibited changes.

### 3. CI coverage depended on manually maintained file lists

Risk: a new module/contract could be added without being explicitly listed in the old workflow's compile/path filters.

Action:
- added `.github/workflows/architecture-contract-guard.yml`;
- guard covers broad `automation/**`, `config/**`, `ops/**` and canonical governance docs;
- compiles the full automation surface via `compileall`;
- runs the architecture validator;
- runs the full unit-test suite.

Validation:
- Architecture & Contract Guard run **#16**, run id `36691439485`, head `346e37d7dbaa57cb0dfe567e17c76e860a04070b`: **SUCCESS**.

The existing full staging workflow is retained for end-to-end behavior/evidence. The two workflows now have distinct responsibilities.

### 4. Mutable operator state was mixed with normative configuration

Risk: `config/` could become a mixture of project law and frequently mutated state, making ownership/cloneability unclear.

Action:
- created canonical `ops/` boundary;
- moved active Smart Issue human-review ledger source to `ops/ads_smart_issue_review_events.json`;
- updated Ads runner/review command defaults;
- removed deprecated `config/ads_smart_issue_review_events.json`;
- added `ops/README.md` and `config/README.md`.

Intentional compatibility debt:
- `.github/workflows/multi-shop-staging.yml` still reads `config/staging_request.json` for push-triggered staging;
- `ops/staging_request.json` is now the canonical target location, while the config copy remains a temporary byte-equivalent compatibility mirror;
- this duplicate is to be removed in a dedicated staging-orchestration migration, not mixed into this architecture batch.

### 5. Documentation had rich evidence but a weak onboarding spine

Risk: `docs/PROJECT_HANDOFF_MULTI_SHOP.md` had become a large chronology. It remained valuable evidence but was inefficient as the first source for a new maintainer.

Action:
- added `docs/CURRENT_SYSTEM_STATE.md`;
- added `docs/README.md` taxonomy;
- added canonical architecture set:
  - `docs/architecture/SYSTEM_OVERVIEW.md`
  - `docs/architecture/MODULE_REGISTRY.md`
  - `docs/architecture/CHANGE_GUIDE.md`
  - `docs/architecture/FAILURE_AND_RECOVERY.md`
  - `docs/architecture/AI_HANDOFF_GUIDE.md`
  - `docs/architecture/CLONE_AND_BOOTSTRAP.md`
- updated root `README.md` and `automation/README.md`.

A new engineer/AI now has a short deterministic reading order instead of needing private conversation context.

### 6. Constitution needed explicit maintainability/replication law

Action:
- ratified `UNIPALM_PROJECT_CONSTITUTION.md` **v0.2**;
- added Functional DONE + Maintainability DONE;
- added machine-readable ownership, failure isolation, immutable-upstream discipline, operational-state separation and standardized replication rules.

No evidence, Intelligence or production-safety rule was relaxed.

### 7. Physical repo structure is still flatter/larger than the desired final form

High-value refactor candidates:
- `automation/modules/historical_intelligence.py` — large multi-responsibility validated facade;
- `automation/modules/semantic_payload.py` — large presentation-adapter surface;
- `.github/workflows/multi-shop-staging.yml` — large orchestration workflow;
- chained Native V2 Ads presentation wrappers — exact runtime-string anchors are brittle.

Decision: **do not mass-move/split now**. These are locked/validated paths and a broad move could create chain failure. Future splits must preserve a stable public facade and prove behavioral/fingerprint equivalence.

The first recommended structural refactor is **Native V2 Extension Composition v1**, because the exact-string wrapper chain has already produced a real integration failure and the next planned Review Console would otherwise deepen that coupling.

### 8. Legacy and cloneability

Active legacy production remains required for rollback/continuity and is explicitly `DO_NOT_CLONE`.

Current cloneability gaps still include:
- production workflow/environment containing current-instance resource assumptions;
- legacy production/control state still single-shop oriented;
- final N-shop production cutover not completed;
- staging-request compatibility mirror not removed;
- some large modules not yet physically decomposed;
- branch `multi-shop-catalog-resolver` is not protected by GitHub branch protection.

These are explicit roadmap items, not hidden architectural assumptions.

## End-to-end validation

Full PREPRODUCTION staging:
- workflow: `Multi-Shop Core CI & Staging QA`;
- run **#558**;
- run id `36691022729`;
- head `5e5f86c8ff295bf1db240686c8838391e7c7d066`;
- conclusion: **SUCCESS**;
- all normal stages from read-only ingestion through Native V2: **PASS**;
- final fail-closed production gate: no production promotion performed.

### Locked Ads/Issue fingerprints remained identical

- Base Ads: `a1faa4cf2e4c9403452fb47d62504a516b4a8d2eaedff7ebe78dcf5a2220f79b`
- Context Qualification: `23cb81876a955fca122ab6d2ad55711682972a6ddc50afc20de9ec77c5157dfc`
- Business Context source: `d4fef77fe3f18d2e9b91ea611dbcd755372fff1e9fc5e29739fb851b9a0a8cd0`
- Dynamic Diagnosis: `4daab89d26c877e858c39b462b6599234b14c39a18e37f5ce373b9e1aae9b4a2`
- Diagnosis Persistence: `4b4cf0fb8fea41db6e1b7c6e470347bc0c212b554774ec6068e743359513dabd`
- Smart Issue Candidate: `2373ef01716950719a6bc16be046e7bb456cde74d5f4b436c05cd5605a6a05e7`
- Smart Issue Registry / final Ads: `234cfc09d01a2418384bf23ea7dabbaf641f92e26cf8d2765ac32e12f50b1448`
- Operator Review Workflow: `314921dc35393c169454559b7378effbfb1d2f0c35b2b5b82f663bcc97c4bc9a`

This proves the maintainability/state-boundary changes did not redefine locked Ads/Issue behavior.

### Semantic / Native validation

- September Semantic fingerprint remained `38e12e9552fd81571b85e37f977bfbeb8feda9a1d3b7e301663f56fa28cad7f6`.
- Native V2 QA: **33/33 PASS**, failed checks 0.
- Native V2 build fingerprint for run #558: `3996ca91b9ab757c82677a03d6babe09cab551821aa4d0372d7662771f9e773b`.
- Smart Issue Registry QA: **18 checks / 0 failed**.
- current real review state remained empty: 0 current candidates, 0 issues; workflow `READY_EMPTY`.
- automatic promotion, transition, resolution, alerts, actions and production activation remained disabled.

## Locked outcome

**System Architecture & Maintainability Foundation v1 is VALIDATED / LOCKED.**

From this checkpoint forward:
- a new module/domain should be registered in `system_module_registry.json`;
- a locked module is not rewritten for downstream convenience;
- new mutable operator state belongs under `ops/` unless explicitly declared legacy compatibility;
- material changes must preserve failure isolation and run architecture validation;
- a module reaches 100% only after Functional DONE + Maintainability DONE;
- risky physical refactors occur as their own compatibility-proven migrations.

## Next recommended architecture milestone

**Native V2 Extension Composition v1**

Goal: replace chained exact-string/monkey-patch presentation wrappers with explicit composable extension slots/hooks before implementing the Smart Issue Review Console. This reduces the highest known downstream coupling risk without changing Intelligence contracts.
