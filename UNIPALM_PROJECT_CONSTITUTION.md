# UNIPALM PROJECT CONSTITUTION

Version: **0.2**  
Status: **LIVING CONSTITUTION — PRE-v1.0**  
Applies to: **all current and future Unipalm data, intelligence, UI, automation, maintenance and production work**

---

## 0. Purpose and authority

This document defines the highest-level, non-negotiable principles of the Unipalm project.

It is intentionally not a copy of every schema, field, threshold, UI label or implementation detail. Those belong in machine-readable contracts, domain documentation, code and tests.

The Constitution defines **what Unipalm is allowed to become and what it must never silently become**.

### Authority model

Normative hierarchy:

1. **`UNIPALM_PROJECT_CONSTITUTION.md`** — project principles and non-negotiable boundaries.
2. **Machine-readable contracts and system ownership registries in `config/`** — precise enforceable rules that specialize the Constitution.
3. **Canonical architecture/domain docs in `docs/`** — rationale, workflow and reviewed design decisions.
4. **Implementation in `automation/`, UI templates and workflows** — execution of the above rules.
5. **Tests and QA gates** — enforcement and regression protection.
6. **Historical audits, run records and handoff notes** — evidence and continuity records, not permission to override higher layers.

If a lower layer conflicts with this Constitution, the conflict must be resolved explicitly. It must never be normalized as an undocumented exception.

Changing this Constitution is allowed only as a deliberate architectural decision with a reason, impact assessment and corresponding contract/test/documentation updates.

---

## 1. Product mission

Unipalm is a **Business Operating System for e-commerce operators**, not merely a reporting dashboard.

Its long-term role is to turn fragmented commerce data into a trustworthy operating loop:

```text
Source Data
  -> Trusted Facts
  -> Semantic Business Model
  -> Context
  -> Comparison / Detection
  -> Explanation
  -> Issue Candidate
  -> Human-reviewed Issue
  -> Human-review Action / Review Options
  -> Business Outcome
  -> Future Learning
```

The system should help an operator understand:

- what is happening;
- whether it is genuinely unusual or important;
- why it is happening, within available evidence;
- what deserves attention next;
- what can and cannot be concluded safely.

Unipalm must prefer **trustworthy restraint over fabricated certainty**.

---

## 2. System boundaries

Unipalm separates five concerns:

1. **Data Foundation** — ingestion, normalization, lineage, data quality and persistence.
2. **Semantic Foundation** — stable business entities, metrics and scopes.
3. **Intelligence Foundation** — context, comparison, anomaly, confidence, attribution and diagnosis.
4. **Issue / Operator Foundation** — persistence, candidate qualification, human review, issue lifecycle and operator state.
5. **Presentation Layer** — canonical payload, Command Center, comparisons and future destinations.

No presentation layer may redefine business facts that belong to the semantic layer.

No intelligence layer may bypass data-quality or evidence gates because the UI needs an answer.

No issue layer may lower an upstream evidence threshold merely to populate an operator surface.

No automation may mutate production/platform state merely because a recommendation or reviewed issue exists.

---

## 3. Canonical architecture

The target architecture is registry-driven and N-shop:

```text
Platform / Source Exports
        -> RAW
        -> Schema Drift Guard
        -> Shop-scoped Staging
        -> Shop-scoped Processed v2
        -> Durable Storage
        -> Semantic v2
        -> Historical + Business Context
        -> Product Intelligence / Ads Intelligence
        -> Context-qualified Diagnosis
        -> Diagnosis Persistence
        -> Smart Issue Candidate
        -> Human Review / Smart Issue Registry
        -> Operator Review Workflow
        -> Canonical UI Payload
        -> Native V2 Destinations
        -> Human Operator
```

The architecture must remain decomposable: each layer has a clear owner, input boundary, output boundary, dependencies and failure boundary.

A downstream layer must not silently repair, reinterpret or conceal an upstream contract violation.

Canonical machine-readable ownership/dependencies live in `config/system_module_registry.json`.

