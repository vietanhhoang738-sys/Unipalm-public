# Product V36 — Deterministic Short-Name System

Status: **VALIDATED PREPRODUCTION PRESENTATION PATCH**  
Validation run: **#467 / 36376609955 — SUCCESS**  
Native patch: **`native-product-intelligence-v36-short-names`**  
Short-name rules: **`product-short-name-v1`**  
Production cutover: **not authorized**

## Goal

Keep canonical Shopee Product titles intact while giving operators compact, recognizable Product labels in the Product destination.

Examples:
- `Găng tay chống nắng ... Unipalm Air S2 ...` -> `Găng tay Air S2`
- `Khẩu trang ... Unipalm Cool S2 ...` -> `Khẩu trang Cool S2`
- `Ống tay ... Air F2 ...` -> `Ống tay Air F2`
- `Cặp Đôi ... Cool S2 & ... Air S4` -> `Cặp đôi Cool S2 + Air S4`
- `Combo 2 ... Cool S3 ...` -> `Combo 2 Khẩu trang Cool S3`

`Unipalm` is intentionally omitted from compact labels inside the first-party Unipalm Command Center because the brand is redundant context. The full canonical title remains available in the HTML title/tooltip and remains part of Product search data.

## Resolver doctrine

The resolver is deterministic and fail-safe. It uses explicit title/category/model structure only:
- categories: `Khẩu trang`, `Găng tay`, `Ống tay`, `Cặp đôi`, plus known accessory aliases;
- families/models: `Cool`, `Air`, `Slim` + `S*` / `F*` / `Plus` tokens;
- combo quantity is preserved;
- male variants keep a `· Nam` discriminator;
- pair products preserve both component models;
- deleted Products use `Sản phẩm đã xóa` plus available identity;
- unknown structures fall back to the full canonical Product title instead of guessing.

## Collision guard

Short names are shop-scoped by Product ID. If two listing IDs resolve to the same compact label:
1. append Parent SKU when available;
2. if the same SKU is still reused, append a short Product ID suffix.

A short-name collision therefore never silently merges two distinct listings.

## Presentation behavior

V36 wraps Product v35. It does not modify Product Intelligence semantics, historical lineage, canonical payloads, or canonical Product names.

The short label is applied to:
- Product structural-signal cards;
- Product detail-table visible names.

The full canonical title remains available through tooltip and remains searchable.

V36 also fixes structural-factor evidence pills that previously cropped text such as `đóng góp ...`. The pill now wraps within the card rather than using ellipsis.

## Implementation

- `automation/modules/product_short_name.py`
- `automation/modules/ui_v2_product_short_names.py`
- `automation/tests/test_product_short_name.py`
- `automation/tests/test_ui_v2_product_short_names.py`
- `automation/multi_shop_native_v2_runner.py`

## Validation

Run #467 passed the complete September chain:

`RAW -> Staging -> Processed v2 -> durable Drive -> Semantic v2 -> Business Context -> Historical -> Product Intelligence -> Canonical Payload -> Native V2`

Native artifact:
- QA: **33 / 33 PASS**
- patch version: `native-product-intelligence-v36-short-names`
- short-name rule version: `product-short-name-v1`
- native build fingerprint: `b64f92e64ef34c8a4a046cd0f9274b5bf5d01fb15da962a9555c42c3f0a1e076`
- HTML SHA256: `c6def0641a1669e3c526aa8adb99a63ac2668c7b227b06210439e8b49e0052dc`
- production V2 template modified: `false`
- production Data Mart written: `false`
- production deployment performed: `false`
- production cutover authorized: `false`

## Decision

V36 supersedes v35 only for Product naming presentation and factor-pill readability. Product v34 remains the structural Intelligence foundation; v35 remains the compact structural-signal layout underneath v36.