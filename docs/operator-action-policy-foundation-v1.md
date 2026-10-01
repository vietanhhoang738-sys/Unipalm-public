# Operator Action Policy Foundation v1

Status: **VALIDATED PREPRODUCTION MILESTONE**

Validated on 2026-09-25.

Final validation:
- GitHub Actions run `36128842184` (#405) — **PASS end-to-end**
- runtime checkpoint: `31ddeef18ba0fd881c7560541bf384edf897084c`

## Objective

Transform a qualified `ISSUE_READY` Smart Issue into bounded, reviewable operator options.

This layer is intentionally **review-only**.

It does not:
- change bids;
- change budgets;
- change prices;
- change promotions;
- pause campaigns;
- publish listing changes;
- contact customers automatically;
- execute any platform mutation;
- send automatic alerts;
- claim causality.

## Contracts

Historical Intelligence:
- contract `2.0`

UI Payload:
- contract `1.14`

Native:
- patch `native-operator-action-policy-v24`

V2 compatibility:
- patch `v2-operator-action-policy-v14`

## States

Allowed scope states:
- `ACTION_OPTIONS_READY`
- `NO_ACTION_OPTIONS`

Every action object uses:
- `status=REVIEW_OPTION`
- `executionMode=HUMAN_REVIEW_ONLY`

## Source gate

Operator Action Policy consumes only:

`ISSUE_READY`

If a scope has no Smart Issue:
- `NO_ACTION_OPTIONS`
- option count = 0.

The policy never bypasses:
- anomaly eligibility;
- detector;
- severity/confidence;
- attribution/association;
- Smart Issue gates.

## Action-option types

### 1. Evidence Validation

Every `ISSUE_READY` receives one generic option:

`VALIDATE_EVIDENCE_BEFORE_CHANGE`

Purpose:
- confirm source data;
- re-check campaign/context;
- verify the issue persists at the next refresh;
- avoid business changes based on one evidence snapshot.

### 2. Targeted Driver Review

A targeted review option is created only when:

- Smart Issue attribution = `ATTRIBUTED`;
- a quantified top driver exists;
- that driver has an explicit review rule.

Current supported review rules:

- Product Clicks → `REVIEW_TRAFFIC_AND_LISTING_VISIBILITY`
- CVR → `REVIEW_CONVERSION_FUNNEL_AND_OFFER`
- AOV → `REVIEW_AOV_PRICE_PROMOTION_MIX`
- Ads Spend → `REVIEW_ADS_SPEND_EFFICIENCY`
- Ads Attributed Sales → `REVIEW_ADS_ATTRIBUTED_SALES`
- Cancelled Sales → `REVIEW_CANCELLATION_AND_FULFILLMENT`
- Order Fees → `REVIEW_FEE_AND_PROMOTION_COST`
- Net Sales After Cancel → `REVIEW_NET_SALES_QUALITY`

`ASSOCIATION_ONLY` issues do **not** receive a targeted driver action.

They receive evidence validation only.

## Action object

Every review option carries:

- deterministic `actionOptionId`;
- source Smart Issue ID;
- scope;
- observation date;
- affected KPI;
- statistical source comparator;
- severity / confidence / attribution lineage;
- why the option is relevant;
- prerequisites;
- KPIs to monitor;
- verification checks;
- stop / reversal checks;
- unresolved uncertainty.

Every option explicitly carries:

- `requiresHumanReview=true`
- `prescriptiveRecommendation=false`
- `platformMutationAllowed=false`
- `automaticExecutionEligible=false`
- `automaticAlertEligible=false`
- `causalClaimEligible=false`

## Bounded policy

Limits:

- maximum 2 options per Smart Issue;
- maximum 6 options per scope.

This prevents a single issue from generating an uncontrolled task list.

## Forbidden directives

The foundation contract explicitly forbids:

- `CHANGE_BID`
- `CHANGE_BUDGET`
- `CHANGE_PRICE`
- `CHANGE_PROMOTION`
- `PAUSE_CAMPAIGN`
- `PUBLISH_LISTING_CHANGE`
- `CONTACT_CUSTOMER_AUTOMATICALLY`

## Smart Issue uncertainty update

Before this milestone, Smart Issues carried:

`ACTION_POLICY_NOT_DEFINED`

That uncertainty is no longer correct because the policy now exists.

The v2.0 contract replaces it with:

- `HUMAN_REVIEW_REQUIRED`
- `PLATFORM_MUTATION_DISABLED`

and preserves:

- `CAUSALITY_NOT_ESTABLISHED`
- `AUTOMATIC_ALERTS_DISABLED`

This is a semantic advancement, not a safety relaxation.

## Synthetic validation

### Attributed GMV issue

Controlled case:
- Smart Issue = `ISSUE_READY`;
- affected KPI = GMV;
- attribution = `ATTRIBUTED`;
- top driver = AOV.

Result:
- action policy = `ACTION_OPTIONS_READY`;
- option count = 2:
  1. `VALIDATE_EVIDENCE_BEFORE_CHANGE`
  2. `REVIEW_AOV_PRICE_PROMOTION_MIX`
- both require human review;
- no mutation or auto execution is allowed.

### Association-only issue

Controlled case:
- Smart Issue = `ISSUE_READY`;
- attribution = `ASSOCIATION_ONLY`.

Result:
- action policy = `ACTION_OPTIONS_READY`;
- option count = 1;
- only `VALIDATE_EVIDENCE_BEFORE_CHANGE` is emitted;
- no targeted driver review is fabricated.

### No issue

If Smart Issue = `NO_ISSUE`:

- action policy = `NO_ACTION_OPTIONS`;
- option count = 0.

## Native V2 behavior

Smart Issue cards can now carry review-option metadata.

When review options exist:
- the card may display the number of review options;
- diagnosis drawer remains disabled;
- action execution remains disabled.

The UI does not convert review options into clickable platform actions.

## Real September 2026 result

Real current data still has no qualified Smart Issue.

### Portfolio
- Smart Issues: `NO_ISSUE`
- Operator Action Policy: `NO_ACTION_OPTIONS`
- action option count: 0

### SYT+
- Smart Issues: `NO_ISSUE`
- Operator Action Policy: `NO_ACTION_OPTIONS`
- action option count: 0

### Mall
- Smart Issues: `NO_ISSUE`
- Operator Action Policy: `NO_ACTION_OPTIONS`
- action option count: 0

This is the correct fail-closed result.

## Runtime capabilities

Enabled foundation machinery:
- `smartIssuesFoundation=true`
- `operatorActionPolicyFoundation=true`

Still operationally disabled:
- `smartIssues=false`
- `operatorActions=false`
- diagnosis;
- automatic alerts;
- automatic execution;
- platform mutations;
- causal claims.

## Run #405 lineage

Business Context fingerprint:
`d4fef77fe3f18d2e9b91ea611dbcd755372fff1e9fc5e29739fb851b9a0a8cd0`

Historical fingerprint:
`9deab0fa9a5ce8261ea28d617e374de8f1e094bfd68c750b2a7f00a011f64f31`

UI Payload fingerprint:
`3fd323cfe6ff1c4943353909b1b83d6c012f3c98c22307e8690cbe8a66f2ceff`

Native fingerprint:
`19fbed9f4b631e3c21ea1a9e629f8f910051efe7aae08b3106626871dbd9e7c6`

Semantic fingerprint remains:
`c25b7cfe67c6d8d477e6e8cd65a466eb3c74ca4f97a3c500b0e9320f1223b321`

Processed:
- SYT+: `7d4fd9288c154e59903525c019d455ee14a807f1f25b7b5c74ed5303641b03aa` — **NOOP**
- Mall: `5cbaff93bdae6d87d6784169e5692698742beed39425536a5a8283b9e9439847` — **NOOP**

Semantic:
- **NOOP**

No canonical business fact was rewritten.

## QA

Historical QA:
- PASS
- failed checks: 0
- Smart Issues evidence-only fail-closed: PASS
- Operator Action Policy review-only fail-closed: PASS

UI Payload QA:
- PASS
- failed checks: 0
- Operator Action Policy binding review-only: PASS
- operational actions off: PASS

Native QA:
- PASS
- failed checks: 0
- patch: `native-operator-action-policy-v24`
- compatibility: `v2-operator-action-policy-v14`

## Artifacts

Run #405:
- staging: `10860214915`
- processed: `10861405045`
- semantic: `10860664752`
- Business Context: `10860664753`
- Historical Intelligence: `10860449868`
- UI Payload: `10860384902`
- Native V2: `10861275262`

Historical digest:
`sha256:51c1885ca66e2ccec8f6e9e855e6728b834d1b13c98f5687a76c95c38e38acf5`

UI Payload digest:
`sha256:dbabd5429632ad13fc4ba554f52c999bb4ca63cc460e5b061498ef67e30ea383`

Native digest:
`sha256:e5adb592bdf4da4e35cc6279c52bbaf3ed27b2238e035db9c494b6a0e285f88f`

## Safety boundary

Still disabled:
- platform mutations;
- automatic business actions;
- automatic alerts;
- operational diagnosis;
- causal claims;
- production Data Mart write;
- production UI/index modification;
- production deployment.

## Recommended next milestone

**Production Cutover Readiness / Shadow Mode v1**

The next milestone should stop adding new intelligence concepts and validate the completed stack as an operational system.

It should:
- run PREPRODUCTION intelligence in shadow mode against real refresh cycles;
- define cutover readiness gates;
- verify lineage/fingerprints across refreshes;
- verify issue/action stability and disappearance behavior;
- define rollback and production activation controls;
- preserve #216 as the approved visual baseline unless a new human visual review explicitly supersedes it.

No production cutover should happen until those gates pass.
