# Failure Isolation & Recovery

Unipalm follows a fail-closed recovery model: preserve the last trustworthy upstream state, identify the failing boundary, repair only that boundary, then revalidate downstream.

## Failure pattern

Expected:

```text
A PASS -> B PASS -> C FAIL -> D BLOCKED
```

C must not rewrite A or B merely to make D run.

## Recovery decision tree

### Source/schema failure

Symptoms:
- missing required columns;
- unknown breaking fingerprint;
- invalid shop identity.

Owner:
- Source Schema Guard / Shop Registry / Staging.

Recovery:
1. inspect source export and schema diff;
2. determine whether drift is semantic or cosmetic;
3. update reviewed schema registry only when meaning is proven;
4. rerun staging;
5. do not touch Processed/Semantic until staging PASS.

### Processed failure

Recovery unit: **one shop + one period**.

Do not rebuild unrelated shops/months to hide an isolated failure.

Published prior partition remains the rollback source until atomic replacement completes.

### Durable storage failure

Atomic writer requirements:
- previous partition remains available until verified swap;
- same fingerprint is NOOP;
- unmanaged existing partition fails rather than overwrites;
- uploaded bytes are verified.

If Drive/API failure is transient, retry only idempotent operations with bounded retry policy.

### Semantic failure

Do not repair in UI. Determine whether the problem is:
- bad Processed input;
- invalid semantic contract implementation;
- incomplete all-shop scope.

If input is valid but semantic logic is wrong, fix Semantic and rerun downstream Intelligence/Payload.

### Context / historical failure

Missing or incompatible evidence produces `UNKNOWN`/`INSUFFICIENT_*` states. Do not substitute an easier comparison period merely to populate an insight.

### Intelligence/diagnosis failure

Preserve the last upstream semantic/context facts. Revalidate the owning intelligence contract and its direct downstream consumers.

A diagnosis/candidate/issue layer must not mutate the underlying factual marts.

### Smart Issue review failure

Operator state is append-only/concurrency-protected.

If an event is rejected:
- refresh the current review workflow;
- compare expected ledger fingerprint;
- submit a new valid event;
- never edit a prior event to force the state.

### Action Authorization failure

Action Authorization remains downstream of human-reviewed Smart Issues.

If a proposal/authorization event is rejected or stale:
- rebuild the current Action Authorization sidecar from the current reviewed issue/evidence lineage;
- refresh the authorization ledger fingerprint;
- do not reuse approval from a changed issue epoch/proposal fingerprint;
- never reinterpret `APPROVED_REVIEW_ONLY` as an execution permit.

### UI/native failure

If a presentation extension no longer matches its parent runtime:
- fail closed;
- repair the presentation composition layer;
- do not weaken data/Intelligence contracts.

The previous Registry UI failure is the reference example: Native failed while upstream Registry/Ads artifacts remained valid.

### Production Cutover Control failure

Production Cutover Control is a downstream deployment-control boundary. A control status of `BLOCKED` is not itself an incident; it is often the correct result when real production-readiness evidence is incomplete.

If a cutover-control gate fails:
1. identify the exact failing lineage/readiness/rollback/authorization gate;
2. keep validated Semantic/Intelligence/UI artifacts unchanged;
3. refresh or collect the missing reviewed evidence rather than flipping readiness flags manually;
4. rebuild the control artifact;
5. if the `cutoverPlanFingerprint` changes, obtain a fresh human plan decision — prior approval does not migrate;
6. never bind an executor or enable production mutation merely to clear the gate.

If the legacy rollback repository surface is missing, restore the required legacy production/recovery component or keep cutover blocked. Do not weaken the required-path gate.

If the cutover authorization ledger is stale, refresh the current ledger fingerprint and prepare a new append-only event. Do not edit or delete prior events to make an old approval fit a new plan.

The v1 rollback drill is simulation-only. `DRY_RUN_PASS` does not satisfy the separate reviewed readiness evidence `rollback_drill_validated`; a real rehearsal must be evidenced before cutover readiness may advance.

### Production-readiness hardening failure

A hardening probe failing is evidence that the corresponding readiness gate is not ready; it is not permission to weaken the probe.

Recovery:
1. keep the failed readiness row `ready=false`;
2. repair only the failing boundary (artifact binding, exact rollback target, credentials/read access, monitoring, or repository governance);
3. rerun Production Readiness Hardening;
4. promote only evidence that actually passes;
5. rerun Production Cutover Control so it independently reproduces the remaining blocker set.

Repository governance is special: a workflow-only convention cannot substitute for an actual server-side protection/ruleset on production branch `main`.

Rollback-runtime evidence must execute the exact active production rollback target (`origin/main` at its captured SHA), not a development compatibility copy.

A changed source lineage, release candidate, production baseline or readiness evidence changes the exact cutover plan identity and therefore requires re-evaluation/fresh approval.

### Production failure

Production recovery remains owned by the active legacy runbooks/workflows until an explicitly executed and accepted N-shop cutover changes that ownership.

PREPRODUCTION tooling, including Production Cutover Control v1, must not be used as an improvised production writer.

During a future explicit execution milestone, the legacy path remains the rollback target until post-deploy verification and the agreed rollback window have completed successfully.

## Recovery evidence to capture

For material incidents record:
- failing module;
- input fingerprint/source period;
- failed check/error;
- unaffected upstream checkpoints;
- exact repair;
- tests run;
- staging/production validation run;
- resulting fingerprint changes;
- rollback performed or not required.

For production-readiness/cutover work additionally capture:
- exact Cutover Plan fingerprint;
- readiness-evidence fingerprint;
- human authorization event/ledger fingerprint where applicable;
- production baseline identity;
- legacy rollback target identity;
- dry-run/rehearsal evidence;
- monitoring/health-check result;
- whether any production write occurred.

## Rollback policy

Prefer reverting the smallest change when a validated locked boundary is unexpectedly altered.

Never use rollback to restore known-corrupt business facts. In that case, keep publication blocked until a corrected artifact is produced and validated.

Never treat a control-plane approval as permission to bypass the executor, deployment, verification or rollback gates required by the production cutover contract.
