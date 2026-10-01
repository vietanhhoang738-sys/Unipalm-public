# Command Center V2 — Data Contract v0.1

Status: AUDITED against production mart and September 2026 processed outputs on 2026-09-21.

## 1. Design principles

1. Command Center V2 is a historical operating-analysis workspace, not a real-time monitoring system.
2. The normal operating workflow is: update source data → rebuild Data Mart → open Command Center.
3. Commercial headline authority uses Shopee Business Insights stage `placed` (Đơn đã đặt) for GMV / Orders / CVR / AOV.
4. Orders `order_created_at` is the timestamp authority for optional matched-hour / hourly order-created analysis.
5. "Today" matched-hour is a convenience view only when the rebuilt dataset contains the current day; it is not an architectural requirement for real-time ingestion.
6. "Yesterday" uses full D-1 vs full D-2.
7. MTD uses day 1 through D vs the same day count in the previous month.
8. Diagnosis is gated by the latest rebuilt dataset and DQ eligibility, not by wall-clock recency.
9. No insight is published only to fill UI space.

## 2. Current source authority

| Domain | Production authority | Current grain | Current observed cutoff |
|---|---|---:|---|
| Orders | orders_processed_YYYY_MM.fact_orders / fact_order_items | order / item | 2026-09-18 present in Sep snapshot |
| Business Insights | fact_shop_performance_daily | shop-day-stage | 2026-09-17 |
| Ads | fact_ads_performance_daily | shop-day | 2026-09-17 |
| Product Performance | fact_product_performance_monthly / variant | product-month | 2026-09 MTD |
| Production Data Mart | dm_* tables | daily / monthly / lifetime | source-dependent |
| Data Health | dm_data_health | source-as-of | 2026-09-17 commercial cutoff |

Important: the dataset cutoff is intentionally treated as the latest rebuilt analytical state. The Command Center must not infer a data-quality problem merely because the wall-clock date is later than the dataset cutoff.

## 3. Time-horizon contract

### TODAY_MATCHED_HOUR (optional convenience view)
- Only active when the rebuilt source set contains the current day.
- cutoff_hour = the latest complete hour available in the Orders snapshot, not the current wall-clock hour.
- current window = available current-day Orders from 00:00 through cutoff_hour.
- comparator = prior day through the same cutoff.
- Orders timestamps support order-created count, placed-sales proxy, and AOV proxy by hour.
- This view must not force the rest of the Command Center into real-time architecture.
- CVR / Visits / Product Clicks remain governed by rebuilt Business Insights data; do not fabricate hourly denominators.

### YESTERDAY_FULL_DAY
- current = D-1 full local day.
- comparator = D-2 full local day.
- BI / Ads daily sources are authoritative when both dates are complete.

### MTD_SAME_DAY_COUNT
- current = month start through latest complete day D.
- comparator = previous month day 1 through D.
- never compare partial MTD with the previous full month.

## 4. KPI contract

| UI KPI | Canonical formula / source | Historical periods | Optional Today matched-hour |
|---|---|---|---|
| GMV | BI `placed.gross_sales` | READY | Orders timestamp sales proxy only when current-day snapshot exists |
| Đơn hàng | BI `placed.order_count` | READY | Orders `order_created_at` count |
| Tỷ lệ chuyển đổi | BI `placed.order_conversion_rate` | READY | No hourly CVR unless BI hourly denominator exists |
| AOV | BI `placed.gross_sales / placed.order_count` | READY | Orders placed-sales proxy / order-created count |
| ROAS Ads | attributed_sales / ad_spend | READY | Use latest rebuilt Ads period; no realtime requirement |
| Ads Spend | SUM(ad_spend) | READY | Use latest rebuilt Ads period; no realtime requirement |

## 5. Commercial-stage authority and Orders timestamp audit

### Canonical commercial stage

Command Center V2 uses `placed` / **Đơn đã đặt** as the default shop operating stage.

