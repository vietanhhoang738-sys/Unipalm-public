# Multi-Shop Native V2 — Human Visual QA (2026-09)

Status: **PASS — current PREPRODUCTION interaction baseline accepted; production promotion remains blocked**

Audit date: 2026-09-24

## Current accepted baseline

- GitHub Actions run: `35988078609` (#216)
- Commit: `75a0ab21b8319898e91feb6c653dbd40b00cb7ce`
- Native patch: `native-sidebar-rail-v13`
- V2 compatibility patch: `v2-comparison-availability-v3`
- Native fingerprint: `bd53638b958c5fb2abc216ee1c39a8dd9c9d158341049c0bd5e17512cab70a4d`
- Native HTML SHA256: `1dea26c5ec827a896d9f1648e632220cce8166c85f80f04e49b49a880ed81f47`
- Source UI Payload fingerprint: `c2e8bf92ea1ef69a222a78f03de51e52d9b7a80f6f57b4217fe13434ddca6f68`
- Source Semantic fingerprint: `3a77d886b5350dda2ea842367e53b6727ecc1073dce0b33f25df0c4f6ed5c62c`
- Production V2 SHA256: `9540f23b4d9537441e3bd4cdeafd15747ab4280a87a0130d223984009d99c952`

Reviewed Drive baseline:

`04_semantic_data_v2/_control/baselines/ui_native_v2/ui_native_v2_baseline_2026_09_run_216.zip`

Older native baselines are historical/superseded and must not be used as current UI guidance.

## Accepted visual / interaction contract

### Shared Design Language — PASS

All destinations share:
- Inter typography;
- V2 palette and dark mode;
- V2 spacing, radius and shadow grammar;
- sidebar/navigation grammar;
- card and numeric formatting conventions;
- Language System;
- Product Naming System.

Different destinations may have different information architecture, but may not create a second visual system.

### Command Center — PASS

Command Center contains:
- `Toàn hệ thống` — aligned portfolio view across all enabled shops;
- `Theo shop` — one-shop monitoring view using that shop's reliable window.

Portfolio ratios are recomputed from additive facts. Cross-shop unique Visits/Buyers are not fabricated.

When historical alert intelligence is unavailable, the UI must say so explicitly. It must not present unavailable alerting as “không có vấn đề”.

### So sánh Shop — PASS

Compare is a separate analysis destination.

Accepted behavior:
- pairwise aligned `latestDay / last7 / mtd`;
- no overall winner/ranking;
- GMV-gap decomposition;
- revenue quality;
- cost and Ads efficiency;
- traffic/channel mix;
- Ads Product analysis aligned by selected horizon;
- Business Product concentration explicitly monthly/MTD only;
- product commercial name is primary; SKU is secondary metadata;
- registry-driven Shop Yêu Thích / Shopee Mall identity badges at useful anchors only.

Repeated explanatory badge legends are not allowed.

### Sidebar viewport rail — PASS

Pinned desktop sidebar:
- uses a true fixed viewport rail outside the scaled V2 app;
- remains visually stable during long-page scroll;
- does not update position from `window.scrollY`.

Unpinned desktop sidebar:
- the same rail slides off-canvas at the current viewport position;
- does not jump back to the document top;
- left-edge hover reveals it at the current position.

Responsive behavior may hide the desktop rail under the existing V2 breakpoint.

## Accessibility / responsive checks

Accepted checks include:
- desktop light/dark;
- mobile Compare;
- no page-level horizontal overflow in reviewed states;
- 200% effective desktop reflow proxy;
- programmatic labels for shop selectors;
- active-state semantics;
- inspected dark muted-text tokens above the ordinary-text 4.5:1 contrast reference threshold.

This is not a blanket WCAG certification.

## Production safety

Still untouched:
- production `automation/command_center_v2_template.html`;
- production `index.html`;
- legacy production Data Mart;
- production deployment.

Production UI binding remains disabled.

## Historical provenance

Runs #156, #176, #187 and #200 were intermediate accepted milestones that led to the current baseline. Their detailed historical implementation notes were intentionally removed from this current QA document to prevent superseded layouts and patch names from being mistaken for active requirements.

Git history and archived Drive baselines remain the source for historical forensic review.
