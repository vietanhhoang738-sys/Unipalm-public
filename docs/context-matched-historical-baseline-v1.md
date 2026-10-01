# Context-Matched Historical Baseline v1

Status: **VALIDATED PREPRODUCTION MILESTONE**

Validated on 2026-09-25.

Final validation:
- GitHub Actions run `36116620804` (#334) — **PASS end-to-end**
- runtime checkpoint: `e2229c602ee134187c34bb6e7f84664d2ae242d8`

## Objective

Preserve the existing all-history factual sample baseline while deriving a separate baseline from only historical samples qualified as:

`CONTEXT_COMPATIBLE`

The matched baseline must never silently fall back to different/unknown context samples.

## Contract

Historical Intelligence contract:
`1.4`

UI Payload contract:
`1.8`

Native patch:
`native-context-matched-baseline-v18`

V2 compatibility patch:
`v2-context-matched-baseline-v8`

## Baseline rules

Applicable sample comparators:
- Same Weekday
- Same Day-of-Month

The original comparator remains unchanged:
- original `baseline` uses all observed samples;
- original `sampleCount` / `sampleDates` are preserved.

A new sibling object is emitted:

`contextMatchedBaseline`

Source samples:
- only samples whose factual context qualification is `CONTEXT_COMPATIBLE`.

Minimum sample requirement:
- same as the original comparator;
- Same Weekday: 4;
- Same Day-of-Month: 3.

If the compatible sample count meets the minimum:
- status = `READY`;
- statistics are published.

If it does not:
- status = `INSUFFICIENT_CONTEXT_MATCHED_HISTORY`;
- compatible sample dates/count remain visible;
- no matched-baseline statistics are emitted.

Hard safety:
- `silentFallbackUsed=false`
- `alertEligible=false`
- `diagnosisEligible=false`
- `causalClaimEligible=false`

## Synthetic validation

Unit tests prove both required paths.

### READY path

With 4 same-weekday samples carrying an equal exact official context profile:
- original all-history baseline remains present;
- matched sample count = 4;
- matched status = `READY`;
- matched statistics are emitted;
- scope/global matched-baseline capability becomes true.

### Insufficient path

When the all-history same-weekday comparator is READY but no historical sample is context-compatible:
- all-history baseline remains present;
- matched count = 0;
- matched status = `INSUFFICIENT_CONTEXT_MATCHED_HISTORY`;
- matched `baseline` statistics field is absent;
- no fallback occurs.

## Real September 2026 result

Business Context fingerprint remains:
`d4fef77fe3f18d2e9b91ea611dbcd755372fff1e9fc5e29739fb851b9a0a8cd0`

### Portfolio

Same Weekday:
- all-history status: `READY`
- all-history samples: 8
- context qualification: `CONTEXT_DIFFERENT`
- matched samples: 0 / 4 required
- matched status: `INSUFFICIENT_CONTEXT_MATCHED_HISTORY`

Same Day-of-Month:
- all-history status: `INSUFFICIENT_HISTORY`
- all-history samples: 1
- matched samples: 0 / 3
- matched status: `INSUFFICIENT_CONTEXT_MATCHED_HISTORY`

Scope matched-baseline enabled:
**false**

### SYT+

Same Weekday:
- all-history status: `READY`
- all-history samples: 8
- matched samples: 0 / 4
- matched status: `INSUFFICIENT_CONTEXT_MATCHED_HISTORY`

Same Day-of-Month:
- all-history samples: 2
- matched samples: 0 / 3
- matched status: `INSUFFICIENT_CONTEXT_MATCHED_HISTORY`

Scope matched-baseline enabled:
**false**

### Mall

Same Weekday:
- all-history status: `READY`
- all-history samples: 8
- aggregate context qualification: `CONTEXT_UNKNOWN`
- matched samples: 0 / 4
- matched status: `INSUFFICIENT_CONTEXT_MATCHED_HISTORY`

Same Day-of-Month:
- all-history samples: 2
- matched samples: 0 / 3
- matched status: `INSUFFICIENT_CONTEXT_MATCHED_HISTORY`

Scope matched-baseline enabled:
**false**

Global Historical/UI Payload capability:
`contextMatchedBaseline=false`

This is an accurate business outcome, not a pipeline failure. The current trusted-history window simply does not yet contain enough context-compatible samples for the latest business context.

## Run #334 lineage

Historical fingerprint:
`915074583bde8db6482596b6c85dc9ab6417c58e10935bff1c099e160b191e4a`

UI Payload fingerprint:
`dfcd2d7509b8cdf044da86913ef7919c69d930b03a916f810d9bf5daa9c42439`

Native fingerprint:
`7edcf9d683e2a03ae0a9f8cb2dd1312703ff8972e66844a6e527ec1dcf3aa6f9`

Semantic fingerprint remains:
`c25b7cfe67c6d8d477e6e8cd65a466eb3c74ca4f97a3c500b0e9320f1223b321`

Processed:
- SYT+: `7d4fd9288c154e59903525c019d455ee14a807f1f25b7b5c74ed5303641b03aa` — **NOOP**
- Mall: `5cbaff93bdae6d87d6784169e5692698742beed39425536a5a8283b9e9439847` — **NOOP**

Semantic:
- **NOOP**

Therefore this batch changes Historical/Payload/Native intelligence metadata only and does not rewrite canonical business facts.

## QA

Historical QA:
- PASS
- failed checks: 0
- context matched baseline contract: PASS
- no silent fallback
- no statistics leak on insufficient matched history

UI Payload QA:
- PASS
- failed checks: 0
- context matched baseline safety: PASS
- context matched baseline contract: PASS
- capability consistency: PASS (`anyReady=false`)

Native QA:
- PASS
- 32 checks
- failed checks: 0

Native wording explicitly includes:
- `Baseline cùng bối cảnh: chưa đủ mẫu`
- `không fallback sang mẫu khác bối cảnh`

The normal same-weekday factual baseline remains visible separately.

## Artifacts

Run #334:
- staging: `10855268349`
- processed: `10855228696`
- semantic: `10855412850`
- business context: `10855392998`
- historical intelligence: `10855353182`
- UI Payload: `10855184105`
- Native V2: `10855328309`

Historical digest:
`sha256:05c274d8fa6126321a46030f69022390bdc65150b6fbdccbc9c13f88c3ee8d64`

UI Payload digest:
`sha256:592d15ac619cc0f31e11f562c52b72032b4a316771a4795cf8ff9480cc64f611`

Native digest:
`sha256:c8b5da6f16417dc5907120959ee1d69499ac98d5ebcaa802018326fd72ee6035`

## Safety

Still off:
- anomaly classification;
- anomaly severity;
- alerts;
- diagnosis;
- causal claims;
- production Data Mart write;
- production UI/index modification;
- production deployment.

## Anomaly Eligibility Guardrails v1 — completed

Completed in run `36118612445` (#349).

See:
- `docs/anomaly-eligibility-guardrails-v1.md`

Current real result:
- Portfolio / SYT+ / Mall are all `ANOMALY_BLOCKED`;
- no KPI is currently eligible;
- this is expected because trusted history/context-matched samples are not deep enough yet;
- anomaly detection remains OFF.

The next milestone is **Anomaly Detection Foundation v1**.
