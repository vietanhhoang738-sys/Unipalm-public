# Production Cutover Readiness / Shadow Mode v1

Implementation date: 2026-09-25  
Status: PREPRODUCTION / observe-only  
Production cutover: **not authorized**

## Purpose

This milestone validates the completed intelligence and operator-policy stack across repeated real refreshes without activating production behavior.

It adds a durable shadow-state contract for:

- trusted lineage continuity across refreshes;
- enabled-shop scope completeness;
- fail-closed safety verification;
- Smart Issue and Action Option appearance, persistence and disappearance;
- consecutive safe/stable refresh gates;
- explicit activation and rollback controls;
- a human-owned production cutover checklist.

It does not add a new intelligence concept and does not change the approved visual baseline.

## Contracts

- Historical Intelligence: `2.1`
- UI Payload: `1.15`
- Native patch: `native-production-shadow-mode-v25`
- V2 compatibility patch: `v2-production-shadow-mode-v15`
- mode: `PREPRODUCTION_OBSERVE_ONLY`

Allowed status values:

- `SHADOW_OBSERVING`
- `READY_FOR_HUMAN_CUTOVER_REVIEW`
- `CUTOVER_BLOCKED`

`READY_FOR_HUMAN_CUTOVER_REVIEW` is evidence that the configured shadow gates passed. It is not cutover authorization.

## Refresh identity and persistence

Every staging refresh receives an explicit `refreshId` from:

`github.run_id + github.run_attempt`

The history artifact now includes:

`shadow_mode_state.json`

Before the next all-shop history build, the workflow locates the latest non-expired successful history artifact for the same month and supplies that state to the builder.

Rules:

- a distinct refresh ID advances refresh counters;
- a repeated refresh ID is idempotent and cannot manufacture readiness;
- only the latest configured number of refresh records is retained;
- missing prior state starts a new observation sequence at refresh 1;
- source period/month regression blocks readiness.

## Source snapshot and lineage

Each shadow refresh records:

- as-of period;
- trusted Semantic month list;
- trusted Semantic fingerprints;
- Business Context fingerprint;
- deterministic source snapshot key.

Lineage states:

- `INITIALIZED`
- `CONSISTENT`
- `ADVANCED`
- `REGRESSION_BLOCKED`

A source snapshot is incomplete when trusted Semantic fingerprints are missing/misaligned, Business Context is missing, or a scope has no latest trusted observation.

## Issue/action transition semantics

The current shadow state stores deterministic Smart Issue IDs and Action Option IDs across Portfolio and all enabled Shop scopes.

Each refresh classifies both object types as:

- appeared;
- persisted;
- disappeared.

Fail-closed lineage rules:

- every current Action Option must reference a current Smart Issue;
- an Action Option cannot persist after its source Smart Issue disappears;
- a normal refresh may clear an issue and all of its actions;
- a state change resets the consecutive stability counter;
- disappearance is evidence-state evolution, not automatic resolution or a platform action.

## Readiness gates

All gates are explicit:

1. `TRUSTED_LINEAGE_COMPLETE`
2. `LINEAGE_CONTINUITY`
3. `ALL_ENABLED_SCOPES_PRESENT`
4. `FAIL_CLOSED_SAFETY`
5. `ISSUE_ACTION_TRANSITIONS_VALID`
6. `MINIMUM_SAFE_REFRESHES`
7. `MINIMUM_STABLE_REFRESHES`
8. `HUMAN_VISUAL_BASELINE_RETAINED`

The minimum is currently:

- 3 consecutive safe refreshes;
- 3 consecutive stable refreshes.

The human-reviewed visual baseline remains run `#216`.

## Activation controls

Always false in v1:

- `productionActivationAllowed`
- `automaticCutoverEnabled`
- `cutoverAuthorized`
- production writes
- platform mutation
- automatic alerts

Cutover requires explicit human approval after every readiness gate passes.

The checklist deliberately remains pending for:

- explicit human cutover approval;
- explicit production deployment approval.

## Rollback controls

The current legacy production pipeline remains the rollback target.

Required controls:

- legacy production path retained;
- rollback required before activation;
- no automatic rollback;
- no modification of production Data Mart, production UI/index or deployment in this milestone.

## Propagation

Shadow evidence is propagated through:

`Historical Intelligence → canonical UI Payload → Native V2 bundle`

The Native bundle carries the state for audit/inspection but does not render an activation control or change the approved visual design.

## Synthetic validation

Covered cases:

- three distinct safe/stable refreshes advance from `SHADOW_OBSERVING` to `READY_FOR_HUMAN_CUTOVER_REVIEW`;
- repeating the same refresh ID does not advance counters;
- an issue/action candidate followed by a normal refresh records both objects as disappeared;
- lineage regression produces `CUTOVER_BLOCKED`;
- cutover/activation remains false even when all readiness gates pass;
- UI Payload and Native V2 preserve the observe-only boundary.

## Local QA

Core repository suite:

- 133 tests
- 133 PASS
- 0 FAIL

Additional checks:

- JSON contracts parse successfully;
- Python compileall: PASS;
- production V2 template foundation: PASS;
- configuration validator reached only the expected local missing-secret guard.

## Canonical real-data validation

