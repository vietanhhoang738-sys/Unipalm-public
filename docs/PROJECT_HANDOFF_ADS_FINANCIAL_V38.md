# PROJECT HANDOFF — Ads Financial UI v38

Status: **PREPRODUCTION — VALIDATED / READY FOR HUMAN VISUAL REVIEW**

This document freezes the technical handoff checkpoint for the Ads destination after the Financial UI v38 upgrade. It supplements `docs/ads-intelligence-v2-foundation.md`; it does not authorize production cutover.

## 1. Validated checkpoint

- Branch: `multi-shop-catalog-resolver`
- Final validation commit: `4f4a8201bfb05fc6c3263ba557a9c4537e7556e5`
- GitHub Actions run: **#508**
- Workflow run id: `36404066896`
- Workflow conclusion: **SUCCESS**
- Validation month: `2026-09`
- Native patch: `native-ads-financial-v38`
- Financial polish: `ads-financial-polish-v2`
- Ads group rule: `ads-product-group-v1`

All canonical gates completed successfully in one run:

`RAW → Staging → Processed v2 → durable Drive → Semantic v2 → Business Context → Historical Intelligence → Product Intelligence → Ads Intelligence → UI Payload → Native V2 → artifact upload`

## 2. Fingerprints

- Semantic v2: `38e12e9552fd81571b85e37f977bfbeb8feda9a1d3b7e301663f56fa28cad7f6`
- Ads Intelligence: `6e85fc4d89d3f662ee68548109048bf6f08f7db70a958725c62c9cbe11c61fb1`
- UI Payload: `a13682ad38db14118c82e8ac7bfe9a26aaa3545af5a287083a5d4c305b1f38d9`
- Native V2 build: `806981eb0bb0b18d712861902ba1180a34bbbe80c89ec6b83df854ac09c72682`

## 3. QA evidence

### Ads Intelligence

- Status: `PASS`
- QA checks: **2,507**
- Failed checks: **0**
- Ads daily rows: `159`
- Ads product daily rows: `3,421`
- Automatic alerts: disabled
- Automatic actions: disabled
- Causal claims: disabled

### Native V2

- Status: `PASS`
- QA checks: **33 / 33 PASS**
- `ui_v2_language_system`: PASS
- `ui_v2_inter_typography`: PASS
- `ui_v2_shared_design_language`: PASS
- `production_binding_absent`: PASS
- Forbidden visible-copy hits: `[]`
- Product naming errors: `[]`

The effective v38 presentation is also regression-tested against the complete `forbidden_visible_phrases` list in `config/ui_v2_presentation_contract.json`.

## 4. Ads destination doctrine

Ads is intentionally different from Product and Command Center.

### Information flow

**Data first → Intelligence last**

1. Scope controls
2. Three-line mathematical efficiency identity
3. Financial KPI strip
4. In-period trend chart
5. Ads funnel
6. Cost-pressure benchmarks
7. Entity breakdown / drill-down
8. CPC × ROAS map
9. **Ads Intelligence Desk** at the bottom

Embedded Intelligence is limited to compact deltas, benchmark state and evidence markers. The operator is expected to read the data first, then use the independent Intelligence Desk as a second interpretation layer.

### Entity scopes

The destination remains single-shop. Within the selected shop it supports:

- `Shop`
- `Nhóm SP`
- `Sản phẩm`

Product groups are deterministic:

- `Khẩu trang`
- `Găng tay`
- `Ống tay`
- `Cặp đôi / Combo`
- `Khác`

Product display labels reuse the Product Short Name system; full commercial names remain preserved in source data.

### Time scopes

Canonical Ads grain is daily, therefore allowed scopes are:

- `Ngày`
- `Tuần`
- `Tháng`
- `Năm`

No finer synthetic grain is manufactured.

## 5. Mathematical visual identity

The hero expresses Ads efficiency in three equivalent visual forms:

1. `ROAS = GMV Ads / Chi tiêu Ads`
2. `ROAS = (AOV × Chuyển đổi) / (CPC × Click)`
3. `ROAS = (AOV × Hiển thị × CTR × CR) / (CPC × Click)`

Each metric node is interactive and may switch the main chart focus. The UI explicitly states that the equation is an identity decomposition and **not a causal conclusion**.

## 6. Chart-first surfaces

v38 includes:

- interactive main trend chart;
- funnel view;
- cost benchmark cards for CPC / CPA / CPM;
- benchmark windows `1W / 1M / 3M / 6M`;
- entity contribution breakdown with drill-down;
- CPC × ROAS product scatter / bubble map;
- green/red financial-direction states using only shared V2 color tokens.

Benchmark windows are fail-closed: a benchmark is unavailable unless every required trusted Ads date exists. Missing source dates are never interpreted as zero spend.

## 7. Trusted Ads history at checkpoint

### SYT+

- Trusted start: `2026-07-01`
- Trusted end: `2026-09-27`
- Day: READY
- Week: READY
- Month: READY
- Year: **not READY** because the shop predates the trusted Ads window and Jan–Jun canonical Ads history is absent.

### Mall

- Trusted start: `2026-07-20`
- Trusted end: `2026-09-27`
- Day: READY
- Week: READY
- Month: READY
- Year 2026: READY under the lifecycle-aware shop-launch rule.

## 8. Operator-language cleanup

The final handoff layer removes backend/awkward visible wording before Native QA. Examples:

- `Ads Spend` → `Chi tiêu Ads`
- `Spend share` → `Tỷ trọng chi tiêu`
- `trusted history` → `dữ liệu Ads đã xác thực`
- `EVIDENCE ONLY` → `THAM KHẢO`

The Ads extension does not define its own font family and inherits the project-wide Inter typography. It also uses the shared V2 `--green-bg` token rather than creating a destination-specific green palette.

## 9. Safety boundary

At run #508:

- `productionCutoverAuthorized = false`
- `productionDataMartWritten = false`
- `productionDeploymentPerformed = false`
- `productionIndexModified = false`
- `productionV2TemplateModified = false`
- `platformMutationAllowed = false`
- `productionActivationEnabled = false`

This checkpoint is a PREPRODUCTION candidate only.

## 10. What is locked vs. what may still iterate

### Locked foundation

Do not rebuild without a validated regression reason:

- Ads daily semantic grain;
- single-shop destination boundary;
- Day / Week / Month / Year doctrine;
- fail-closed trusted-date coverage;
- non-causal ROAS decomposition;
- Shop / Product Group / Product entity scopes;
- data-first page order;
- Intelligence Desk at the bottom;
- shared typography/color system;
- Ads Intelligence / Payload / Native fingerprints and QA lineage.

### Safe future iteration

Human visual review may still tune spacing, chart density, label hierarchy, tooltip behavior or interaction affordances without changing the semantic contracts above. Any such change must rerun core tests and the full PREPRODUCTION checkpoint before being accepted.

## 11. Recommended continuation

After human visual approval of v38, freeze it as the Ads visual baseline and continue with the next domain foundation (Traffic Intelligence V2) rather than reopening Ads architecture unless review reveals a concrete usability defect.