Historical headline metrics:
- GMV = BI placed gross_sales
- Orders = BI placed order_count
- CVR = BI placed order_conversion_rate
- AOV = BI placed gross_sales / placed order_count
- Traffic = BI placed visits
- Product Clicks = BI placed product_clicks

This matches the user's operating workflow and keeps the entire commercial diagnosis on one consistent stage.

### Orders timestamp role

fact_orders contains order_created_at at minute-level, e.g. 2026-09-01 10:16, 12:27, 17:38, 19:33, etc. This is sufficient for:
- order-created count by hour,
- order-value / item-sales proxy by hour,
- AOV proxy by hour,
- product order / product sales trend by hour or day.

It represents the placed/order-created event, which is exactly the intended commercial stage for Command Center V2. It is therefore appropriate for hourly order-created analysis. BI remains the daily authority for the canonical placed GMV/CVR/AOV totals.

### Intraday gross-sales reconciliation audit

A candidate Orders proxy:
- daily item sales base = SUM(fact_order_items.item_buyer_payment)
- subtract seller-funded order-level discounts where contractually appropriate.

Against BI placed gross_sales for 2026-09-01..17, a simple item-buyer-payment minus shop-voucher proxy reconciled exactly on most days, but showed residual differences on 09/09 (~0.48%), 09/12 (~1.26%), and 09/14 (~0.59%).

Conclusion: Orders supports intraday timing, but the gross-sales semantic must be formally reconciled before it is called canonical GMV.

## 6. GMV driver explanation

For rebuilt BI historical periods, use the placed-stage multiplicative bridge:

GMV = Visits × Product Click Rate × Placed CVR × AOV

Where:
- Product Click Rate = placed product_clicks / placed visits
- Placed CVR = placed orders / placed product_clicks
- AOV = placed gross_sales / placed orders

Recommended driver labels:
1. Lượt truy cập effect
2. Product click rate effect
3. CVR effect
4. AOV effect
5. Residual / interaction

This is a historical diagnosis engine. It should prioritize Yesterday / prior week / prior month / MTD and other rebuilt periods. Optional Today matched-hour does not require an hourly CVR decomposition.


## 6A. GMV Driver Engine v1

Command Center uses an exact **Shopee-native top-level identity**:

`GMV = Product Clicks × CVR × AOV`

Driver contribution is calculated with **Shapley decomposition** across the three user-facing factors:
- Lượt nhấp vào sản phẩm
- Tỷ lệ chuyển đổi
- AOV

`Product Click Rate` is **not** a Shopee Center KPI. It is a derived technical ratio:

`Derived Click Rate = Product Clicks / Visits`

It is kept only in a second-level supporting bridge:

`Product Clicks = Visits × Derived Click Rate`

This prevents double-counting Traffic and Product Clicks in the top-level GMV decomposition while preserving Traffic as an explanatory supporting signal.

Why Shapley:
- multiple factors can move at the same time,
- a fixed sequential bridge makes attribution depend on calculation order,
- Shapley averages all factor orders and allocates interaction effects fairly,
- the three top-level driver effects sum exactly to `ΔGMV` apart from floating-point rounding.

Output per top-level driver:
- current / previous value,
- percentage change,
- GMV effect value,
- direction,
- share of absolute explanatory effects,
- share of net GMV change,
- rank.

Supporting click bridge additionally reports:
- Visits current / previous / delta,
- derived click-rate current / previous / delta,
- Product Clicks current / previous / delta.

No artificial residual bucket is required when all three top-level factors are positive and available.

## 6B. Historical Baseline Engine v1

The anomaly engine evaluates **change vs historical change patterns**, not merely a hard-coded percentage threshold.

For each horizon:
- **Hôm qua:** historical same-weekday observations; each observation is compared with its immediately prior day.
- **7 ngày gần nhất:** historical rolling 7-day windows; each is compared with the preceding 7-day window.
- **MTD:** historical day-1-to-D windows; each is compared with day-1-to-D of the prior month.

Metrics currently baselined:
- GMV
- Orders
- Visits
- Product Clicks
- Product Click Rate
- CVR
- AOV
- Ads Spend
- ROAS

