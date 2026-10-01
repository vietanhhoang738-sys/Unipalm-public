# Business Context Calendar Foundation v1

Status: **VALIDATED PREPRODUCTION MILESTONE**

Research and implementation date: 2026-09-25.

## Objective

Create an explicit-source context layer for historical comparisons without inferring campaigns from business metrics.

Target chain:

`Reviewed external sources -> Business Context Calendar -> context-day facts -> Historical Intelligence -> UI Payload`

The foundation does **not** enable:
- anomaly claims;
- alert severity;
- causal diagnosis;
- context-matched baselines.

## Source authority hierarchy

### A1 — Platform seller official

Highest authority for seller-facing campaign dates and operational programs.

Examples:
- Shopee Ads / Seller-facing pages;
- TikTok Shop Seller Center / Academy.

### A2 — Platform consumer official

Official platform campaign landing pages and official platform editorial pages.

### B1 — Government official

Used for national/public-holiday context.

### C1 — Industry analytics

Metric.vn and equivalent market-intelligence sources.

Role:
- market-season significance;
- broad seasonal planning context;
- industry-wide interpretation.

C1 must **not** manufacture exact platform campaign dates.

## Hard source rules

1. Exact campaign-day matching requires A1, A2 or B1 evidence.
2. Search-result snippets are research leads only and cannot become canonical evidence.
3. An image-only official campaign calendar is retained as a source reference if its dates cannot be reliably machine-read.
4. No campaign is inferred from GMV, Orders, Ads Spend, ROAS or other observed metric movement.
5. If a source confirms a named campaign but not its full window, only the verified portion is stored.
6. Industry analytics may define market-season context but is `matching_eligible=false`.

## Reviewed source registry

### Shopee

#### 7.7 Siêu Sale Đón Hè

Official Shopee consumer landing page:
- source tier: A2
- campaign: `7.7 Siêu Sale Đón Hè`
- verified window: `2026-06-26..2026-07-09`
- peak day: `2026-07-07`

#### August 2026 Super Sale windows

Official Shopee Ads seller page:
`https://ads.shopee.vn/news/557`

Verified August windows:
- 1.8 Sale Mở Màn: `2026-08-01`
- 8.8 Siêu Sale Nửa Giá: `2026-08-05..2026-08-08`
- Ngày Hội Thành Viên: `2026-08-09..2026-08-10`
- 15.8 Sale Giữa Tháng: `2026-08-15`
- Ngày Hội Thành Viên: `2026-08-20`
- 25.8 Lương Về Sale To: `2026-08-24..2026-08-25`

Foundation v1 encodes all six official August sale/program windows listed on this Shopee seller-facing page: 1.8, 8.8, Member Day 9–10.8, 15.8, Member Day 20.8, and 25.8.

#### 9.9 Ngày Siêu Mua Sắm

Official Shopee consumer campaign page:
- source tier: A2
- verified window: `2026-08-26..2026-09-11`
- peak day: `2026-09-09`

#### Siêu Hội Trăng Rằm

Same official Shopee campaign content:
- verified window: `2026-09-16..2026-09-18`

#### 15th / payday recurring cadence

Official Shopee Blog documents recurring:
- mid-month sale on day 15;
- payday/end-month sale on day 25.

Foundation v1 uses the official cadence only when an exact date/event is represented conservatively.

For 25.9, the accessible official page identifies the named payday campaign but does not establish a wider canonical campaign window. Therefore v1 encodes only:
`2026-09-25`.

### TikTok Shop

#### Official 2026 Campaign Calendar

TikTok Shop Seller Academy publishes an official 2026 campaign-calendar page.

The September monthly calendar is exposed as an image in the accessible source.

Policy:
- retained under `reference_only`;
- no dates are auto-transcribed from unreadable image content;
- future readable/structured official evidence may promote individual dates.

#### 8.8

Official TikTok Shop seller-policy content explicitly refers to preparation for the 8.8 campaign.

Foundation encoding:
- verified named peak day only: `2026-08-08`;
- no wider date window inferred.

