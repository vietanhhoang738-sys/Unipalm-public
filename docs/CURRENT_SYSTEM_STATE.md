# CURRENT SYSTEM STATE — Unipalm

Updated: **2026-10-01**  
Repository: `vietanhhoang738-sys/Unipalm`  
Development branch: `multi-shop-catalog-resolver`

This file is the concise current-state entrypoint. Historical milestone chronology remains in `PROJECT_HANDOFF_MULTI_SHOP.md`.

## Production boundary

Production remains on the guarded legacy single-shop path. The registry-driven N-shop path is still **PREPRODUCTION**.

The new Production Cutover Control can evaluate readiness and record an explicit human decision for an exact cutover plan, but it **cannot deploy**. Production Data Mart, production UI/index, external platform state and legacy recovery remain protected. `executionEnabled`, `executionPermitIssued`, `platformMutationAllowed` and `productionActivationEnabled` remain false.

## Canonical target flow

```text
Platform exports / RAW
  -> Source Schema Drift Guard
  -> Shop-scoped Staging
  -> Shop-scoped Processed v2
  -> Durable Processed storage
  -> Semantic v2
  -> Historical + Business Context
  -> Product Intelligence / Ads Intelligence
  -> Context-qualified Ads Diagnosis
  -> Diagnosis Persistence
  -> Smart Issue Candidate
  -> Human Review Registry
  -> Operator Review Workflow
  -> Alert Policy v1
       -> eligibility / severity / routing / dedupe / cooldown
       -> delivery disabled
  -> Recommendation / Action Authorization v1
       -> bounded review proposal
       -> explicit APPROVE / REJECT / REVOKE ledger
       -> APPROVED_REVIEW_ONLY at most
       -> executor NOT bound / execution disabled
  -> Canonical UI Payload
  -> Native V2 Extension Composition v1.3
       + Operator Review Workflow sidecar
       + Alert Policy sidecar
       + Action Authorization sidecar
  -> read-only operator presentation
  -> Production Cutover Control v1
       -> validated artifact lineage
       -> legacy rollback-surface gate
       -> reviewed production-readiness evidence
       -> deterministic exact Cutover Plan fingerprint
       -> simulation-only rollback drill
       -> explicit human plan approval
       -> authenticated executor boundary NOT bound
       -> execution permit NOT issued
  -> future explicit execution milestone only after all readiness gates are evidenced
```

## Current locked functional modules

The following foundations have completed their declared version scope and are locked compatibility surfaces:
- Shop Registry / N-shop identity boundary;
- Source Schema Guard;
- Catalog Resolver;
- Multi-Shop Staging;
- Processed v2 + control plane;
- durable Processed writer;
- Semantic v2 + durable Semantic writer;
- Business Context Calendar;
- Historical Intelligence;
- Product Intelligence;
- Ads Intelligence + Context Qualification;
- Ads Dynamic Diagnosis;
- Diagnosis Persistence;
- Smart Issue Candidate;
- Smart Issue Registry / Human Review;
- Smart Issue Operator Review Workflow;
- Smart Issue Alert Policy v1;
- Recommendation / Action Authorization v1;
- canonical UI Payload;
- Native V2 presentation foundation;
- Native V2 Extension Composition v1 / additive v1.1 / v1.2 / v1.3;
- Smart Issue Review Console UI v1;
- Alert Policy read-only Native UI v1;
- Action Authorization read-only Native UI v1;
- Production Cutover Preparation & Execution-Control Hardening v1;
- Final Hardening / Monitoring + Production Readiness Evidence Closure v1;
- System Architecture & Maintainability Foundation v1.

Locked means downstream work must not casually rewrite the module. A behavior/contract change requires explicit versioning or a compatibility-preserving migration with equivalence evidence.

## Latest operator/control checkpoints

### Smart Issue Review Console v1
- real-data replay #9 / `36707186385`: PASS;
- full staging #577 / `36707308126`: PASS;
- composition v1.1, 11 extensions, one compatibility bridge;
- read-only sidecar presentation; no browser ledger write.