Robust statistics:
- median historical delta,
- P10 / P25 / P75 / P90,
- MAD,
- robust z-score,
- sample size,
- confidence.

A signal is not alert-eligible merely because it is outside the historical band.

### Campaign / calendar context v1

Each comparison carries a context signature:
- double-day count imbalance (e.g. 9.9),
- payday-window day-count imbalance,
- month-start day-count imbalance.

The engine first tries to learn from historical comparisons with the same context signature.
If there are fewer than 4 comparable historical observations, it falls back to broader history with lower confidence.

If the current comparison has a context mismatch and there is not enough matched-context history:
- `suppressedByContext = true`
- `alertEligible = false`

Example validated on the current dataset:
- 11–17/09 vs 04–10/09 has a double-day imbalance because the previous window contains 9.9.
- Raw GMV delta is therefore not sufficient evidence for a business alert.

These calendar rules are a first deterministic layer, not an authoritative campaign calendar. A future explicit commerce-calendar dimension can override/extend these tags.


## 7. Smart Issues

### Whole-shop daily anomalies
DERIVABLE from historical dm_shop_daily + dm_ads_daily + dm_order_quality_daily.

Recommended scoring dimensions:
- expected baseline,
- deviation,
- persistence,
- sample size,
- business impact,
- confidence,
- calendar/campaign context.

### Intraday anomalies
Not a V2 priority. Do not add streaming / hourly BI / Ads infrastructure unless a future operating requirement explicitly needs it.


## 7A. Smart Issue Scoring Engine v1

The `Cần xử lý` block is not a list of all negative deltas. It is a ranked set of **actionable historical anomalies**.

Initial whole-shop issue candidates are tied to user-facing GMV drivers:
- Lượt nhấp vào sản phẩm
- Tỷ lệ chuyển đổi
- AOV

Lượt truy cập remains an upstream supporting signal for Product Clicks and is not scored as a second simultaneous top-level GMV driver.

An issue candidate must satisfy all of the following:
1. its Shapley GMV effect is negative,
2. the metric is `LOW` versus its historical change baseline,
3. the historical baseline itself is alert-eligible,
4. campaign/calendar context does not suppress the signal,
5. persistence is sufficient,
6. final Smart Issue score is at least 50.

### Scoring dimensions

All inputs are normalized to 0–1.

- **Impact**: absolute negative Shapley GMV effect, scaled so a 15% prior-period GMV effect reaches full materiality.
- **Deviation**: severity of historical deviation using robust z-score, with crossing the historical P10 band treated as meaningful.
- **Persistence**: repeated daily underperformance against same-weekday historical expected bands.
- **Confidence**: historical sample confidence from the baseline engine.
- **Context**: campaign/calendar comparability factor.

The score uses a weighted geometric mean:

`Score = 100 × Impact^0.30 × Deviation^0.25 × Persistence^0.20 × Confidence^0.15 × Context^0.10`

This remains multiplicative: a weak dimension can prevent a superficially large raw delta from becoming an alert.

### Actionability gate

A one-day driver signal must **not** automatically become an issue when total GMV is still within its historical range.

- If total GMV is historically `LOW`, lower persistence can be accepted.
- If total GMV is `NORMAL`, persistence must be stronger.
- A one-day signal can bypass the persistence gate only when deviation is extreme (`|robustZ| >= 2.5`).

Severity:
- `High`: score >= 70 **and** total GMV is itself alert-eligible LOW.
- `Med`: score >= 50, or any otherwise-High driver whose total GMV remains within historical range.
- score < 50: not shown in `Cần xử lý`.

The engine is explicitly allowed to return:

`NO_ACTIONABLE_ISSUES`

No `Info` filler is generated simply to occupy UI space.

### Persistence logic

Daily persistence uses same-weekday historical expected bands over the previous 12 weeks and prefers matching calendar context when enough samples exist.

- Yesterday horizon: recent consecutive low days, target 3 days for full persistence.
- Rolling 7D: combines low-day count within the window and consecutive low days at the tail.
- MTD: combines low-day density within MTD and consecutive tail persistence.