#### 9.9

Official TikTok Shop seller-policy content explicitly refers to the 9.9 campaign.

Foundation encoding:
- verified named peak day only: `2026-09-09`;
- no wider date window inferred.

#### LIVE Marathon

Official TikTok Shop seller material:
- program: `LIVESTREAM MARATHON 2026 - Càng LIVE Càng Cháy`
- verified window: `2026-09-17..2026-09-27`.

### Vietnam public holiday context

Official government notice:
- National Day public-sector holiday window:
  `2026-08-29..2026-09-02`.

This is MARKET context, not a platform campaign.

### Metric.vn

Metric H1/2026 market report identifies Q3 seasonal marketing inflection points:
- July: summer/travel high season;
- August–September: Back-to-School;
- seasonal weather transition.

Foundation encodes:
- July summer season as market-season context;
- August–September Back-to-School as market-season context.

Both have:
- `exact_date_verified=false`;
- `matching_eligible=false`.

These periods may qualify market conditions but cannot be used as exact Shopee/TikTok campaign matches.

## Canonical files

- `config/business_context_contract.json`
- `config/business_context_calendar.json`
- `automation/modules/business_context_calendar.py`
- `automation/multi_shop_context_runner.py`
- `automation/tests/test_business_context_calendar.py`

## Monthly freshness guard

Business Context contract 1.1 is fail-closed across month boundaries.

The calendar has a reviewed `checked_at` date. If the requested `as_of_period` is later than the calendar review month, context QA fails and the all-shop Historical chain is blocked.

Example:
- calendar reviewed in September 2026;
- a normal September rebuild is allowed;
- an October 2026 run is blocked until the source calendar is reviewed again.

This prevents stale campaign assumptions from silently propagating into a new month.

## Context-day grain

Each expanded row uses:

`data_date + context_id`

and carries:
- platform;
- scope type;
- optional shop ID;
- context type;
- context family;
- window type;
- peak-day flag;
- source ID / tier;
- verification status;
- exact-date verification flag;
- matching-eligibility flag.

Platform-wide events are not duplicated per shop.

Shop-specific promotions will use `scope_type=SHOP` and an explicit `shop_id`.

## Runtime artifacts

For each as-of period:

- `context_events.json`
- `context_days.jsonl`
- `context_qa_report.json`
- `context_manifest.json`
- `business_context_summary_<YYYY-MM>.json`

## Context source fingerprint

The deterministic Context fingerprint includes:
- contract version;
- calendar version / review date;
- reviewed source registry;
- source evidence text;
- selected context events;
- reference-only sources.

Editing a reviewed source/evidence or campaign date therefore changes the Context fingerprint and downstream Historical lineage.

## Historical Intelligence binding

Historical Intelligence contract 1.2 accepts this layer as an explicit context source.

For each factual comparator, the foundation stores separate summaries for:
- current window;
- reference window;
- sample windows where applicable.

Context output includes:
- event IDs;
- context families;
- context types;
- platforms;
- matching-eligible event IDs;
- peak events;
- source tiers.

The current foundation deliberately emits:

`matchEvaluation = NOT_EVALUATED_FOUNDATION_ONLY`

It does not yet decide whether current/reference windows are context-matched.

## Fail-closed safety

Still disabled:
- context-matched baseline;
- anomaly classification;
- alerting;
- diagnosis;
- production Data Mart write;
- production UI modification.

## Validated September checkpoint

