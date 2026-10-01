# Anomaly Detection Foundation v1

Status: **VALIDATED PREPRODUCTION MILESTONE**

Validated on 2026-09-25.

Final validation:
- GitHub Actions run `36120626467` (#360) — **PASS end-to-end**
- runtime checkpoint: `83b6f3761f5fb4acb937b05a8f65a2314a93bce8`

## Objective

Build a robust statistical detector that can produce analytical evidence only after Anomaly Eligibility Guardrails allow evaluation.

This is the final **intelligence foundation** layer.

It does not:
- publish an operator anomaly verdict;
- assign severity;
- trigger alerts;
- diagnose causes;
- make causal claims.

## Contracts

Historical Intelligence:
- contract `1.6`

UI Payload:
- contract `1.10`

Native:
- patch `native-anomaly-detection-foundation-v20`

V2 compatibility:
- patch `v2-anomaly-detection-foundation-v10`

## Detector states

Exactly three detector states are allowed:

- `NORMAL`
- `DEVIATION_CANDIDATE`
- `NOT_EVALUATED`

`DEVIATION_CANDIDATE` is statistical evidence only. It is explicitly **not an alert**.

## Statistical method

Method:
`MODIFIED_Z_SCORE_MAD`

For an eligible KPI:

`modified_z = 0.67448975 × (current - baseline_median) / baseline_MAD`

The context-matched historical baseline now stores:
- median;
- mean;
- min;
- max;
- MAD.

Absolute modified-Z threshold:
`3.5`

A KPI becomes `DEVIATION_CANDIDATE` only when all gates pass:

1. metric anomaly eligibility = `ANOMALY_ELIGIBLE`;
2. matched baseline statistics exist;
3. MAD > 0;
4. baseline median != 0 for relative effect measurement;
5. directionality gate passes;
6. minimum effect-size gate passes;
7. `abs(modified_z) >= 3.5`.

Otherwise an evaluated KPI is `NORMAL`.

If the robust score cannot be evaluated safely, status is `NOT_EVALUATED`.

## Fail-closed cases

No score is published when:
- anomaly eligibility is blocked;
- matched baseline statistics are unavailable;
- MAD = 0;
- relative effect is undefined because baseline median = 0.

Canonical reasons:
- `ANOMALY_ELIGIBILITY_BLOCKED`
- `BASELINE_STATISTICS_UNAVAILABLE`
- `ROBUST_SCALE_ZERO`
- `RELATIVE_EFFECT_UNDEFINED`

For every `NOT_EVALUATED` KPI:
- `scorePublished=false`
- `modifiedZScore` is absent.

## Minimum effect sizes

Configured relative effect gates:

- GMV: 15%
- Orders: 15%
- Product Clicks: 15%
- AOV: 10%
- CVR: 10%
- Ads Spend: 20%
- Ads Attributed Sales: 15%
- ROAS: 15%
- Cancelled Sales: 25%
- Net Sales After Cancel: 15%
- Order Fees: 20%
- Total Platform Cost Ratio: 15%

These thresholds prevent tiny statistical deviations from becoming candidates solely because historical variance is low.

## KPI directionality

Lower-only:
- GMV
- Orders
- Product Clicks
- AOV
- CVR
- Ads Attributed Sales
- ROAS
- Net Sales After Cancel

Higher-only:
- Cancelled Sales
- Total Platform Cost Ratio

Two-sided:
- Ads Spend
- Order Fees

Directionality controls candidacy, not business diagnosis.

## Synthetic validation

Repository tests prove all three detector states.

### NORMAL

With:
- 3 complete trusted months;
- READY same-weekday comparator;
- READY context-matched baseline;
- non-zero MAD;
- current GMV near historical median;

the detector:
- publishes a modified Z-score;
- remains `NORMAL`;
- does not alert.

### DEVIATION_CANDIDATE

With the same valid history/context but a materially lower GMV:
- eligibility remains READY;
- lower-only direction gate passes;
- effect exceeds 15%;
- absolute modified Z exceeds 3.5;
- GMV becomes `DEVIATION_CANDIDATE`.

Still:
- no severity;
- no alert;
- no diagnosis;
- no causal claim.

### NOT_EVALUATED

With blocked anomaly eligibility:
- detector returns `NOT_EVALUATED`;
- no score is published.

## Real September 2026 result

The current real dataset remains intentionally blocked by upstream eligibility.

### Portfolio

Current trusted observation:
`2026-09-17`

Foundation result:
- status: `NOT_EVALUATED`
- evaluated KPI checks: 0
- normal KPI checks: 0
- deviation candidates: 0
- not evaluated KPI checks: 60

Reason chain for Same Weekday includes:
- `PORTFOLIO_LIFECYCLE_HISTORY_TOO_SHORT`
- `INSUFFICIENT_CONTEXT_MATCHED_HISTORY`
- `CONTEXT_DIFFERENT`

Therefore all 12 Same Weekday KPI results:
- `NOT_EVALUATED`
- `scorePublished=false`

### SYT+

Current trusted observation:
`2026-09-17`

Foundation result:
- status: `NOT_EVALUATED`
- evaluated KPI checks: 0
- deviation candidates: 0
- not evaluated KPI checks: 60

Primary block:
- `INSUFFICIENT_HISTORY_DEPTH`

Same Weekday also remains blocked by:
- insufficient context-matched history;
- different exact campaign context.

### Mall

Current trusted observation:
`2026-09-23`

Foundation result:
- status: `NOT_EVALUATED`
- evaluated KPI checks: 0
- deviation candidates: 0
- not evaluated KPI checks: 60

Primary lifecycle block:
- `SHOP_LIFECYCLE_HISTORY_TOO_SHORT`

Same Weekday also has:
- `INSUFFICIENT_CONTEXT_MATCHED_HISTORY`
- `CONTEXT_UNKNOWN`

This correctly treats Mall as a young shop rather than a missing-data shop.

## Runtime capabilities

Historical:
- `anomalyEligibilityGuardrails=true`
- `anomalyDetectionFoundation=true`
- `anomalyDetection=false`
- `contextMatchedBaseline=false`
- `historicalAlerts=false`
- `historicalDiagnosis=false`

UI Payload:
- `anomalyDetectionFoundation=true`
- `anomalyDetection=false`

The distinction is intentional:

`anomalyDetectionFoundation=true`
means PREPRODUCTION evidence machinery exists.

`anomalyDetection=false`
means anomaly detection is not an active operator capability.

## Run #360 lineage

Business Context fingerprint:
`d4fef77fe3f18d2e9b91ea611dbcd755372fff1e9fc5e29739fb851b9a0a8cd0`

Historical fingerprint:
`e384f879a271bfdef205b68d5be7f131f937e311f6331370a6ed4586cea1adb2`

UI Payload fingerprint:
`3c813f82d87dd53214a7d311b9f639db6ce378893f4423f5ac7ac68a2dd12f85`

Native fingerprint:
`2cf8c07762c0c0b1b89ca422de17eae302292705a82e794b09f8778e636d2c4b`

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
- anomaly eligibility guardrails fail-closed: PASS
- anomaly detection foundation fail-closed: PASS

UI Payload QA:
- PASS
- failed checks: 0
- anomaly eligibility binding: PASS
- operational anomaly detection capability off: PASS
- anomaly detection foundation binding fail-closed: PASS

Native QA:
- PASS
- 32 checks
- failed checks: 0

Native wording includes:
- `Detector nền tảng: chưa đánh giá`
- `Detector cùng-thứ: NOT_EVALUATED`
- deviation-candidate wording explicitly says it is not an alert.

## Artifacts

Run #360:
- staging: `10856852993`
- processed: `10857181294`
- semantic: `10857350625`
- Business Context: `10857960127`
- Historical Intelligence: `10858055158`
- UI Payload: `10858355014`
- Native V2: `10858350019`

Historical artifact digest:
`sha256:b31d4179b40552c3d8b86cb608f8e4cf1aaae39492cfcc612506b5eb2c58b8b7`

UI Payload digest:
`sha256:ae267fc5c4570bcb0588a0a84de8eb029c3e81f49cc3569fee219a9640d4ae38`

Native artifact digest:
`sha256:84a3d2636a765fd2f2e392d286c416aca18f80867a564f82aa63c4203755c0ec`

## Safety boundary

Still disabled:
- operational anomaly detection;
- anomaly severity;
- automatic alerts;
- diagnosis;
- causal claims;
- production Data Mart write;
- production UI/index modification;
- production deployment.

## Intelligence foundation status

With this milestone, the **Intelligence Foundation is complete**:

1. trusted historical data;
2. lifecycle-aware history;
3. factual historical comparators;
4. explicit Business Context Calendar;
5. context qualification;
6. context-matched historical baseline;
7. anomaly eligibility guardrails;
8. robust anomaly detection foundation.

The system can now safely answer:

- what happened;
- how it compares with history;
- whether the comparison context is compatible;
- whether enough matched history exists;
- whether anomaly evaluation is allowed;
- and, when allowed, whether the observation is statistically ordinary or a deviation candidate.

It still cannot yet responsibly answer:
- how severe the issue is;
- why it happened;
- what action should be taken.

## Anomaly Severity & Confidence v1 — completed

Completed in run `36122612645` (#371).

See:
- `docs/anomaly-severity-confidence-v1.md`

Candidate-only severity/confidence evidence is now implemented.

Current real result:
- Portfolio / SYT+ / Mall = `NOT_ASSESSED`;
- no severity/confidence scores are emitted because there are no real deviation candidates yet;
- operational severity, alerts and diagnosis remain OFF.

The next milestone is **Diagnosis / Driver Attribution Foundation v1**.
