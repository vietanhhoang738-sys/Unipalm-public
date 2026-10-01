"""Fail-closed validation for the source-complete, operations-empty public repo."""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable

from build_public_snapshot import DATA_SUFFIXES, TEXT_SUFFIXES, classify_secret_hits


ROOT = Path(__file__).resolve().parents[1]
TRUSTED_ROOT_COMMIT = "220923e55ea606d01db8b80ca383fd14c6a66585"
TRUSTED_ROOT_TREE = "0ecb9634f8cdbd56122ab22cddad71c0ed5c08bd"
ALLOWED_WORKFLOWS = {".github/workflows/public-ci.yml"}
ALLOWED_ACTIONS = {"actions/checkout", "actions/setup-python"}
EXPECTED_SHOPS = {
    "syt_plus": ("SHP_VN_1000000001", "1000000001"),
    "mall": ("SHP_VN_1000000002", "1000000002"),
}
CREDENTIAL_FILE_RE = re.compile(
    r"(^|/)(\.env($|\.)|credentials?[^/]*\.(json|ya?ml)|"
    r"service[_-]?account[^/]*\.json|.*\.(pem|p12|key))$",
    re.I,
)


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=check,
        text=True,
        encoding="utf-8",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def load_json(relative_path: str) -> Any:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def tracked_files() -> list[str]:
    output = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
    ).stdout
    return [item.decode("utf-8") for item in output.split(b"\0") if item]


def iter_identifier_values(value: Any, *, key: str = "") -> Iterable[tuple[str, str]]:
    if isinstance(value, dict):
        for child_key, child in value.items():
            yield from iter_identifier_values(child, key=str(child_key))
    elif isinstance(value, list):
        for child in value:
            yield from iter_identifier_values(child, key=key)
    elif isinstance(value, str) and (key.endswith("_id") or key.endswith("_ids")):
        yield key, value


def validate_history(blockers: list[dict[str, Any]]) -> None:
    roots = [line for line in git("rev-list", "--max-parents=0", "HEAD").stdout.splitlines() if line]
    if roots != [TRUSTED_ROOT_COMMIT]:
        blockers.append({"type": "UNTRUSTED_ROOT_HISTORY", "roots": roots})

    ancestor = git("merge-base", "--is-ancestor", TRUSTED_ROOT_COMMIT, "HEAD", check=False)
    if ancestor.returncode != 0:
        blockers.append({"type": "TRUSTED_ROOT_NOT_ANCESTOR"})

    root_tree = git("rev-parse", f"{TRUSTED_ROOT_COMMIT}^{{tree}}", check=False)
    if root_tree.returncode != 0 or root_tree.stdout.strip() != TRUSTED_ROOT_TREE:
        blockers.append(
            {
                "type": "TRUSTED_ROOT_TREE_CHANGED",
                "actual": root_tree.stdout.strip() or None,
            }
        )


def validate_workflow(path: Path, blockers: list[dict[str, Any]]) -> None:
    text = path.read_text(encoding="utf-8")
    lower = text.lower()

    forbidden_fragments = {
        "pull_request_target": "PRIVILEGED_PULL_REQUEST_TRIGGER",
        "repository_dispatch": "EXTERNAL_DISPATCH_TRIGGER",
        "workflow_run": "CHAINED_WORKFLOW_TRIGGER",
        "${{ secrets.": "SECRET_REFERENCE",
        "id-token: write": "OIDC_WRITE_PERMISSION",
        "contents: write": "CONTENTS_WRITE_PERMISSION",
        "actions: write": "ACTIONS_WRITE_PERMISSION",
        "packages: write": "PACKAGES_WRITE_PERMISSION",
        "pull-requests: write": "PULL_REQUEST_WRITE_PERMISSION",
        "deployments: write": "DEPLOYMENT_WRITE_PERMISSION",
        "security-events: write": "SECURITY_EVENT_WRITE_PERMISSION",
        "write-all": "WRITE_ALL_PERMISSION",
    }
    for fragment, kind in forbidden_fragments.items():
        if fragment in lower:
            blockers.append({"type": kind, "path": path.relative_to(ROOT).as_posix()})

    if re.search(r"(?m)^\s{2}schedule:\s*$", text):
        blockers.append({"type": "SCHEDULED_WORKFLOW", "path": path.relative_to(ROOT).as_posix()})
    if not re.search(r"(?m)^permissions:\s*\n\s{2}contents:\s*read\s*$", text):
        blockers.append({"type": "MISSING_READ_ONLY_PERMISSIONS"})
    if "persist-credentials: false" not in text:
        blockers.append({"type": "CHECKOUT_CREDENTIALS_NOT_DISABLED"})

    uses = re.findall(r"(?m)^\s*-?\s*uses:\s*([^\s#]+)", text)
    for reference in uses:
        if "@" not in reference:
            blockers.append({"type": "UNPINNED_ACTION", "reference": reference})
            continue
        action, revision = reference.rsplit("@", 1)
        if action not in ALLOWED_ACTIONS:
            blockers.append({"type": "UNAPPROVED_ACTION", "reference": reference})
        if not re.fullmatch(r"[0-9a-f]{40}", revision):
            blockers.append({"type": "MUTABLE_ACTION_REFERENCE", "reference": reference})


