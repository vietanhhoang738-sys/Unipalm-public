# Multi-Shop UI Payload Contract v1.x

Status: PREPRODUCTION  
Current contract version: **1.2**  
Source layer: Semantic v2 only

## Purpose

This layer is the canonical boundary between the multi-shop semantic model and the active Native V2 PREPRODUCTION UI.

It prevents the UI from:
- joining shop-local business keys;
- averaging ratios;
- comparing shops across unequal source cutoffs;
- recomputing business logic from raw marts;
- silently treating incomplete capabilities as available.

The canonical flow is now:

`RAW -> Staging/Schema Guard -> Processed v2 -> Durable Processed -> Semantic v2 -> Durable Semantic -> UI Payload v1.x -> Native V2 PREPRODUCTION`

The current consumer is the Native V2 PREPRODUCTION adapter. Production UI remains unbound and unmodified.

## Runtime files

- `config/ui_payload_contract.json`
- `automation/modules/semantic_payload.py`
- `automation/multi_shop_payload_runner.py`
- `automation/tests/test_semantic_payload.py`

CI evidence is emitted under:

`payload_artifacts/<YYYY-MM>/`

with:
- `ui_payload.json`
- `payload_manifest.json`
- `payload_qa_report.json`

## Scope model

The payload has three explicit scope modes.

### Portfolio

Portfolio scope represents all enabled shops.

Its date window is the intersection of every shop's common reliable window:

`portfolio_start = MAX(shop.common_reliable_start)`

`portfolio_end = MIN(shop.common_reliable_end)`

This prevents a fresher shop from receiving extra days in a portfolio total.

September 2026 real validation:
- SYT+: reliable through 2026-09-17
- Mall: reliable through 2026-09-21
- Portfolio: 2026-09-01 through 2026-09-17

Portfolio ratios are recomputed from additive facts:
- AOV = total placed GMV / total placed Orders
- CVR = total placed Orders / total Product Clicks
- ROAS = total attributed Ads sales / total Ads spend
- platform cost ratio = (total order fees + total Ads spend) / total net sales after cancel

The payload does not expose cross-shop totals for non-additive unique metrics such as Visits, Buyers, Unique Impressions, or Unique Clicks.

### Shop

Shop scope uses that shop's own common reliable window.

Daily Visits/Buyers may be shown at shop-day grain because they are source metrics at that grain.

Product view is supported only inside shop scope in v1.

### Compare

Compare scope is pairwise and N-shop safe.

For each unordered pair of enabled shops, the adapter creates one comparison using the intersection of only those two shops' common reliable windows.

Comparison semantics are explicit:
- left shop
- right shop
- right minus left absolute difference
- right versus left percentage difference

Compare data is horizon-first:
- `latestDay`
- `last7`
- `mtd`

Pair-level MTD compatibility aliases (`leftHeadline`, `rightHeadline`, `metrics`) were removed in contract v1.2. Consumers must read the selected horizon directly.

Ads Product analysis uses `dm_ads_product_daily` and is aligned to the selected Compare horizon. Business Product concentration remains explicitly MTD/monthly because Product Performance is monthly-grain.

The payload does not choose a winner or rank shops.

For N shops, pair count is:

`N * (N - 1) / 2`

Synthetic 3-shop tests verify all three pair combinations.

## Shop selector

Selector order is controlled by Shop Registry through `dim_shop`.

The payload must not sort current shop identities inside runtime code.

Current registry order:
1. SYT+
2. Mall

Adding another shop must be configuration/onboarding work, not a payload code fork.

## Product identity policy

Product ID is shop-local.

Canonical identity remains:

`shop_id + product_id`

The same Product ID may exist in several shops without collision.

Payload v1 deliberately does not create Portfolio Product aggregation because:
1. Product ID is not cross-shop identity;
2. Product Performance is monthly/MTD and does not yet expose an exact daily cutoff suitable for safe cross-shop alignment.

Each shop payload contains its own Product list and catalog join state.

## Traffic policy

Traffic is built from Semantic v2 daily traffic rows, not from a pre-aggregated monthly row when cross-shop alignment is required.

Only the `placed` commercial stage is used for the operating payload.

Within the aligned window, additive traffic facts are summed by:

`channel_group + traffic_source`

and ratios are recomputed.

Group totals and child sources remain separate rows.

## Capability flags

The payload explicitly advertises what is and is not supported.

Current enabled capabilities:
- multi-shop selector
- Portfolio scope
- pairwise Compare
- shop-level Product view

Current disabled capabilities:
- cross-shop Product aggregation
- Customer Lifetime
- 6-month historical Intelligence
- Today matched-hour
- production UI binding

A UI must respect these flags rather than fabricate a missing feature.

## QA gates

Payload QA blocks on:
- selector shop scope mismatch;
- missing shop scope;
- Portfolio GMV reconciliation;
- Portfolio Orders reconciliation;
- incorrect AOV/CVR/ROAS recomputation;
- wrong N-shop Compare pair count;
- duplicate compare IDs;
- duplicate product identity inside a shop.

The payload is deterministic for unchanged Semantic v2 facts.

## Current real validation

Cleanup checkpoint: GitHub Actions run #244 / `35992225052` — PASS.

UI Payload contract: `1.2`

Source Semantic fingerprint:

`fb862a21b281d3b33611e35c060d5dfbbe19a3bdbb455fc9f9c034b755a3c162`

Payload fingerprint:

`58f054911b139278ee2cf0350e76746bb77dc3e8f22c4a578721b0ca03af4f78`

Current payload behavior:
- 2 registry shops;
- Portfolio / Toàn hệ thống scope;
- 2 individual Shop scopes;
- 1 pairwise Compare object;
- Compare stores horizon-aligned business data only and does not duplicate per-shop V2 payloads inside each pair;
- production UI binding remains disabled.

Native V2 downstream validation from the same run passed 30/30 checks.

## Safety boundary

UI Payload v1:
- does not write the legacy Data Mart;
- does not publish a legacy payload;
- does not modify production UI;
- does not deploy `index.html`;
- does not bind to Command Center V2 template.

The current consumer is the native V2 PREPRODUCTION adapter. Production UI binding remains disabled.