---

## 4. Source-of-truth doctrine

Unipalm must always make the source of truth explicit.

### Runtime configuration

- Shop identity/configuration comes from `config/shop_registry.json`.
- Source schemas come from `config/source_schema_registry.json`.
- Module ownership/dependencies come from `config/system_module_registry.json`.
- Storage targets/policies come from the storage registry.
- Business-context rules and calendars come from their dedicated contracts/configuration.
- UI and presentation behavior comes from the UI contracts.

Concrete current shop identities must not become generic runtime assumptions.

### Operational state

New mutable human/operator control state belongs under `ops/`, not inside normative business contracts.

Operational state must be explicit, concurrency-protected or append-only where required, and must not silently become a second definition of business truth.

Active legacy production state may remain outside `ops/` only as an explicit compatibility exception until approved cutover.

### External evidence hierarchy

For business-context evidence, prefer:

1. platform seller-official sources;
2. platform consumer-official sources;
3. government/official regulatory sources;
4. reputable industry analytics for broader market context.

Search snippets and unverified secondary fragments must not become canonical business evidence.

### Runtime state vs project law

Current fingerprints, run IDs, current month availability, current issue counts and temporary PREPRODUCTION status belong in current-state/audit evidence. They should not be hard-coded into this Constitution unless they define a permanent principle.

---

## 5. Multi-shop principles

Unipalm is **N-shop by architecture**, even when only a small number of real shops are enabled.

Non-negotiable rules:

1. Every business-grain fact that belongs to a shop carries `shop_id`.
2. Listing identity is scoped by `shop_id + product_id`; Product ID is never globally unique.
3. Generic runtime modules must not hard-code current Shop IDs, shop names or a fixed shop count.
4. A new shop should be onboarded primarily through registry/configuration and source availability, not by cloning core logic.
5. One shop's ingestion or QA failure is an independent failure domain.
6. Legacy single-shop paths must fail closed when they encounter mixed-shop data.
7. Cross-shop ratios must be recomputed from additive numerators/denominators; ratios must not be averaged across shops.
8. Cross-shop evidence may support resolution/analysis, but no current shop is a permanent reference-shop role.
9. Product identity must never be inferred across shops from presentation-name similarity alone.
10. New multi-shop logic must remain valid for a synthetic third or later shop.

Canonical references:
- `config/shop_registry.json`
- `docs/multi-shop-architecture-audit-2026-09.md`
- `docs/multi-shop-catalog-resolver.md`

---

## 6. Data and semantic principles

### Facts before presentation

Business facts must be normalized and made trustworthy before they are rendered. The UI is not a reconciliation layer.

### Shop-local grain

All shop-grain marts preserve shop identity through the full chain.

### Additivity discipline

Metrics must respect mathematical grain:
- additive facts may be summed where valid;
- ratios are recomputed;
- non-additive unique metrics must not be naively summed across periods/scopes;
- cross-domain KPIs use compatible reliable windows.

### Semantic stability

The semantic layer is the contract between raw operational data and intelligence/presentation. New pages should consume semantic/canonical payloads rather than re-derive business logic independently.

### Durable and idempotent publication

Persistence should be deterministic and idempotent where possible. A repeated equivalent build should resolve to NOOP rather than rewrite canonical facts unnecessarily.

Canonical references:
- `config/processed_layer_contract.json`
- `config/semantic_mart_contract.json`
- `docs/multi-shop-processed-control-plane.md`
- `docs/multi-shop-semantic-mart-v1.md`

---

## 7. Data quality and fail-closed doctrine

**Fail closed is a core Unipalm behavior.**

If required evidence, lineage, identity, history, schema validity or compatibility is insufficient, Unipalm must explicitly surface a degraded/insufficient state instead of inventing certainty.

Examples include:
- schema drift that breaks required semantics;
- missing shop identity;
- mixed-shop data entering a single-shop legacy path;
- insufficient historical samples;
- unavailable context-compatible baselines;
- unqualified anomaly evidence;
- unsupported attribution;
- missing product names;
- stale operator review state;
- incompatible downstream presentation shape.