Each generated issue includes a stable anomaly identifier based on metric + first observed date, allowing the later Diagnostic Drawer lifecycle to reuse the same anomaly rather than recreate it from scratch.

### Current v1 scope

Smart Issue v1 covers whole-shop commercial GMV drivers.

Ads-specific efficiency anomalies, product-level anomalies, and data-health issues use separate diagnostic contracts and should not be forced into the same scoring formula merely for UI consistency.


## 8. Product Opportunity / Problem

| Signal | Status | Source |
|---|---|---|
| Product order / sales trend | DERIVABLE | Orders fact_order_items + order_created_at |
| Product Ads trend | READY / DERIVABLE | dm_ads_product_daily |
| Product monthly performance | READY | dm_product_monthly |
| Daily product CVR anomaly | MISSING | current Product Performance is monthly |
| Daily product traffic/click anomaly | MISSING | no canonical product-day organic traffic table |
| Long-history confidence score | DERIVABLE after baseline engine | V2 diagnostic mart |

Do not display a CVR-based product problem until daily product traffic/click denominators are available.


## 8A. Product Opportunity / Problem Engine v1

The Home product block is intentionally **structural and high-confidence**, not a daily noise detector.

### Historical frame

A product must have at least 5 of 6 positive completed-month observations.

The engine compares:
- **Recent window:** latest 3 complete months
- **Previous window:** 3 complete months immediately before that

Current MTD is **corroborating evidence only**. It is never used as the primary historical baseline.

Core product metrics:
- placed GMV
- placed Orders
- Product Clicks
- CTR
- product CVR = placed Orders / Product Clicks
- AOV

### Materiality and eligibility

A product must:
- be currently active,
- not be a technical gift / gift SKU,
- have >= 83% six-month history coverage,
- contribute at least 2% of recent-3-month product GMV,
- show at least 35% structural GMV change,
- have at least two supporting metrics moving in the same direction.

A signal also requires either:
- at least one persistent month-to-month move at the tail, or
- current MTD daily pace corroborating the same direction.

### Signal score

The v1 structural score combines:
- trend magnitude: 28%
- product materiality: 24%
- supporting metric agreement: 18%
- multi-month persistence: 15%
- current-MTD corroboration: 15%

Minimum score: **70**.

The engine is allowed to return:
`NO_HIGH_CONFIDENCE_SIGNALS`

The UI must not invent a matching Opportunity card when only a Problem qualifies, or vice versa.

### Current validated result

On the current dataset, only one product signal passes the v1 gate:

**Khẩu trang chống tia UV Cool S3 — Vấn đề**
- recent 3-month GMV vs prior 3 months: about -43.0%
- Orders: about -45.2%
- Product Clicks: about -31.8%
- CVR: about -19.6%
- AOV: slightly positive
- current MTD daily pace continues to corroborate the weaker structural trend

No product Opportunity currently passes the same high-confidence gate.


## 9. Business Pulse

DERIVABLE as deterministic narrative from:
- selected time horizon,
- KPI deltas,
- GMV driver bridge,
- high-confidence Smart Issues,
- source eligibility.

The LLM/text layer may phrase the explanation, but it must not invent the underlying diagnosis.


## 8A.1 Product Signal Ranking v1

Signal eligibility and priority ranking are separate layers.

A product must first pass the Product Opportunity / Problem Engine gate.
Only eligible signals enter the ranking layer.

Priority is calculated from four normalized 0–1 dimensions:

- **GMV Impact**: normalized structural GMV impact on the shop. Prior-3M GMV is day-count normalized to the recent-3M window before impact is calculated. An impact equivalent to 5% of recent shop product GMV reaches full scale.
- **Deviation**: absolute structural GMV change. A 60% move reaches full scale.
- **Persistence**: combines month-to-month tail persistence with current-MTD corroboration.
- **Confidence**: six-month coverage and agreement across supporting evidence.

Formula:

`Priority Score = 100 × (Impact × Deviation × Persistence × Confidence)^(1/4)`

