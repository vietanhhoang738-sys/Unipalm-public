# Production Cutover Preparation & Execution-Control Hardening v1

Status: **PREPRODUCTION — implementation milestone**

## Purpose

This module answers a narrow question: **is the validated N-shop system ready to ask for an explicit production cutover decision, and can that decision be recorded without accidentally becoming an execution permit?**

It does not deploy, switch production data, change `index.html`, call a platform/provider, or replace the legacy production pipeline.

## Control flow

```text
Validated full staging artifacts
  -> Action Authorization safety + lineage gate
  -> Native V2 safety + lineage gate
  -> Legacy rollback repository surface gate
  -> Reviewed production-readiness evidence gates
  -> Deterministic Cutover Plan fingerprint
  -> Dry-run rollback drill simulation
  -> Explicit human cutover authorization ledger
  -> Authenticated Executor boundary
       authenticated executor required
       executor NOT bound
       execution disabled
       execution permit NOT issued
       production activation disabled
```

## Status model

`BLOCKED`
: one or more upstream or production-readiness gates are not yet satisfied.

`READY_FOR_EXPLICIT_APPROVAL`
: all technical/readiness gates pass, but there is no human approval for the exact plan fingerprint.

`APPROVED_NOT_EXECUTABLE`
: a human has approved the exact plan fingerprint for a **future explicit execution milestone**. It is still not an execution permit.

A production deployment status does not exist in v1.

## Readiness evidence

Mutable reviewed evidence lives in `ops/production_cutover_evidence.json`. The required checks are:

- production data binding validated;
- production UI binding validated;
- deployment dry-run validated;
- rollback drill validated;
- legacy rollback runtime verified;
- production credentials verified;
- monitoring readiness validated;
- repository deployment guard verified.

A check cannot be set `ready=true` without non-empty evidence, reviewer identity and timezone-aware review timestamp.

These are mutable operational facts, not normative contract rules.

## Human cutover authorization

Mutable events live in `ops/production_cutover_authorization_events.json`.

Allowed actions:
- `APPROVE_CUTOVER_PLAN`;
- `REJECT_CUTOVER_PLAN`;
- `REVOKE_CUTOVER_PLAN`.

Concurrency and staleness rules:
- events are append-only;
- apply requires the expected current ledger fingerprint;
- approval is bound to the exact `cutoverPlanFingerprint`;
- a new HEAD, artifact lineage, readiness-evidence fingerprint or plan change produces a new plan fingerprint and therefore requires fresh approval;
- rejected/revoked plans are terminal.

Approval state is deliberately named `APPROVED_FOR_EXPLICIT_EXECUTION_MILESTONE`, not `AUTHORIZED_TO_DEPLOY`.

## Authenticated executor boundary

v1 defines requirements only. It does not bind an executor.

A future executor must provide:
- authenticated short-lived session;
- maximum session TTL 900 seconds;
- identity claims: actor, session ID, issued-at, expiry, exact cutover-plan fingerprint;
- PREPARE/COMMIT separation;
- deterministic idempotency key;
- append-only audit evidence;
- rollback plan before COMMIT;
- post-deploy verification before the deployment can be accepted.

v1 hard-locks:
- `authenticatedExecutorBound=false`;
- `executionEnabled=false`;
- `executionPermitIssued=false`;
- `platformMutationAllowed=false`;
- `productionActivationEnabled=false`;
- automatic cutover=false;
- automatic rollback=false.

## Rollback drill

The control artifact contains a deterministic **simulation-only** rollback drill:

1. capture production baseline;
2. verify legacy rollback target;
3. verify new artifact lineage;
4. simulate binding switch;
5. simulate health-check failure;
6. simulate rollback to legacy;
7. verify post-rollback baseline.

Every step records `productionWritePerformed=false`. Passing this simulation proves the control-plan structure, not that a real production rollback has been rehearsed. The separate readiness gate `rollback_drill_validated` remains false until a reviewed real dry-run/rehearsal is performed and evidence is recorded.

## Legacy rollback boundary

The repository-level legacy production/recovery surface must remain present while this module is in force. The required paths are declared in `config/production_cutover_control_contract.json` and include the active production workflow, production runner, source processor, maintenance recovery path, frozen template, legacy state and legacy dependency registry.

Missing rollback files block the cutover plan and block the simulated rollback drill rather than being silently ignored.

## Workflow

`.github/workflows/production-cutover-control.yml` is intentionally a separate manual PREPRODUCTION control-plane workflow. It consumes artifacts from a **successful** `Multi-Shop Core CI & Staging QA` run on `multi-shop-catalog-resolver`, then builds the cutover-control artifact without any production credentials or write permission.

This separation is deliberate: production authorization is not part of ordinary data refresh/staging.

## Canonical files

- contract: `config/production_cutover_control_contract.json`;
- engine: `automation/modules/production_cutover_control.py`;
- runner: `automation/multi_shop_production_cutover_control_runner.py`;
- human authorization command: `automation/production_cutover_authorization_command.py`;
- readiness evidence: `ops/production_cutover_evidence.json`;
- authorization ledger: `ops/production_cutover_authorization_events.json`;
- tests: `automation/tests/test_production_cutover_control.py`;
- replay/control workflow: `.github/workflows/production-cutover-control.yml`.

## Completion rule for this milestone

This milestone may be `LOCKED_V1` while real cutover status is still `BLOCKED`. The feature is correct when it reliably identifies blockers, protects the exact plan/lineage, records human decisions safely, proves the rollback-plan simulation, and keeps execution impossible.

Actual production readiness and actual cutover require later reviewed evidence plus a separate explicit execution milestone.
