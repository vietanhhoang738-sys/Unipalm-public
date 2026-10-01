# Unipalm Change Guide

Use this guide to answer **where should I change this?** before editing code.

The machine-readable owner remains `config/system_module_registry.json`.

## Common changes

| Goal | Primary owner / first place to inspect | Required validation | Do not solve it by |
|---|---|---|---|
| Add/disable a shop | `config/shop_registry.json` | Shop Registry + staging + synthetic N-shop tests | hard-coding the shop in runners/UI |
| Shopee export adds/renames columns | `config/source_schema_registry.json` + schema guard | schema registry + staging QA | local parser alias hacks |
| Change catalog identity resolution | `automation/modules/catalog_resolver.py` | catalog tests + multi-shop staging | matching by display-name similarity |
| Change Processed business shape | `config/processed_layer_contract.json` | Processed tests + downstream compatibility | patching Semantic/UI around it |
| Change Semantic KPI definition | `config/semantic_mart_contract.json` + `semantic_mart.py` | Semantic tests + payload/intelligence compatibility | recomputing KPI differently in UI |
| Change Drive/storage destination | `config/storage_registry.json` | writer tests + forbidden-root safety | embedding resource IDs in business modules |
| Add/update official campaign context | `config/business_context_calendar.json` | Business Context tests | inferred/search-snippet dates |
| Change historical comparator/baseline policy | `config/historical_intelligence_contract.json` | historical tests + downstream staging | silently falling back to incompatible history |
| Change Product Intelligence policy | `config/product_intelligence_contract.json` | product intelligence tests | adding local UI heuristics |
| Change Ads metric/comparison policy | `config/ads_intelligence_contract.json` | Ads tests + diagnosis compatibility | bypassing Context Qualification |
| Change Dynamic Diagnosis | `config/ads_dynamic_diagnosis_contract.json` | diagnosis tests + persistence compatibility | reading raw signal arrays in UI |
| Change persistence confirmation | `config/ads_diagnosis_persistence_contract.json` | persistence tests + candidate compatibility | changing Candidate thresholds |
| Change Smart Issue candidate materiality | `config/ads_smart_issue_candidate_contract.json` | candidate tests + Registry compatibility | changing Registry to force issues |
| Change issue lifecycle/human review | `config/ads_smart_issue_registry_contract.json` | Registry tests + Operator Workflow | automatic issue creation |
| Submit a human review event | `automation/ads_smart_issue_review_command.py` + `ops/ads_smart_issue_review_events.json` | expected-ledger fingerprint + explicit `--apply` | editing issue state directly |
| Change review workflow actions | `config/ads_smart_issue_review_workflow_contract.json` | workflow tests | UI direct ledger mutation |
| Add/change canonical payload fields | `config/ui_payload_contract.json` | payload tests + Native V2 QA | local destination business logic |
| Change shared UI language/design | `config/ui_v2_presentation_contract.json` | UI tests + human visual QA when material | creating a destination-specific design system |
| Modify current production pipeline | legacy production files only with explicit safety review | production-specific QA + rollback | treating PREPRODUCTION readiness as permission |

## Change procedure

Before modifying a locked module:

1. Read `UNIPALM_PROJECT_CONSTITUTION.md`.
2. Locate the module in `config/system_module_registry.json`.
3. Read its contract and canonical docs.
4. Identify direct downstream consumers.
5. Record the existing fingerprint/checkpoint if the layer is deterministic.
6. Decide the change type:
   - config/evidence update;
   - backward-compatible bug fix;
   - internal refactor;
   - contract/version change.
7. Make the smallest owner-scoped change.
8. Run architecture validation and module tests.
9. Run downstream compatibility tests.
10. Full-stage when the changed module participates in the PREPRODUCTION chain.
11. Compare fingerprints/artifacts and confirm unrelated upstream layers did not change.
12. Update canonical documentation/current state if the change alters architecture or an accepted checkpoint.

## Refactor rule

Never mix all of these in one batch unless unavoidable:
- file/folder move;
- algorithm/business-rule change;
- contract schema change;
- storage migration;
- production cutover.

Prefer one dimension at a time so a regression has a small search surface.

## Additive change rule

When possible, introduce a downstream sidecar or new version rather than mutating a locked upstream layer. Prove the new consumer works against the locked producer first.

## Rollback trigger

Rollback/revert the change rather than patch forward blindly when:
- an upstream locked fingerprint changes unexpectedly;
- a source-of-truth boundary becomes ambiguous;
- the module begins silently recovering from a contract violation;
- production-write safety changes unintentionally;
- a change requires multiple unrelated downstream exceptions to make tests pass.
