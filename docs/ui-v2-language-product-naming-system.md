# UI V2 — Language System & Product Naming System

Status: **HARD CONTRACT**  
Applies to: production V2 foundation, PREPRODUCTION native multi-shop extensions, Compare, future UI V2 screens and diagnostic/product surfaces.

Machine-readable contract:
`config/ui_v2_presentation_contract.json`

## 1. Typography

- Primary UI font: **Inter**.
- Native multi-shop extensions inherit the existing V2 typography.
- Native extensions must not introduce a separate `font-family`.
- Existing V2 spacing, type hierarchy and compact number formatting remain authoritative unless a later reviewed UI system explicitly changes them.

## 2. Language System

The UI is **Vietnamese-first**, with established e-commerce jargon retained where it is natural for Vietnamese operators.

Reference style:
- Metric-style commerce/e-commerce reporting terminology;
- Bộ Công Thương / iDEA-style professional Vietnamese terminology;
- actual e-commerce operator language rather than literal translation.

Keep common industry terms when useful:
- GMV
- AOV
- CVR
- ROAS
- CTR
- SKU
- LTV
- Ads
- MTD
- Business Pulse

Do not expose implementation/backend language to operators.

Examples of preferred UI wording:
- Tổng quan so sánh
- Chất lượng doanh thu
- Cơ cấu chi phí
- Hiệu quả quảng cáo
- Nguồn truy cập & chuyển đổi
- Hiệu quả quảng cáo theo sản phẩm
- Cơ cấu doanh số sản phẩm
- cùng kỳ dữ liệu
- Doanh thu thuần
- Chi phí Ads
- Tỷ trọng doanh thu

Examples that must not be used as visible native UI copy:
- Performance summary
- Revenue quality
- Cost structure
- Ads performance
- Traffic & conversion mix
- Right vs Left
- aligned / aligned window
- source files
- operating view
- Shop-local identity
- cross-shop

Internal field names and backend contracts may remain English. This rule applies to **visible operator copy**, not implementation identifiers.

## 3. Product Naming System

Whenever the UI refers to a product, the **commercial product name is the primary visible label**.

Hierarchy:
1. `productName` — primary visible label.
2. SKU / resolved parent SKU — secondary metadata only.
3. Product ID / Variation ID — technical lineage/debug only.

Correct:
```
Cặp Đôi Yêu Kiều
SKU: CB019
```

Incorrect:
```
CB019
Cặp Đôi Yêu Kiều
```

If `productName` is unavailable:
- show `Chưa xác định tên sản phẩm`;
- keep SKU as secondary metadata;
- never silently promote SKU or Product ID into the product-name position.

The naming rule does not alter identity semantics:
- Product ID remains shop-local;
- no cross-shop Product ID merge is introduced;
- presentation name similarity must never be used to infer cross-shop identity.

## 4. QA gates

Native V2 build must fail if:
- the presentation contract is inactive;
- Inter is not the configured primary font;
- the native extension overrides `font-family`;
- forbidden visible copy appears in the native runtime;
- a product with `productName` is presented primarily as SKU/Product ID;
- a product without a name silently promotes SKU/Product ID as its name.

Unit tests additionally lock:
- commercial name priority;
- SKU metadata behavior;
- missing-name degraded state;
- language-copy lint;
- production V2 immutability.

## 5. Scope

These are permanent UI V2 rules. New pages — including Product, Ads, Customer, Traffic, Compare and future Command Center/Home work — must reuse this contract rather than define their own terminology or product-name fallback behavior.