Silent fallback is forbidden when the fallback would change the meaning of the result.

A visible `INSUFFICIENT_*`, `UNKNOWN`, blocked/degraded state or empty result is preferable to a plausible but unsupported number or claim.

---

## 8. Intelligence principles

Unipalm intelligence must be **evidence-bound, context-aware and uncertainty-preserving**.

### Context before judgment

A change is not automatically an anomaly. The system must consider the validity and comparability of the reference period and available business context.

### Qualification before detection

Anomaly/detection logic must not bypass eligibility rules.

### Severity and confidence are distinct

The size/importance of a business movement and confidence in the evidence are different concepts and must remain distinguishable.

### Attribution is not causality

Driver decomposition, contribution and statistical association do not automatically establish causal truth. The system must not upgrade association into causal language.

### Persistent is not automatically material or current

Repeated evidence, economic materiality, recency and issue-worthiness are separate gates and must not be collapsed for convenience.

### No issue without evidence

A Smart Issue may be created only after the preceding evidence gates are satisfied and the configured human-review rule is satisfied. The system must not generate an issue merely to keep an intelligence surface visually populated.

---

## 9. Human review and Operator Action principles

The existence of a Smart Issue Candidate does not authorize creation of a Smart Issue. The existence of a Smart Issue does not authorize an automatic business action.

Current issue/operator policy is deliberately **human-review-first**.

Non-negotiable boundaries unless a future Constitution revision explicitly changes them:

- issue promotion and lifecycle transitions require explicit governed human review;
- action/review options retain issue/evidence lineage;
- unsupported targeted actions must not be fabricated;
- association-only evidence must not be presented as a driver-specific prescription;
- operator options expose prerequisites, monitoring and uncertainty where relevant;
- stale review state must fail closed through concurrency/fingerprint checks;
- automatic platform mutation is not implied by recommendation quality;
- production mutations require a separately designed, explicitly governed execution layer.

Presentation code must not directly mutate operator review state.

---

## 10. UI and information-architecture principles

Unipalm V2 has **one shared Design Language** and may have multiple destinations with different information architecture.

Different destinations may answer different operator questions, but they must not become separate visual products or separate business-logic systems.

### Current destination model

- **Command Center**: monitoring — what is happening now, why, and what needs attention.
- **So sánh Shop**: analysis — where selected shops differ and what drives the difference.

Future Product, Ads, Customer, Traffic, Finance or Inventory destinations may have their own information architecture, but must inherit the shared V2 foundation.

### Shared visual foundation

All V2 destinations inherit:
- Inter typography;
- V2 color tokens;
- V2 light/dark behavior;
- V2 spacing rhythm;
- V2 radius and shadow language;
- V2 sidebar/navigation grammar;
- V2 card and hierarchy grammar;
- common number/currency conventions;
- the common language and naming system.

A destination must not introduce a parallel font family, color system, card family or terminology system merely because its content differs.

Canonical references:
- `config/ui_v2_presentation_contract.json`
- `docs/ui-v2-destination-architecture.md`
- `automation/command_center_v2_template.html`

---

## 11. Language system

Operator-facing Unipalm UI is **Vietnamese-first**, while retaining established e-commerce terminology where that is the natural language of Vietnamese operators.

Avoid both extremes:
- literal Vietnamese translation that feels unnatural to e-commerce operators;
- unnecessary English/backend terminology exposed in the UI.

Common industry terms such as GMV, AOV, CVR, ROAS, CTR, SKU, LTV, Ads and MTD may remain when they improve clarity.

Backend field names may remain English. Operator-facing copy must follow the presentation contract.

Terminology should be consistent across destinations; a new page must reuse the existing Language System rather than invent local vocabulary.

---

## 12. Product naming and entity presentation

Commercial product identity and technical identity are not the same presentation concern.

