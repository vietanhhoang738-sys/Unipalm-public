#!/usr/bin/env python3
"""Validate Unipalm's machine-readable architecture and maintenance boundaries.

This validator intentionally checks structure, ownership and dependency rules only.
It must not redefine business contracts owned by domain modules.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "config" / "system_module_registry.json"

ALLOWED_STATUSES = {"LOCKED_V1", "ACTIVE_LEGACY", "PREPRODUCTION_ACTIVE", "DEFERRED_BY_DESIGN"}
ALLOWED_LANES = {"core", "legacy"}
REQUIRED_TRUE_POLICIES = {
    "immutable_upstream_on_downstream_change",
    "contract_change_requires_explicit_versioning",
    "locked_refactor_requires_behavioral_equivalence",
    "generic_core_forbids_concrete_shop_identity",
    "new_domain_must_register_module",
    "production_mutation_requires_explicit_human_approval",
    "fail_closed_on_contract_or_dependency_violation",
}
PATH_FIELDS = (
    "implementation_paths",
    "runner_paths",
    "contract_paths",
    "config_paths",
    "doc_paths",
    "test_paths",
)


def _read(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_architecture(registry_path: str | Path = DEFAULT_REGISTRY) -> Dict[str, Any]:
    path = Path(registry_path)
    if not path.is_absolute():
        path = ROOT / path
    data = _read(path)
    errors: List[str] = []
    warnings: List[str] = []

    if str(data.get("version")) != "1.0":
        errors.append("system module registry version must be 1.0")
    if data.get("status") != "PREPRODUCTION_GOVERNANCE":
        errors.append("system module registry must remain PREPRODUCTION_GOVERNANCE")

    policy = data.get("policy") or {}
    for key in sorted(REQUIRED_TRUE_POLICIES):
        if policy.get(key) is not True:
            errors.append(f"policy {key} must remain true")
    if policy.get("operational_state_root") != "ops/":
        errors.append("operational_state_root must be ops/")

    layer_rows = data.get("layers") or []
    layer_ids = [str(x.get("id") or "") for x in layer_rows]
    if len(layer_ids) != len(set(layer_ids)):
        errors.append("layer ids must be unique")
    layer_order: Dict[str, int] = {}
    for row in layer_rows:
        lid = str(row.get("id") or "")
        if not lid:
            errors.append("layer id is required")
            continue
        try:
            order = int(row.get("order"))
        except Exception:
            errors.append(f"layer {lid} order must be an integer")
            continue
        if order in layer_order.values():
            errors.append(f"layer order {order} is duplicated")
        layer_order[lid] = order

    modules = data.get("modules") or []
    module_ids = [str(x.get("id") or "") for x in modules]
    if not module_ids or any(not x for x in module_ids):
        errors.append("every module requires a non-empty id")
    if len(module_ids) != len(set(module_ids)):
        errors.append("module ids must be unique")
    by_id = {str(x.get("id")): x for x in modules if x.get("id")}

    for module_id, module in by_id.items():
        lane = str(module.get("lane") or "")
        status = str(module.get("status") or "")
        layer = str(module.get("layer") or "")
        if lane not in ALLOWED_LANES:
            errors.append(f"{module_id}: invalid lane {lane!r}")
        if status not in ALLOWED_STATUSES:
            errors.append(f"{module_id}: invalid status {status!r}")
        if layer not in layer_order:
            errors.append(f"{module_id}: unknown layer {layer!r}")

        dependencies = [str(x) for x in (module.get("dependencies") or [])]
        for dep in dependencies:
            if dep not in by_id:
                errors.append(f"{module_id}: unknown dependency {dep}")
                continue
            dep_module = by_id[dep]
            if lane == "core" and dep_module.get("lane") == "core":
                if layer in layer_order and str(dep_module.get("layer")) in layer_order:
                    if layer_order[str(dep_module.get("layer"))] > layer_order[layer]:
                        errors.append(f"{module_id}: core dependency {dep} points downstream")

        for field in PATH_FIELDS:
            values = module.get(field) or []
            if not isinstance(values, list):
                errors.append(f"{module_id}: {field} must be a list")
                continue
            for rel in values:
                rel_s = str(rel)
                if not rel_s:
                    errors.append(f"{module_id}: empty path in {field}")
                elif not (ROOT / rel_s).exists():
                    errors.append(f"{module_id}: referenced path does not exist: {rel_s}")

        if status == "LOCKED_V1":
            if not module.get("implementation_paths"):
                errors.append(f"{module_id}: LOCKED_V1 requires implementation_paths")
            if not module.get("doc_paths"):
                errors.append(f"{module_id}: LOCKED_V1 requires canonical documentation")
            if not module.get("test_paths"):
                errors.append(f"{module_id}: LOCKED_V1 requires regression tests")
            if not str(module.get("failure_boundary") or "").strip():
                errors.append(f"{module_id}: LOCKED_V1 requires failure_boundary")
            if not module.get("change_entrypoints"):
                errors.append(f"{module_id}: LOCKED_V1 requires change_entrypoints")

        for rel in module.get("change_entrypoints") or []:
            if not (ROOT / str(rel)).exists():
                errors.append(f"{module_id}: change entrypoint does not exist: {rel}")

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str, chain: List[str]) -> None:
        if node in visiting:
            errors.append("dependency cycle: " + " -> ".join(chain + [node]))
            return
        if node in visited:
            return
        visiting.add(node)
        for dep in by_id.get(node, {}).get("dependencies") or []:
            if dep in by_id:
                visit(str(dep), chain + [node])
        visiting.remove(node)
        visited.add(node)

    for module_id in sorted(by_id):
        visit(module_id, [])

    operational = data.get("operational_state") or {}
    if operational.get("canonical_root") != "ops/":
        errors.append("operational_state.canonical_root must be ops/")
    for rel in operational.get("paths") or []:
        rel_s = str(rel)
        if not rel_s.startswith("ops/"):
            errors.append(f"operational state must live under ops/: {rel_s}")
        if not (ROOT / rel_s).exists():
            errors.append(f"operational state path does not exist: {rel_s}")
    for row in operational.get("legacy_exceptions") or []:
        rel_s = str(row.get("path") or "")
        if not rel_s or not (ROOT / rel_s).exists():
            errors.append(f"legacy operational-state exception missing path: {rel_s!r}")
        if not str(row.get("reason") or "").strip():
            errors.append(f"legacy operational-state exception requires reason: {rel_s}")

    contract_paths = {
        str(rel)
        for module in modules
        for rel in (module.get("contract_paths") or [])
    }
    for rel in operational.get("paths") or []:
        if str(rel) in contract_paths:
            errors.append(f"mutable operational state cannot be a normative contract: {rel}")

    for row in data.get("known_refactor_candidates") or []:
        rel = str(row.get("path") or "")
        if not rel or not (ROOT / rel).exists():
            errors.append(f"refactor candidate path missing: {rel!r}")
            continue
        if str(row.get("risk") or "") not in {"LOW", "MEDIUM", "HIGH"}:
            errors.append(f"refactor candidate {rel} has invalid risk")
        if not str(row.get("reason") or "").strip():
            errors.append(f"refactor candidate {rel} requires reason")
        try:
            size = (ROOT / rel).stat().st_size
            if size >= 60000:
                warnings.append(f"large validated surface: {rel} ({size} bytes)")
        except OSError:
            pass

    return {
        "status": "PASS" if not errors else "FAIL",
        "moduleCount": len(modules),
        "layerCount": len(layer_rows),
        "errorCount": len(errors),
        "warningCount": len(warnings),
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    result = validate_architecture()
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
