# Ads Intelligence V2 Foundation

**Status:** PREPRODUCTION foundation validated  
**Canonical checkpoint:** run #496 (`36395583180`)  
**Validated branch:** `multi-shop-catalog-resolver`  
**Native patch:** `native-ads-intelligence-v37`

## 1. Purpose

Ads V2 is a single-shop diagnostic workspace. It is not a cross-shop comparison page and it does not replace the Command Center. Its operator question is:

> How efficiently is this shop using Ads, what changed versus an equivalent prior period, which products deserve attention, and which mathematical ROAS factor contributed most to that change?

The destination follows the project Destination Scope Doctrine:

- one shop at a time;
- no `So sánh Shop` surface inside Ads;
- canonical Ads source grain is **daily**;
- supported time scopes are **Ngày / Tuần / Tháng / Năm**;
- unavailable scopes are explicitly disabled rather than synthesized from incomplete history;
- production remains untouched.

## 2. Canonical sources

Ads Intelligence v1 trusts only QA-passed durable Semantic v2 partitions.

Canonical marts:

- `dm_ads_daily` — shop/date grain;
- `dm_ads_product_daily` — shop/date/product grain.

Legacy `ads_processed_*` files are not authoritative for this foundation.

All ratio metrics are recomputed from additive facts. Ratios are never averaged across days.

Derived metrics include:

- CTR = Clicks / Impressions;
- CVR Ads = Conversions / Clicks;
- ROAS = Ads-attributed sales / Ads spend;
- CPC = Ads spend / Clicks;
- CPM = Ads spend × 1000 / Impressions;
- CPA = Ads spend / Conversions;
- ACOS = Ads spend / Ads-attributed sales;
- Ads AOV = Ads-attributed sales / Conversions.

## 3. Time-scope behavior

### Day

One selected trusted Ads date. Prior-day comparison is used only if the prior date is also trusted.

### Week

Rolling seven-day window ending on the selected trusted date. Comparison is the immediately preceding non-overlapping seven-day window.

### Month

Calendar month from day 1 to the latest trusted date in that month. Comparison uses the same elapsed-day count in the immediately previous calendar month when the required dates are trusted.

### Year

Calendar YTD for a pre-existing shop. A shop explicitly identified as `SHOP_LAUNCH` may begin at its first trusted operating date. Missing pre-launch days are not treated as missing business history.

## 4. Intelligence policy

Ads V2 does not use a simplistic global rule such as `low ROAS = bad`.

Product signals compare the same product against its own equivalent previous period. A product must have meaningful current spend share before it can become a signal.

Foundation thresholds:

- minimum product spend share: 3%;
- minimum absolute ROAS change: 15%;
- maximum product signals retained per snapshot: 8.

Signals are ranked using spend scale, ROAS change, sales movement and confidence.

### ROAS driver decomposition

The foundation uses the business identity:

`ROAS = Ads CVR × Ads AOV / CPC`

An exact Shapley decomposition over that identity assigns the modeled ROAS gap to:

- CVR Ads;
- AOV Ads;
- CPC.

These values are **identity contributions, not causal claims**. The UI explicitly states this boundary.

## 5. Real validated coverage at run #496

Trusted canonical Semantic Ads months: `2026-07`, `2026-08`, `2026-09`.

### SYT+

- trusted Ads dates: `2026-07-01` → `2026-09-27`;
- Day: available;
- Week: available where a contiguous seven-day window exists;
- Month: Jul / Aug / Sep available;
- Year 2026: **disabled** because this is a pre-existing shop and canonical Ads history does not yet cover Jan–Jun.

Latest validated 7D window ending `2026-09-27`:

- Ads spend: 1,759,881 VND;
- Ads-attributed sales: 19,163,400 VND;
- ROAS: 10.889x;
- CPC: 2,004 VND;
- CPA: 7,586 VND;
- Ads CVR: 26.42%;
- driver contribution order: CVR Ads, CPC, Ads AOV.

September through `2026-09-27`:

- Ads spend: 11,061,718 VND;
- Ads-attributed sales: 97,125,680 VND;
- ROAS: 8.780x;
- CPC: 2,280 VND;
- CPA: 9,859 VND;
- Ads CVR: 23.13%.

### Mall

- trusted Ads dates: `2026-07-20` → `2026-09-27`;
- Day: available;
- Week: available where a contiguous seven-day window exists;
- Month: Jul / Aug / Sep available;
- Year 2026: **available** from the trusted shop-launch date; pre-launch dates are not fabricated.

Latest validated 7D window ending `2026-09-27`:

- Ads spend: 992,427 VND;
- Ads-attributed sales: 7,914,765 VND;
- ROAS: 7.975x;
- CPC: 1,588 VND;
- CPA: 11,676 VND;
- Ads CVR: 13.60%;
- driver contribution order: CPC, CVR Ads, Ads AOV.

September through `2026-09-27`:

- Ads spend: 6,194,653 VND;
- Ads-attributed sales: 45,043,765 VND;
- ROAS: 7.271x;
- CPC: 2,042 VND;
- CPA: 13,265 VND;
- Ads CVR: 15.40%.

Mall Year 2026 is usable as a shop-lifecycle window, but it currently has `INSUFFICIENT_COMPARISON_HISTORY`; Ads V2 therefore shows the period facts without fabricating year-over-year intelligence.

## 6. Native V2 presentation

Native Ads v37 is Intelligence-first and inherits the shared V2 design/language system.

Order of presentation:

1. operational Ads summary;
2. evidence state / product signals;
3. core Ads KPIs;
4. ROAS-factor contribution;
5. daily spend rhythm;
6. product-level Ads efficiency table.

Product names reuse the deterministic Product Short Name system. Full listing titles remain available as tooltip/search context.

The Ads destination does not expose a Compare scope.

## 7. Validation evidence

Run #496 completed the full chain successfully:

`RAW → Staging → Processed v2 → Drive → Semantic v2 → Context → Historical → Product Intelligence → Ads Intelligence → Payload → Native V2`

Ads Intelligence:

- QA status: PASS;
- QA checks: 2,507;
- failed checks: 0;
- Ads Intelligence fingerprint: `1f61f6701bb3462de0955a22754fada73fc52e148f431dc7409958f1a22d27f3`;
- trusted shop-level Ads rows: 159;
- trusted product-level Ads rows: 3,421.

Native V2:

- QA status: PASS;
- QA checks: 33;
- failed checks: 0;
- Native patch: `native-ads-intelligence-v37`;
- Native build fingerprint: `c6adfc397ee01b01ad4f74bef4de8ca8a77d4442dbf2c13e3ce09b305d62a5c2`;
- shared Design Language: PASS;
- Language System: PASS;
- forbidden visible-copy hits: none.

## 8. Safety boundary

Run #496 confirms:

- production cutover is not authorized;
- production Data Mart was not written;
- production deployment was not performed;
- production index was not modified;
- production V2 template was not modified;
- platform mutation is disabled;
- automatic Ads actions/alerts are disabled;
- causal claims are disabled.

## 9. Remaining capability gaps

This checkpoint closes the **Ads Intelligence V2 Foundation**, not the final Ads capability.

Remaining incremental work may include:

- safe canonical Ads history backfill for SYT+ if Year/YTD is required before enough new history accumulates;
- deeper campaign / placement / bidding-method diagnostics if a durable semantic grain is added;
- stronger Business Context qualification for mega-sale/payday Ads behavior;
- Ads-specific Operator Action policies after evidence quality is validated in human operation;
- human visual acceptance of Native v37 before treating it as the Ads visual baseline.

No production cutover should be inferred from this checkpoint.
