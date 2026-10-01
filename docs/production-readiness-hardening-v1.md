# Final Hardening / Monitoring + Production Readiness Evidence Closure v1

Status: **VALIDATED PREPRODUCTION CAPABILITY**  
Production readiness state: **7/8 PASS — BLOCKED_EXTERNAL_GOVERNANCE**

## Purpose

This milestone closes the gap between a technically validated PREPRODUCTION system and evidence-backed production readiness.

It does not deploy Unipalm. It produces a deterministic release candidate, rehearses switch/rollback in an isolated workspace, verifies the exact current production rollback target, probes the live production URL, verifies production credentials only through read-only behavior, and records readiness evidence.

A readiness gate becomes `ready=true` only from concrete evidence. The module never treats a passing PREPRODUCTION build as production authorization.

## Boundary

Upstream owner: `production_cutover_control` + locked Native v1.3 artifact.

Canonical implementation:
- contract: `config/production_readiness_hardening_contract.json`;
- engine: `automation/modules/production_readiness_hardening.py`;
- runner: `automation/multi_shop_production_readiness_runner.py`;
- workflow: `.github/workflows/production-readiness-hardening.yml`;
- tests: `automation/tests/test_production_readiness_hardening.py`;
- mutable readiness state: `ops/production_cutover_evidence.json`.

The module is PREPRODUCTION-only and additive. It does not rewrite Semantic, Intelligence, Action Authorization, UI Payload, Native or the active legacy production stack.

## Eight readiness gates

The gate order is fixed:

1. `production_data_binding_validated`;
2. `production_ui_binding_validated`;
3. `deployment_dry_run_validated`;
4. `rollback_drill_validated`;
5. `legacy_rollback_runtime_verified`;
6. `production_credentials_verified`;
7. `monitoring_readiness_validated`;
8. `repository_deployment_guard_verified`.

The first seven are objectively verifiable by the hardening workflow. The last gate is deliberately external governance: it requires an actual server-side protection/ruleset on production branch `main`. A workflow that merely checks itself is not an acceptable substitute.

## Release-candidate packaging

The validated Native v1.3 artifact is transformed into a deterministic static candidate `index.html` only inside PREPRODUCTION evidence storage.

The candidate preserves the locked Native runtime and adds deployment-observability metadata:
- `unipalm-release-candidate`;
- `unipalm-native-build`;
- `unipalm-semantic-build`;
- `unipalm-cutover-source-run`.

Required invariants:
- at least two selected shops;
- composition `native-v2-extension-composition-v1.3`;
- `ads_action_authorization` extension present;
- canonical inline scope bundle present;
- no `fetch(` or `XMLHttpRequest` network runtime;
- Action Authorization remains read-only;
- production-cutover and production-write flags remain false.

The release candidate is not copied to production by this module.

## Deployment rehearsal

Deployment rehearsal occurs only inside a temporary isolated filesystem:

```text
current production index bytes
  -> exact baseline SHA
  -> backup baseline
  -> write release-candidate bytes to temporary index.html
  -> verify candidate SHA exactly
  -> restore backup
  -> verify restored SHA exactly equals original baseline SHA
```

Both `repositoryWritePerformed` and `productionWritePerformed` must remain false.

This is stronger than the earlier abstract rollback-plan simulation because it rehearses actual candidate/baseline bytes, but it is still not a real production cutover.

## Exact rollback target rule

Legacy rollback validation must test the production rollback target that would actually be used, not an arbitrary development compatibility copy.

The workflow therefore:
1. fetches `origin/main`;
2. captures its exact commit SHA;
3. creates a detached worktree at that SHA;
4. compiles the retained production/recovery runtime there;
5. runs retained dependency/artifact regression tests;
6. runs that exact production `source_processor.py --dry-run` with production credentials/read access;
7. performs no production writes.

This distinction matters because development compatibility code can legitimately diverge from the exact active production rollback target.

## Credential evidence

The credential gate requires:
- `automation/validate_config.py` PASS;
- exact production rollback target can perform the required source/data access in dry-run mode;
- no secret value is persisted into evidence artifacts.

The gate verifies usable credentials/read access, not merely the existence of secret names.

## Monitoring evidence

The workflow probes the fixed production URL three times with cache-busting query parameters.

Monitoring readiness requires:
- 3/3 successful HTTP probes;
- HTTP success;
- the exact active `unipalm-build` marker from the current `main` pipeline state is present in every response;
- the candidate itself contains the future release-monitoring markers.

This verifies that current production observability works before a cutover is attempted.

## Repository deployment guard

`repository_deployment_guard_verified` is intentionally fail-closed.

PASS requires:
- production branch is `main`;
- GitHub reports the branch/ruleset as protected;
- direct production pushes are server-side restricted.

A CI check, README rule, or workflow convention alone is insufficient because it does not prevent an out-of-band direct push.

Current state: `main protected=false`, therefore this gate correctly remains false.

## Evidence promotion

The hardening engine emits `production_cutover_evidence_candidate.json`. Evidence is promoted to `ops/production_cutover_evidence.json` only for observations that actually passed.

Current canonical state:
- 7 checks `ready=true` with automated evidence/reviewer/timestamp;
- `repository_deployment_guard_verified=false` with explicit blocker evidence.

After evidence promotion, Production Cutover Control is rerun. It must independently consume the canonical evidence and reproduce the remaining blocker rather than trusting the hardening summary.

## Safety invariants

Always false in v1:
- production write performed;
- repository write performed by rehearsal;
- production Data Mart written;
- production UI/index modified;
- production deployment performed;
- platform mutation allowed;
- authenticated executor bound;
- execution enabled;
- execution permit issued;
- production activation enabled;
- automatic cutover enabled;
- automatic rollback enabled.

## Failure boundary

If any artifact, rollback target, credential, monitoring or governance check fails:
- that readiness row stays `ready=false`;
- downstream Cutover Control remains blocked;
- upstream validated artifacts remain untouched;
- no weaker substitute may be used simply to reach a READY state.

A changed release lineage or production baseline must be re-evidenced before cutover approval.

## Next transition

This milestone is complete when its evidence engine and monitoring/rehearsal controls are validated, even if a real external governance gate remains blocked.

The next operational dependency is to enable and reverify an appropriate server-side GitHub production-branch protection/ruleset. Only then may Production Cutover Control advance from `BLOCKED` toward `READY_FOR_EXPLICIT_APPROVAL`; that still does not deploy production.
