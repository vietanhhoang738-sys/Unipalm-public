# Smart Issues Foundation v1

Status: **VALIDATED PREPRODUCTION MILESTONE**

Validated on 2026-09-25.

Final validation:
- GitHub Actions run `36126435907` (#395) — **PASS end-to-end**
- runtime checkpoint: `d9beda8c7158d03b5f8af6f3eb67ec91f442b064`

## Objective

Synthesize the validated intelligence evidence chain into a durable operator-facing issue object.

A Smart Issue is an evidence bundle. It is not:
- an automatic alert;
- an operational diagnosis;
- a causal claim;
- an autonomous action recommendation.

## Contracts

Historical Intelligence:
- contract `1.9`

UI Payload:
- contract `1.13`

Native:
- patch `native-smart-issues-foundation-v23`

V2 compatibility:
- patch `v2-smart-issues-foundation-v13`

## Issue states

Allowed states:
- `ISSUE_READY`
- `NO_ISSUE`

An issue is emitted only when the evidence chain passes all required gates.

## Evidence gates

Required:
1. detector = `DEVIATION_CANDIDATE`;
2. severity >= MEDIUM;
3. confidence >= MEDIUM;
4. driver boundary = `ATTRIBUTED` or `ASSOCIATION_ONLY`.

If any required gate fails:
- no issue is created.

## Issue object

A Smart Issue binds:
- deterministic issue ID;
- scope;
- observation date;
- source comparator;
- affected KPI;
- current value;
- context-matched baseline median;
- relative effect;
- modified Z-score;
- signal severity;
- evidence confidence;
- attribution boundary;
- top identity contributor when available;
- associated candidate signals when attribution is unavailable;
- Business Context evidence;
- matched-sample depth;
- lifecycle/history evidence;
- unresolved uncertainty.

Every issue explicitly keeps:
- `automaticAlertEligible=false`
- `actionRecommendationEligible=false`
- `operationalDiagnosisEnabled=false`
- `causalClaimEligible=false`

## Surface policy

Smart Issues are attached to:
`LATEST_TRUSTED_OBSERVATION`

In Native V2 this maps to:
- **Ngày gần nhất**

It is not copied into 7D or MTD merely because those tabs exist.

The issue retains its actual statistical `sourceComparator` such as `sameWeekday`, so the UI surface and evidence source remain distinct and auditable.

## Deduplication

Policy:
- max 1 issue per comparator;
- dedupe scope-level issues by `AFFECTED_METRIC`;
- max 5 issues per scope.

This prevents a single underlying KPI deviation from producing many repeated operator cards.

## Ranking

Ranking order:
1. attribution status;
2. business KPI priority;
3. severity score;
4. confidence score;
5. absolute effect size.

Attribution priority:
- `ATTRIBUTED` > `ASSOCIATION_ONLY`.

Business KPI priority:
- GMV: 100
- Orders: 90
- ROAS: 85
- Net Sales After Cancel: 80
- Platform Cost Ratio: 75
- CVR: 70
- AOV: 65
- Product Clicks: 60
- Ads Attributed Sales: 55
- Cancelled Sales: 50
- Ads Spend: 45
- Order Fees: 40

This policy was added after synthetic QA showed that a derived cost ratio could otherwise outrank the primary GMV issue in the same comparator.

## Uncertainty contract

At the original #395 checkpoint, every issue retained:
- `CAUSALITY_NOT_ESTABLISHED`
- `AUTOMATIC_ALERTS_DISABLED`
- `ACTION_POLICY_NOT_DEFINED`

After Operator Action Policy Foundation v1 (#405), the last item is superseded by:
- `HUMAN_REVIEW_REQUIRED`
- `PLATFORM_MUTATION_DISABLED`

The current contract keeps causal/alert uncertainty while acknowledging that a review-only action policy now exists.

Additional uncertainty:
- `IDENTITY_CONTRIBUTION_NOT_CAUSAL` for exact identity attribution;
- `ASSOCIATION_ONLY_NOT_ATTRIBUTION` for association-only issues;
- `CONTEXT_COMPATIBILITY_NOT_CONFIRMED` when exact context compatibility is not established.

## Synthetic validation

### Attributed GMV issue

Controlled evidence:
- history READY;
- context-matched baseline READY;
- GMV = `DEVIATION_CANDIDATE`;
- severity HIGH;
- confidence HIGH;
- GMV attribution = `ATTRIBUTED`;
- AOV is the top identity contribution.

Result:
- `ISSUE_READY`;
- one scope-level issue;
- affected KPI = `placedGmv`;
- source comparator = `sameWeekday`;
- top driver = `placedAov`;
- no alert/action/diagnosis/causal flag.

### Association-only issue

Controlled evidence:
- GMV remains NORMAL;
- AOV becomes `DEVIATION_CANDIDATE`;
- AOV has no supported independent business identity.

Result:
- `ISSUE_READY`;
- affected KPI = `placedAov`;
- attribution boundary = `ASSOCIATION_ONLY`;
- no fabricated top driver;
- uncertainty explicitly states association is not attribution.

### Blocked / normal paths

If detector is `NORMAL` or `NOT_EVALUATED`:
- `NO_ISSUE`;
- issue count = 0.

## Native V2 behavior

The existing V2 issue surface is reused.

Foundation behavior:
- issue card is visible when an issue exists;
- empty state remains visible when no issue qualifies;
- foundation issue action displays `Bằng chứng đã tổng hợp`;
- diagnosis drawer is disabled unless `operationalDiagnosisEnabled=true`.

Current value remains false.

This prevents the UI from implying that an operational diagnosis or action capability already exists.

## Real September 2026 result

Current real data still has no detector candidate because trusted-history/context-matched depth is insufficient.

### Portfolio
- Smart Issues status: `NO_ISSUE`
- issue count: 0

### SYT+
- Smart Issues status: `NO_ISSUE`
- issue count: 0

### Mall
- Smart Issues status: `NO_ISSUE`
- issue count: 0

For every real scope:
- automatic alerts = false;
- action recommendations = false;
- operational diagnosis = false;
- causal claims = false.

This is the correct fail-closed result.

## Runtime capabilities

Enabled evidence machinery:
- `anomalyEligibilityGuardrails=true`
- `anomalyDetectionFoundation=true`
- `anomalySeverityConfidence=true`
- `driverAttributionFoundation=true`
- `smartIssuesFoundation=true`

Still operationally disabled:
- `anomalyDetection=false`
- `anomalySeverity=false`
- `diagnosis=false`
- `smartIssues=false`
- automatic alerts;
- action recommendations;
- causal claims.

## Run #395 lineage

Business Context fingerprint:
`d4fef77fe3f18d2e9b91ea611dbcd755372fff1e9fc5e29739fb851b9a0a8cd0`

Historical fingerprint:
`ffec9afddff8af536aecb8ef5cd890ab22830d50f2a502e095aba729ed5b5f8c`

UI Payload fingerprint:
`dfcceccf489224e2129512ecdec380b5ece58d794ea3edd9bb26d648871fa9b5`

Native fingerprint:
`dadfbf83b835f7b3fd21ba85ee5a49b35845d52b01e081a73db19d5df47aef45`

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

UI Payload QA:
- PASS
- failed checks: 0
- Smart Issues binding evidence-only: PASS
- operational Smart Issues off: PASS

Native QA:
- PASS
- failed checks: 0
- patch: `native-smart-issues-foundation-v23`
- compatibility: `v2-smart-issues-foundation-v13`

## Artifacts

Run #395:
- staging: `10859743747`
- processed: `10858764003`
- semantic: `10858953905`
- Business Context: `10859938531`
- Historical Intelligence: `10859013843`
- UI Payload: `10859973639`
- Native V2: `10859248888`

Historical digest:
`sha256:9b96942a639931ef55eb4f642333a7e2f71ca3466f90ced1a630318c167f7f89`

UI Payload digest:
`sha256:ffc1a6fb5a12ab1cb55b91a1d0eab3d3dbdfbb049e7fa4d1a2252971eefd9e7e`

Native digest:
`sha256:5da19e35e2188b062ca238df99613c02fa2c83a05de1f8ffa977eb50baba76f8`

## Safety boundary

Still disabled:
- automatic alerts;
- action recommendations;
- operational diagnosis;
- causal claims;
- operational anomaly detection/severity;
- production Data Mart write;
- production UI/index modification;
- production deployment.

## Operator Action Policy Foundation v1 — completed

Completed in run `36128842184` (#405).

See:
- `docs/operator-action-policy-foundation-v1.md`

The system now creates bounded, human-review-only action options from qualified Smart Issues while keeping platform mutation, automatic execution, alerts and causal claims OFF.

Current real result:
- Portfolio / SYT+ / Mall = `NO_ACTION_OPTIONS`;
- no option is fabricated while real Smart Issues remain `NO_ISSUE`.

The next milestone is **Production Cutover Readiness / Shadow Mode v1**.
