# UI V2 Portfolio Semantic Audit — 2026-09-25

Status: **HARDENED PREPRODUCTION CONTRACT**

Scope: `Command Center > Toàn hệ thống` only. This milestone does not redesign the accepted V2 visual baseline and does not modify production V2, production Data Mart, index or deployment.

## Business meaning

`Toàn hệ thống` means the aggregate of **all enabled shops** over the intersection of their common reliable windows.

A Portfolio day is valid only when every enabled shop contributes that day. The view must fail closed rather than mix unequal shop coverage.

## Metric classes

### Additive across shops and days

Safe additive components include GMV, Orders, Product Clicks, Ads Spend, Ads Attributed Sales, order fees, cancelled sales and other transaction/count facts explicitly listed in `config/ui_payload_contract.json`.

### Ratios

Ratios are never averaged across shops.

- AOV = SUM(Placed GMV) / SUM(Placed Orders)
- CVR = SUM(Placed Orders) / SUM(Product Clicks)
- ROAS = SUM(Ads Attributed Sales) / SUM(Ads Spend)
- Platform cost ratio = (SUM(Order Fees) + SUM(Ads Spend)) / SUM(Net Sales After Cancel)

The same rule is enforced at Portfolio daily grain and Portfolio headline grain.

### Non-additive unique metrics

Portfolio must not expose totals for:

- Visits
- Buyers
- New Buyers
- Existing Buyers
- Potential Buyers
- Unique Impressions
- Unique Clicks

These metrics are not safely additive across shops and/or days. Absence is intentional; the UI must not silently convert unavailable Portfolio uniques into zero.

## Time semantics

The latest trusted Portfolio date is the aligned `commonReliableEnd`, not the wall-clock previous day.

The visible label is therefore **“Ngày gần nhất”**, while the legacy internal V2 key remains `yesterday` only for renderer compatibility.

A period comparison is published only when both the current and previous calendar windows contain the full expected number of days. Partial windows degrade to “comparison unavailable”; they are not compared as if equivalent.

## UI binding

Portfolio continues to reuse the accepted production V2 renderer through the PREPRODUCTION compatibility layer.

The compatibility layer now guarantees:

- visible Portfolio source label = `Toàn hệ thống`;
- latest complete date wording = `Ngày gần nhất`;
- Visits are marked unavailable in Portfolio period models;
- comparison deltas are emitted only for complete matched-length windows.

## QA gates

Payload QA now blocks:

- any forbidden non-additive Portfolio total;
- a Portfolio day missing an enabled shop;
- AOV/CVR/ROAS/platform-cost ratios that are not recomputed from additive components.

Native V2 QA now blocks Portfolio binding if:

- “Ngày gần nhất” semantics are absent;
- Portfolio source identity is not `Toàn hệ thống`;
- unavailable Visits are treated as available;
- a comparison is marked available without complete current and previous windows.

## Deferred to the next milestone

The next audit is `Command Center > Theo shop`.

That audit must separately decide the semantics of Visits/Buyers across multi-day windows, traffic/funnel metrics, product scope, and which shop-local metrics are valid for Day / 7D / MTD. No Portfolio decision in this document should be used to infer those shop-scope rules.
