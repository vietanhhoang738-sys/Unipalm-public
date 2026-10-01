# Production Cutover Preparation & Execution-Control Hardening v1 — Validation Checkpoint

Date: **2026-10-01**  
Milestone capability state: **VALIDATED / LOCKED — 100% PREPRODUCTION**  
Real production cutover state: **BLOCKED — expected and correct**

## What this checkpoint locks

This milestone locks the control plane that decides whether a validated N-shop build may advance toward an explicit human production-cutover decision.

It does **not** authorize or perform production deployment. The capability is considered complete when it can prove lineage, expose missing production-readiness evidence, bind human approval to an exact deterministic plan, simulate the rollback plan, and keep all execution/mutation paths disabled.

## Upstream validated source

Control-plane replay consumes real artifacts from full PREPRODUCTION staging #598 / `36811937549`:
- source head: `648c38a8d0adf7efb5c42ae759ab666fb62ac713`;
- September Semantic: `00f96406d52414e9a2d201a7ba3eada8dccc57b9deeced0fd38e97558569de20`;
- UI Payload build: `53cf875fff27d5bb153f68f5ebb34adc107a979e5705624e74c4b2ebdcb239f9`;
- Native v1.3 build: `94179a3764a8008b4441945932140df2a13bb3d77c0b006819839c0705bbceab`;
- Native source template SHA-256: `63ae292cb8b55e8f06a27a528e175e2d959b7595545ce36560df4071c61b8761`;
- Action Authorization: `c091ab68545012c49a2bf9e8de0e814c8b8113909800e8559e183e667178b501`;
- Action Authorization ledger: `c417e44fdec7bd95ba3092aa648cfa50712d4e817113d7c3f1913ce4971b2b78`.

The control plane does not re-derive those business artifacts. It validates their lineage and safety state.

## Canonical real-data replay

Workflow: `Production Cutover Control PREPRODUCTION`  
Run #1 / `36814332136`: **SUCCESS**  
Control-plane head: `fc3d39332e3fc5979b464f38bc2b7995bdb72971`

The workflow successfully:
- resolved a compatible successful Multi-Shop staging run;
- downloaded the real Ads / Action Authorization artifact;
- downloaded the real Native v1.3 artifact;
- compiled the control-plane runtime;
- ran the Production Cutover Control unit suite;
- built the real control artifact;
- enforced the non-execution safety boundary;
- uploaded control evidence.

Artifact:
- name: `production-cutover-control-2026-09`;
- artifact ID: `11140368144`;
- digest: `sha256:17bf59deda0b7c6baa18183ab9a86765f67d85f762cbd4273802dda11219d8d8`.

## Test and QA evidence

Synthetic regression suite: **9/9 PASS**.

Covered negative and safety cases include:
- missing readiness evidence remains BLOCKED;
- all readiness evidence only reaches explicit approval gate;
- plan approval remains non-executable;
- approval is bound to the exact cutover-plan fingerprint;
- changed HEAD/lineage requires fresh approval;
- stale authorization-ledger fingerprint fails closed;
- missing legacy rollback surface blocks cutover and rollback drill;
- readiness evidence cannot claim ready without reviewer/evidence/timestamp;
- unsafe executor binding in contract is rejected;
- Native production-mutation regression blocks instead of being normalized.

Real artifact Control QA: **27/27 PASS**, 0 failures.

## Current real control state

Current control status is **`BLOCKED`** because the following 8 reviewed production-readiness checks have not yet been evidenced:
1. `production_data_binding_validated`;
2. `production_ui_binding_validated`;
3. `deployment_dry_run_validated`;
4. `rollback_drill_validated`;
5. `legacy_rollback_runtime_verified`;
6. `production_credentials_verified`;
7. `monitoring_readiness_validated`;
8. `repository_deployment_guard_verified`.

This is not a feature failure. It is the intended fail-closed result. No readiness flag was fabricated to force the system toward production.

Current control identity:
- cutover plan fingerprint: `40c5b829cf70171b4cacb92aac290c3f1a1220b085f1edec9a032dc1a135db61`;
- Production Cutover Control fingerprint: `29f261b097600b0e1c3c38f0585a2d9729362cc7949fd1ffcb61bec623a6b065`;
- readiness evidence fingerprint: `489b3e387890088a22c18766cd437263c374f1e409c50c28bdf55d369e62d95f`;
- empty cutover authorization ledger fingerprint: `a9f975bcb6ac76ff1c7d46568f185778ebb892649033e1b17e09cbb4ca39301d`.