def validate_operations_empty(blockers: list[dict[str, Any]]) -> None:
    pipeline = load_json("automation/pipeline_state.json")
    if (
        pipeline.get("run_id") != "PUBLIC_SNAPSHOT_NOT_RUN"
        or pipeline.get("build_id") != "PUBLIC_SNAPSHOT_NOT_RUN"
        or pipeline.get("qa") != "NOT_RUN"
        or pipeline.get("production_url") != "https://example.invalid/"
        or pipeline.get("generated_at") is not None
    ):
        blockers.append({"type": "PIPELINE_STATE_NOT_RESET"})

    for relative_path in ("config/staging_request.json", "ops/staging_request.json"):
        request = load_json(relative_path)
        if request.get("month") != "YYYY-MM" or request.get("requested_at") is not None:
            blockers.append({"type": "STAGING_REQUEST_NOT_RESET", "path": relative_path})

    evidence = load_json("ops/production_cutover_evidence.json")
    ready = [
        name
        for name, value in evidence.get("checks", {}).items()
        if value.get("ready")
        or value.get("reviewedBy")
        or value.get("reviewedAt") is not None
    ]
    if ready:
        blockers.append({"type": "CUTOVER_EVIDENCE_NOT_RESET", "checks": ready})


def validate_pseudonyms(blockers: list[dict[str, Any]]) -> None:
    registry = load_json("config/shop_registry.json")
    actual = {
        str(shop.get("shop_key")): (
            str(shop.get("shop_id")),
            str(shop.get("shopee_shop_id")),
        )
        for shop in registry.get("shops", [])
    }
    if actual != EXPECTED_SHOPS:
        blockers.append({"type": "SHOP_IDENTIFIERS_NOT_PSEUDONYMIZED"})

    for relative_path in ("config/shop_registry.json", "config/storage_registry.json"):
        for key, value in iter_identifier_values(load_json(relative_path)):
            if key in {"shop_id", "shopee_shop_id"}:
                continue
            if value and not value.startswith(("PUBLIC_RESOURCE_", "PUBLIC_SNAPSHOT_")):
                blockers.append(
                    {
                        "type": "RESOURCE_IDENTIFIER_NOT_PSEUDONYMIZED",
                        "path": relative_path,
                        "key": key,
                    }
                )


def validate_tree(blockers: list[dict[str, Any]]) -> None:
    files = tracked_files()
    workflows = {path for path in files if path.startswith(".github/workflows/")}
    if workflows != ALLOWED_WORKFLOWS:
        blockers.append(
            {
                "type": "WORKFLOW_ALLOWLIST_MISMATCH",
                "expected": sorted(ALLOWED_WORKFLOWS),
                "actual": sorted(workflows),
            }
        )

    if "index.html" in files:
        blockers.append({"type": "PRODUCTION_ARTIFACT_PRESENT", "path": "index.html"})

    data_files = [path for path in files if Path(path).suffix.lower() in DATA_SUFFIXES]
    if data_files:
        blockers.append({"type": "TRACKED_DATA_FILES", "paths": data_files})

    credential_files = [path for path in files if CREDENTIAL_FILE_RE.search(path)]
    if credential_files:
        blockers.append({"type": "CREDENTIAL_FILES", "paths": credential_files})

    secret_hits: list[dict[str, Any]] = []
    for relative_path in files:
        path = ROOT / relative_path
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8", errors="strict")
        secret_hits.extend(classify_secret_hits(Path(relative_path), text))
    if secret_hits:
        blockers.append(
            {"type": "PLAINTEXT_SECRET_INDICATOR", "count": len(secret_hits), "items": secret_hits}
        )

    for relative_path in sorted(workflows):
        validate_workflow(ROOT / relative_path, blockers)


def main() -> int:
    blockers: list[dict[str, Any]] = []
    audit = load_json("PUBLIC_SNAPSHOT_AUDIT.json")
    if (
        audit.get("status") != "PASS"
        or audit.get("blockerCount") != 0
        or not audit.get("sourceCompleteOperationsEmpty")
        or int(audit.get("privateIdentifierCountSanitized", 0)) < 1
    ):
        blockers.append({"type": "SOURCE_SNAPSHOT_AUDIT_NOT_PASSING"})

    validate_history(blockers)
    validate_tree(blockers)
    validate_operations_empty(blockers)
    validate_pseudonyms(blockers)

    result = {
        "status": "PASS" if not blockers else "FAIL",
        "blockerCount": len(blockers),
        "blockers": blockers,
        "trustedRootCommit": TRUSTED_ROOT_COMMIT,
        "allowedWorkflowCount": len(ALLOWED_WORKFLOWS),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if not blockers else 1


if __name__ == "__main__":
    sys.exit(main())