GitHub Actions run `36163777627` (#407), commit `f3ece03c7e52d829139481e09b2a11539ce254bb`, is the first canonical all-shop September shadow observation. Both `core-tests` and full `staging` passed.

Observed evidence:

- refresh ID: `36163777627-1`;
- status: `SHADOW_OBSERVING`;
- refresh sequence: `1`;
- consecutive safe refreshes: `1/3`;
- consecutive stable refreshes: `1/3`;
- lineage status: `INITIALIZED`, with lineage validation PASS;
- failed gates: none;
- pending gates: `MINIMUM_SAFE_REFRESHES`, `MINIMUM_STABLE_REFRESHES`;
- Historical fingerprint: `f7e4bccea88a06614279d43e6dfcde2235e73b32c1d7e00b1c404fb3135172f9`;
- UI Payload fingerprint: `ee828633b42fec15a759d11ff9fa7bc8b909f6d3b6cbfa29720f953d5d50b5ef`;
- Native fingerprint: `1706c59f67b1d8db6fe25a29c0532ec0c9c8f4c33c7129d828574623a408d801`.

This observation cannot be declared cutover-ready because the contract requires three distinct successful refreshes.

### Canonical observation 2

GitHub Actions run `36165107810` (#408), commit `36a3e16317be068c5362d25fd2e602b3979a278f`, completed successfully on 2026-09-26.

Observed evidence:

- refresh ID: `36165107810-1`;
- previous refresh ID: `36163777627-1`;
- status: `SHADOW_OBSERVING`;
- refresh sequence: `2`;
- consecutive safe refreshes: `2/3`;
- consecutive stable refreshes: `2/3`;
- lineage status: `CONSISTENT`, with lineage validation PASS;
- source snapshot key unchanged at `4165d021b6faf0b8f9e9255a4845c7a3f109e1fc9aca99597c25df4889ac2b10`;
- failed gates: none;
- pending gates: `MINIMUM_SAFE_REFRESHES`, `MINIMUM_STABLE_REFRESHES`;
- Historical fingerprint: `e8872de70b6568c8ea865eca23de34fecb3c8fe1db48b4a69558de94393065a7`;
- UI Payload fingerprint: `43ec276ff68eb063d91ea798c5b09a2855e5f13c991e4dfd8133d1a68fc89d5a`;
- Native fingerprint: `0b20678448d9ff2da75166624d125556aaf518950e5479b1303f0d3d0a9ab57f`;
- history artifact ID: `10877686004`, digest `sha256:826f7d3ed2f909a2aed49df1b5f30e0e5eb1a4085af8b6b80fd006406a4abbd5`.

Observation 2 proves that the workflow restored observation 1 state and advanced continuity without changing the trusted source snapshot. Production activation remains unauthorized.

### Canonical observation 3

GitHub Actions run `36166448309` (#409), commit `32e486e9ee009079c3ffc00d8eb0d1358ca19336`, completed successfully on 2026-09-26.

Observed evidence:

- refresh ID: `36166448309-1`;
- previous refresh ID: `36165107810-1`;
- status: `READY_FOR_HUMAN_CUTOVER_REVIEW`;
- refresh sequence: `3`;
- consecutive safe refreshes: `3/3`;
- consecutive stable refreshes: `3/3`;
- lineage status: `CONSISTENT`, with lineage validation PASS;
- source snapshot key remained `4165d021b6faf0b8f9e9255a4845c7a3f109e1fc9aca99597c25df4889ac2b10` across all three observations;
- all eight readiness gates: PASS;
- failed gates: none;
- pending gates: none;
- Historical QA: `17/17 PASS`, fingerprint `633d754808b8650bb357646bbbc9127a1cf5fe21c98d2680ed3a01af5241ea1e`;
- UI Payload fingerprint: `97b83b7d491b7ec47a4803a62f652fcc53dd8d0ce604a2d917b87eea3df6d75c`;
- Native QA: `33/33 PASS`, fingerprint `0f712159ee14398936e3667b68966b65f403fc452cd28025ddd3cedf46dbd223`;
- source production V2 SHA256 remained `9540f23b4d9537441e3bd4cdeafd15747ab4280a87a0130d223984009d99c952`;
- history artifact ID: `10877828363`, digest `sha256:9caffa79a10ff5fdf54fa2a310acd879c63e77e8900f39f4d058bed7dc4cd885`;
- Native V2 artifact ID: `10877143917`, digest `sha256:403bd90dff0c760430eb17cfc748b07d9b7e9f306b56e9f695f6d5d5d4504a7e`.

Observation 3 satisfies the automated shadow-readiness thresholds. It does not authorize production cutover: `productionActivationAllowed`, `automaticCutoverEnabled`, `cutoverAuthorized`, production writes and platform mutation remain false.

### UI canary smoke validation

The exact Native V2 HTML from run #409 was served locally as a read-only canary and inspected in a browser. The smoke validation passed:

- meaningful page content rendered with no error overlay or browser console errors;
- `Command Center > Toàn hệ thống` rendered the latest-day, rolling-7-day and MTD views;
- `Command Center > Theo shop` rendered both SYT+ and Mall, and shop switching updated the URL and bound data;
- the separate `So sánh Shop` destination rendered the same-period shop comparison, GMV drivers, order funnel, costs, Ads, traffic and product sections;
- light/dark mode switching worked;
- `PREPRODUCTION` and `Data healthy` remained visible;
- no production Data Mart, production index, deployment or activation control was modified.

This is an automated/operator smoke check, not the final human visual acceptance. The accepted human-reviewed visual baseline remains run #216 until a reviewer explicitly approves the #409 canary.

Expected current evidence remains:

- Processed SYT+: NOOP;
- Processed Mall: NOOP;
- Semantic: NOOP;
- Smart Issues: `NO_ISSUE` on current real data;
- Operator Action Policy: `NO_ACTION_OPTIONS`;
- Shadow Mode: `READY_FOR_HUMAN_CUTOVER_REVIEW` after observation 3;
- production cutover: not authorized.

Do not manufacture issues/actions or duplicate refresh IDs to satisfy the stability gates.

## Next milestone

Perform the human UI canary acceptance and Cutover Readiness Review. Production activation remains a separate explicitly approved decision.
