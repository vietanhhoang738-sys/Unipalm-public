# Multi-Shop Catalog Audit — 2026-09 snapshot

Scope: Shopee Seller Center listing export `mass_update_sales_info` dated 2026-09-23 is now the authoritative channel-listing snapshot. Product Performance remains a KPI/performance source and fallback only.

## Shop contract

- SYT+ = Shopee Shop ID 1000000001
- Mall = Shopee Shop ID 1000000002

## Source precedence

For Shopee listing metadata:

1. `mass_update_sales_info` Seller Center export — authoritative observed channel metadata.
2. Product Performance — fallback when no listing snapshot is available.
3. Catalog Resolver / SKU Master — resolves canonical family or missing metadata; never overwrites observed Seller Center metadata by prefix guessing.

The listing export is a snapshot source, not a transaction fact source.

## 2026-09-23 observed listing snapshot

### SYT+

- 42 product listings.
- 426 variation rows.
- 38/42 products have observed Parent SKU in Seller Center.
- 4 products have blank Parent SKU in Seller Center:
  - 41433706033 — Air S5 Plus.
  - 44616073433 — Air S6.
  - 48316005736 — Air S1 Plus.
  - 49566580179 — gift Scrunchie.
- 3 variation rows have blank Variation SKU.
- Parent SKU is not globally unique: examples include `CT001` and `PK001` reused by multiple listings.
- Variation SKU is also not listing-unique; many sellable SKUs intentionally appear in more than one listing.

### Mall

- 29 product listings.
- 256 variation rows.
- **29/29 products have observed Parent SKU in Seller Center.**
- 1 variation row has blank Variation SKU (UV test card).
- Parent SKU is not globally unique: `GL008` is used by both an Air F3 single listing and an Air F3 Combo 2 listing.
- Variation SKU is also reused across multiple listings.

This supersedes the earlier Product Performance-only conclusion that 10 Mall listings were missing Parent SKU. Those blanks were caused by the Product Performance export contract and are not authoritative evidence that Seller Center Parent SKU is absent.

## Corrected historical anomaly: Cặp Đôi Yêu Kiều

Mall product `50562805590` was exported on 2026-09-23 with:

- observed Parent SKU: **CB019**
- historical/mistyped variation SKUs:
  - `CB020-PIN-2L3D`
  - `CB020-LGR-2L3D`
  - `CB020-BLA-2L3D`

The user confirmed on 2026-09-23 that those Mall Variation SKUs were entered incorrectly in Seller Center. The current Drive snapshot `mass_update_sales_info_1000000002_20260923104414.xlsx` now confirms they have been corrected to:

- `CB019-PIN-2L3D`
- `CB019-LGR-2L3D`
- `CB019-BLA-2L3D`

This now matches SYT+ product `57355176782`, whose Parent SKU is `CB019` and whose sellable variation family is also `CB019-*`.

Operational interpretation:
- the earlier 2026-09-23 uploaded export remains an immutable historical snapshot showing the old typo;
- the current Drive Seller Center export at 10:44:14 already supersedes it and confirms `CB019-*` as current listing metadata;
- no resolver exception or CB020 family mapping should be created for this product;
- do not rewrite the old snapshot, because retaining the old value provides an audit trail of the correction.

## Other corrected current-parent examples from Mall

Seller Center directly confirms, among others:

- Air S6 product 41683884546 -> Parent SKU `GL027`
- Air S1 Plus product 50516150640 -> Parent SKU `GL032`
- Air S5 Plus product 54016823943 -> Parent SKU `GL021`
- Cool S3 Plus product 40383627310 -> Parent SKU `MS012`
- Combo 2 Air F2 product 42332018609 -> Parent SKU `GL009-CB2`
- Combo 2 Air F3 product 55813870935 -> Parent SKU `GL008`
- Cặp Đôi Tỏa Sáng product 56663876307 -> Parent SKU `CB024`
- Cặp Đôi Năng Động product 57962778684 -> Parent SKU `CB007`
- UV test card product 50112779301 -> Parent SKU `PK001`

## Identity rules after this audit

Identity layers remain separate:

1. `product_id` — Shopee listing identity within one shop.
2. observed `parent_sku` — Seller Center channel metadata; not guaranteed globally unique.
3. `variation_id` — Shopee variation identity within the listing.
4. `variation_sku` — sellable SKU; may be reused across listings.
5. `canonical_family_key` — internal cross-shop family used for analytics.
6. SKU Master/BOM — canonical inventory/business authority.

Do not join two listings solely because Parent SKU matches.
Do not join two listings solely because a Variation SKU overlaps.
Do not infer Parent SKU from Variation SKU prefix.

## Operational consequence

The Seller Center listing export should be ingested as a repeatable snapshot whenever the user exports it. It can update observed listing name, Product ID, Variation ID/name, Parent SKU, Variation SKU, current price and seller stock without manually editing historical files.

Historical snapshots should be retained with `snapshot_at` so price/stock/listing changes remain auditable.

No production Data Mart rows or UI were modified by this audit.
