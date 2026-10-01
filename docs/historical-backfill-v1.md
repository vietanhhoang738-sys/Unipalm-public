# Historical Backfill v1 — July & August 2026

Status: **VALIDATED PREPRODUCTION MILESTONE**

Validated on 2026-09-25.

Scope:
- common multi-shop history for `2026-07` and `2026-08`;
- September refresh after historical parser hardening;
- no production Data Mart/UI/index/deployment write.

## Objective

Promote real historical RAW into trusted history through the same canonical chain used by the current month:

`RAW -> Schema Guard -> Staging QA -> Processed v2 -> Durable Processed -> Semantic v2 -> Durable Semantic -> Historical Intelligence`

No historical month is trusted merely because a RAW folder/file exists.

## July investigation

Initial run `36094468534` (#260) correctly stopped at Staging QA.

### Historical Ads schema

SYT+ July Ads used one repeated row schema fingerprint across all 31 daily exports:

`6fecc7a5e5f8ad040b87e299f2368389c4c38e660fee69cdecd397fac60899e4`

Review showed:
- all required canonical fields resolved;
- no unknown columns;
- no missing required fields;
- the same fingerprint repeated across 31 files.

The fingerprint was subsequently reviewed and added to the accepted Ads schema baseline.

### Orders / Business Insights GMV semantics

The initial historical Orders proxy omitted the Shopee-funded subsidy column.

Business Insights Gross Sales includes platform-funded subsidy, while historical Orders export exposes the subsidy separately through:

`Được Shopee trợ giá -> shopee_subsidy`

The canonical reconciliation now uses:

`sum(item_buyer_payment + shopee_subsidy) - shop_voucher`

For cancelled orders, when the item-level proxy is not semantically equivalent, the QA may use the observed order-level `order_total_value` fallback for that cancelled order.

This remains a QA reconciliation proxy only. It does not redefine the canonical GMV fact source; BI remains authoritative for placed GMV.

July evidence after the fix:

### SYT+

- BI placed orders: `1,896`
- Orders distinct orders: `1,896`
- BI placed GMV: `396,832,609`
- Shopee subsidy restored: `142,734,500`
- selected proxy: `ITEM_PAYMENT_PLUS_SHOPEE_SUBSIDY_MINUS_SHOP_VOUCHER`
- Orders proxy: `398,104,323`
- difference: `+0.320466%`
- QA threshold: `0.5%`
- reconciliation: **PASS**

### Mall

- BI placed orders: `4`
- Orders distinct orders: `4`
- BI placed GMV: `960,000`
- one cancelled-order fallback
- selected proxy: `CANCELLED_ORDER_TOTAL_VALUE_FALLBACK`
- Orders proxy: `960,000`
- difference: `0%`
- reconciliation: **PASS**

## July publication

Run `36095755224` (#265): **PASS end-to-end**

Processed fingerprints:
- SYT+: `beed58ac13e7e74a6267660ce9c44e1f9df3febe4df9fb12abe483f207dbe561`
- Mall: `d7aa440e99dec8981fc7f27449c1fcb0b11ade12aeadf6a899e019ffa8c63310`

Both Processed partitions: **PUBLISHED**

Semantic:
- fingerprint: `70ddd954833cb413b8127cbe51b4ce801c1a6766ffe8d20ac34d0ca15c2f3571`
- status: **PUBLISHED**

July freshness:
- SYT+: `2026-07-01..2026-07-31`
- Mall: `2026-07-20..2026-07-30`
- Portfolio common window: `2026-07-20..2026-07-30`

July historical fingerprint:
`b0fc80a2fa2f242de6f51158e0c845504d09ec29caccba0ebc893767f892e0ae`

## August publication and Drive retry hardening

August Staging and Processed QA were PASS from the first attempt.

Processed fingerprints:
- SYT+: `a0f11f399d183343b994e3c04ec5381d0d3721382f69b4e7e66e4244a104ab0a`
- Mall: `3ff37c4aba69efe731b48cfff947b3e11b263dcde8a20b3f0f4cebd3d42677be`

The first August attempts exposed transient Google Drive read timeouts after/around atomic publication. No QA was weakened.

The writer was hardened with bounded retry around idempotent atomic operations. The retry is safe because:
- a failure before activation leaves the previous canonical partition untouched;
- a successful activation becomes fingerprint-identical and therefore NOOP on retry.

Run `36098115309` (#274): **PASS**
- Processed: NOOP for both shops
- Semantic fingerprint: `39bd92c7aa44794a2f823511e67a58e26e09a679c38d5bc0412ddf75c8951351`
- Semantic: PUBLISHED
- history trusted months as-of August: `2026-07, 2026-08`

Run `36098360904` (#275): **PASS**
- Processed: NOOP for both shops
- Semantic: NOOP
- Semantic fingerprint unchanged
- proves full August `PUBLISHED -> NOOP` idempotency

August freshness:
- SYT+: `2026-08-01..2026-08-27`
- Mall: `2026-08-01..2026-08-31`
- Portfolio common window: `2026-08-01..2026-08-27`

August historical fingerprint:
`ec5ffd11951312c170b7de6a6923b99496c7dccf80f3352c1dcccec99265cac7`

## September refresh after historical parser hardening

Run `36098551468` (#276): **PASS end-to-end**

September was rebuilt with the current Orders schema/parser so all trusted months share current semantics.

Processed fingerprints:
- SYT+: `7d4fd9288c154e59903525c019d455ee14a807f1f25b7b5c74ed5303641b03aa`
- Mall: `5cbaff93bdae6d87d6784169e5692698742beed39425536a5a8283b9e9439847`

Both were atomically **PUBLISHED**, replacing the previous September Processed partitions.

Semantic:
- fingerprint: `c25b7cfe67c6d8d477e6e8cd65a466eb3c74ca4f97a3c500b0e9320f1223b321`
- status: **PUBLISHED**

September freshness:
- SYT+: `2026-09-01..2026-09-17`
- Mall: `2026-09-01..2026-09-23`
- Portfolio common window: `2026-09-01..2026-09-17`

UI Payload fingerprint:
`4438f3026f0bd0e8a3b61800262d5222b1ee6b0590f002778ebdc2d3cfd3a68d`

Native V2 fingerprint:
`3e701fa64252e3b9c8d440580387e18fcd11e33bc59fce1baa43b01494e9870e`

## Trusted history after backfill

Historical Intelligence fingerprint:
`12f6667a045535ea7b17616f45acfc12b0157fa572d4ee0c14f662ab25ea66fa`

Trusted Semantic months:
- `2026-07`
- `2026-08`
- `2026-09`

Processed READY months for both current shops:
- `2026-07`
- `2026-08`
- `2026-09`

### Actual coverage

Portfolio:
- trusted start: `2026-07-20`
- trusted end: `2026-09-17`
- trusted days: `55`
- available months: 3
- complete months: **0**

SYT+:
- trusted start: `2026-07-01`
- trusted end: `2026-09-17`
- trusted days: `75`
- complete months: `2026-07` only

Mall:
- trusted start: `2026-07-20`
- trusted end: `2026-09-23`
- trusted days: `65`
- complete months: `2026-08` only

Therefore the global historical status correctly remains:
- Portfolio: `INSUFFICIENT_HISTORY`
- SYT+: `INSUFFICIENT_HISTORY`
- Mall: `INSUFFICIENT_HISTORY`
- 6M Intelligence: OFF
- Historical alerts: OFF
- Diagnosis: OFF

Three available months are **not** equivalent to three complete months.

## Comparator readiness after backfill

Even though overall anomaly-history readiness remains insufficient, several deterministic comparators now have enough real data.

Portfolio:
- Previous Day: READY
- Previous 7D: READY
- Previous-month matched MTD: READY
- Same Weekday: READY, 8 real prior samples
- Same Day-of-Month: INSUFFICIENT_HISTORY, 1 sample

SYT+:
- Previous Day: READY
- Previous 7D: READY
- Previous-month matched MTD: READY
- Same Weekday: READY, 8 samples
- Same Day-of-Month: INSUFFICIENT_HISTORY, 2 samples

Mall:
- Previous Day: READY
- Previous 7D: READY
- Previous-month matched MTD: READY
- Same Weekday: READY, 8 samples
- Same Day-of-Month: INSUFFICIENT_HISTORY, 2 samples

A READY comparator is factual comparison availability only. It does **not** enable anomaly labels, alerts or diagnosis.

## Evidence artifacts

July run #265:
- staging: artifact `10846812618`
- processed: artifact `10847915688`
- semantic: artifact `10847756473`
- history: artifact `10847736628`

August idempotency run #275:
- staging: artifact `10848945419`
- processed: artifact `10848745935`
- semantic: artifact `10847939749`
- history: artifact `10848780855`

September refresh run #276:
- staging: artifact `10848656204`
- processed: artifact `10849170173`
- semantic: artifact `10848746446`
- history: artifact `10848516755`
- UI Payload: artifact `10848746451`
- Native V2: artifact `10848521663`

History artifact #276 digest:
`sha256:66d943e6b5f1294682c895e94ab082aedc2ed47f071bf78f1e013650130d6c03`

## Safety boundary

Across this batch:
- production Data Mart written: false
- production V2 modified: false
- production index modified: false
- production deployment performed: false
- historical alerts enabled: false
- diagnosis enabled: false

## Next milestone

Recommended next batch: **Historical Comparator Binding v1**.

Use only READY factual comparators as operator context in Command Center / Business Pulse:
- previous-period context;
- matched MTD context;
- same-weekday baseline context.

Do not emit anomaly/alert/diagnosis claims while overall history is `INSUFFICIENT_HISTORY` or context is unavailable.

Older SYT+-only `2025-11..2026-06` remains a separate future Shop-history persistence problem and must not be merged into the all-shop Portfolio Semantic namespace.

## Lifecycle clarification after backfill

Mall's July coverage beginning on `2026-07-20` must not be described as a missing July data problem.

Mall only began operating in late July. Historical Intelligence 1.1 therefore models:
- `coverageOrigin=SHOP_LAUNCH`
- `startPolicy=FIRST_TRUSTED_SEMANTIC_DATE`
- `preStartDatesAreMissing=false`

The current first trusted Semantic date is `2026-07-20`.

Portfolio history similarly begins when all currently enabled shops are active.

As a result, the earlier phrase “partial July” is valid only as a **calendar-shape description**. It must not imply a missing source period before Mall's launch.

Historical Comparator Binding v1 is now complete; see:
- `docs/historical-comparator-binding-v1.md`

The next milestone is **Business Context Calendar Foundation v1**.