Visible product-label hierarchy:
1. commercial `productName`;
2. SKU / resolved parent SKU as secondary metadata;
3. Product ID / Variation ID for technical lineage/debug only.

If the commercial name is unavailable, the UI must show an explicit missing-name state. It must not silently promote SKU/Product ID into the product-name position.

Presentation similarity must not redefine cross-shop identity semantics.

---

## 13. QA and validation principles

A feature is not complete because code runs once.

For material architecture/intelligence changes, validation should cover the relevant combination of:
- unit tests;
- contract parsing/validation;
- compile/static checks;
- architecture/dependency validation;
- synthetic edge cases;
- multi-shop isolation cases;
- real-data validation;
- idempotency/NOOP behavior;
- lineage/fingerprint continuity;
- fail-closed negative cases;
- visual/browser inspection where presentation is affected;
- production-safety verification.

Tests should enforce permanent rules where machine enforcement is practical.

Human visual approval and automated technical QA are different gates. One must not be silently substituted for the other.

---

## 14. Production safety

Production safety has priority over migration speed.

Non-negotiable rules:

1. PREPRODUCTION validation does not equal production authorization.
2. A readiness state does not itself authorize cutover.
3. Production activation requires explicit human approval and an explicit deployment decision.
4. Legacy production remains a rollback target until the new path is deliberately accepted.
5. Production Data Mart, production UI/index and platform state must not be mutated by a PREPRODUCTION milestone unless that milestone explicitly includes an approved cutover.
6. Automatic cutover, automatic rollback and automatic platform mutation require their own explicitly reviewed governance before they may exist.
7. Fingerprint/lineage regressions must block rather than silently continue.

Shadow mode is evidence collection, not permission to deploy.

---

## 15. Change governance

Every substantial new feature should answer these questions before it is considered architecturally complete:

1. Which constitutional principle does it serve?
2. Which registered module/layer owns the business logic?
3. Does it introduce a new contract or extend an existing one?
4. Does it preserve N-shop behavior?
5. Does it preserve shop isolation and grain?
6. What happens when data/evidence is insufficient?
7. What claims is it allowed to make, and which remain forbidden?
8. Does the UI reuse the shared Design/Language System?
9. Which QA gates prevent regression?
10. Does it alter production risk or permissions?
11. What is its failure boundary and rollback path?
12. Can a new maintainer identify where to change it from the repository alone?

### Constitutional change rule

A Constitution change must not be hidden inside a feature implementation.

A deliberate change should include:
- the clause being changed;
- why the current clause is insufficient;
- downstream contracts/docs affected;
- migration/compatibility impact;
- new or updated QA enforcement.

---

## 16. Maintainability, module isolation and anti-chain-failure principles

Maintainability is a product requirement, not post-project cleanup.

### Functional DONE + Maintainability DONE

A module is `LOCKED` only when both are true.

**Functional DONE** requires the declared version behavior and relevant QA/integration validation to pass.

**Maintainability DONE** requires:
- registered owner and dependencies;
- explicit input/output/failure boundaries;
- canonical source of truth;
- contract/config ownership;
- identified tests;
- documented change entrypoints;
- compatibility/rollback expectations;
- enough repository guidance for a new engineer/AI to maintain the module without undocumented project memory.

### Failure isolation

Expected failure propagation is:

```text
Upstream PASS -> Current module FAIL -> Downstream BLOCKED
```

A failing module must not silently mutate valid upstream artifacts to keep the chain running.

### Immutable-upstream principle

A downstream feature must not rewrite a locked upstream contract for convenience. Prefer an additive downstream module, sidecar or explicit new contract version.

### Refactor discipline

Do not combine a large file move, business-rule change, contract change, storage migration and production cutover in one refactor unless unavoidable.

Large locked modules should be split behind stable compatibility facades and equivalence tests.

### Machine-readable ownership

`config/system_module_registry.json` is the canonical system ownership/dependency registry and must pass `automation/validate_architecture.py`.

---