GitHub Actions run `36113962295` (#313): **PASS end-to-end**

Runtime checkpoint:
`a9c981d010465cd67d41c6df9e5d13fdca951a5c`

### Business Context

Contract:
`1.1`

Calendar version:
`2026.09.25`

Context fingerprint:
`d4fef77fe3f18d2e9b91ea611dbcd755372fff1e9fc5e29739fb851b9a0a8cd0`

Validated output:
- reviewed sources: 12
- selected events: 17
- context-day rows: 157
- exact-date matching-eligible events: 15
- failed Context QA checks: 0
- explicit-source-only: true

Context QA PASS checks:
- source IDs unique;
- event IDs unique;
- calendar review covers September 2026;
- all sources valid;
- all events valid;
- no search-snippet-only canonical sources.

Artifact:
- `multi-shop-business-context-2026-09`
- artifact ID: `10854197899`
- digest: `sha256:5f6ba702fd54fa4d9d8065aacdd85eccad4160a3b0ca6ca56b2151b899c4b1b7`

### Historical Intelligence 1.2

Historical fingerprint:
`6e700e748b00991625e77abb440188854e1675033038697e89b7f74a3d3e0cd4`

Bound Context fingerprint:
`d4fef77fe3f18d2e9b91ea611dbcd755372fff1e9fc5e29739fb851b9a0a8cd0`

Historical QA:
- business context bound all scopes: PASS
- comparator context bound fail-closed: PASS
- alerts fail-closed: PASS
- diagnosis fail-closed: PASS
- trusted Semantic months still `2026-07, 2026-08, 2026-09`

Artifact:
- ID `10854247722`
- digest `sha256:476a0d1908ae0855483f8971a9fce69321d6f5bbc66b179d14ae53a04002537c`

### UI Payload 1.6

UI Payload fingerprint:
`e56dbc7dcb442418007e042c42c1e1465dffe382deb4f11bfab0daafbf84ed25`

Capabilities:
- `historicalComparatorContext=true`
- `businessContextCalendar=true`
- `contextMatchedBaseline=false`
- `historicalAlerts=false`
- `historicalDiagnosis=false`

QA:
- historical context all scopes bound: PASS
- historical context factual only: PASS
- business context lineage all scopes: PASS
- context-matched baseline fail-closed: PASS

Artifact:
- ID `10854083403`
- digest `sha256:27b22453d66058142e5a73d576439bbb465fbce3e2ca2beba921cd27913b06a8`

### Native V2

Native patch remains:
`native-historical-comparator-v16`

Compatibility patch remains:
`v2-historical-comparator-v6`

Native fingerprint:
`d40893b865ad63fdaa0f850c98a662f89e837e18e657a1933abd0b3985965c2f`

Production V2 source SHA256 remains unchanged:
`9540f23b4d9537441e3bd4cdeafd15747ab4280a87a0130d223984009d99c952`

Artifact:
- ID `10854098417`
- digest `sha256:bba1582539ef4cc22ecb547f3aa7e5cff177ab797bd55347d4ad7ee5649af2ca`

### Upstream business-fact stability

Processed v2:
- SYT+: `7d4fd9288c154e59903525c019d455ee14a807f1f25b7b5c74ed5303641b03aa` — **NOOP**
- Mall: `5cbaff93bdae6d87d6784169e5692698742beed39425536a5a8283b9e9439847` — **NOOP**

Semantic:
- `c25b7cfe67c6d8d477e6e8cd65a466eb3c74ca4f97a3c500b0e9320f1223b321` — **NOOP**

Therefore Context Foundation changed context/intelligence lineage only and did not rewrite canonical business facts.

### Real comparator context examples

At Portfolio latest trusted date `2026-09-17`:
- Previous Day comparator current and reference days are both inside Back-to-School market season + Shopee Siêu Hội Trăng Rằm.
- Previous 7D current window contains 9.9, 15.9 and Siêu Hội Trăng Rằm context.
- Previous 7D reference window contains 9.9 context.
- context matching is intentionally still `NOT_EVALUATED_FOUNDATION_ONLY`.

For Mall latest trusted date `2026-09-23`:
- latest-day Context contains Back-to-School market season only;
- 25.9 is not incorrectly attached because the trusted business date has not reached 25/09.

This confirms context is date-aligned rather than blindly month-tagged.

## Context-Aware Comparator Qualification v1 — completed

Completed in run `36115233375` (#324).

See:
- `docs/context-aware-comparator-qualification-v1.md`

The next milestone is **Context-Matched Historical Baseline v1**.
