"""PREPRODUCTION Final Hardening / Monitoring + Production Readiness Evidence Closure v1.

This module builds and validates a deployment-ready *candidate package* and
rehearses switch/rollback only inside an isolated temporary workspace.  It
never writes production, never deploys, never binds an executor and never
changes the canonical readiness ledger by itself.
"""
from __future__ import annotations

import hashlib
import html
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence


def s(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha_obj(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return _sha_bytes(raw.encode("utf-8"))


def _read_json(path: str | Path) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json(path: str | Path, value: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _policy(contract: Mapping[str, Any]) -> Dict[str, Any]:
    if s(contract.get("version")) != "1.0":
        raise ValueError("Production Readiness Hardening contract version must be 1.0")
    if s(contract.get("layer_name")) != "multi_shop_production_readiness_hardening_v1":
        raise ValueError("unexpected Production Readiness Hardening layer")
    if s(contract.get("status")) != "PREPRODUCTION":
        raise ValueError("Production Readiness Hardening contract must remain PREPRODUCTION")
    raw = dict(contract.get("production_readiness_hardening") or {})
    if raw.get("enabled") is not True or s(raw.get("mode")) != "PRODUCTION_READINESS_HARDENING_V1":
        raise ValueError("Production Readiness Hardening mode mismatch")

    expected = [
        "production_data_binding_validated",
        "production_ui_binding_validated",
        "deployment_dry_run_validated",
        "rollback_drill_validated",
        "legacy_rollback_runtime_verified",
        "production_credentials_verified",
        "monitoring_readiness_validated",
        "repository_deployment_guard_verified",
    ]
    if list(raw.get("required_check_order") or []) != expected:
        raise ValueError("Production Readiness Hardening gate order mismatch")
    if list(raw.get("automatically_verifiable_checks") or []) != expected[:7]:
        raise ValueError("Production Readiness Hardening automatic gate set mismatch")
    if list(raw.get("external_governance_checks") or []) != [expected[-1]]:
        raise ValueError("Production Readiness Hardening governance gate mismatch")

    candidate = dict(raw.get("native_release_candidate") or {})
    if s(candidate.get("target_path")) != "index.html":
        raise ValueError("release candidate target must remain index.html")
    if s(candidate.get("required_composition_version")) != "native-v2-extension-composition-v1.3":
        raise ValueError("release candidate requires locked Native v1.3")
    if s(candidate.get("required_extension")) != "ads_action_authorization":
        raise ValueError("release candidate requires Action Authorization extension")
    if int(candidate.get("required_selected_shop_minimum") or 0) < 2:
        raise ValueError("release candidate must require multi-shop scope")
    if candidate.get("single_file_static_binding_required") is not True or candidate.get("production_write_allowed") is not False:
        raise ValueError("release candidate must remain static and non-production")

    rehearsal = dict(raw.get("deployment_rehearsal") or {})
    for key in ("isolated_workspace_required", "baseline_backup_required", "candidate_byte_verification_required", "rollback_exact_baseline_hash_required"):
        if rehearsal.get(key) is not True:
            raise ValueError(f"deployment rehearsal requirement missing: {key}")
    if rehearsal.get("repository_write_allowed") is not False or rehearsal.get("production_write_allowed") is not False:
        raise ValueError("deployment rehearsal cannot write repository/production")

    legacy = dict(raw.get("legacy_runtime_probe") or {})
    if any(legacy.get(k) is not True for k in ("source_processor_dry_run_required", "legacy_compile_required", "legacy_dependency_tests_required")):
        raise ValueError("legacy runtime probe requirements incomplete")
    if legacy.get("production_sheet_write_allowed") is not False:
        raise ValueError("legacy runtime probe must remain read-only")

    creds = dict(raw.get("credential_probe") or {})
    if any(creds.get(k) is not True for k in ("configuration_validation_required", "read_only_production_source_access_required", "secret_values_must_not_be_persisted")):
        raise ValueError("credential probe requirements incomplete")

    monitor = dict(raw.get("monitoring_probe") or {})
    if monitor.get("fixed_production_url_required") is not True or monitor.get("exact_current_build_marker_required") is not True or monitor.get("candidate_release_marker_required") is not True:
        raise ValueError("monitoring probe requirements incomplete")
    if int(monitor.get("minimum_successful_http_probes") or 0) < 3 or monitor.get("production_write_allowed") is not False:
        raise ValueError("monitoring probe safety mismatch")

    guard = dict(raw.get("repository_guard") or {})
    if s(guard.get("production_branch")) != "main" or guard.get("branch_protection_required") is not True:
        raise ValueError("repository guard must require protected main")
    if guard.get("soft_workflow_only_guard_is_insufficient") is not True or guard.get("direct_push_must_be_server_side_restricted") is not True:
        raise ValueError("repository guard cannot accept a soft workflow-only substitute")

    evidence = dict(raw.get("evidence") or {})
    if evidence.get("candidate_only") is not True or s(evidence.get("canonical_state_path")) != "ops/production_cutover_evidence.json":
        raise ValueError("readiness evidence boundary mismatch")
    if s(evidence.get("automatic_reviewer")) != "automation:production-readiness-hardening-v1":
        raise ValueError("automatic readiness reviewer mismatch")
    if evidence.get("ready_requires_concrete_evidence") is not True or evidence.get("blocked_gate_must_remain_false") is not True:
        raise ValueError("readiness evidence safety mismatch")

    if bool(raw.get("production_activation_enabled")):
        raise ValueError("Production Readiness Hardening cannot activate production")
    safety = dict(contract.get("safety") or {})
    unsafe = (
        "write_production_data_mart", "modify_production_ui", "modify_production_index",
        "production_deployment_allowed", "platform_mutation_allowed", "production_activation_enabled",
        "authenticated_executor_bound", "execution_enabled", "execution_permit_issued",
        "automatic_cutover_enabled", "automatic_rollback_enabled",
    )
    if any(bool(safety.get(k)) for k in unsafe):
        raise ValueError("Production Readiness Hardening safety flags must remain false")
    return raw


def _release_identity(native_summary: Mapping[str, Any], *, period: str, source_run_id: str, source_head_sha: str) -> Dict[str, str]:
    return {
        "period": s(period),
        "sourceRunId": s(source_run_id),
        "sourceHeadSha": s(source_head_sha),
        "semanticFingerprint": s(native_summary.get("source_semantic_fingerprint")),
        "payloadBuildFingerprint": s(native_summary.get("source_payload_build_fingerprint")),
        "nativeBuildFingerprint": s(native_summary.get("native_build_fingerprint")),
        "nativeTemplateSha256": s(native_summary.get("source_v2_template_sha256")),
    }


def build_release_candidate_html(native_html: str, native_summary: Mapping[str, Any], *, period: str, source_run_id: str, source_head_sha: str) -> Dict[str, Any]:
    identity = _release_identity(native_summary, period=period, source_run_id=source_run_id, source_head_sha=source_head_sha)
    if any(not value for value in identity.values()):
        raise ValueError("release candidate lineage is incomplete")
    if "</head>" not in native_html.lower():
        raise ValueError("Native release candidate has no </head> boundary")
    release_fp = _sha_obj(identity)
    tags = "\n".join([
        f'<meta name="unipalm-release-candidate" content="{html.escape(release_fp, quote=True)}">',
        f'<meta name="unipalm-native-build" content="{html.escape(identity["nativeBuildFingerprint"], quote=True)}">',
        f'<meta name="unipalm-semantic-build" content="{html.escape(identity["semanticFingerprint"], quote=True)}">',
        f'<meta name="unipalm-cutover-source-run" content="{html.escape(identity["sourceRunId"], quote=True)}">',
    ])
    lower = native_html.lower()
    pos = lower.index("</head>")
    candidate = native_html[:pos] + tags + "\n" + native_html[pos:]
    return {
        "html": candidate,
        "releaseCandidateFingerprint": release_fp,
        "releaseCandidateSha256": _sha_bytes(candidate.encode("utf-8")),
        "identity": identity,
    }


def rehearse_deployment_and_rollback(*, baseline_bytes: bytes, candidate_bytes: bytes) -> Dict[str, Any]:
    baseline_sha = _sha_bytes(baseline_bytes)
    candidate_sha = _sha_bytes(candidate_bytes)
    with tempfile.TemporaryDirectory(prefix="unipalm-cutover-rehearsal-") as td:
        root = Path(td)
        target = root / "index.html"
        backup = root / "index.legacy.backup.html"
        target.write_bytes(baseline_bytes)
        backup.write_bytes(target.read_bytes())
        backup_sha = _sha_bytes(backup.read_bytes())
        target.write_bytes(candidate_bytes)
        staged_candidate_sha = _sha_bytes(target.read_bytes())
        candidate_verified = staged_candidate_sha == candidate_sha
        shutil.copyfile(backup, target)
        restored_sha = _sha_bytes(target.read_bytes())
        rollback_verified = restored_sha == baseline_sha == backup_sha
    return {
        "status": "PASS" if candidate_verified and rollback_verified else "FAIL",
        "mode": "ISOLATED_FILESYSTEM_REHEARSAL",
        "baselineSha256": baseline_sha,
        "candidateSha256": candidate_sha,
        "backupSha256": backup_sha,
        "stagedCandidateSha256": staged_candidate_sha,
        "restoredBaselineSha256": restored_sha,
        "candidateByteVerified": candidate_verified,
        "rollbackExactBaselineHashVerified": rollback_verified,
        "repositoryWritePerformed": False,
        "productionWritePerformed": False,
    }


def _probe_pass(probe: Mapping[str, Any], key: str) -> bool:
    return s(probe.get(key)).upper() == "PASS"


def _evidence_row(*, name: str, passed: bool, evidence: str, reviewer: str, observed_at: str, method: str) -> Dict[str, Any]:
    return {
        "name": name,
        "status": "PASS" if passed else "BLOCKED",
        "method": method,
        "detail": evidence,
        "evidenceCandidate": {
            "ready": bool(passed),
            "evidence": evidence,
            "reviewedBy": reviewer,
            "reviewedAt": observed_at,
        },
    }


def build_production_readiness_hardening(*, native_summary: Mapping[str, Any], native_html: str, production_baseline_bytes: bytes, external_probe: Mapping[str, Any], contract: Mapping[str, Any], period: str, source_run_id: str, source_head_sha: str) -> Dict[str, Any]:
    policy = _policy(contract)
    observed_at = s(external_probe.get("observedAt"))
    if not observed_at:
        raise ValueError("external readiness probe observedAt is required")
    # Timestamp syntax/offset is validated by the upstream workflow; the evidence
    # candidate preserves it verbatim for the cutover-control evidence validator.
    reviewer = s((policy.get("evidence") or {}).get("automatic_reviewer"))
    candidate_policy = dict(policy.get("native_release_candidate") or {})

    required_markers = [s(x) for x in candidate_policy.get("required_inline_markers") or []]
    forbidden = [s(x) for x in candidate_policy.get("forbidden_runtime_network_primitives") or []]
    extensions = [s(x) for x in native_summary.get("native_extension_ids") or []]
    native_safety = native_summary.get("safety") or {}
    data_binding_ok = (
        s(native_summary.get("status")) == "PASS"
        and native_summary.get("native_v2_ready") is True
        and int(native_summary.get("selected_shop_count") or 0) >= int(candidate_policy.get("required_selected_shop_minimum") or 2)
        and s(native_summary.get("native_extension_composition_version")) == s(candidate_policy.get("required_composition_version"))
        and s(candidate_policy.get("required_extension")) in extensions
        and all(marker in native_html for marker in required_markers)
        and not any(token and token in native_html for token in forbidden)
        and all(bool(s(native_summary.get(k))) for k in ("source_semantic_fingerprint", "source_payload_build_fingerprint", "native_build_fingerprint", "source_v2_template_sha256"))
    )
    data_evidence = (
        f"Native artifact from staging run {source_run_id}; shops={native_summary.get('selected_shop_count')}; "
        f"semantic={s(native_summary.get('source_semantic_fingerprint'))}; payload={s(native_summary.get('source_payload_build_fingerprint'))}; "
        f"selfContainedInlineBundle={data_binding_ok}."
    )

    release = build_release_candidate_html(native_html, native_summary, period=period, source_run_id=source_run_id, source_head_sha=source_head_sha)
    candidate_html = release["html"]
    release_meta_names = [s(x) for x in candidate_policy.get("release_meta_names") or []]
    meta_ok = all(f'name="{name}"' in candidate_html for name in release_meta_names)
    ui_safety_ok = (
        native_summary.get("ads_action_authorization_ui_ready") is True
        and native_summary.get("ads_action_authorization_read_only") is True
        and native_summary.get("ads_action_authorization_execution_enabled") is False
        and native_summary.get("ads_action_authorization_platform_mutation_allowed") is False
        and native_summary.get("ads_action_authorization_production_activation_enabled") is False
        and native_safety.get("productionCutoverAuthorized") is False
        and native_safety.get("productionDataMartWritten") is False
        and native_safety.get("productionDeploymentPerformed") is False
        and native_safety.get("productionIndexModified") is False
    )
    ui_binding_ok = data_binding_ok and meta_ok and ui_safety_ok and "<html" in candidate_html.lower() and "</html>" in candidate_html.lower()
    ui_evidence = (
        f"Release candidate {release['releaseCandidateFingerprint']} packages Native v1.3 as single static index.html; "
        f"sha256={release['releaseCandidateSha256']}; monitoringMeta={meta_ok}; presentationSafety={ui_safety_ok}."
    )

    rehearsal = rehearse_deployment_and_rollback(
        baseline_bytes=production_baseline_bytes,
        candidate_bytes=candidate_html.encode("utf-8"),
    )
    deployment_ok = ui_binding_ok and rehearsal["candidateByteVerified"] is True and rehearsal["repositoryWritePerformed"] is False and rehearsal["productionWritePerformed"] is False
    deployment_evidence = (
        f"Isolated index switch rehearsal: baseline={rehearsal['baselineSha256']}; candidate={rehearsal['candidateSha256']}; "
        f"candidateByteVerified={rehearsal['candidateByteVerified']}; repositoryWrite=false; productionWrite=false."
    )
    rollback_ok = rehearsal["status"] == "PASS" and rehearsal["rollbackExactBaselineHashVerified"] is True
    rollback_evidence = (
        f"Isolated rollback rehearsal restored exact production baseline sha256={rehearsal['restoredBaselineSha256']} "
        f"after candidate switch; exactHashVerified={rehearsal['rollbackExactBaselineHashVerified']}; productionWrite=false."
    )

    legacy_ok = (
        _probe_pass(external_probe, "legacyCompileStatus")
        and _probe_pass(external_probe, "legacyDependencyTestsStatus")
        and _probe_pass(external_probe, "legacySourceProcessorDryRunStatus")
        and external_probe.get("legacySourceProcessorProductionWritePerformed") is False
    )
    legacy_evidence = (
        f"Legacy compile={s(external_probe.get('legacyCompileStatus'))}; tests={s(external_probe.get('legacyDependencyTestsStatus'))}; "
        f"source_processor --dry-run={s(external_probe.get('legacySourceProcessorDryRunStatus'))}; "
        f"reliableEnd={s(external_probe.get('legacyReliableEnd'))}; productionWrite=false."
    )

    credentials_ok = (
        _probe_pass(external_probe, "configurationValidationStatus")
        and _probe_pass(external_probe, "readOnlyProductionSourceAccessStatus")
        and external_probe.get("secretValuesPersisted") is False
    )
    credential_evidence = (
        f"Configuration validation={s(external_probe.get('configurationValidationStatus'))}; "
        f"read-only production source access={s(external_probe.get('readOnlyProductionSourceAccessStatus'))}; "
        "secret values were not persisted."
    )

    minimum_probes = int((policy.get("monitoring_probe") or {}).get("minimum_successful_http_probes") or 3)
    monitoring_ok = (
        _probe_pass(external_probe, "productionUrlHealthStatus")
        and int(external_probe.get("successfulHttpProbes") or 0) >= minimum_probes
        and external_probe.get("exactCurrentBuildMarkerPresent") is True
        and meta_ok
    )
    monitoring_evidence = (
        f"Live fixed URL health={s(external_probe.get('productionUrlHealthStatus'))}; "
        f"successfulProbes={int(external_probe.get('successfulHttpProbes') or 0)}/{minimum_probes}; "
        f"HTTP={external_probe.get('productionHttpStatus')}; exactCurrentBuildMarker={external_probe.get('exactCurrentBuildMarkerPresent')}; "
        f"candidateReleaseMarker={meta_ok}."
    )

    guard_policy = dict(policy.get("repository_guard") or {})
    guard_ok = (
        external_probe.get("mainBranchProtected") is True
        and external_probe.get("serverSideDirectPushRestricted") is True
        and s(external_probe.get("productionBranch")) == s(guard_policy.get("production_branch"))
    )
    guard_evidence = (
        f"Production branch={s(external_probe.get('productionBranch'))}; protected={external_probe.get('mainBranchProtected')}; "
        f"serverSideDirectPushRestricted={external_probe.get('serverSideDirectPushRestricted')}. "
        "Workflow-only checks are intentionally insufficient."
    )

    rows = [
        _evidence_row(name="production_data_binding_validated", passed=data_binding_ok, evidence=data_evidence, reviewer=reviewer, observed_at=observed_at, method="AUTO_VERIFIED_ARTIFACT_LINEAGE"),
        _evidence_row(name="production_ui_binding_validated", passed=ui_binding_ok, evidence=ui_evidence, reviewer=reviewer, observed_at=observed_at, method="AUTO_VERIFIED_RELEASE_PACKAGE"),
        _evidence_row(name="deployment_dry_run_validated", passed=deployment_ok, evidence=deployment_evidence, reviewer=reviewer, observed_at=observed_at, method="AUTO_VERIFIED_ISOLATED_REHEARSAL"),
        _evidence_row(name="rollback_drill_validated", passed=rollback_ok, evidence=rollback_evidence, reviewer=reviewer, observed_at=observed_at, method="AUTO_VERIFIED_EXACT_HASH_ROLLBACK"),
        _evidence_row(name="legacy_rollback_runtime_verified", passed=legacy_ok, evidence=legacy_evidence, reviewer=reviewer, observed_at=observed_at, method="AUTO_VERIFIED_LEGACY_READ_ONLY_RUNTIME"),
        _evidence_row(name="production_credentials_verified", passed=credentials_ok, evidence=credential_evidence, reviewer=reviewer, observed_at=observed_at, method="AUTO_VERIFIED_SECRET_PRESENCE_AND_READ_ACCESS"),
        _evidence_row(name="monitoring_readiness_validated", passed=monitoring_ok, evidence=monitoring_evidence, reviewer=reviewer, observed_at=observed_at, method="AUTO_VERIFIED_LIVE_HEALTH_AND_RELEASE_MARKERS"),
        _evidence_row(name="repository_deployment_guard_verified", passed=guard_ok, evidence=guard_evidence, reviewer=reviewer, observed_at=observed_at, method="EXTERNAL_GOVERNANCE_SERVER_SIDE_GUARD"),
    ]

    pass_count = sum(1 for row in rows if row["status"] == "PASS")
    auto_names = set(policy.get("automatically_verifiable_checks") or [])
    auto_pass = all(row["status"] == "PASS" for row in rows if row["name"] in auto_names)
    if pass_count == len(rows):
        status = "READY_FOR_CUTOVER_CONTROL_REEVALUATION"
    elif auto_pass and not guard_ok:
        status = "BLOCKED_EXTERNAL_GOVERNANCE"
    else:
        status = "BLOCKED_READINESS"

    candidate_evidence = {
        "version": "1.0",
        "evidence_name": "production_cutover_readiness_evidence",
        "checks": {row["name"]: dict(row["evidenceCandidate"]) for row in rows},
    }
    result = {
        "status": status,
        "mode": s(policy.get("mode")),
        "period": s(period),
        "sourceStagingRunId": s(source_run_id),
        "sourceHeadSha": s(source_head_sha),
        "releaseCandidateFingerprint": release["releaseCandidateFingerprint"],
        "releaseCandidateSha256": release["releaseCandidateSha256"],
        "releaseIdentity": release["identity"],
        "productionBaselineSha256": rehearsal["baselineSha256"],
        "checks": rows,
        "passCount": pass_count,
        "blockedCount": len(rows) - pass_count,
        "deploymentRehearsal": rehearsal,
        "evidenceCandidate": candidate_evidence,
        "safety": {
            "preproductionOnly": True,
            "productionWritePerformed": False,
            "repositoryWritePerformed": False,
            "productionDataMartWritten": False,
            "productionUiModified": False,
            "productionIndexModified": False,
            "productionDeploymentPerformed": False,
            "platformMutationAllowed": False,
            "authenticatedExecutorBound": False,
            "executionEnabled": False,
            "executionPermitIssued": False,
            "productionActivationEnabled": False,
            "automaticCutoverEnabled": False,
            "automaticRollbackEnabled": False,
        },
    }
    result["productionReadinessHardeningFingerprint"] = _sha_obj({
        "period": result["period"],
        "sourceStagingRunId": result["sourceStagingRunId"],
        "sourceHeadSha": result["sourceHeadSha"],
        "release": release["identity"],
        "releaseCandidateFingerprint": release["releaseCandidateFingerprint"],
        "productionBaselineSha256": result["productionBaselineSha256"],
        "checks": rows,
        "safety": result["safety"],
    })
    result["releaseCandidateHtml"] = candidate_html
    return result


def validate_production_readiness_hardening(value: Mapping[str, Any], *, contract: Mapping[str, Any]) -> Dict[str, Any]:
    policy = _policy(contract)
    checks = []

    def ck(name: str, ok: bool, detail: Any = None) -> None:
        checks.append({"name": name, "status": "PASS" if ok else "FAIL", "detail": detail or {}})

    ck("status_known", s(value.get("status")) in {"READY_FOR_CUTOVER_CONTROL_REEVALUATION", "BLOCKED_EXTERNAL_GOVERNANCE", "BLOCKED_READINESS"})
    ck("fingerprint_present", bool(s(value.get("productionReadinessHardeningFingerprint"))))
    ck("release_fingerprint_present", bool(s(value.get("releaseCandidateFingerprint"))) and bool(s(value.get("releaseCandidateSha256"))))
    ck("lineage_present", bool(s(value.get("period"))) and bool(s(value.get("sourceStagingRunId"))) and bool(s(value.get("sourceHeadSha"))))
    rows = list(value.get("checks") or [])
    expected = list(policy.get("required_check_order") or [])
    ck("gate_order", [s(x.get("name")) for x in rows] == expected)
    ck("gate_states", len(rows) == 8 and all(s(x.get("status")) in {"PASS", "BLOCKED"} for x in rows))
    ck("counts", int(value.get("passCount") or 0) == sum(1 for x in rows if s(x.get("status")) == "PASS") and int(value.get("blockedCount") or 0) == sum(1 for x in rows if s(x.get("status")) == "BLOCKED"))
    for row in rows:
        candidate = row.get("evidenceCandidate") or {}
        ck(f"{s(row.get('name'))}_evidence_present", bool(s(candidate.get("evidence"))) and bool(s(candidate.get("reviewedBy"))) and bool(s(candidate.get("reviewedAt"))))
        ck(f"{s(row.get('name'))}_ready_matches", candidate.get("ready") is (s(row.get("status")) == "PASS"))
    rehearsal = value.get("deploymentRehearsal") or {}
    ck("isolated_rehearsal", s(rehearsal.get("mode")) == "ISOLATED_FILESYSTEM_REHEARSAL")
    ck("rehearsal_no_writes", rehearsal.get("repositoryWritePerformed") is False and rehearsal.get("productionWritePerformed") is False)
    safety = value.get("safety") or {}
    for key in (
        "productionWritePerformed", "repositoryWritePerformed", "productionDataMartWritten",
        "productionUiModified", "productionIndexModified", "productionDeploymentPerformed",
        "platformMutationAllowed", "authenticatedExecutorBound", "executionEnabled",
        "executionPermitIssued", "productionActivationEnabled", "automaticCutoverEnabled",
        "automaticRollbackEnabled",
    ):
        ck(f"safety_{key}", safety.get(key) is False)
    candidate_evidence = value.get("evidenceCandidate") or {}
    ck("candidate_evidence_shape", s(candidate_evidence.get("version")) == "1.0" and s(candidate_evidence.get("evidence_name")) == "production_cutover_readiness_evidence" and list((candidate_evidence.get("checks") or {}).keys()) == expected)
    failed = [x for x in checks if x["status"] == "FAIL"]
    return {"status": "PASS" if not failed else "FAIL", "failedCheckCount": len(failed), "checks": checks}


def bind_production_readiness_artifact(*, native_summary_path: str | Path, native_html_path: str | Path, production_baseline_path: str | Path, external_probe_path: str | Path, contract_path: str | Path, output_dir: str | Path, period: str, source_run_id: str, source_head_sha: str) -> Dict[str, Any]:
    contract = _read_json(contract_path)
    native_summary = _read_json(native_summary_path)
    external_probe = _read_json(external_probe_path)
    native_html = Path(native_html_path).read_text(encoding="utf-8")
    baseline = Path(production_baseline_path).read_bytes()
    result = build_production_readiness_hardening(
        native_summary=native_summary,
        native_html=native_html,
        production_baseline_bytes=baseline,
        external_probe=external_probe,
        contract=contract,
        period=period,
        source_run_id=source_run_id,
        source_head_sha=source_head_sha,
    )
    release_html = result.pop("releaseCandidateHtml")
    qa = validate_production_readiness_hardening(result, contract=contract)
    if qa["status"] != "PASS":
        failed = [x["name"] for x in qa["checks"] if x["status"] == "FAIL"]
        raise ValueError(f"Production Readiness Hardening QA failed: {failed[:30]}")
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "release_candidate_index.html").write_text(release_html, encoding="utf-8")
    _write_json(out / "production_readiness_hardening.json", result)
    _write_json(out / "production_readiness_hardening_qa.json", qa)
    _write_json(out / "production_cutover_evidence_candidate.json", result["evidenceCandidate"])
    return {"status": "PASS", "qa": qa, "artifact": result}
