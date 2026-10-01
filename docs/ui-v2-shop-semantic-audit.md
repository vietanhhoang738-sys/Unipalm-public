# UI V2 Shop Semantic Audit — 2026-09-25

Status: **HARDENED PREPRODUCTION CONTRACT**

Scope: `Command Center > Theo shop`.

This batch does not redesign the accepted V2 visual baseline and does not modify production V2, production Data Mart, index or deployment.

## Scope identity

A Shop view is exactly one registry-backed `shop_id` over that shop's own common reliable window. No metric in this view may borrow rows from another shop.

## Metric classes

Period-additive facts such as GMV, Orders, Product Clicks, Ads spend/sales, cancellations/refunds and order fees may be summed across days inside one shop. Ratios are recomputed from additive components, never averaged:

- AOV = SUM(Placed GMV) / SUM(Placed Orders)
- CVR = SUM(Placed Orders) / SUM(Product Clicks)
- ROAS = SUM(Ads Attributed Sales) / SUM(Ads Spend)
- Platform cost ratio = (SUM(Order Fees) + SUM(Ads Spend)) / SUM(Net Sales After Cancel)

Daily-unique facts remain daily-only:

- Visits
- Buyers
- New Buyers
- Existing Buyers
- Potential Buyers

They remain available on daily rows but are not summed into 7D or MTD unique totals. The Shop headline omits them.

## Funnel definition

The period-safe primary conversion metric is:

`Placed CVR = Placed Orders / Product Clicks`

Visits are not the denominator of period CVR. A Visits → Product Clicks bridge is permitted only for a one-day period until an exact period-level unique Visits source exists.

## Traffic Source

Multi-day Traffic Source output uses only additive sales, impressions, clicks, attributed orders and attributed units. CTR, conversion rate, sales/order and shares are recomputed after aggregation.

Traffic buyers, unique impressions and unique clicks are intentionally not emitted into multi-day Shop traffic output.

## Product Performance

Business Product Performance remains **source-MTD, shop-scoped**.

Identity remains `shop_id + product_id`.

The current source must not be back-derived into Day or 7D Product Performance, and Product ID must never be cross-shop merged.

## Time labels and partial windows

The latest trusted date is shown as **Ngày gần nhất**.

If a requested 7D or MTD window is not fully covered, the UI labels the observed window instead of pretending it is complete, for example `4 ngày khả dụng · 01/09–04/09`.

Comparisons remain available only when both current and previous windows are complete and matched.

## QA gates

Payload QA blocks daily-unique fields in Shop headline, duplicate Shop-day grain, incorrect daily AOV/CVR/ROAS/platform-cost recomputation, unique Traffic metrics leaking into multi-day output, and Product Performance escaping the source-MTD shop-only contract.

Native V2 QA blocks one-day Visits disappearing when present, 7D/MTD Visits being summed, Product coverage losing the source-MTD constraint, and comparisons being marked available with incomplete windows.

## Next milestone

The next batch is **Historical Intelligence foundation**: establish multi-month history and comparator contracts before Business Pulse / Smart Issues are allowed to publish historical alerts or diagnoses.
