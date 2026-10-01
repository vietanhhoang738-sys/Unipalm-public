# Historical Comparator Binding v1 — 2026-09-25

Status: **VALIDATED PREPRODUCTION MILESTONE**

Final validation:
- GitHub Actions run `36111013628` (#291) — **PASS end-to-end**
- runtime checkpoint: `7973cdd0d383a85f9a5cb8a54cf5253a12d7331d`

## Business clarification incorporated

Mall began operating only in late July 2026. Therefore dates before the beginning of Mall's trusted history are **pre-launch**, not missing data.

The registry now models history origin explicitly:

- SYT+: `PREEXISTING_BEFORE_TRUSTED_WINDOW`
- Mall: `SHOP_LAUNCH` with `FIRST_TRUSTED_SEMANTIC_DATE`

The current observed trusted lifecycle boundary for Mall is `2026-07-20`. This is a data-derived first trusted Semantic date, not an independently asserted exact legal/store-opening timestamp.

Portfolio history now uses origin:
`ALL_ENABLED_SHOPS_ACTIVE`

So Portfolio history before Mall became active is not classified as a missing Portfolio period.

## Historical Intelligence contract 1.1

Historical coverage now separates:

1. **coverage origin**
2. **calendar completeness**
3. **history depth**
4. **data-gap interpretation**

New coverage fields include:
- `coverageOrigin`
- `startPolicy`
- `lifecycleStartDate`
- `preStartDatesAreMissing`
- `coverageInterpretation`
- `historySpanDays`
- `calendarCompleteMonthCount`

Historical status may still be `INSUFFICIENT_HISTORY`, but for Mall and Portfolio the reason is now:

`HISTORY_LENGTH_NOT_DATA_GAP`

This means the historical record is young, not that the pipeline lost pre-launch data.

## Real lifecycle-aware history at run #291

Historical fingerprint:
`8c61ea948f5c175f9dcaf9cbcd630b536b5f68b71bf2a2e74ce45d46373163da`

Trusted Semantic months remain:
- `2026-07`
- `2026-08`
- `2026-09`

### Portfolio

- origin: `ALL_ENABLED_SHOPS_ACTIVE`
- observed lifecycle start: `2026-07-20`
- trusted end: `2026-09-17`
- trusted day count: 55
- history span: 60 calendar days
- pre-start dates are missing: **false**
- overall status: `INSUFFICIENT_HISTORY`
- reason: `HISTORY_LENGTH_NOT_DATA_GAP`

### SYT+

- origin: `PREEXISTING_BEFORE_TRUSTED_WINDOW`
- trusted start: `2026-07-01`
- trusted end: `2026-09-17`
- trusted day count: 75
- overall status: `INSUFFICIENT_HISTORY`
- reason: `MORE_TRUSTED_HISTORY_REQUIRED`

### Mall

- origin: `SHOP_LAUNCH`
- observed lifecycle start: `2026-07-20`
- trusted end: `2026-09-23`
- trusted day count: 65
- history span: 66 calendar days
- pre-start dates are missing: **false**
- overall status: `INSUFFICIENT_HISTORY`
- reason: `HISTORY_LENGTH_NOT_DATA_GAP`

## UI Payload contract 1.5

Historical Intelligence is now bound into the canonical UI Payload.

New lineage:
- source Semantic fingerprint:
  `c25b7cfe67c6d8d477e6e8cd65a466eb3c74ca4f97a3c500b0e9320f1223b321`
- source Historical fingerprint:
  `8c61ea948f5c175f9dcaf9cbcd630b536b5f68b71bf2a2e74ce45d46373163da`
- UI Payload fingerprint:
  `0f168586b6e4a136e6914c5e9c7760f8d03137a270d546a9682a70964d59aca5`

Capabilities:
- `historicalComparatorContext=true`
- `historicalAlerts=false`
- `historicalDiagnosis=false`
- `historicalIntelligence6m=false`

Portfolio and each Shop receive a `historicalContext` block containing only:
- history status/depth reason;
- lifecycle-aware coverage;
- comparator status;
- comparator windows/metrics or baseline samples;
- context availability;
- fail-closed alert/diagnosis flags.

The UI Payload does not expose anomaly severity or diagnosis as a side effect of comparator binding.

## Command Center / Business Pulse binding

Native V2 now uses:
- **current facts** from current Semantic/UI Payload;
- **reference facts** from Historical Intelligence when the comparator is READY.

This distinction is deliberate. Historical binding must not replace current-day metrics such as Shop Visits.

Bound factual comparators:
- `yesterday -> previousDay`
- `last7 -> previous7d`
- `mtd -> previousMonthMtd`

Same-weekday history is exposed as a factual baseline support signal.

Current comparator availability for Portfolio and both shops:
- Previous Day: READY
- Previous 7D: READY
- Previous-month matched MTD: READY
- Same Weekday: READY
- Same Day-of-Month: INSUFFICIENT_HISTORY

The Business Pulse visible wording explicitly says the historical comparison is factual and **not** an anomaly, alert or diagnosis.

For launch-period scopes, the UI can also explain:
- Mall history begins at shop launch;
- pre-launch dates are not missing;
- Portfolio history begins when all enabled shops are active.

## Native V2 lineage

Native patch:
`native-historical-comparator-v16`

Compatibility patch:
`v2-historical-comparator-v6`

Native fingerprint:
`52a881b192bd51f5d2da849b5534b7c0c612e788fb339e3b3b2c6715ab97bcb7`

Source production V2 SHA256 remains:
`9540f23b4d9537441e3bd4cdeafd15747ab4280a87a0130d223984009d99c952`

Production source V2 was not modified.

## Data-chain stability

Run #291 proved this batch changed interpretation/binding, not canonical business facts.

Processed v2:
- SYT+ fingerprint `7d4fd9288c154e59903525c019d455ee14a807f1f25b7b5c74ed5303641b03aa` — **NOOP**
- Mall fingerprint `5cbaff93bdae6d87d6784169e5692698742beed39425536a5a8283b9e9439847` — **NOOP**

Semantic:
- fingerprint `c25b7cfe67c6d8d477e6e8cd65a466eb3c74ca4f97a3c500b0e9320f1223b321` — **NOOP**

Therefore lifecycle semantics and historical comparator binding did not rewrite stable business facts.

## Evidence

Run #291 artifacts:
- staging: `10852827952`
- processed: `10853362132`
- semantic: `10852952796`
- history: `10853082511`
- UI Payload: `10852728561`
- Native V2: `10852952803`

History artifact digest:
`sha256:653f99be6ce126464104c6bba522af374a50b6f708889435ecf116989c07fa96`

Payload artifact digest:
`sha256:6a47e04a06dd64577911bfb4547340ffaf9313ff72294347627b76fdc7011de5`

Native artifact digest:
`sha256:2280da27c4c906123a62bc32b89002fc05d8f4f6afb8eab1b78cdeaa717b30be`

## Safety

Still false/off:
- production Data Mart writes
- production V2 modification
- production index modification
- production deployment
- historical anomaly generation
- historical alerts
- historical diagnosis

## Recommended next milestone

**Business Context Calendar Foundation v1**

Historical comparisons are now technically and semantically available. The next blocker to responsible diagnosis is context.

Build an explicit context layer for:
- Shopee campaign / mega-sale windows;
- payday windows;
- public-holiday / special-event periods where relevant;
- seller promotion windows;
- observed price-change context when a reliable source exists.

Rules:
- explicit source only;
- no inferred campaign labels from metric movements;
- context can qualify a comparison but cannot manufacture an alert;
- continue to preserve Mall's launch lifecycle in every historical comparison.

Older SYT+-only history remains useful later for Shop-specific deep history, but it should stay separate from Portfolio history.