## 17. Standardization and replication principles

Unipalm should be maintainable and clonable without copying hidden current-instance assumptions.

The architecture must distinguish:

- **reusable core** — generic engines/contracts/frameworks;
- **instance configuration** — shops, storage/resource IDs, reviewed source/context configuration, branding where permitted;
- **secrets** — injected externally and never committed;
- **operator state** — instance-specific mutable state under governed boundaries;
- **legacy** — continuity/recovery components that must not be cloned as future architecture.

A new shop should not require a copy of generic algorithms.

A future new seller/brand instance should be bootstrappable primarily by replacing documented instance configuration, evidence and secrets while reusing the core.

The active legacy production stack is explicitly `DO_NOT_CLONE` until retired.

---

## 18. Rules for future pages and capabilities

New Product, Ads, Customer, Traffic, Finance, Inventory or other intelligence surfaces must not create independent mini-systems.

They must reuse, where applicable:
- Shop Registry;
- source-schema boundaries;
- Processed/Semantic layers;
- canonical UI payload patterns;
- historical/context qualification;
- uncertainty/fail-closed behavior;
- issue/operator governance;
- shared Design Language;
- shared Language System;
- existing entity naming rules;
- production-safety gates.

A new domain may extend Unipalm. It may not fork Unipalm's architecture by convenience.

---

## 19. What this Constitution deliberately does not freeze yet

Version 0.2 does **not** permanently freeze:
- exact thresholds used by anomaly/intelligence models;
- final long-horizon learning methodology;
- future action-outcome learning loops;
- future automatic alert policy;
- any future platform-mutation/execution layer;
- final production deployment architecture after cutover;
- detailed information architecture of future destinations;
- exact KPI catalog beyond currently reviewed contracts;
- final physical package/folder layout where logical ownership is already explicit.

These areas may evolve while remaining inside the principles above.

---

## 20. Documentation lifecycle

Documentation roles:

```text
Constitution
  -> permanent principles and governance

config/*_contract.json + system module registry
  -> machine-readable enforceable behavior and ownership

docs/CURRENT_SYSTEM_STATE.md
  -> concise current validated state

docs/architecture/* + canonical domain docs
  -> system/domain design, maintenance and rationale

audit / historical handoff docs
  -> evidence, chronology and operational continuity

implementation + tests
  -> executable behavior and enforcement
```

Do not copy the same detailed rule into many documents. Prefer a single canonical owner with references.

Historical chronology must not masquerade as current state.

Before future v1.0 ratification:
- mark superseded documents;
- remove obsolete duplication;
- normalize names/references;
- verify contracts/modules have canonical docs/tests;
- audit implementation against this Constitution;
- confirm production/cutover governance is explicit.

---

## 21. Canonical entrypoints

A new engineer, AI agent or reviewer should begin with:

1. `UNIPALM_PROJECT_CONSTITUTION.md`
2. `README.md`
3. `docs/CURRENT_SYSTEM_STATE.md`
4. `docs/architecture/SYSTEM_OVERVIEW.md`
5. `config/system_module_registry.json`
6. relevant `config/*_contract.json`
7. relevant canonical domain document
8. implementation and tests registered for the affected module

`docs/PROJECT_HANDOFF_MULTI_SHOP.md` remains detailed milestone chronology/provenance, not the fastest current-state entrypoint.

---

## 22. Ratification state of v0.2

Version 0.2 preserves the validated principles of v0.1 and adds explicit project-wide law for:
- machine-readable module ownership;
- Functional DONE + Maintainability DONE;
- failure isolation / anti-chain-failure behavior;
- immutable-upstream change discipline;
- operational-state separation;
- standardized replication/core-vs-instance boundaries;
- repository-first handoff to new engineers/AI maintainers.

It does not authorize production cutover and does not relax any existing evidence, human-review or safety boundary.

Until a reviewed v1.0 exists, this remains a **Living Constitution**: stable principles should be added deliberately while transient runtime details stay in current-state/audit records.