A geometric mean is used so a product cannot rank highly from one extreme dimension while the others are weak.

Ranking outputs:
- globalRank
- rankWithinType
- priorityScore
- structuralImpactValue
- structuralImpactShare
- priorityComponents

Home behavior:
- show the highest-priority Problem, if any;
- show the highest-priority Opportunity, if any;
- never create a filler card when one side has no eligible signal.

The payload additionally retains ranked summaries for up to:
- top 10 Problems,
- top 10 Opportunities,
- top 20 signals overall.

Current validation:
- only one product currently passes the eligibility gate: Cool S3;
- it ranks Problem #1 with Priority Score about 80.6/100;
- its normalized structural impact is about ₫68.0M, equivalent to about 8.8% of recent-3M shop product GMV.


## 8B. Product root-cause diagnosis contract

The Product Drawer must separate **what the data proves** from **what still needs verification**.

### Evidence layers

For a structural product signal, the engine evaluates:
- Doanh số / đơn hàng
- Lượt xem sản phẩm
- Lượt nhấp vào sản phẩm
- CTR
- Lượt truy cập trang sản phẩm
- Tỷ lệ thoát
- Lượt thêm vào giỏ
- Tỷ lệ truy cập → thêm vào giỏ
- CVR
- Doanh số trên mỗi đơn (AOV)
- Số sản phẩm/đơn
- Product-level Ads: impressions, clicks, conversions, attributed sales, Ads Spend, ROAS, CPC, CPA and ACOS when available

The UI language follows marketplace operating terminology used in Vietnam:
- Vietnamese first for business meaning,
- familiar abbreviations such as GMV / CVR / AOV / Ads may remain when they help operators,
- internal derived metrics must be explicitly marked as derived,
- technical implementation words such as `baseline`, `corroborate`, `driver`, `signal score` should not be the primary user-facing wording.

### Direct findings vs hypotheses

**Direct findings** require observable metric evidence.

Example patterns:
- Views and Product Clicks fall while CTR is stable/up → distribution/exposure is weaker; click attractiveness is not the primary bottleneck.
- Bounce Rate rises while Visit→ATC and CVR fall → post-click funnel quality is weaker.
- AOV is stable/up → order value does not explain the GMV decline, but this does not rule out price/voucher effects on CVR.
- Product Ads impressions/clicks/spend fall while ROAS improves → paid volume/support is lower, but Ads efficiency itself is not the weak point.

**Hypotheses** must be labeled as hypotheses until the system has direct evidence:
- search/recommendation distribution loss,
- PDP/offer competitiveness,
- traffic-quality shift,
- price/voucher,
- review/rating,
- stock/variation availability,
- paid-support changes,
- category/competitive demand shifts.

Every hypothesis must include a concrete verification step.

### Ads integration rule

Product diagnosis must combine **Product Performance + Ads** whenever product-level Ads data exists.

The product Ads mart contract includes:
- impressions / clicks / CTR
- conversions / CVR
- attributed sales
- Ads Spend
- ROAS
- CPC / CPA / ACOS

Do not interpret high Ads contribution or dependence as a problem by itself. Diagnose Ads only when its **volume, efficiency, or change pattern** materially helps explain the product trend.

### Current Cool S3 evidence

For the current validated Cool S3 signal, recent 3 complete months vs prior 3 complete months show approximately:
- GMV -43.0%
- Orders -45.2%
- Product Views -35.7%
- Product Clicks -31.8%
- CTR +6.1%
- Bounce Rate about +99%
- Visit→ATC Rate about -26.3%
- CVR about -19.6%
- AOV about +3.8%
- Product Ads, recent 28d vs prior 28d: impressions about -62.8%, clicks -59.4%, Ads Spend -68.7%, attributed sales -51.1%, ROAS +56.3%

Therefore the current evidence-led conclusion is:
1. product exposure/distribution weakened materially;
2. post-click funnel quality also weakened;
3. paid distribution volume also contracted materially, while ROAS improved; lower paid volume is a plausible contributor, not poor Ads efficiency;
4. order value is not the main explanation;
5. specific operational causes such as price, voucher, listing content, rating, stock or variation availability remain hypotheses until directly checked.