## Technical gates that already PASS

The real artifact confirms:
- Action Authorization artifact ready with executor blocked;
- Action Authorization safety blocked from execution/production activation;
- Native v1.3 artifact PASS;
- required composition version and `ads_action_authorization` extension present;
- one compatibility bridge only;
- legacy nested-wrapper build path false;
- Native Action Authorization lineage matches the backend sidecar;
- Native executor/provider/platform mutation flags remain false;
- production Data Mart/UI/deployment/index/template safety flags remain false;
- all-shop scope is present;
- artifact lineage fingerprints are present;
- required legacy production/recovery repository surface remains present.

## Rollback drill result

The deterministic rollback-plan simulation is **`DRY_RUN_PASS`** with 7/7 steps present and PASS:
1. capture production baseline;
2. verify legacy rollback target;
3. verify new artifact lineage;
4. simulate binding switch;
5. simulate health-check failure;
6. simulate rollback to legacy;
7. verify post-rollback baseline.

Every step records `productionWritePerformed=false`.

This proves the control structure only. It does not falsely mark the separate real-world readiness gate `rollback_drill_validated` as complete. A reviewed rehearsal with evidence is still required before real cutover readiness can advance.

## Human cutover authorization boundary

Cutover authorization is append-only under `ops/production_cutover_authorization_events.json`.

Allowed decisions:
- `APPROVE_CUTOVER_PLAN`;
- `REJECT_CUTOVER_PLAN`;
- `REVOKE_CUTOVER_PLAN`.

Approval is bound to the exact `cutoverPlanFingerprint`. A new HEAD, source lineage, readiness-evidence fingerprint or control-plan change produces a new plan fingerprint and therefore requires fresh approval.

Even an approved plan becomes only `APPROVED_FOR_EXPLICIT_EXECUTION_MILESTONE`. It never becomes an execution permit in v1.

## Authenticated executor boundary

The future executor contract requires:
- authenticated short-lived session;
- maximum TTL 900 seconds;
- actor/session/issued-at/expiry/exact-plan claims;
- PREPARE / COMMIT separation;
- deterministic idempotency key;
- audit trail;
- rollback plan before COMMIT;
- post-deploy verification.

Current hard safety state remains:
- `authenticatedExecutorBound = false`;
- `executionEnabled = false`;
- `executionPermitIssued = false`;
- `providerBindingEnabled = false`;
- `platformMutationAllowed = false`;
- `productionActivationEnabled = false`;
- `automaticCutoverEnabled = false`;
- `automaticRollbackEnabled = false`.

## Maintainability boundary

Canonical maintenance files:
- contract: `config/production_cutover_control_contract.json`;
- engine: `automation/modules/production_cutover_control.py`;
- runner: `automation/multi_shop_production_cutover_control_runner.py`;
- human authorization command: `automation/production_cutover_authorization_command.py`;
- readiness evidence: `ops/production_cutover_evidence.json`;
- cutover authorization ledger: `ops/production_cutover_authorization_events.json`;
- tests: `automation/tests/test_production_cutover_control.py`;
- control replay workflow: `.github/workflows/production-cutover-control.yml`;
- design doc: `docs/production-cutover-preparation-execution-control-v1.md`.

Failure boundary:
- invalid upstream lineage/safety, missing rollback surface, stale authorization state or any missing readiness evidence blocks the plan;
- a downstream control-plane failure never rewrites validated business artifacts;
- approval never enables execution in this version.

Rollback boundary:
- legacy production remains active and retained;
- remove/disable this PREPRODUCTION control module without modifying locked Semantic/Intelligence/Native artifacts;
- authorization/readiness state is isolated under `ops/`.

## Deferred by design

Not authorized by this checkpoint:
- marking the 8 readiness gates PASS without reviewed evidence;
- binding production credentials to this control plane;
- authenticated executor implementation/binding;
- issuance of an execution permit;
- production Data Mart switch;
- production UI/index switch;
- actual deployment;
- real automatic rollback;
- provider/platform mutation;
- retirement of legacy production/recovery components.

The next milestone must close the real production-readiness evidence and monitoring gaps before an explicit production cutover decision is considered.
