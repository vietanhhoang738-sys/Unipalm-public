# Anomaly Eligibility Guardrails v1

Status: **VALIDATED PREPRODUCTION MILESTONE**

Validated on 2026-09-25.

Final validation:
- GitHub Actions run `36118612445` (#349) — **PASS end-to-end**
- runtime checkpoint: `48f10f4c089625368750625c38fc2d56d815ec24`

## Objective

Define whether a historical observation is even eligible for anomaly evaluation.

This layer does **not** detect anomalies.

It only emits:
- `ANOMALY_ELIGIBLE`
- `ANOMALY_BLOCKED`

at:
- scope level;
- comparator level;
- KPI level.

## Contracts

Historical Intelligence:
- contract `1.5`

UI Payload:
- contract `1.9`

Native:
- patch `native-anomaly-eligibility-v19`

V2 compatibility:
- patch `v2-anomaly-eligibility-v9`

## Eligibility gates

For statistical anomaly evaluation, the guardrail considers:

1. comparator readiness;
2. complete current/reference windows where applicable;
3. trusted history depth;
4. lifecycle state;
5. verified Business Context lineage;
6. context qualification;
7. context-matched baseline readiness;
8. metric-level matched baseline availability.

Window comparators:
- Previous Day
- Previous 7D
- Previous-month matched MTD

remain factual comparisons only and carry:
`NO_STATISTICAL_BASELINE_METHOD`

They may support operator understanding but are not automatically treated as statistical anomaly tests.

Sample-based statistical comparators:
- Same Weekday
- Same Day-of-Month

may become anomaly-eligible only when the context-matched baseline is READY and all other guards pass.

## Reason codes

Canonical reason codes include:
- `COMPARATOR_NOT_READY`
- `DATA_WINDOW_INCOMPLETE`
- `INSUFFICIENT_HISTORY_DEPTH`
- `SHOP_LIFECYCLE_HISTORY_TOO_SHORT`
- `PORTFOLIO_LIFECYCLE_HISTORY_TOO_SHORT`
- `CONTEXT_LINEAGE_UNAVAILABLE`
- `CONTEXT_DIFFERENT`
- `CONTEXT_UNKNOWN`
- `INSUFFICIENT_CONTEXT_MATCHED_HISTORY`
- `NO_STATISTICAL_BASELINE_METHOD`
- `METRIC_BASELINE_UNAVAILABLE`

Native V2 translates these into operator wording rather than exposing raw backend codes.

## Synthetic READY validation

Unit tests prove that a scope with:
- 3 complete trusted months;
- READY Same Weekday comparator;
- verified Context lineage;
- at least 4 `CONTEXT_COMPATIBLE` samples;
- READY context-matched baseline;

produces:
- Same Weekday comparator = `ANOMALY_ELIGIBLE`;
- all KPI eligibility statuses = `ANOMALY_ELIGIBLE`.

Even then:
- anomaly detection remains OFF;
- severity remains OFF;
- alerts remain OFF;
- diagnosis remains OFF;
- causal claims remain OFF.

Window comparators remain blocked by `NO_STATISTICAL_BASELINE_METHOD`.

## Real September 2026 eligibility result

No current scope is anomaly-eligible yet.

### Portfolio

Scope:
- `ANOMALY_BLOCKED`
- eligible comparators: 0
- blocked comparators: 5
- eligible KPI checks: 0
- blocked KPI checks: 60

History:
- status: `INSUFFICIENT_HISTORY`
- lifecycle origin: `ALL_ENABLED_SHOPS_ACTIVE`

Previous Day:
- `ANOMALY_BLOCKED`
- reasons:
  - `PORTFOLIO_LIFECYCLE_HISTORY_TOO_SHORT`
  - `NO_STATISTICAL_BASELINE_METHOD`

Previous 7D:
- reasons additionally include `CONTEXT_DIFFERENT`.

Previous-month MTD:
- reasons additionally include `CONTEXT_DIFFERENT`.

Same Weekday:
- `ANOMALY_BLOCKED`
- reasons:
  - `PORTFOLIO_LIFECYCLE_HISTORY_TOO_SHORT`
  - `INSUFFICIENT_CONTEXT_MATCHED_HISTORY`
  - `CONTEXT_DIFFERENT`
- matched baseline: 0 / 4 required.

Same Day-of-Month:
- also blocked by comparator readiness and matched-history insufficiency.

### SYT+

Scope:
- `ANOMALY_BLOCKED`
- eligible comparators: 0
- eligible KPI checks: 0

History:
- origin: `PREEXISTING_BEFORE_TRUSTED_WINDOW`
- reason: `MORE_TRUSTED_HISTORY_REQUIRED`

Main block code:
- `INSUFFICIENT_HISTORY_DEPTH`

Same Weekday additionally has:
- `INSUFFICIENT_CONTEXT_MATCHED_HISTORY`
- `CONTEXT_DIFFERENT`

### Mall

Scope:
- `ANOMALY_BLOCKED`
- eligible comparators: 0
- eligible KPI checks: 0

Lifecycle:
- origin: `SHOP_LAUNCH`

Main lifecycle block code:
- `SHOP_LIFECYCLE_HISTORY_TOO_SHORT`

Previous Day:
- also carries `CONTEXT_UNKNOWN`
- plus `NO_STATISTICAL_BASELINE_METHOD`.

Same Weekday:
- reasons:
  - `SHOP_LIFECYCLE_HISTORY_TOO_SHORT`
  - `INSUFFICIENT_CONTEXT_MATCHED_HISTORY`
  - `CONTEXT_UNKNOWN`

This correctly distinguishes a young Mall shop from a missing-data problem.

## Runtime capabilities

Historical:
- `anomalyEligibilityGuardrails=true`
- `anomalyDetection=false`
- `contextMatchedBaseline=false`
- `historicalAlerts=false`
- `historicalDiagnosis=false`

UI Payload:
- `anomalyEligibilityGuardrails=true`
- `anomalyDetection=false`

## Run #349 lineage

Business Context fingerprint:
`d4fef77fe3f18d2e9b91ea611dbcd755372fff1e9fc5e29739fb851b9a0a8cd0`

Historical fingerprint:
`2393eb36a7d7c31589aca8385d36b7931e8c996cb857a87016a8dbd70526c4dd`

UI Payload fingerprint:
`976bb49da517cf3d8fffde2813394ea073d2e38154dc5d42f5da8cda4d1b3a0d`

Native fingerprint:
`230462a060cc99740f0a24081d46531e1ff51fa606c99eedbfa9d764898c1a92`

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
- context qualification factual-only: PASS
- context-matched baseline contract: PASS

UI Payload QA:
- PASS
- failed checks: 0
- anomaly eligibility guardrails bound fail-closed: PASS
- anomaly detection capability off: PASS
- Business Context lineage: PASS
- matched-baseline capability consistency: PASS

Native QA:
- PASS
- failed checks: 0
- native patch: `native-anomaly-eligibility-v19`
- V2 compatibility: `v2-anomaly-eligibility-v9`

Operator wording includes:
- `Chưa đủ điều kiện đánh giá anomaly`
- translated block reasons such as:
  - lịch sử Portfolio còn ngắn;
  - lịch sử từ lúc shop mở bán còn ngắn;
  - chưa đủ mẫu lịch sử cùng bối cảnh;
  - chưa có baseline thống kê phù hợp.

## Artifacts

Run #349:
- staging: `10856601509`
- processed: `10855956745`
- semantic: `10856326345`
- Business Context: `10856411159`
- Historical Intelligence: `10856470973`
- UI Payload: `10856116458`
- Native V2: `10856161336`

Historical artifact digest:
`sha256:898bec311a51dd0f1dc1bf700855bf8eabd7ca34e573502388589b413599ba00`

UI Payload digest:
`sha256:b2a0fa3acb0c6a171aadf3b4deabfde832e4e9b2600c565562e8a1454be49272`

Native digest:
`sha256:98811b16a5c44450d18523cfd9673faefc944f28a0b648a4fe7661a3f98ddd43`

## Safety boundary

Still disabled:
- anomaly detection;
- anomaly classification;
- anomaly severity;
- automatic alerts;
- diagnosis;
- causal claims;
- production Data Mart write;
- production UI/index modification;
- production deployment.

## Anomaly Detection Foundation v1 — completed

Completed in run `36120626467` (#360).

See:
- `docs/anomaly-detection-foundation-v1.md`

The detector now uses modified Z-score + MAD, effect-size gates and KPI directionality, while remaining PREPRODUCTION evidence only.

Current real result:
- Portfolio / SYT+ / Mall = `NOT_EVALUATED`;
- no KPI score is published because current eligibility is blocked;
- operational anomaly detection remains OFF.

The **Intelligence Foundation is complete**.

The next milestone is **Anomaly Severity & Confidence v1**.