## 9A. Diagnostic Drawer lifecycle contract

The Drawer is no longer a static mock. It renders from the exact signal object that was clicked.

### Shop Smart Issue Drawer

Input key:
- `anomalyId`

Payload includes:
- metric and severity,
- score / confidence,
- Shapley GMV impact,
- historical baseline statistics,
- persistence,
- campaign/calendar context,
- 30-day actual series,
- 30-day expected median / P10 / P90 when available,
- deterministic next-check list.

Chart:
- actual metric line,
- expected P10–P90 band,
- low observations highlighted.

The Drawer must not assert unsupported causes such as “listing changed” or “Ads caused this” unless an upstream diagnostic source proves that claim.

### Product Signal Drawer

Input key:
- `signalId`

Payload includes:
- product name / category,
- 6 complete historical months,
- recent 3M vs prior 3M,
- Product Clicks / CVR / AOV changes,
- current MTD corroboration,
- Ads support when product-level Ads activity exists,
- deterministic next-check list.

Chart:
- placed GMV over the six complete historical months,
- recent three months visually distinguished.

### Lifecycle

The same `anomalyId` / `signalId` should be reused across rebuilds while the underlying signal remains the same.
A later lifecycle layer can transition:
- OPEN
- MONITORING
- RESOLVED

The Drawer is versioned by rebuilt evidence, not recreated as a different alert every time the dashboard opens.


## 10. Data Health contract

Current dm_data_health is READY for source-level status, but V2 should add/derive:
- latest_complete_data_date,
- latest_partial_data_datetime,
- freshness_hours,
- complete_vs_partial flag,
- DQ blocking count,
- DQ warning count,
- metric_eligibility_today,
- metric_eligibility_yesterday,
- metric_eligibility_mtd,
- diagnosis_eligible.

If a source is older than another rebuilt source, the UI should show its actual coverage. Do not call it "stale" solely because the wall-clock date advanced; the relevant question is whether the dataset was intentionally rebuilt and internally consistent.

## 11. V2 mart layers

### dm_shop_hourly
Purpose: optional Orders-timestamp matched-hour analysis using the placed/order-created event.

This table is useful for:
- order-created distribution by hour,
- matched-hour Orders,
- placed-sales proxy by hour,
- AOV proxy by hour,
- product/order timing analysis.

It is **not** a dependency for the historical core of Command Center.

No `fact_intraday_commercial_snapshot` or `fact_intraday_ads_snapshot` is required for the current V2 scope.

## 12. D2 readiness summary

| D2 block | Status now |
|---|---|
| Historical placed GMV / Orders / CVR / AOV | READY |
| Yesterday card | READY |
| MTD card | READY |
| Prior week / prior month comparisons | DERIVABLE |
| Optional Today matched-hour Orders timing | READY from Orders timestamp when current-day data exists |
| Optional Today matched-hour sales/AOV proxy | DERIVABLE |
| 6 KPI historical periods | READY |
| Business Pulse historical periods | DERIVABLE |
| GMV Explanation historical periods | DERIVABLE |
| Whole-shop Smart Issues daily | DERIVABLE |
| Product sales/order opportunities | DERIVABLE |
| Product daily CVR issues | MISSING |
| Data Health | READY, needs V2 eligibility fields |
| Diagnostic Drawer | PARTIAL; evidence depends on signal type |

## 13. Next implementation order

1. Keep `dm_shop_hourly` as an optional placed/order-created analytical layer.
2. Bind Yesterday + MTD + historical period selection + Data Health to real mart data.
3. Make `placed` the canonical stage for GMV / Orders / CVR / AOV.
4. Implement historical GMV driver decomposition.
5. Build historical baseline / anomaly scoring from prior business patterns.
6. Build product opportunity/problem engine only where historical evidence is strong.
7. Extend product-day authority later if daily product CVR diagnosis becomes necessary.
8. Do not build realtime BI/Ads snapshot infrastructure for the current scope.
