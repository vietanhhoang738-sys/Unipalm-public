# UI V2 — Shared Design Language & Destination Architecture

Status: **HARD CONTRACT — PREPRODUCTION**

Machine-readable contracts:
- `config/ui_v2_presentation_contract.json`
- `config/destination_scope_contract.json`

## Principle

Unipalm V2 has **one shared Design Language** and multiple destinations with different information architecture.

Different destinations may:
- answer different operator questions;
- use different content modules;
- have different page lengths and analytical depth;
- expose different time scopes when their canonical source grain differs.

Different destinations must **not** create their own:
- font family;
- color palette;
- dark-mode palette;
- card style family;
- spacing/radius/shadow language;
- terminology system.

The production `automation/command_center_v2_template.html` remains the read-only visual foundation during PREPRODUCTION.

## Destination Scope Doctrine

### Cross-shop orchestration

Cross-shop orchestration belongs to:
- `Command Center` Portfolio scope;
- `So sánh Shop` destination.

### Domain destinations

Product, Ads, Traffic, Customer and later domain pages are **single-shop diagnostic workspaces**.

Non-negotiable rules:
- one Shop is selected at a time;
- there is no `So sánh Shop` mode inside a domain destination;
- Product IDs remain shop-local;
- cross-shop Product merge is forbidden;
- the global time selector must follow the canonical business-source grain;
- a finer-grain supporting source may not fabricate finer granularity for the destination.

### Time scope by source grain

For a canonical **daily** source:
- Ngày;
- Tuần;
- Tháng;
- Năm.

For a canonical **monthly** source:
- 1 tháng;
- 3 tháng;
- 6 tháng;
- Năm.

Daily/weekly display is forbidden when the canonical source is monthly, even if a supporting source such as Ads has daily rows.

For **Customer**:
- global scope is Lifetime;
- no global time selector;
- first purchase, last purchase, recency, active months and similar dates are analytical attributes, not global page filters.

Unavailable horizons must be explicitly disabled. Partial history must never be presented as a complete horizon.

## Current destinations

### Command Center

Purpose:
quickly understand current business health and operating priority.

Scopes:
- Portfolio / Toàn hệ thống;
- one Shop.

Primary mental model:
**monitoring + orchestration** — what is happening now, why, and what needs attention.

Command Center is Intelligence-first: interpretation precedes detailed metric inspection.

### So sánh Shop

Purpose:
deep comparison between two shops.

Scope:
- Shop A ↔ Shop B.

Primary mental model:
**cross-shop analysis** — where two shops differ and why.

Compare uses destination-specific information architecture while reusing V2 visual primitives and tokens.

### Product

Status: **PREPRODUCTION FOUNDATION**

Purpose:
understand product performance inside one Shop and identify which products are driving growth, drag, concentration, funnel weakness or opportunity.

Scopes:
- exactly one Shop;
- time: `1 tháng / 3 tháng / 6 tháng / Năm`.

Canonical business source:
- `dm_product_monthly`;
- grain: `shop_id + data_month + product_id`.

Supporting sources:
- product Ads daily data aggregated into the selected Product horizon;
- current listing/catalog metadata.

Supporting daily Ads does **not** authorize Product day/week views.

Product information priority:
1. Product Intelligence summary;
2. attention / evidence-history state;
3. portfolio structure and concentration;
4. product funnel;
5. Ads support/efficiency;
6. detailed product table.

Product naming follows the shared Product Naming System: commercial product name is primary; SKU is secondary; Product ID is technical metadata only.

## Future domain scope already locked

### Ads

- single Shop only;
- canonical grain: daily;
- Ngày / Tuần / Tháng / Năm;
- no cross-shop comparison inside Ads.

### Traffic

- single Shop only;
- canonical grain: daily;
- Ngày / Tuần / Tháng / Năm;
- no cross-shop comparison inside Traffic.

### Customer

- single Shop only;
- Lifetime-first;
- no global time selector;
- no cross-shop comparison inside Customer.

## Shared foundation

All destinations inherit:
- Inter typography;
- production V2 CSS variables and palette;
- V2 sidebar and navigation grammar;
- V2 light/dark modes;
- V2 radius/shadow/spacing rhythm;
- V2 card hierarchy and number formatting;
- Language System;
- Product Naming System.

Destination-specific CSS may only style content that has no existing V2 primitive. It may not introduce a parallel visual system.

## Navigation contract

PREPRODUCTION sidebar exposes destination navigation.

Command Center scope controls (`Toàn hệ thống`, `Theo shop`) remain inside Command Center and are not separate destinations.

`So sánh Shop` is its own cross-shop destination.

`Sản phẩm` is its own single-shop domain destination. Its Shop and time selectors belong to Product and must not inherit Compare controls.

Future Ads / Traffic / Customer destinations must implement the Destination Scope Doctrine before they can be added to navigation.

## Current QA gates

The Native V2 builder must block an artifact when:
- Inter is overridden;
- a destination defines a color literal outside the approved V2 foundation palette;
- Language System or Product Naming System fails;
- Product exposes day/week horizons;
- Product exposes a cross-shop compare mode;
- an unavailable Product horizon is represented as complete;
- a destination silently aggregates non-additive metrics;
- production V2/Data Mart/index/deployment safety is violated.

Validated Command Center baseline before Product work:
- run #418 / `36217309491`;
- Native patch: `native-production-shadow-mode-v32`;
- Command Center Intelligence-first human visual review: PASS;
- production safety flags remain false.
