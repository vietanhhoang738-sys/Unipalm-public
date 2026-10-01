# Diagnosis / Driver Attribution Foundation v1

Status: **VALIDATED PREPRODUCTION MILESTONE**

Validated on 2026-09-25.

Final validation:
- GitHub Actions run `36124417830` (#381) — **PASS end-to-end**
- runtime checkpoint: `c46734268ab85983e4e1bd28958df045414295e8`

## Objective

Add a fail-closed diagnostic foundation that can separate:

1. measurable identity contribution;
2. co-moving association;
3. unsupported causal claims.

This layer is still PREPRODUCTION evidence only.

It does **not**:
- publish an operational diagnosis;
- claim causality;
- trigger alerts;
- recommend actions.

## Contracts

Historical Intelligence:
- contract `1.8`

UI Payload:
- contract `1.12`

Native:
- patch `native-driver-attribution-foundation-v22`

V2 compatibility:
- patch `v2-driver-attribution-foundation-v12`

## Allowed statuses

Exactly three driver-attribution states are used:

- `ATTRIBUTED`
- `ASSOCIATION_ONLY`
- `NOT_DIAGNOSED`

## Upstream gates

Driver attribution is candidate-only.

A metric must first pass:

`trusted facts → historical baseline → context qualification → matched baseline → anomaly eligibility → anomaly detector → severity/confidence`

The attribution layer then requires:
- detector state = `DEVIATION_CANDIDATE`;
- severity/confidence = `ASSESSED`;
- evidence confidence >= `MEDIUM`.

If any gate fails:
- `NOT_DIAGNOSED`.

## Attribution policy

Method:
`EXACT_SHAPLEY_ON_BUSINESS_IDENTITY`

Reference:
`CONTEXT_MATCHED_BASELINE_MEDIANS`

Supported identities:

### Placed GMV

`GMV = Product Clicks × CVR × AOV`

Drivers:
- Product Clicks
- CVR
- AOV

### Placed Orders

`Orders = Product Clicks × CVR`

Drivers:
- Product Clicks
- CVR

### ROAS

`ROAS = Ads Attributed Sales / Ads Spend`

Drivers:
- Ads Attributed Sales
- Ads Spend

### Net Sales After Cancel

`Net Sales = Placed GMV - Cancelled Sales`

Drivers:
- Placed GMV
- Cancelled Sales

### Total Platform Cost Ratio

`Platform Cost Ratio = (Order Fees + Ads Spend) / Net Sales After Cancel`

Drivers:
- Order Fees
- Ads Spend
- Net Sales After Cancel

## Exact Shapley behavior

For a supported identity:
- each driver is replaced from reference → current across every driver-order permutation;
- marginal contributions are averaged;
- contributions must close back to the modeled identity difference.

QA requires:
- identity closure residual <= numerical tolerance;
- no causal flag on any contribution.

Each contribution contains:
- driver current value;
- reference median;
- driver difference;
- driver direction;
- contribution value;
- contribution share of modeled gap.

## Baseline-alignment guard

Independent metric medians do not always form a perfectly closed business identity.

Therefore the layer checks:

`baseline identity residual / target baseline median`

Maximum accepted residual:
`25%`

If identity alignment is too weak:
- no Shapley contribution is published;
- result becomes `ASSOCIATION_ONLY`.

This prevents a visually neat but structurally unreliable attribution from being shown.

## Association policy

Association source:
`CO_MOVING_DEVIATION_CANDIDATES_ONLY`

If a candidate KPI has no supported business identity:
- status = `ASSOCIATION_ONLY`;
- co-moving deviation candidates may be listed;
- they are explicitly marked:
  - `relationType=CO_MOVING_DEVIATION_CANDIDATE`
  - `causalClaim=false`.

Association is not attribution.

## Synthetic validation

Repository tests prove both primary paths.

### GMV attribution

Controlled data:
- history READY;
- context-matched baseline READY;
- evidence confidence HIGH;
- current GMV materially lower;
- Product Clicks unchanged;
- CVR unchanged;
- AOV materially lower.

Result:
- GMV detector = `DEVIATION_CANDIDATE`;
- GMV driver attribution = `ATTRIBUTED`;
- top driver = `placedAov`;
- identity = `GMV = Product Clicks × CVR × AOV`;
- Shapley contributions close exactly to modeled difference;
- causal claim remains false.

### Unsupported KPI identity

The same synthetic case makes AOV itself a deviation candidate.

AOV has no independent causal driver identity in the current contract.

Result:
- AOV attribution = `ASSOCIATION_ONLY`;
- co-moving candidate signals remain visible;
- no driver contribution is fabricated.

### Non-candidate paths

For `NORMAL` or `NOT_EVALUATED` metrics:
- attribution = `NOT_DIAGNOSED`;
- no identity contribution is published.

## Real September 2026 result

Current real data remains blocked before the detector/diagnosis stages because history and context-matched depth are still insufficient.

### Portfolio

Driver Attribution Foundation:
- status: `NOT_DIAGNOSED`
- attributed metrics: 0
- association-only metrics: 0
- not diagnosed metrics: 60

### SYT+

Driver Attribution Foundation:
- status: `NOT_DIAGNOSED`
- attributed metrics: 0
- association-only metrics: 0
- not diagnosed metrics: 60

### Mall

Driver Attribution Foundation:
- status: `NOT_DIAGNOSED`
- attributed metrics: 0
- association-only metrics: 0
- not diagnosed metrics: 60

Across all real scopes:
- non-NOT_DIAGNOSED metrics: 0
- unsafe causal/operational diagnosis flags: 0

This is the correct outcome.

The absence of a diagnosis is evidence that the guardrails are working, not a missing feature.

## Runtime capabilities

Historical:
- `anomalyEligibilityGuardrails=true`
- `anomalyDetectionFoundation=true`
- `anomalySeverityConfidence=true`
- `driverAttributionFoundation=true`

Still operationally disabled:
- `anomalyDetection=false`
- `anomalySeverity=false`
- `diagnosis=false`
- `historicalDiagnosis=false`
- historical alerts.

## Run #381 lineage

Business Context fingerprint:
`d4fef77fe3f18d2e9b91ea611dbcd755372fff1e9fc5e29739fb851b9a0a8cd0`

Historical fingerprint:
`8dd1ff703235ed18767bf9ff669c717c994e66b91f862fee312eef0ff4cd1e41`

UI Payload fingerprint:
`67cfd56615654c02b1410be2ddf5f64058df6cf2d8bee7d155e4d2af48be985d`

Native fingerprint:
`a9bb0395baf99c0c4e82241b72c3d1bcfc7a0513fabd51ccc58dbcafbe46d851`

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
- status: PASS
- failed checks: 0
- diagnosis fail-closed: PASS
- driver attribution noncausal fail-closed: PASS

UI Payload QA:
- status: PASS
- failed checks: 0
- driver attribution bound noncausal: PASS
- operational diagnosis off: PASS

Native QA:
- status: PASS
- failed checks: 0
- patch: `native-driver-attribution-foundation-v22`
- compatibility: `v2-driver-attribution-foundation-v12`

Native wording distinguishes:
- identity contribution;
- association-only evidence;
- `NOT_DIAGNOSED`;
- explicit `không phải causal claim`.

## Artifacts

Run #381:
- staging: `10858911887`
- processed: `10859386933`
- semantic: `10859766818`
- Business Context: `10859766822`
- Historical Intelligence: `10859761857`
- UI Payload: `10858782314`
- Native V2: `10859786931`

Historical digest:
`sha256:97d7088c22cbccf797ee1e2c9fb5902497f5483ff170cdbc6390839839855e3f`

UI Payload digest:
`sha256:8c41edbde0289c89af47990fe546eb1b7b58e3217ff1f9402d297133da13e22a`

Native digest:
`sha256:9e09102583daf5fcef907669f54243e32178d5b957c71956eae7d7cdd280909b`

## Safety boundary

Still disabled:
- operational diagnosis;
- causal claims;
- automatic alerts;
- operational anomaly detection/severity;
- production Data Mart write;
- production UI/index modification;
- production deployment.

## Smart Issues Foundation v1 — completed

Completed in run `36126435907` (#395).

See:
- `docs/smart-issues-foundation-v1.md`

The system can now synthesize qualified evidence into a deduplicated Smart Issue while keeping alerts, action recommendations, diagnosis and causal claims disabled.

Current real result:
- Portfolio / SYT+ / Mall = `NO_ISSUE`;
- no issue is fabricated while real anomaly eligibility remains blocked.

The next milestone is **Operator Action Policy Foundation v1**.
