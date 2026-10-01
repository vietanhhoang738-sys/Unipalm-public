# Command Center V2 — Failure Domains & Recovery Map

## Design rule

Core commerce reporting must not fail because an optional intelligence feature fails.

The system is split into independent failure domains with explicit contracts,
health states and maintenance paths.

| Domain | Owns | Reads | Writes | Failure behavior | Blocking? | Recovery |
|---|---|---|---|---|---|---|
| Core Source Processor | BI / Orders / shop Ads / product monthly / hourly mart | READY processed outputs | core mart partitions | fail closed | YES | fix source/DQ then rerun core pipeline |
| Product Ads Mart | product-level Ads aggregated by date + product_id | processed Ads | dm_ads_product_daily only | mark DEGRADED; preserve prior healthy partition | NO for core dashboard | run Product Ads Mart Audit / Backfill workflow |
| Product Signal Detection | eligibility for Problem / Opportunity | dm_product_monthly + product Ads mart | payload only | return DEGRADED / 0 signals | NO | inspect featureHealth.productIntelligence |
| Product Ranking | priority ordering of eligible signals | eligible signal objects | payload only | Product Intelligence degrades; core periods/KPIs remain | NO | unit tests + ranking module |
| Root-Cause Diagnosis | evidence + hypotheses for selected product | product performance + Ads evidence | payload only | hide/limit product diagnosis | NO | inspect signal diagnostic payload |
| Command Center Historical Core | Yesterday / Rolling 7D / MTD, KPI, GMV bridge | commercial mart + shop Ads | payload | fail closed if core authority invalid | YES | inspect mart/source QA |
| UI Adapter | render payload | window.UNIPALM_DATA | browser only | hide unavailable optional block; show feature/data health | NO for unrelated modules | inspect browser payload + featureHealth |

## Health contract

Feature states:
- READY: feature is eligible for normal use.
- DEGRADED: feature is unavailable or incomplete; unrelated modules remain usable.
- NO_HIGH_CONFIDENCE_SIGNALS: engine healthy, but no business signal passes gates.
- DISABLED_BY_DESIGN: feature intentionally not enabled.

\`commandCenter.featureHealth\` currently contains:
- \`productAdsMart\`
- \`productIntelligence\`

Core source health remains in \`health.sources\`.

## Product Ads isolation

Aggregation key is strictly:
- data_date
- product_id

Campaign IDs / service keys are lineage only.

Policy:
1. Sum ALL product-scope campaign rows for the same product/day.
2. Validate uniqueness of date + product_id.
3. Validate non-negative spend.
4. Validate derived ROAS and daily spend-share.
5. Write only the requested monthly partition.
6. If candidate/build/write fails, keep the previous healthy product Ads partition and mark the feature DEGRADED.
7. Do not block Orders / BI / shop KPI publishing because product Ads intelligence failed.

Maintenance:
- workflow: \`Product Ads Mart Audit / Backfill\`
- default: audit-only
- apply mode is explicit and only needed when audit is unhealthy.

## Product Intelligence isolation

Detection and ranking are separate:
- Detection decides eligibility.
- Ranking orders eligible signals.
- Diagnosis explains selected signals.

Pure modules:
- \`automation/modules/ads_product_mart.py\`
- \`automation/modules/product_ranking.py\`

The production publisher catches Product Intelligence exceptions and returns a
DEGRADED product intelligence payload while preserving the historical Command
Center core.

## Test pyramid

### 1. Pure module CI
Workflow: \`Data V2 Module CI\`

Checks:
- Python compile.
- Multiple Ads campaigns for one product are aggregated correctly.
- Campaign restart does not break product history.
- Ranking favors business impact over extreme percentage movement on tiny products.
- Problems and Opportunities rank independently.

No Google credentials required.

### 2. Read-only integration dry-run
Workflow: \`Data V2 Integration Dry Run\`

Checks:
- source candidate build with \`source_processor.py --dry-run\`.
- product Ads maintenance audit path.
- Command Center payload built from production mart.
- featureHealth states.
- Product Signal Ranking structure.

No mart write and no deploy.

### 3. Production publish
Existing \`Unipalm Production Pipeline\`.

Only run/merge after layers 1–2 pass.

## Debug order

When Command Center has a problem:

1. Check \`commandCenter.featureHealth\`.
2. If Product Ads Mart DEGRADED:
   - run/inspect Product Ads Mart maintenance artifact.
   - do not debug Orders/BI first.
3. If Product Intelligence DEGRADED but Ads mart READY:
   - inspect detection/ranking unit CI and integration artifact.
4. If core KPIs are wrong:
   - inspect commercial mart / Business Insights authority.
5. If payload is right but UI is wrong:
   - debug UI adapter only.

This order prevents a local feature failure from becoming a whole-system debugging exercise.