### Alert Policy v1
- backend staging checkpoint #581 / `36804875725`: PASS;
- real-data Native replay #15 / `36805693856`: PASS;
- full staging #587 / `36805799727`: PASS;
- Alert Policy QA 21/21 PASS;
- composition v1.2, 12 extensions, one compatibility bridge;
- delivery/provider binding disabled.

### Recommendation / Action Authorization v1
- backend real-data replay #1 / `36809200022`: PASS;
- integrated full staging #592 / `36810351226`: PASS;
- Native v1.3 real-data replay #21 / `36811763385`: PASS;
- final full staging #598 / `36811937549`: PASS end-to-end;
- Action Authorization QA 22/22 PASS;
- UI Payload QA 42/42 PASS;
- Native QA 33/33 PASS;
- composition `native-v2-extension-composition-v1.3`, 13 extensions, one compatibility bridge;
- current real state `READY_EMPTY`: 0 proposals because there are 0 human-promoted Smart Issues;
- authenticated executor, execution, provider binding, platform mutation and production activation disabled.

Detailed design: `docs/recommendation-action-authorization-v1.md`.  
Checkpoint: `docs/audits/recommendation-action-authorization-v1-checkpoint.md`.

### Production Cutover Preparation & Execution-Control Hardening v1
- source artifacts: successful full staging #598 / `36811937549`;
- canonical real-data control replay #1 / `36814332136`: PASS;
- synthetic Production Cutover Control tests: **9/9 PASS**;
- real control QA: **27/27 PASS**;
- control replay artifact: `production-cutover-control-2026-09`, ID `11140368144`;
- artifact digest: `sha256:17bf59deda0b7c6baa18183ab9a86765f67d85f762cbd4273802dda11219d8d8`;
- rollback-plan simulation: `DRY_RUN_PASS`, 7/7 required steps, zero production writes;
- all upstream lineage/safety gates PASS;
- required legacy rollback repository surface retained;
- current real cutover-control state: **`BLOCKED`** because 8 production-readiness evidence gates remain unevidenced;
- authenticated executor is not bound;
- execution permit is not issued;
- production activation remains disabled.

Current cutover-control identity from the validated #598 source artifacts:
- Cutover Plan: `40c5b829cf70171b4cacb92aac290c3f1a1220b085f1edec9a032dc1a135db61`;
- Production Cutover Control: `29f261b097600b0e1c3c38f0585a2d9729362cc7949fd1ffcb61bec623a6b065`;
- readiness evidence: `489b3e387890088a22c18766cd437263c374f1e409c50c28bdf55d369e62d95f`;
- empty cutover authorization ledger: `a9f975bcb6ac76ff1c7d46568f185778ebb892649033e1b17e09cbb4ca39301d`.

Detailed design: `docs/production-cutover-preparation-execution-control-v1.md`.  
Checkpoint: `docs/audits/production-cutover-preparation-execution-control-v1-checkpoint.md`.

### Final Hardening / Monitoring + Production Readiness Evidence Closure v1
- canonical hardening run #2 / `36818971898`: SUCCESS;
- hardening artifact `production-readiness-hardening-2026-09`, ID `11141818994`;
- artifact digest `sha256:5c87239706e25c05c77b147140dd4c816ec4c18a1c04a2867fc7929567079d7f`;
- hardening QA PASS, regression suite PASS;
- deterministic release candidate fingerprint `28a94db7e4029fd8122a6d7c0e94ee4b8591bb8570c43f5daed82d90c06d50c8`;
- release candidate SHA-256 `5440df729311de7108a2b6fbe729ceecec37e9a7658a4a8ad1dacec6eb8ebb51`;
- current production baseline SHA-256 `1980b97a17207282d4c4addc439d07a2685310e39e4fb50aa0b92702ff8ddb85`;
- exact active `origin/main` rollback runtime compile/tests/read-only dry-run PASS;
- live fixed production URL monitoring 3/3 PASS with exact active build marker;
- readiness evidence **7/8 PASS**;
- only blocker: `repository_deployment_guard_verified=false` because `main protected=false`;
- no production/repository write, deployment, execution permit or production activation occurred.

