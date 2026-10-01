"""Build a fail-closed, source-complete / operations-empty public snapshot.

The public snapshot is intentionally created from one trusted private HEAD.
It does not carry Git history, production dashboard artifacts, mutable runtime
state, live Google resource IDs, or scheduled production execution.

This module never mutates the source tree. It copies to a separate output
folder, sanitizes that copy, and emits a machine-readable audit report.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Set, Tuple


TEXT_SUFFIXES = {
    ".py", ".json", ".md", ".yml", ".yaml", ".html", ".txt", ".toml", ".ini", ".cfg"
}
DATA_SUFFIXES = {".csv", ".xlsx", ".xls", ".parquet", ".sqlite", ".db"}

HIGH_CONFIDENCE_SECRET_PATTERNS = {
    "PEM_PRIVATE_KEY": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "GOOGLE_API_KEY": re.compile(r"AIza[0-9A-Za-z_-]{30,}"),
    "GOOGLE_OAUTH_CLIENT_SECRET": re.compile(r"GOCSPX-[0-9A-Za-z_-]{20,}"),
    "GOOGLE_REFRESH_TOKEN": re.compile(r"1//[0-9A-Za-z_-]{20,}"),
    "GOOGLE_ACCESS_TOKEN": re.compile(r"ya29\.[0-9A-Za-z_-]{20,}"),
    "GITHUB_CLASSIC_PAT": re.compile(r"ghp_[0-9A-Za-z]{30,}"),
    "GITHUB_FINE_GRAINED_PAT": re.compile(r"github_pat_[0-9A-Za-z_]{40,}"),
    "SLACK_TOKEN": re.compile(r"xox[baprs]-[0-9A-Za-z-]{20,}"),
    "AWS_ACCESS_KEY": re.compile(r"AKIA[0-9A-Z]{16}"),
}

OPAQUE_SCRIPT_RE = re.compile(
    r"<script[^>]*type=[\"']application/octet-stream[\"'][^>]*>.*?</script>",
    re.I | re.S,
)

PUBLIC_RESOURCE_PREFIX = "PUBLIC_RESOURCE_"
PUBLIC_SHOP_IDS = {
    "syt_plus": ("SHP_VN_1000000001", "1000000001"),
    "mall": ("SHP_VN_1000000002", "1000000002"),
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def walk_scalar_strings(value: Any, *, key: str = "") -> Iterable[Tuple[str, str]]:
    if isinstance(value, dict):
        for child_key, child in value.items():
            yield from walk_scalar_strings(child, key=str(child_key))
    elif isinstance(value, list):
        for child in value:
            yield from walk_scalar_strings(child, key=key)
    elif isinstance(value, str):
        yield key, value


def collect_live_identifiers(source_root: Path) -> Set[str]:
    """Collect exact live identifiers that must not survive the export.

    We intentionally use exact values from authoritative private registries and
    the production workflow instead of broad ID regexes, which can collide with
    hashes/fingerprints and break source code unnecessarily.
    """
    values: Set[str] = set()

    for rel in ("config/shop_registry.json", "config/storage_registry.json"):
        data = load_json(source_root / rel)
        for key, value in walk_scalar_strings(data):
            low = key.lower()
            if (
                low.endswith("_id")
                or low in {"shop_id", "shopee_shop_id", "folder_id"}
                or low.endswith("_file_id")
                or low.endswith("_root_id")
            ) and value:
                values.add(value)

    workflow = (source_root / ".github/workflows/unipalm-pipeline.yml").read_text(
        encoding="utf-8"
    )
    for match in re.finditer(r'UNIPALM_[A-Z_]+_ID:\s*["\']([^"\']+)["\']', workflow):
        value = match.group(1).strip()
        if value and "${{" not in value:
            values.add(value)

    return {value for value in values if not value.startswith(PUBLIC_RESOURCE_PREFIX)}


def copy_source_tree(source_root: Path, output_root: Path, excluded_paths: Iterable[str]) -> None:
    excluded = {Path(p).as_posix() for p in excluded_paths}
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True)

    for src in source_root.rglob("*"):
        rel = src.relative_to(source_root).as_posix()
        if rel == ".git" or rel.startswith(".git/"):
            continue
        if rel in excluded:
            continue
        if rel.startswith("public_snapshot/"):
            continue
        if src.is_dir():
            (output_root / rel).mkdir(parents=True, exist_ok=True)
            continue
        dest = output_root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)


def reset_pipeline_state(root: Path) -> None:
    write_json(
        root / "automation/pipeline_state.json",
        {
            "run_id": "PUBLIC_SNAPSHOT_NOT_RUN",
            "build_id": "PUBLIC_SNAPSHOT_NOT_RUN",
            "candidate_reliable_end": "",
            "qa": "NOT_RUN",
            "production_url": "https://example.invalid/",
            "generated_at": None,
        },
    )


def reset_staging_request(path: Path) -> None:
    write_json(
        path,
        {
            "shop_key": "all",
            "month": "YYYY-MM",
            "mode": "normal",
            "requested_at": None,
            "reason": "Public snapshot template; configure a private staging request before execution.",
            "validation_revision": "public-snapshot-template",
        },
    )


def reset_cutover_evidence(root: Path) -> None:
    path = root / "ops/production_cutover_evidence.json"
    source = load_json(path)
    checks: Dict[str, Any] = {}
    for name in source.get("checks", {}):
        checks[name] = {
            "ready": False,
            "evidence": "Not configured in the public source snapshot.",
            "reviewedBy": "",
            "reviewedAt": None,
        }
    write_json(
        path,
        {
            "version": str(source.get("version", "1.0")),
            "evidence_name": str(source.get("evidence_name", "production_cutover_readiness_evidence")),
            "checks": checks,
        },
    )


def pseudonymize_shop_registry(root: Path, live_identifiers: Set[str]) -> Dict[str, str]:
    path = root / "config/shop_registry.json"
    data = load_json(path)
    replacements: Dict[str, str] = {}
    resource_counter = 1

    for shop in data.get("shops", []):
        key = str(shop.get("shop_key", ""))
        public_pair = PUBLIC_SHOP_IDS.get(key)
        if public_pair:
            old_shop_id = str(shop.get("shop_id", ""))
            old_numeric = str(shop.get("shopee_shop_id", ""))
            if old_shop_id:
                replacements[old_shop_id] = public_pair[0]
            if old_numeric:
                replacements[old_numeric] = public_pair[1]
            shop["shop_id"] = public_pair[0]
            shop["shopee_shop_id"] = public_pair[1]

        for candidate in shop.get("raw_root_candidates", []):
            old = str(candidate.get("folder_id", ""))
            if old:
                public = f"{PUBLIC_RESOURCE_PREFIX}SHOP_{resource_counter:02d}"
                replacements[old] = public
                candidate["folder_id"] = public
                resource_counter += 1

    write_json(path, data)
    return replacements


def _sanitize_storage_value(key: str, value: Any, replacements: MutableMapping[str, str], counter: List[int]) -> Any:
    low = key.lower()
    if isinstance(value, dict):
        out: Dict[str, Any] = {}
        for child_key, child in value.items():
            if child_key == "current_baseline" and isinstance(child, dict):
                clean: Dict[str, Any] = {}
                for baseline_key, baseline_value in child.items():
                    if isinstance(baseline_value, bool):
                        clean[baseline_key] = False
                    elif baseline_key == "period":
                        clean[baseline_key] = "YYYY-MM"
                    elif baseline_key == "auth_mode":
                        clean[baseline_key] = baseline_value
                    else:
                        if isinstance(baseline_value, str) and baseline_value:
                            replacements[baseline_value] = "PUBLIC_SNAPSHOT_NOT_CONFIGURED"
                        clean[baseline_key] = "PUBLIC_SNAPSHOT_NOT_CONFIGURED"
                out[child_key] = clean
            else:
                out[child_key] = _sanitize_storage_value(child_key, child, replacements, counter)
        return out
    if isinstance(value, list):
        if low.endswith("_ids") or low.endswith("root_ids"):
            result = []
            for item in value:
                if isinstance(item, str) and item:
                    public = f"{PUBLIC_RESOURCE_PREFIX}{counter[0]:03d}"
                    counter[0] += 1
                    replacements[item] = public
                    result.append(public)
                else:
                    result.append(item)
            return result
        return [_sanitize_storage_value(key, item, replacements, counter) for item in value]
    if isinstance(value, str) and (
        low.endswith("_id") or low.endswith("_file_id") or low.endswith("_root_id")
    ):
        public = f"{PUBLIC_RESOURCE_PREFIX}{counter[0]:03d}"
        counter[0] += 1
        if value:
            replacements[value] = public
        return public
    return value


def pseudonymize_storage_registry(root: Path) -> Dict[str, str]:
    path = root / "config/storage_registry.json"
    data = load_json(path)
    replacements: Dict[str, str] = {}
    sanitized = _sanitize_storage_value("root", data, replacements, [1])
    write_json(path, sanitized)
    return replacements


def disable_production_schedule(root: Path) -> None:
    path = root / ".github/workflows/unipalm-pipeline.yml"
    text = path.read_text(encoding="utf-8")
    old = (
        "on:\n"
        "  schedule:\n"
        "    # 08:00 Asia/Ho_Chi_Minh = 01:00 UTC\n"
        "    - cron: \"0 1 * * *\"\n"
        "  workflow_dispatch:\n"
    )
    new = (
        "# Public source snapshot: scheduled production execution is intentionally disabled.\n"
        "on:\n"
        "  workflow_dispatch:\n"
    )
    if old not in text:
        raise RuntimeError("production workflow schedule block changed; refusing non-deterministic export")
    text = text.replace(old, new, 1)
    marker = "  pipeline:\n    runs-on: ubuntu-latest\n"
    replacement = (
        "  pipeline:\n"
        "    # Explicit opt-in is required even for manual dispatch in a public clone.\n"
        "    if: ${{ vars.UNIPALM_PUBLIC_PRODUCTION_ENABLE == 'true' }}\n"
        "    runs-on: ubuntu-latest\n"
    )
    if marker not in text:
        raise RuntimeError("production workflow job block changed; refusing non-deterministic export")
    text = text.replace(marker, replacement, 1)
    path.write_text(text, encoding="utf-8")


def exact_replacement_map(live_identifiers: Set[str], structural: Mapping[str, str]) -> Dict[str, str]:
    replacements = dict(structural)
    next_index = 1
    for value in sorted(live_identifiers):
        if value in replacements:
            continue
        replacements[value] = f"{PUBLIC_RESOURCE_PREFIX}LIVE_{next_index:03d}"
        next_index += 1
    replacements["https://example.invalid/"] = "https://example.invalid/"
    replacements["maintainer@example.invalid"] = "maintainer@example.invalid"
    return replacements


def replace_literals_in_text_tree(root: Path, replacements: Mapping[str, str]) -> None:
    ordered = sorted(replacements.items(), key=lambda item: len(item[0]), reverse=True)
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8", errors="strict")
        updated = text
        for old, new in ordered:
            if old:
                updated = updated.replace(old, new)
        if updated != text:
            path.write_text(updated, encoding="utf-8")


OPAQUE_ALPHABET = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=_-")


def _opaque_run_length(text: str, start: int, end: int) -> int:
    left = start
    while left > 0 and text[left - 1] in OPAQUE_ALPHABET:
        left -= 1
    right = end
    while right < len(text) and text[right] in OPAQUE_ALPHABET:
        right += 1
    return right - left


def classify_secret_hits(path: Path, text: str) -> List[Dict[str, Any]]:
    opaque_ranges = [(m.start(), m.end()) for m in OPAQUE_SCRIPT_RE.finditer(text)]
    hits: List[Dict[str, Any]] = []
    for name, pattern in HIGH_CONFIDENCE_SECRET_PATTERNS.items():
        for match in pattern.finditer(text):
            inside_opaque_script = any(
                start <= match.start() < end for start, end in opaque_ranges
            )
            in_long_opaque_run = _opaque_run_length(
                text, match.start(), match.end()
            ) >= 256
            if inside_opaque_script or in_long_opaque_run:
                continue
            hits.append({"indicator": name, "path": path.as_posix()})
    return hits


def validate_snapshot(
    root: Path,
    *,
    forbidden_literals: Iterable[str],
    live_identifiers: Iterable[str],
) -> Dict[str, Any]:
    blockers: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []

    if (root / "index.html").exists():
        blockers.append({"type": "PRODUCTION_ARTIFACT_PRESENT", "path": "index.html"})
    if (root / ".git").exists():
        blockers.append({"type": "GIT_HISTORY_PRESENT", "path": ".git"})

    forbidden = {x for x in forbidden_literals if x} | {x for x in live_identifiers if x}
    secret_hits: List[Dict[str, Any]] = []
    leaked_literals: List[Dict[str, Any]] = []
    data_files: List[str] = []
    scheduled_workflows: List[str] = []

    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if path.suffix.lower() in DATA_SUFFIXES:
            data_files.append(rel)
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8", errors="strict")
        secret_hits.extend(classify_secret_hits(Path(rel), text))
        for literal in forbidden:
            if literal in text:
                leaked_literals.append({"path": rel, "literalClass": "PRIVATE_EXACT_LITERAL"})
                break
        if rel.startswith(".github/workflows/") and re.search(r"(?m)^\s{2}schedule:\s*$", text):
            scheduled_workflows.append(rel)

    if secret_hits:
        blockers.append({"type": "PLAINTEXT_SECRET_INDICATOR", "count": len(secret_hits), "items": secret_hits})
    if leaked_literals:
        blockers.append({"type": "PRIVATE_LITERAL_REMAINS", "count": len(leaked_literals), "items": leaked_literals})
    if data_files:
        blockers.append({"type": "TRACKED_DATA_FILE", "count": len(data_files), "paths": sorted(data_files)})
    if scheduled_workflows:
        blockers.append({"type": "SCHEDULED_WORKFLOW_PRESENT", "paths": sorted(scheduled_workflows)})

    pipeline = load_json(root / "automation/pipeline_state.json")
    if pipeline.get("qa") != "NOT_RUN":
        blockers.append({"type": "PIPELINE_STATE_NOT_RESET"})

    cutover = load_json(root / "ops/production_cutover_evidence.json")
    ready_checks = [name for name, value in cutover.get("checks", {}).items() if value.get("ready")]
    if ready_checks:
        blockers.append({"type": "CUTOVER_EVIDENCE_NOT_RESET", "checks": ready_checks})

    audit = {
        "status": "PASS" if not blockers else "FAIL",
        "snapshotVersion": "unipalm-public-source-snapshot-v1",
        "sourceCompleteOperationsEmpty": not blockers,
        "blockerCount": len(blockers),
        "blockers": blockers,
        "warningCount": len(warnings),
        "warnings": warnings,
        "checks": {
            "productionArtifactAbsent": not (root / "index.html").exists(),
            "gitHistoryAbsent": not (root / ".git").exists(),
            "highConfidencePlaintextSecretCount": len(secret_hits),
            "privateLiteralLeakCount": len(leaked_literals),
            "trackedDataFileCount": len(data_files),
            "scheduledWorkflowCount": len(scheduled_workflows),
            "pipelineStateReset": pipeline.get("qa") == "NOT_RUN",
            "cutoverReadyCheckCount": len(ready_checks),
        },
    }
    return audit


def build_snapshot(source_root: Path, output_root: Path, manifest_path: Path) -> Dict[str, Any]:
    manifest = load_json(manifest_path)
    live_identifiers = collect_live_identifiers(source_root)
    copy_source_tree(source_root, output_root, manifest.get("excluded_paths", []))

    reset_pipeline_state(output_root)
    reset_staging_request(output_root / "config/staging_request.json")
    reset_staging_request(output_root / "ops/staging_request.json")
    reset_cutover_evidence(output_root)

    structural: Dict[str, str] = {}
    structural.update(pseudonymize_shop_registry(output_root, live_identifiers))
    structural.update(pseudonymize_storage_registry(output_root))
    disable_production_schedule(output_root)

    replacements = exact_replacement_map(live_identifiers, structural)
    replace_literals_in_text_tree(output_root, replacements)

    audit = validate_snapshot(
        output_root,
        forbidden_literals=manifest.get("forbidden_public_literals", []),
        live_identifiers=live_identifiers,
    )
    audit["sourceBranch"] = manifest.get("source_branch")
    audit["excludedPaths"] = manifest.get("excluded_paths", [])
    audit["privateIdentifierCountSanitized"] = len(live_identifiers)
    write_json(output_root / "PUBLIC_SNAPSHOT_AUDIT.json", audit)
    if audit["status"] != "PASS":
        raise RuntimeError("public snapshot audit failed: " + json.dumps(audit["blockers"], ensure_ascii=False))
    return audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", default=".")
    parser.add_argument("--output", required=True)
    parser.add_argument("--manifest", default="config/public_export_manifest.json")
    args = parser.parse_args()

    source_root = Path(args.source_root).resolve()
    output_root = Path(args.output).resolve()
    manifest_path = source_root / args.manifest
    audit = build_snapshot(source_root, output_root, manifest_path)
    print(json.dumps(audit, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
