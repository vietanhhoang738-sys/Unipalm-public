# Multi-Shop Catalog Resolver

## Purpose

Resolve listing/catalog identity across an arbitrary number of enabled shops without requiring every Shopee listing to have perfect Product SKU / Parent SKU metadata.

The resolver is configuration-driven. It has no named "reference shop" role.

## Identity layers

Keep these separate:

1. `shop_id + product_id` — channel listing identity.
2. observed Parent/Product SKU — channel metadata.
3. `shop_id + variation_id` — channel variation identity.
4. Variation SKU — sellable SKU, not guaranteed globally unique.
5. `canonical_family_key` — internal cross-shop analytical family.
6. SKU Master/BOM — canonical inventory/business authority.

Never join listings solely on Product ID, Parent SKU, or Variation SKU across shops.

## Metadata authority

Observed listing metadata priority:

1. Seller Center `mass_update_sales_info` snapshot.
2. Product Performance fallback.
3. Resolver / SKU Master evidence for missing canonical information.

An observed Seller Center Parent SKU beats resolver inference.

Do not infer Parent SKU from Variation SKU prefixes.

## N-shop resolution order

For each target listing:

1. Existing observed Parent SKU -> `DIRECT_PARENT`.
2. Exact SKU Master sellable-SKU evidence may establish `canonical_family_key`.
3. Listings from **all other enabled shops** may provide cross-shop reference evidence.
4. Same-shop listings are excluded from cross-shop evidence.
5. Multiple reference shops supporting the same Parent SKU are consensus evidence and do not compete with each other.
6. Different Parent SKUs with strong overlapping variation evidence create conflict/review.
7. Strong unique evidence may produce `AUTO_REFERENCE_PARENT`.
8. Exact master family without safe channel parent -> `FAMILY_ONLY`.
9. Ambiguous/weak reference -> `REVIEW_REFERENCE`.
10. Insufficient evidence -> `UNMATCHED`.

Resolver outputs are staging observations/proposals only.

## Why pairwise margin was removed

With 3+ shops, two independent reference listings can both correctly support the same Parent SKU.

Treating the second listing as a competitor would lower confidence simply because more shops agree.

The resolver therefore compares the best candidate against the best **different Parent SKU**, while recording:
- supporting listing count;
- supporting shop count;
- competing Parent SKUs;
- variation overlap;
- title similarity;
- SKU Master family votes.

## Historical anomaly rule

Snapshots are immutable observations.

If a user corrects Seller Center after an export:
- keep the old snapshot;
- ingest the newer snapshot;
- use the latest valid observation as current metadata;
- do not create a resolver mapping from a known typo.

Example: Mall product `50562805590` previously exposed mistyped `CB020-*` Variation SKUs while Parent SKU was `CB019`. A later Seller Center export confirms the corrected `CB019-*` values. `CB020-*` is historical anomaly evidence only.

## Safety

The resolver never:
- writes Seller Center;
- writes SKU Master;
- writes production Data Mart;
- guesses from SKU prefixes;
- assumes exactly two shops.