After canonical evidence promotion, independent Production Cutover Control run #2 / `36819129833` PASS with QA 27/27, rollback `DRY_RUN_PASS`, blocker count 1 and sole blocker `repository_deployment_guard_verified`.

Detailed design: `docs/production-readiness-hardening-v1.md`.  
Checkpoint: `docs/audits/production-readiness-hardening-v1-checkpoint.md`.

## Production Cutover Control v1 — locked operating rules

`BLOCKED` is a valid and currently expected state. It means the control plane is refusing to infer production readiness from PREPRODUCTION success.

Eight production-readiness checks must be separately evidenced:
1. production data binding validated;
2. production UI binding validated;
3. deployment dry-run validated;
4. rollback drill validated;
5. legacy rollback runtime verified;
6. production credentials verified;
7. monitoring readiness validated;
8. repository deployment guard verified.

Mutable evidence lives in `ops/production_cutover_evidence.json`. A readiness row cannot become `ready=true` without evidence, reviewer identity and timezone-aware review timestamp.

Human plan decisions live append-only in `ops/production_cutover_authorization_events.json`. Approval is bound to the exact deterministic `cutoverPlanFingerprint`; a changed HEAD, artifact lineage, readiness evidence or plan requires fresh approval.

Even a valid approval yields only `APPROVED_FOR_EXPLICIT_EXECUTION_MILESTONE`. It does not issue an execution permit.

Future executor requirements are already constrained: authenticated short-lived session, maximum TTL 900 seconds, exact plan binding, PREPARE/COMMIT separation, idempotency, audit trail, rollback plan and post-deploy verification. The executor itself is intentionally not bound in v1.

## Current validated artifact identity

September source data is validated through 30/09:
- September Semantic: `00f96406d52414e9a2d201a7ba3eada8dccc57b9deeced0fd38e97558569de20`;
- Historical Intelligence: `3467c96917e47a412b5506f82add8ad196ee565a98145197a72615a2f41bceb3`;
- Product Intelligence: `cbe2282d682eaefc7629e93b106b427630e605092b65a9e445bca330f44c1bbf`;
- Ads Intelligence / Smart Issue Registry: `bfc579acbfd05edc842a45d4c8b0dcf5677d8eaf9462c47ecb17b7fca22bca54`;
- Operator Review Workflow: `2e0a8f9924bf6b980789764baad4cfc618fd7df95e5ad58308e3f46634f8aff0`;
- Operator review ledger: `a5a99966fbd29c99d0264b89772e768401f9e8d0c7707c27d2e872b5d650970d`;
- Alert Policy: `da056580f7d2de3198387b1dc4d9649b95c59f208e8121e0c4bc034639a8bf0c`;
- Alert delivery ledger: `cc754cd279d91007ec63043b43ec794d993029a2e800cc06ba4565d4c2815f77`;
- Action Authorization: `c091ab68545012c49a2bf9e8de0e814c8b8113909800e8559e183e667178b501`;
- Action Authorization ledger: `c417e44fdec7bd95ba3092aa648cfa50712d4e817113d7c3f1913ce4971b2b78`;
- UI Payload build: `53cf875fff27d5bb153f68f5ebb34adc107a979e5705624e74c4b2ebdcb239f9`;
- Native v1.3 build: `94179a3764a8008b4441945932140df2a13bb3d77c0b006819839c0705bbceab`.

Data fingerprints may legitimately change with new valid source data. Locked contracts/behavior are protected by lineage validation, contract tests and fail-closed gates rather than by freezing an old monthly data fingerprint.

## RAW source-data incident note

Staging #591 detected Mall Shop ID inside a SYT+ Ads RAW input. The user confirmed this was their own accidental RAW data placement and corrected it. This was **not a system defect**.

