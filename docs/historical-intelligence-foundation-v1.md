# Historical Intelligence Foundation v1 — 2026-09-25

Status: **PREPRODUCTION / FAIL-CLOSED**

This layer exists to make future Business Pulse, Diagnosis and Smart Issues historically grounded. It does **not** enable historical alerts yet.

## Trust boundary

There are three different meanings of history:

1. **RAW source presence** — proves a source file exists and may be backfillable.
2. **Processed readiness** — proves a shop/month has passed normalized processed QA.
3. **Trusted historical business data** — only a published Semantic partition with QA PASS and the complete enabled-shop identity set.

RAW folder presence is therefore `BACKFILL_CANDIDATE_ONLY`. It is never fed directly into anomaly/baseline logic.

## Comparator contract

The foundation defines deterministic, non-alerting comparators:

- previous day;
- previous 7-day period;
- previous-month matched MTD;
- same weekday, requiring at least 4 real prior samples;
- same day-of-month, requiring at least 3 real prior samples.

All AOV/CVR/ROAS/platform-cost ratios are recomputed from additive components.

A short comparator may be `READY` while the overall historical layer remains `INSUFFICIENT_HISTORY`.

## Minimum history

- General historical readiness: 3 complete months.
- Six-month intelligence: 6 complete months.
- Same-weekday baseline: minimum 4 observations.
- Same-day-of-month baseline: minimum 3 observations.
- A partial current month does not count as a complete historical month.

## Context

Campaign/calendar context is explicit-only. Hooks are reserved for campaign type, mega-sale, payday, holiday, promotion and price-change context.

Until a real context dataset is bound:
- context status = `CONTEXT_UNAVAILABLE`;
- no context-matched claim may be made;
- alerts and diagnosis remain disabled.

## Orders historical layout

Historical Orders has two observed layouts:

- newer months: immutable `snapshot_YYYY-MM-DD` folders;
- older months: `final/`.

The loader now uses:
`latest snapshot -> legacy final -> month root`.

This unlocks historical backfill without changing current September snapshot behavior.

## Runtime artifacts

The runner creates:
- `history_inventory.json`
- `historical_intelligence.json`
- `history_qa_report.json`
- `history_manifest.json`
- `multi_shop_history_summary_<YYYY-MM>.json`

## Safety

This foundation:
- does not write production Data Mart;
- does not modify production UI;
- does not enable historical alerts;
- does not enable diagnosis;
- does not treat RAW presence as trusted history.

## Next step

After the real inventory is validated, the next batch is **Historical Backfill v1**:

`RAW historical months -> Staging/Schema QA -> shop-scoped Processed v2 history -> trusted Semantic history`

Backfill should first establish the common multi-shop period needed for Portfolio/Compare, while older shop-only history requires an explicit persistence contract before it is used for Shop intelligence.

## Validated real inventory — run #259

GitHub Actions run `36090296993` (#259): **PASS**.

Historical build fingerprint:
`fc6418b091497ae7c5a9560d4ea9348b50c3f13a481b7520950082455e92a171`

The same fingerprint was produced in run #257 and #259, confirming deterministic rebuild against unchanged trusted history/inventory.

### Trusted history

Published Semantic QA-PASS history currently contains only:
- `2026-09`

Processed v2 READY history currently contains only:
- SYT+: `2026-09`
- Mall: `2026-09`

Therefore:
- Portfolio historical status: `INSUFFICIENT_HISTORY`
- SYT+ historical status: `INSUFFICIENT_HISTORY`
- Mall historical status: `INSUFFICIENT_HISTORY`
- Six-month intelligence: disabled
- Historical alerts: disabled
- Diagnosis: disabled

This is the intended fail-closed result.

### RAW backfill candidates

Source-presence inventory found complete core-domain candidates (Orders + Ads + Business Insights) and Product Performance candidates for:

SYT+:
- `2025-11`
- `2025-12`
- `2026-01` through `2026-09`

Mall:
- `2026-07`
- `2026-08`
- `2026-09`

These are **source-presence candidates only**. Each historical month must still pass Schema Drift Guard, Staging QA, Processed QA and Semantic QA before becoming trusted history.

### Backfill implication

The first common multi-shop backfill window is:
`2026-07..2026-08`

September is already trusted.

Older SYT+ months `2025-11..2026-06` can later support Shop-only historical intelligence, but they must not be silently inserted into the current all-enabled-shops Semantic portfolio namespace. A shop-scoped historical persistence contract is required first.

CI artifact:
- `multi-shop-history-2026-09`
- artifact ID `10845416876`
- digest `sha256:f3ef6091f095ce744078cc32cc2ed269cc0e9d1ca92a1f3460e93cdcc83c7e5a`

## Historical Backfill v1 — validated

Historical Backfill v1 is complete. See:
- `docs/historical-backfill-v1.md`

Final validation:
- July publish: run `36095755224` (#265) — PASS
- August final publish: run `36098115309` (#274) — PASS
- August idempotency: run `36098360904` (#275) — PASS
- September refresh / full history checkpoint: run `36098551468` (#276) — PASS

Trusted Semantic history now contains:
- `2026-07`
- `2026-08`
- `2026-09`

Current Historical Intelligence fingerprint:
`12f6667a045535ea7b17616f45acfc12b0157fa572d4ee0c14f662ab25ea66fa`

Coverage is not equivalent to three complete months:
- Portfolio: 55 trusted days, `2026-07-20..2026-09-17`, 0 complete months
- SYT+: 75 trusted days, one complete month (`2026-07`)
- Mall: 65 trusted days, one complete month (`2026-08`)

Therefore overall historical status remains `INSUFFICIENT_HISTORY` and 6M intelligence / alerts / diagnosis stay disabled.

However deterministic factual comparators are now available:
- Previous Day: READY
- Previous 7D: READY
- Previous-month matched MTD: READY
- Same Weekday: READY with 8 real prior samples
- Same Day-of-Month: still INSUFFICIENT_HISTORY

The next milestone is **Historical Comparator Binding v1**: expose READY comparisons as operator context without promoting them into anomaly/alert/diagnosis claims.

## Lifecycle-aware comparator binding — run #291

User-confirmed business context: Mall only began operating in late July 2026.

Historical Intelligence contract 1.1 now distinguishes a young shop from missing data:
- Mall origin: `SHOP_LAUNCH`
- observed lifecycle boundary: `2026-07-20`
- `preStartDatesAreMissing=false`
- Mall history-depth reason: `HISTORY_LENGTH_NOT_DATA_GAP`
- Portfolio origin: `ALL_ENABLED_SHOPS_ACTIVE`
- Portfolio history-depth reason: `HISTORY_LENGTH_NOT_DATA_GAP`

The observed boundary is the first trusted Semantic date and should not be over-interpreted as an independently verified exact launch timestamp.

Run `36111013628` (#291): PASS.

Historical fingerprint:
`8c61ea948f5c175f9dcaf9cbcd630b536b5f68b71bf2a2e74ce45d46373163da`

Historical comparator context is now bound into UI Payload 1.5 and Native V2:
- Previous Day
- Previous 7D
- previous-month matched MTD
- Same Weekday factual baseline

Historical alerts and diagnosis remain disabled.

See:
- `docs/historical-comparator-binding-v1.md`

Next milestone:
**Business Context Calendar Foundation v1**.

