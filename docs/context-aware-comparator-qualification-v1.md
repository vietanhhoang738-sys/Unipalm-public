# Context-Aware Comparator Qualification v1

Status: **VALIDATED PREPRODUCTION MILESTONE**

Validated on 2026-09-25.

Final validation:
- GitHub Actions run `36115233375` (#324) — **PASS end-to-end**
- runtime checkpoint: `9b0b34aee7fbef0b8db91e50fdec8f9bd722d53c`

## Objective

Qualify factual historical comparisons by explicit business context without making causal claims.

This batch answers only:

> Are the current and reference periods context-compatible enough to compare directly?

It does **not** answer:

> Why did the metric move?

## Qualification statuses

Exactly three operator statuses are allowed:

- `CONTEXT_COMPATIBLE`
- `CONTEXT_DIFFERENT`
- `CONTEXT_UNKNOWN`

## Decision policy

Only context rows with `matching_eligible=true` participate in qualification.

Those rows are backed by exact-date official platform/government sources.

Broad industry/season context such as Metric Back-to-School:
- remains visible;
- does not decide compatibility;
- cannot turn an unknown pair into a compatible pair.

### Exact matching profile

Each comparison window is summarized by a deterministic exact-context profile at grain:

`scope_type + platform + context_family + day_count + peak_day_count`

Event IDs are deliberately not part of the compatibility identity.

Example:

Shopee 8.8 and Shopee 9.9 can both represent family:
`DOUBLE_DAY_MEGA_SALE`

but they are only compatible when their normalized window profiles are equal.

### Window rules

If comparator data itself is not READY:
- `CONTEXT_UNKNOWN`

If current/reference window lengths differ:
- `CONTEXT_UNKNOWN`

If neither side has an exact matching-eligible event:
- `CONTEXT_UNKNOWN`

This is deliberately conservative. Absence of an exact reviewed event does not prove the period is a normal period.

If only one side has an exact event:
- `CONTEXT_DIFFERENT`

If both sides have exact events and the normalized profiles are equal:
- `CONTEXT_COMPATIBLE`

If both sides have exact events but profiles differ:
- `CONTEXT_DIFFERENT`

## Sample-baseline rules

Same-weekday and same-day-of-month samples are qualified one by one.

The current factual baseline is **not filtered** in this batch.

For each sample:
- compatible / different / unknown is recorded.

The aggregate sample qualification is:
- compatible only when all samples are compatible;
- different only when all samples are different;
- unknown when samples are mixed or contain unknowns.

This prevents mixed historical samples from being presented as context-matched history.

## Safety

Still disabled:
- context-matched baseline filtering;
- causal claims;
- anomaly severity;
- alerts;
- diagnosis;
- production Data Mart writes;
- production UI/index/deployment changes.

Every qualification object explicitly keeps:
- `contextMatchedBaselineEligible=false`
- `causalClaimEligible=false`
- `alertEligible=false`
- `diagnosisEligible=false`

## Contract versions

Historical Intelligence:
- contract `1.3`

UI Payload:
- contract `1.7`

Native:
- patch `native-context-qualified-v17`

V2 compatibility:
- patch `v2-context-qualified-v7`

## Run #324 lineage

Business Context fingerprint remains:
`d4fef77fe3f18d2e9b91ea611dbcd755372fff1e9fc5e29739fb851b9a0a8cd0`

Historical fingerprint:
`4e1aa6008022518566811aea96318ccf033cdcff4aa03765986e04473c4a385d`

UI Payload fingerprint:
`725e39867e7525d9c9f978a0a2aeb3e5b3e19ebbbbb674c56083c5e4b7d6d262`

Native fingerprint:
`916151c505b792b5ac54871d53a49be055a178c0ef4de0e1d4294bd3cd3ad3fb`

Source Semantic fingerprint remains:
`c25b7cfe67c6d8d477e6e8cd65a466eb3c74ca4f97a3c500b0e9320f1223b321`

Processed v2:
- SYT+: `7d4fd9288c154e59903525c019d455ee14a807f1f25b7b5c74ed5303641b03aa` — **NOOP**
- Mall: `5cbaff93bdae6d87d6784169e5692698742beed39425536a5a8283b9e9439847` — **NOOP**

Semantic:
- **NOOP**

Therefore this batch changed historical/context interpretation only and did not rewrite canonical business facts.

## Real qualification results

### Portfolio — latest trusted date 2026-09-17

Previous Day:
- status: READY
- qualification: `CONTEXT_COMPATIBLE`
- reason: `EXACT_MATCHING_PROFILE_EQUAL`
- current 17/09 and reference 16/09 both have:
  `FESTIVAL_CAMPAIGN × 1 day × non-peak`

Previous 7D:
- status: READY
- qualification: `CONTEXT_DIFFERENT`
- current exact profile includes:
  - one day of `DOUBLE_DAY_MEGA_SALE`
  - two days of `FESTIVAL_CAMPAIGN`
  - one peak day of `MID_MONTH`
- reference exact profile contains seven days of `DOUBLE_DAY_MEGA_SALE`
- result: contexts are materially different.

Previous-month matched MTD:
- status: READY
- qualification: `CONTEXT_DIFFERENT`
- September side includes:
  - National Day public holiday;
  - 9.9;
  - Mid-month;
  - Mid-Autumn festival campaign.
- August side includes:
  - Month opening;
  - 8.8;
  - Member Day;
  - Mid-month.
- result: different exact campaign profile.

Same Weekday:
- status: READY
- 8 samples
- compatible: 0
- different: 8
- unknown: 0
- aggregate qualification: `CONTEXT_DIFFERENT`

The current 17/09 festival context has no same-weekday sample with an equal exact-context profile.

### SYT+

Latest trusted date is also 2026-09-17.

Results match Portfolio for the main factual comparators:
- Previous Day: `CONTEXT_COMPATIBLE`
- Previous 7D: `CONTEXT_DIFFERENT`
- Previous-month matched MTD: `CONTEXT_DIFFERENT`
- Same Weekday: `CONTEXT_DIFFERENT` with 0 compatible / 8 different.

### Mall — latest trusted date 2026-09-23

Previous Day:
- status: READY
- qualification: `CONTEXT_UNKNOWN`
- reason: `NO_EXACT_MATCHING_EVENT_ON_EITHER_SIDE`

Both 22/09 and 23/09 are within broad Back-to-School market season, but that Metric-derived season cannot prove exact campaign compatibility.

Previous 7D:
- `CONTEXT_DIFFERENT`

Current window contains part of the Mid-Autumn campaign while the reference window contains a different mix of 9.9, Mid-month and Mid-Autumn context.

Previous-month matched MTD:
- `CONTEXT_DIFFERENT`

Same Weekday:
- status: READY
- compatible: 0
- different: 5
- unknown: 3
- aggregate: `CONTEXT_UNKNOWN`

This is deliberately not simplified into a false matched baseline.

## QA evidence

Historical QA:
- status: PASS
- failed checks: 0
- business context bound all scopes: PASS
- comparator context bound fail-closed: PASS
- context qualification factual-only: PASS

UI Payload QA:
- status: PASS
- failed checks: 0
- historical context all scopes bound: PASS
- business context lineage all scopes: PASS
- context matched baseline fail-closed: PASS
- context comparator qualification factual-only: PASS

Native validation:
- displays:
  - `Bối cảnh tương thích`
  - `Khác bối cảnh`
  - `Chưa rõ bối cảnh`
- visible wording explicitly states:
  `chỉ đánh giá khả năng so sánh, không kết luận nguyên nhân`

## Artifacts

Run #324:
- staging: `10854937448`
- processed: `10854598067`
- semantic: `10855027543`
- business context: `10854543159`
- historical intelligence: `10854712910`
- UI Payload: `10854802835`
- Native V2: `10855092355`

Historical artifact digest:
`sha256:b7fa665aa41e7064827c504cbe3df5cb701283915faef6fe0924d641c358b2c9`

UI Payload artifact digest:
`sha256:7d013e1593361dc7f85dbfbfc15021c9883a5fc04ac83a3d30c8451ed0a79263`

Native artifact digest:
`sha256:e40c905b4086a79c2ed213950e98d35cf7e780dd19432cf0a090f7584d709c80`

## Context-Matched Historical Baseline v1 — completed

Completed in run `36116620804` (#334).

See:
- `docs/context-matched-historical-baseline-v1.md`

Real result:
- all-history Same Weekday baseline remains READY;
- current compatible sample count is 0 for Portfolio, SYT+ and Mall;
- matched baseline therefore correctly remains `INSUFFICIENT_CONTEXT_MATCHED_HISTORY`;
- no silent fallback is used.

The next milestone is **Anomaly Eligibility Guardrails v1**.