The system behavior was correct: the shop-ID isolation guard failed closed. A read-only audit subsequently confirmed the corrected source set, and full staging #592 and #598 passed. No parser or shop-isolation guard was weakened.

## System Architecture & Maintainability Foundation v1 — LOCKED

Repository governance remains based on:
- `UNIPALM_PROJECT_CONSTITUTION.md`;
- `config/system_module_registry.json`;
- `automation/validate_architecture.py`;
- `automation/tests/test_system_architecture_registry.py`;
- `ops/` as canonical mutable operator/control-state boundary;
- Architecture & Contract Guard CI;
- architecture/change/recovery/clone/handoff docs under `docs/architecture/`.

Production Cutover Control is registered in a dedicated `deployment_control` layer after presentation. This allows it to validate both Action Authorization and the final Native artifact without reversing dependency direction.

## Current known technical debt / readiness work

### Active legacy production
Keep until an explicitly accepted production cutover and rollback window: `.github/workflows/unipalm-pipeline.yml`, `.github/workflows/product-ads-mart-maintenance.yml`, `automation/run_pipeline.py`, `automation/source_processor.py`, `automation/backfill_product_ads.py`, `automation/frozen_v14_template.html`, `automation/pipeline_state.json`. Do not clone the legacy stack for future shops.

### Production-readiness evidence state
Seven of eight gates now have real reviewed evidence. The sole remaining blocker is `repository_deployment_guard_verified=false` because production branch `main` is not protected server-side. Do not substitute workflow-only conventions for an enforced GitHub branch/ruleset guard.

### Staging request compatibility mirror
`ops/staging_request.json` is the target operational-state location, but staging still reads `config/staging_request.json` for `[staging]` pushes. Until orchestration is migrated, both files must remain byte-equivalent.

### Native base compatibility bridge
Canonical composition retains one temporary base bridge because locked `ui_v2_native` does not yet expose first-class bundle/style/runtime hooks. Do not add a second bridge.

### Google Drive OAuth operational hardening
The writer is validated with `user_oauth`; the OAuth app remains in Testing publishing status. Long-lived Production OAuth/domain setup is part of production-readiness hardening. Do not bypass Drive gates.

### Notification delivery
Alert Policy stops at policy/routing intent. Authenticated provider delivery, retry semantics and channel credentials remain **DEFERRED BY DESIGN** unless a business need is explicitly approved.

### Platform execution
Action Authorization remains `APPROVED_REVIEW_ONLY`. Production Cutover Control may at most record `APPROVED_FOR_EXPLICIT_EXECUTION_MILESTONE`. Authenticated executor binding and any real platform/deployment mutation remain **DEFERRED BY DESIGN** until a separate explicit execution milestone.

### Repository governance
Production branch `main` is currently reported as unprotected, so `repository_deployment_guard_verified=false`. This is the only remaining production-readiness blocker. The development branch is also not protected. A real server-side branch protection/ruleset must be enabled and reverified; workflow-only policy is insufficient.

## Next sequence

1. Enable and reverify an enforced server-side protection/ruleset for production branch `main`; rerun hardening + Cutover Control to reach 8/8 evidence.
2. Production-readiness audit on the exact candidate lineage and exact Cutover Plan fingerprint.
3. Explicit human production cutover decision.
4. Separate authenticated execution/cutover milestone with PREPARE/COMMIT and rollback controls.
5. Observe a rollback/health window, then retire legacy production components and complete physical cleanup/clone template.

## First files for a new engineer / AI

Read in this order:
1. `UNIPALM_PROJECT_CONSTITUTION.md`
2. `README.md`
3. this file
4. `docs/architecture/SYSTEM_OVERVIEW.md`
5. `config/system_module_registry.json`
6. `docs/production-cutover-preparation-execution-control-v1.md` when touching cutover/readiness work
7. the relevant `config/*_contract.json`
8. the relevant domain document
9. implementation and tests registered for that module
