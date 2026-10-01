# Product V35 — Compact Structural Signals

Status: **VALIDATED PREPRODUCTION PRESENTATION PATCH**  
Validation run: **#460 / 36374787141 — SUCCESS**  
Native patch: **`native-product-intelligence-v35-compact-signals`**  
Production cutover: **not authorized**

## Problem

Product v34 rendered all structural Product signals vertically inside the right side of the Product hero. When SYT+ had several evidence-backed signals, the right column determined the full hero height and created a very large empty area under the Product summary on the left.

The insufficient-history state was already compact and should not be redesigned.

## V35 presentation rule

The patch is conditional.

When `.product-signal` rows exist:
- the top hero row keeps Product summary on the left and structural-analysis status on the right;
- the signal list moves visually into a full-width strip below the top row;
- desktop uses up to four equal signal cards in one row;
- tablet uses two columns;
- mobile uses one column;
- long Product names are clamped to two lines;
- signal metadata and factor pills use overflow protection;
- the non-causal methodology note spans the full signal strip.

When no structural signals exist (for example Mall `INSUFFICIENT_OPERATING_HISTORY`):
- the v34 compact hero layout is preserved;
- the patch does not force a signal grid or extra vertical section.

## Signal-count wording

V35 also aligns the summary title with the visible signal mix. If the four displayed signals contain both problems and opportunities, the title reports both, for example:

`3 cần chú ý · 1 cơ hội`

This avoids the v34 mismatch where the heading could say three products needed attention while four signal cards were visible.

## Implementation

- `automation/modules/ui_v2_product_compact_signals.py`
- `automation/tests/test_ui_v2_product_compact_signals.py`
- `automation/multi_shop_native_v2_runner.py`

V35 wraps the validated v34 Product destination. It does not modify Product Intelligence semantics, history lineage, Product payload contracts, or the production V2 template.

## Validation

Workflow run #460 passed the complete chain:

`RAW -> Staging -> Processed v2 -> durable Drive -> Semantic v2 -> Business Context -> Historical -> Product Intelligence -> Canonical Payload -> Native V2`

Native artifact validation:
- patch version: `native-product-intelligence-v35-compact-signals`
- Native QA: **33 / 33 PASS**
- native fingerprint: `909270f2df97944f4b0b462fa454525bc2810e2d4be73d46c24199f9feadd79a`
- Native HTML SHA256: `14133d05183a92bf1421e0f5a80558248e1897ab5fe0ee6c94df0d3a53761eed`
- production V2 template modified: `false`
- production Data Mart written: `false`
- production deployment performed: `false`
- production cutover authorized: `false`

## Decision

V35 supersedes v34 only for Product structural-signal presentation. V34 remains the locked structural Product Intelligence foundation underneath it.
