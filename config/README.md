# Unipalm Configuration Boundary

`config/` contains **normative contracts, registries and curated evidence/configuration**. It should not be used as a general mutable runtime-state directory.

## Categories

### Machine-readable contracts

Files matching `*_contract.json` define enforceable behavior for a specific layer. A contract change is an architectural change and must be accompanied by the relevant tests, documentation and downstream compatibility validation.

Examples:
- `processed_layer_contract.json`
- `semantic_mart_contract.json`
- `historical_intelligence_contract.json`
- `ads_intelligence_contract.json`
- `ads_dynamic_diagnosis_contract.json`
- `ads_diagnosis_persistence_contract.json`
- `ads_smart_issue_candidate_contract.json`
- `ads_smart_issue_registry_contract.json`
- `ads_smart_issue_review_workflow_contract.json`
- `ui_payload_contract.json`
- `ui_v2_presentation_contract.json`

### Registries

Registries identify instance/runtime resources and canonical ownership boundaries:
- `shop_registry.json` — enabled shop identities and raw-root candidates;
- `source_schema_registry.json` — reviewed source schema/alias boundary;
- `storage_registry.json` — PREPRODUCTION storage namespaces and writer policy;
- `system_module_registry.json` — machine-readable system ownership/dependency map;
- `legacy_pipeline_dependencies.json` — migration-only dependency inventory for the active legacy production path.

### Curated evidence/configuration

- `business_context_calendar.json` — reviewed Business Context evidence/calendar.

## Mutable operational state

New mutable operator/control state belongs under `ops/`, not `config/`.

Canonical examples:
- `ops/staging_request.json`
- `ops/ads_smart_issue_review_events.json`

Historical compatibility copies may temporarily remain under `config/` while an active workflow still references them. Such copies are migration debt, not the target architecture, and must not become a second source of truth.

## Change rule

Before editing a file here, identify its owner module in `config/system_module_registry.json` and run:

```bash
python automation/validate_architecture.py
cd automation && python -m unittest discover -s tests -p "test_*.py" -v
```

Do not use configuration changes to bypass a fail-closed runtime gate or to silently redefine business facts.
