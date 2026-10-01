# Anomaly Severity & Confidence v1

Status: **VALIDATED PREPRODUCTION MILESTONE**

Validated on 2026-09-25.

Final validation:
- GitHub Actions run `36122612645` (#371) — **PASS end-to-end**
- runtime checkpoint: `f656f9c73eddc54aa4c890d8a2e89c0ee45cac40`

## Objective

Assess the strength and evidence quality of a statistical deviation candidate.

This layer runs **only** when the detector state is:
`DEVIATION_CANDIDATE`

It does not run for:
- `NORMAL`
- `NOT_EVALUATED`

For those states it returns:
`NOT_ASSESSED`

## Contracts

Historical Intelligence:
- contract `1.7`

UI Payload:
- contract `1.11`

Native:
- patch `native-anomaly-severity-confidence-v21`

V2 compatibility:
- patch `v2-anomaly-severity-confidence-v11`

## Meaning boundary

Severity in this layer means:

`STATISTICAL_AND_RELATIVE_MAGNITUDE_ONLY_NOT_BUSINESS_IMPACT`

Therefore:
- HIGH severity does not mean high business damage;
- it means the detected deviation is statistically strong and materially large relative to its KPI baseline.

Confidence means quality of evidence supporting the deviation candidate.

Neither field is:
- an alert;
- a diagnosis;
- a causal claim;
- an action recommendation.

## Severity score

Method:
`WEIGHTED_SIGNAL_STRENGTH`

Components:

1. Statistical strength

`min(abs(modified_z) / (z_threshold × 2), 1)`

2. Relative effect strength

`min(abs(effect_pct) / (minimum_effect_pct × 3), 1)`

Weights:
- statistical strength: 50%
- relative effect strength: 50%

Severity score range:
`0..1`

Levels:
- LOW: score < 0.55
- MEDIUM: 0.55 <= score < 0.80
- HIGH: score >= 0.80

## Confidence score

Method:
`WEIGHTED_EVIDENCE_QUALITY`

Components:

1. Context-matched sample depth
   - `min(sample_count / (required_sample_count × 2), 1)`
   - weight: 50%

2. Exact Context lineage
   - verified matching signature exists
   - weight: 20%

3. History readiness
   - scope history status is READY
   - weight: 15%

4. Robust scale validity
   - detector has a published score and MAD > 0
   - weight: 15%

Confidence score range:
`0..1`

Levels:
- LOW: score < 0.60
- MEDIUM: 0.60 <= score < 0.85
- HIGH: score >= 0.85

## Candidate-only rule

For every detector metric:

### If `DEVIATION_CANDIDATE`

The layer must publish:
- severity score;
- severity level;
- confidence score;
- confidence level;
- evidence components.

### If `NORMAL` or `NOT_EVALUATED`

The layer must return:
- `status=NOT_ASSESSED`
- `severityPublished=false`
- `confidencePublished=false`

and must not include:
- `severityScore`
- `confidenceScore`

This prevents an ordinary or unevaluated KPI from receiving a misleading severity label.

## Synthetic validation

Repository unit tests prove:

### Candidate path

A controlled case with:
- READY history;
- READY context-matched baseline;
- enough compatible samples;
- materially lower GMV;
- modified Z beyond the detector threshold;

produces:
- detector = `DEVIATION_CANDIDATE`
- severity/confidence = `ASSESSED`
- severity = HIGH
- confidence = HIGH

Still:
- `businessImpactClaim=false`
- alert = false
- diagnosis = false
- causal claim = false

### NORMAL path

A statistically ordinary eligible GMV:
- detector = `NORMAL`
- severity/confidence = `NOT_ASSESSED`
- no severity/confidence scores are emitted.

### NOT_EVALUATED path

A KPI blocked by anomaly eligibility:
- detector = `NOT_EVALUATED`
- severity/confidence = `NOT_ASSESSED`
- no severity/confidence scores are emitted.

## Real September 2026 result

Current data still contains no detector candidate because upstream eligibility is blocked.

### Portfolio

Current detector:
- `NOT_EVALUATED`
- deviation candidate count: 0
- not evaluated metric checks: 60

Severity/Confidence:
- status: `NOT_ASSESSED`
- assessed candidate metrics: 0
- not assessed metrics: 60
- LOW/MEDIUM/HIGH severity counts: 0/0/0
- LOW/MEDIUM/HIGH confidence counts: 0/0/0

### SYT+

Current detector:
- `NOT_EVALUATED`
- deviation candidate count: 0
- not evaluated metric checks: 60

Severity/Confidence:
- `NOT_ASSESSED`
- assessed candidate metrics: 0
- not assessed metrics: 60

### Mall

Current detector:
- `NOT_EVALUATED`
- deviation candidate count: 0
- not evaluated metric checks: 60

Severity/Confidence:
- `NOT_ASSESSED`
- assessed candidate metrics: 0
- not assessed metrics: 60

No real-data severity or confidence score is published.

## Runtime capabilities

Historical:
- `anomalyEligibilityGuardrails=true`
- `anomalyDetectionFoundation=true`
- `anomalySeverityConfidence=true`
- `anomalyDetection=false`
- `anomalySeverity=false`
- `historicalAlerts=false`
- `historicalDiagnosis=false`

Interpretation:
- the PREPRODUCTION evidence machinery exists;
- operational anomaly/severity capabilities remain disabled.

## Run #371 lineage

Business Context fingerprint:
`d4fef77fe3f18d2e9b91ea611dbcd755372fff1e9fc5e29739fb851b9a0a8cd0`

Historical fingerprint:
`4b910bb2a6b3453e28aa1b4b59afe622661acd2ad7c50ffc7cd02127cddd8c76`

UI Payload fingerprint:
`07ed7e8999baf61154a2eb1239c95d6ff128347fc770589976ccfedc82f1086a`

Native fingerprint:
`1294f3832054dd6e36f3e6a5c18455fcc75740e172be1be4c64f8273a30d8697`

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
- context matched baseline contract: PASS
- anomaly eligibility guardrails fail-closed: PASS
- anomaly detection foundation fail-closed: PASS
- anomaly severity/confidence candidate-only: PASS

UI Payload:
- PASS

Native:
- PASS
- native patch `v21`
- V2 compatibility `v11`

## Artifacts

Run #371:
- staging: `10858373419`
- processed: `10858323502`
- semantic: `10858438504`
- Business Context: `10858428639`
- Historical Intelligence: `10858713382`
- UI Payload: `10858718351`
- Native V2: `10858143688`

Historical digest:
`sha256:6b36a0dc76ee3724f8bc810e9eba02595d372a3cfefb5ba0993b8aa6291ae439`

UI Payload digest:
`sha256:85731a61b71ab0b3a9c7d28f9a9483289d0a650c150d6d203a4e2200ba8eb6ba`

Native digest:
`sha256:566b95f41457b7cc4d432259bbefb99f36cad38a9c2e90ea5a14dd1c083c02a3`

## Safety boundary

Still disabled:
- operational anomaly detection;
- operational anomaly severity;
- automatic alerts;
- diagnosis;
- causal claims;
- production Data Mart write;
- production UI/index modification;
- production deployment.

## Diagnosis / Driver Attribution Foundation v1 — completed

Completed in run `36124417830` (#381).

See:
- `docs/diagnosis-driver-attribution-foundation-v1.md`

The system now distinguishes exact identity contribution from association and unsupported diagnosis, while keeping causal claims and operational diagnosis OFF.

Current real result:
- Portfolio / SYT+ / Mall = `NOT_DIAGNOSED`;
- no attribution is published because there is no real deviation candidate yet.

The next milestone is **Smart Issues Foundation v1**.
