"""PREPRODUCTION Production Cutover Preparation & Execution-Control Hardening v1.

The module evaluates whether the validated N-shop path is prepared to request an
explicit production cutover decision. It never performs deployment, platform
mutation, provider binding, automatic cutover or automatic rollback.

A human APPROVE_CUTOVER_PLAN event only records approval for a future explicit
execution milestone. No execution permit is issued by this module.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence


def s(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _sha(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _time(value: Any) -> dt.datetime:
    text = s(value)
    if not text:
        raise ValueError("timezone-aware timestamp is required")
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = dt.datetime.fromisoformat(normalized)
    except Exception as exc:
        raise ValueError(f"invalid timezone-aware timestamp: {value!r}") from exc
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include an explicit timezone")
    return parsed


def _read_json(path: str | Path) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json(path: str | Path, value: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _policy(contract: Mapping[str, Any]) -> Dict[str, Any]:
    if s(contract.get("version")) != "1.0":
        raise ValueError("Production Cutover Control contract version must be 1.0")
    if s(contract.get("layer_name")) != "multi_shop_production_cutover_control_v1":
        raise ValueError("unexpected Production Cutover Control layer")
    if s(contract.get("status")) != "PREPRODUCTION":
        raise ValueError("Production Cutover Control contract must remain PREPRODUCTION")
    raw = dict(contract.get("cutover_control") or {})
    if raw.get("enabled") is not True:
        raise ValueError("cutover_control must be enabled")
    if s(raw.get("mode")) != "PRODUCTION_CUTOVER_PREPARATION_V1":
        raise ValueError("unexpected Production Cutover Control mode")
    expected_sources = {
        "action_authorization_source": "ads_action_authorization.json",
        "native_summary_source": "multi_shop_native_v2_summary_<YYYY-MM>.json",
        "readiness_evidence_source": "production_cutover_evidence.json",
        "authorization_event_source": "production_cutover_authorization_events.json",
    }
    for key, expected in expected_sources.items():
        if s(raw.get(key)) != expected:
            raise ValueError(f"Production Cutover Control source mismatch: {key}")
    if raw.get("require_all_shop_scope") is not True:
        raise ValueError("production cutover preparation must require all-shop scope")
    if s(raw.get("required_native_composition_version")) != "native-v2-extension-composition-v1.3":
        raise ValueError("Production Cutover Control v1 requires locked Native v1.3")
    if s(raw.get("required_native_extension")) != "ads_action_authorization":
        raise ValueError("Production Cutover Control v1 requires Action Authorization extension")
    if int(raw.get("required_compatibility_bridge_count") or 0) != 1:
        raise ValueError("Production Cutover Control v1 requires exactly one compatibility bridge")

    readiness = [s(x) for x in raw.get("required_readiness_checks") or []]
    expected_readiness = [
        "production_data_binding_validated",
        "production_ui_binding_validated",
        "deployment_dry_run_validated",
        "rollback_drill_validated",
        "legacy_rollback_runtime_verified",
        "production_credentials_verified",
        "monitoring_readiness_validated",
        "repository_deployment_guard_verified",
    ]
    if readiness != expected_readiness:
        raise ValueError("Production Cutover Control readiness gates mismatch")

    required_legacy = [s(x) for x in raw.get("required_legacy_repository_paths") or []]
    if not required_legacy or len(required_legacy) != len(set(required_legacy)):
        raise ValueError("required legacy rollback repository paths must be non-empty and unique")

    auth = dict(raw.get("authorization") or {})
    if auth.get("append_only") is not True:
        raise ValueError("production cutover authorization ledger must be append-only")
    if list(auth.get("actions") or []) != [
        "APPROVE_CUTOVER_PLAN", "REJECT_CUTOVER_PLAN", "REVOKE_CUTOVER_PLAN"
    ]:
        raise ValueError("production cutover authorization actions mismatch")
    if list(auth.get("pending_actions") or []) != ["APPROVE_CUTOVER_PLAN", "REJECT_CUTOVER_PLAN"]:
        raise ValueError("pending production cutover authorization actions mismatch")
    if list(auth.get("approved_actions") or []) != ["REVOKE_CUTOVER_PLAN"]:
        raise ValueError("approved production cutover authorization actions mismatch")
    if list(auth.get("rejected_actions") or []) or list(auth.get("revoked_actions") or []):
        raise ValueError("rejected/revoked production cutover authorization states must be terminal")
    if s(auth.get("approval_status")) != "APPROVED_FOR_EXPLICIT_EXECUTION_MILESTONE":
        raise ValueError("cutover approval must stop before execution")
    for key in (
        "expected_ledger_fingerprint_required",
        "cutover_plan_fingerprint_binding_required",
        "deterministic_event_id",
        "authorized_at_timezone_required",
        "authorized_by_required",
        "ledger_apply_requires_explicit_flag",
    ):
        if auth.get(key) is not True:
            raise ValueError(f"production cutover authorization requirement missing: {key}")

    drill = dict(raw.get("rollback_drill") or {})
    if drill.get("dry_run_only") is not True:
        raise ValueError("rollback drill must remain dry-run-only")
    expected_steps = [
        "CAPTURE_PRODUCTION_BASELINE",
        "VERIFY_LEGACY_ROLLBACK_TARGET",
        "VERIFY_NEW_ARTIFACT_LINEAGE",
        "SIMULATE_BINDING_SWITCH",
        "SIMULATE_HEALTH_CHECK_FAILURE",
        "SIMULATE_ROLLBACK_TO_LEGACY",
        "VERIFY_POST_ROLLBACK_BASELINE",
    ]
    if list(drill.get("required_steps") or []) != expected_steps:
        raise ValueError("rollback drill step contract mismatch")
    if drill.get("automatic_rollback_enabled") is not False or drill.get("production_write_allowed") is not False:
        raise ValueError("rollback drill cannot enable production mutation")

    executor = dict(raw.get("executor_boundary") or {})
    required_true = (
        "authenticated_executor_required",
        "dry_run_only",
        "short_lived_session_required",
        "prepare_commit_separation_required",
        "idempotency_key_required",
        "audit_trail_required",
        "rollback_plan_required",
        "post_deploy_verification_required",
    )
    if any(executor.get(k) is not True for k in required_true):
        raise ValueError("Production Cutover Control executor requirement missing")
    if int(executor.get("max_session_ttl_seconds") or 0) != 900:
        raise ValueError("Production Cutover Control max session TTL must remain 900 seconds")
    expected_claims = ["actor", "sessionId", "issuedAt", "expiresAt", "cutoverPlanFingerprint"]
    if list(executor.get("identity_claims_required") or []) != expected_claims:
        raise ValueError("Production Cutover Control executor identity claims mismatch")
    forbidden_true = (
        "authenticated_executor_bound",
        "execution_enabled",
        "automatic_cutover_enabled",
        "automatic_rollback_enabled",
        "provider_binding_enabled",
        "platform_mutation_allowed",
        "production_activation_enabled",
        "execution_permit_issued",
    )
    if any(bool(executor.get(k)) for k in forbidden_true):
        raise ValueError("Production Cutover Control v1 executor must remain unbound and non-executable")
    if bool(raw.get("production_activation_enabled")):
        raise ValueError("Production Cutover Control v1 cannot activate production")

    safety = dict(contract.get("safety") or {})
    unsafe = [
        "write_production_data_mart",
        "modify_production_ui",
        "platform_mutation_allowed",
        "production_activation_enabled",
        "authenticated_executor_bound",
        "execution_enabled",
        "execution_permit_issued",
        "automatic_cutover_enabled",
        "automatic_rollback_enabled",
    ]
    if any(bool(safety.get(k)) for k in unsafe):
        raise ValueError("Production Cutover Control contract safety flags must remain false")
    return raw


def readiness_evidence_fingerprint(evidence: Mapping[str, Any]) -> str:
    return _sha({
        "version": s(evidence.get("version")),
        "evidence_name": s(evidence.get("evidence_name")),
        "checks": evidence.get("checks") or {},
    })


def _readiness_checks(evidence: Mapping[str, Any], required: Sequence[str]) -> Dict[str, Dict[str, Any]]:
    if s(evidence.get("version")) != "1.0" or s(evidence.get("evidence_name")) != "production_cutover_readiness_evidence":
        raise ValueError("unexpected production cutover readiness evidence")
    raw = evidence.get("checks") or {}
    if set(raw) != set(required):
        raise ValueError("production cutover readiness evidence keys mismatch")
    out: Dict[str, Dict[str, Any]] = {}
    for key in required:
        row = raw.get(key)
        if not isinstance(row, Mapping):
            raise ValueError(f"readiness evidence row must be an object: {key}")
        ready = row.get("ready") is True
        evidence_text = s(row.get("evidence"))
        reviewed_by = s(row.get("reviewedBy"))
        reviewed_at = s(row.get("reviewedAt"))
        if ready:
            if not evidence_text or not reviewed_by or not reviewed_at:
                raise ValueError(f"ready cutover evidence requires evidence/reviewer/timestamp: {key}")
            _time(reviewed_at)
        elif reviewed_at:
            _time(reviewed_at)
        out[key] = {
            "ready": ready,
            "evidence": evidence_text,
            "reviewedBy": reviewed_by,
            "reviewedAt": reviewed_at,
        }
    return out


def cutover_authorization_ledger_fingerprint(ledger: Mapping[str, Any]) -> str:
    return _sha({
        "version": s(ledger.get("version")),
        "ledger_name": s(ledger.get("ledger_name")),
        "events": list(ledger.get("events") or []),
    })


def _authorization_events(ledger: Mapping[str, Any]) -> List[Dict[str, Any]]:
    if s(ledger.get("version")) != "1.0" or s(ledger.get("ledger_name")) != "production_cutover_authorization_events":
        raise ValueError("unexpected production cutover authorization ledger")
    out: List[Dict[str, Any]] = []
    seen = set()
    for raw in ledger.get("events") or []:
        if not isinstance(raw, Mapping):
            raise ValueError("cutover authorization events must be objects")
        event_id = s(raw.get("eventId"))
        action = s(raw.get("action")).upper()
        plan_fp = s(raw.get("cutoverPlanFingerprint"))
        authorized_at = s(raw.get("authorizedAt"))
        authorized_by = s(raw.get("authorizedBy"))
        if not event_id or event_id in seen:
            raise ValueError(f"duplicate or missing cutover authorization eventId: {event_id!r}")
        seen.add(event_id)
        if action not in {"APPROVE_CUTOVER_PLAN", "REJECT_CUTOVER_PLAN", "REVOKE_CUTOVER_PLAN"}:
            raise ValueError(f"unsupported cutover authorization action: {action!r}")
        if not plan_fp or not authorized_by:
            raise ValueError(f"cutover authorization event identity incomplete: {event_id}")
        _time(authorized_at)
        out.append({
            "eventId": event_id,
            "action": action,
            "cutoverPlanFingerprint": plan_fp,
            "authorizedAt": authorized_at,
            "authorizedBy": authorized_by,
            "note": s(raw.get("note")),
        })
    out.sort(key=lambda x: (_time(x["authorizedAt"]), x["eventId"]))
    return out


def _authorization_state(plan_fingerprint: str, events: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    relevant = [dict(x) for x in events if s(x.get("cutoverPlanFingerprint")) == plan_fingerprint]
    state = "PENDING_CUTOVER_AUTHORIZATION"
    latest: Dict[str, Any] = {}
    for event in relevant:
        action = s(event.get("action"))
        if state == "PENDING_CUTOVER_AUTHORIZATION":
            if action == "APPROVE_CUTOVER_PLAN":
                state = "APPROVED_FOR_EXPLICIT_EXECUTION_MILESTONE"
            elif action == "REJECT_CUTOVER_PLAN":
                state = "REJECTED"
            else:
                raise ValueError("REVOKE_CUTOVER_PLAN is invalid before approval")
        elif state == "APPROVED_FOR_EXPLICIT_EXECUTION_MILESTONE":
            if action == "REVOKE_CUTOVER_PLAN":
                state = "REVOKED"
            else:
                raise ValueError("approved cutover plan only allows revoke")
        else:
            raise ValueError("rejected/revoked cutover plan is terminal")
        latest = event
    available = {
        "PENDING_CUTOVER_AUTHORIZATION": ["APPROVE_CUTOVER_PLAN", "REJECT_CUTOVER_PLAN"],
        "APPROVED_FOR_EXPLICIT_EXECUTION_MILESTONE": ["REVOKE_CUTOVER_PLAN"],
        "REJECTED": [],
        "REVOKED": [],
    }[state]
    return {
        "state": state,
        "availableActions": available,
        "eventCount": len(relevant),
        "latestEvent": latest,
        "executionPermitIssued": False,
        "productionActivationEnabled": False,
    }


def _legacy_repository_gate(repo_root: str | Path, required_paths: Sequence[str]) -> Dict[str, Any]:
    root = Path(repo_root)
    missing = [rel for rel in required_paths if not (root / rel).exists()]
    return {
        "status": "PASS" if not missing else "FAIL",
        "requiredPaths": list(required_paths),
        "missingPaths": missing,
        "legacyRollbackRepositorySurfaceRetained": not missing,
    }


def build_rollback_drill(plan_fingerprint: str, policy: Mapping[str, Any], *, legacy_gate: Mapping[str, Any]) -> Dict[str, Any]:
    drill_policy = dict(policy.get("rollback_drill") or {})
    steps = []
    for index, step in enumerate(drill_policy.get("required_steps") or [], start=1):
        status = "PASS"
        if step == "VERIFY_LEGACY_ROLLBACK_TARGET" and legacy_gate.get("status") != "PASS":
            status = "BLOCKED"
        steps.append({"sequence": index, "step": step, "status": status, "productionWritePerformed": False})
    blocked = [x for x in steps if x["status"] != "PASS"]
    return {
        "status": "DRY_RUN_PASS" if not blocked else "BLOCKED",
        "mode": "SIMULATION_ONLY",
        "cutoverPlanFingerprint": plan_fingerprint,
        "steps": steps,
        "productionWritePerformed": False,
        "automaticRollbackEnabled": False,
        "rollbackExecutionAuthorized": False,
        "drillFingerprint": _sha({"plan": plan_fingerprint, "steps": steps}),
    }


def _validate_upstream(action_authorization: Mapping[str, Any], native_summary: Mapping[str, Any], policy: Mapping[str, Any]) -> List[Dict[str, Any]]:
    gates: List[Dict[str, Any]] = []

    def gate(name: str, ok: bool, detail: Any = None) -> None:
        gates.append({"name": name, "status": "PASS" if ok else "FAIL", "detail": detail or {}})

    aa_status = s(action_authorization.get("status"))
    aa_fp = s(action_authorization.get("actionAuthorizationFingerprint"))
    aa_execution = action_authorization.get("executionBoundary") or {}
    aa_safety = action_authorization.get("safety") or {}
    gate("action_authorization_ready", aa_status in {"READY", "READY_EMPTY"} and bool(aa_fp), {"status": aa_status})
    gate("action_authorization_execution_blocked", aa_execution.get("authenticatedExecutorRequired") is True and aa_execution.get("authenticatedExecutorBound") is False and aa_execution.get("executionEnabled") is False and aa_execution.get("dryRunOnly") is True and aa_execution.get("providerBindingEnabled") is False and aa_execution.get("platformMutationAllowed") is False and aa_execution.get("productionActivationEnabled") is False)
    gate("action_authorization_safety_blocked", aa_safety.get("automaticExecutionEnabled") is False and aa_safety.get("platformMutationAllowed") is False and aa_safety.get("productionActivationEnabled") is False)

    native_safety = native_summary.get("safety") or {}
    extensions = list(native_summary.get("native_extension_ids") or [])
    gate("native_status", s(native_summary.get("status")) == "PASS" and native_summary.get("native_v2_ready") is True)
    gate("native_composition_locked", native_summary.get("native_extension_composition_ready") is True and s(native_summary.get("native_extension_composition_version")) == s(policy.get("required_native_composition_version")) and int(native_summary.get("native_extension_compatibility_bridge_count") or 0) == int(policy.get("required_compatibility_bridge_count") or 0) and native_summary.get("legacy_nested_wrapper_build_path_used") is False and s(policy.get("required_native_extension")) in extensions, {"extensions": extensions})
    gate("native_action_authorization_lineage", native_summary.get("ads_action_authorization_ui_ready") is True and native_summary.get("ads_action_authorization_read_only") is True and s(native_summary.get("ads_action_authorization_fingerprint")) == aa_fp)
    gate("native_execution_blocked", native_summary.get("ads_action_authorization_authenticated_executor_bound") is False and native_summary.get("ads_action_authorization_execution_enabled") is False and native_summary.get("ads_action_authorization_provider_binding_enabled") is False and native_summary.get("ads_action_authorization_platform_mutation_allowed") is False and native_summary.get("ads_action_authorization_production_activation_enabled") is False)
    gate("native_production_safety", native_safety.get("productionCutoverAuthorized") is False and native_safety.get("productionDataMartWritten") is False and native_safety.get("productionDeploymentPerformed") is False and native_safety.get("productionIndexModified") is False and native_safety.get("productionV2TemplateModified") is False)
    gate("all_shop_scope", int(native_summary.get("selected_shop_count") or 0) >= 2)
    gate("artifact_lineage_present", all(bool(s(native_summary.get(key))) for key in ("source_payload_build_fingerprint", "source_semantic_fingerprint", "native_build_fingerprint", "source_v2_template_sha256")))
    return gates


def build_production_cutover_control(*, action_authorization: Mapping[str, Any], native_summary: Mapping[str, Any], readiness_evidence: Mapping[str, Any], authorization_ledger: Mapping[str, Any], contract: Mapping[str, Any], repo_root: str | Path, period: str, head_sha: str, staging_run_id: str) -> Dict[str, Any]:
    policy = _policy(contract)
    required_readiness = [s(x) for x in policy.get("required_readiness_checks") or []]
    evidence = _readiness_checks(readiness_evidence, required_readiness)
    evidence_fp = readiness_evidence_fingerprint(readiness_evidence)
    ledger_events = _authorization_events(authorization_ledger)
    ledger_fp = cutover_authorization_ledger_fingerprint(authorization_ledger)

    upstream_gates = _validate_upstream(action_authorization, native_summary, policy)
    legacy_gate = _legacy_repository_gate(repo_root, policy.get("required_legacy_repository_paths") or [])
    upstream_gates.append({"name": "legacy_rollback_repository_surface", "status": legacy_gate["status"], "detail": legacy_gate})

    lineage = {
        "period": s(period),
        "headSha": s(head_sha),
        "stagingRunId": s(staging_run_id),
        "semanticFingerprint": s(native_summary.get("source_semantic_fingerprint")),
        "payloadBuildFingerprint": s(native_summary.get("source_payload_build_fingerprint")),
        "nativeBuildFingerprint": s(native_summary.get("native_build_fingerprint")),
        "nativeTemplateSha256": s(native_summary.get("source_v2_template_sha256")),
        "actionAuthorizationFingerprint": s(action_authorization.get("actionAuthorizationFingerprint")),
        "actionAuthorizationLedgerFingerprint": s(action_authorization.get("authorizationLedgerFingerprint")),
        "cutoverReadinessEvidenceFingerprint": evidence_fp,
        "cutoverAuthorizationLedgerFingerprint": ledger_fp,
    }
    if not lineage["period"] or not lineage["headSha"] or not lineage["stagingRunId"]:
        raise ValueError("Production Cutover Control run lineage is incomplete")

    readiness_rows = [{"name": key, "status": "PASS" if evidence[key]["ready"] else "BLOCKED", "detail": evidence[key]} for key in required_readiness]
    technical_pass = all(x["status"] == "PASS" for x in upstream_gates)
    evidence_pass = all(x["status"] == "PASS" for x in readiness_rows)

    plan_lineage = {k: v for k, v in lineage.items() if k != "cutoverAuthorizationLedgerFingerprint"}
    plan_core = {
        "mode": s(policy.get("mode")),
        "lineage": plan_lineage,
        "requiredReadinessChecks": required_readiness,
        "upstreamGates": upstream_gates,
        "legacyRollbackRepositorySurface": legacy_gate,
        "executorPolicy": policy.get("executor_boundary") or {},
        "rollbackPolicy": policy.get("rollback_drill") or {},
    }
    plan_fp = _sha(plan_core)
    authorization = _authorization_state(plan_fp, ledger_events)
    rollback_drill = build_rollback_drill(plan_fp, policy, legacy_gate=legacy_gate)

    if not technical_pass or not evidence_pass:
        status = "BLOCKED"
    elif authorization["state"] == "PENDING_CUTOVER_AUTHORIZATION":
        status = "READY_FOR_EXPLICIT_APPROVAL"
    elif authorization["state"] == "APPROVED_FOR_EXPLICIT_EXECUTION_MILESTONE":
        status = "APPROVED_NOT_EXECUTABLE"
    else:
        status = "BLOCKED"

    blockers = [x["name"] for x in upstream_gates if x["status"] != "PASS"]
    blockers += [x["name"] for x in readiness_rows if x["status"] != "PASS"]
    if authorization["state"] in {"REJECTED", "REVOKED"}:
        blockers.append("cutover_authorization_" + authorization["state"].lower())

    executor = dict(policy.get("executor_boundary") or {})
    result = {
        "status": status,
        "mode": s(policy.get("mode")),
        "cutoverPlanFingerprint": plan_fp,
        "readinessEvidenceFingerprint": evidence_fp,
        "cutoverAuthorizationLedgerFingerprint": ledger_fp,
        "lineage": lineage,
        "upstreamGates": upstream_gates,
        "readinessGates": readiness_rows,
        "blockers": blockers,
        "authorization": authorization,
        "rollbackDrill": rollback_drill,
        "executorBoundary": {
            "authenticatedExecutorRequired": True,
            "authenticatedExecutorBound": False,
            "executionEnabled": False,
            "dryRunOnly": True,
            "shortLivedSessionRequired": True,
            "maxSessionTtlSeconds": int(executor.get("max_session_ttl_seconds") or 0),
            "identityClaimsRequired": list(executor.get("identity_claims_required") or []),
            "prepareCommitSeparationRequired": True,
            "idempotencyKeyRequired": True,
            "auditTrailRequired": True,
            "rollbackPlanRequired": True,
            "postDeployVerificationRequired": True,
            "automaticCutoverEnabled": False,
            "automaticRollbackEnabled": False,
            "providerBindingEnabled": False,
            "platformMutationAllowed": False,
            "productionActivationEnabled": False,
            "executionPermitIssued": False,
            "futureExecutionIdempotencyKey": "cutover_exec_" + _sha({"plan": plan_fp, "head": s(head_sha)})[:24],
        },
        "safety": {
            "preproductionOnly": True,
            "productionCutoverAuthorized": False,
            "productionDataMartWritten": False,
            "productionUiModified": False,
            "productionDeploymentPerformed": False,
            "platformMutationAllowed": False,
            "authenticatedExecutorBound": False,
            "executionEnabled": False,
            "executionPermitIssued": False,
            "automaticCutoverEnabled": False,
            "automaticRollbackEnabled": False,
        },
    }
    result["productionCutoverControlFingerprint"] = _sha({
        "plan": plan_core,
        "planFingerprint": plan_fp,
        "readiness": readiness_rows,
        "authorization": authorization,
        "rollbackDrill": rollback_drill,
        "safety": result["safety"],
    })
    return result


def validate_production_cutover_control(value: Mapping[str, Any], *, contract: Mapping[str, Any]) -> Dict[str, Any]:
    policy = _policy(contract)
    checks: List[Dict[str, Any]] = []

    def ck(name: str, ok: bool, detail: Any = None) -> None:
        checks.append({"name": name, "status": "PASS" if ok else "FAIL", "detail": detail or {}})

    ck("status_known", s(value.get("status")) in {"BLOCKED", "READY_FOR_EXPLICIT_APPROVAL", "APPROVED_NOT_EXECUTABLE"})
    ck("control_fingerprint_present", bool(s(value.get("productionCutoverControlFingerprint"))))
    ck("plan_fingerprint_present", bool(s(value.get("cutoverPlanFingerprint"))))
    ck("readiness_fingerprint_present", bool(s(value.get("readinessEvidenceFingerprint"))))
    ck("authorization_ledger_fingerprint_present", bool(s(value.get("cutoverAuthorizationLedgerFingerprint"))))
    lineage = value.get("lineage") or {}
    ck("lineage_complete", all(bool(s(lineage.get(k))) for k in ("period", "headSha", "stagingRunId", "semanticFingerprint", "payloadBuildFingerprint", "nativeBuildFingerprint", "nativeTemplateSha256", "actionAuthorizationFingerprint", "actionAuthorizationLedgerFingerprint", "cutoverReadinessEvidenceFingerprint", "cutoverAuthorizationLedgerFingerprint")))
    upstream = list(value.get("upstreamGates") or [])
    ck("upstream_gates_present", bool(upstream) and all(s(x.get("status")) in {"PASS", "FAIL"} for x in upstream))
    readiness = list(value.get("readinessGates") or [])
    ck("readiness_gate_count", [s(x.get("name")) for x in readiness] == list(policy.get("required_readiness_checks") or []))
    ck("readiness_gate_states", all(s(x.get("status")) in {"PASS", "BLOCKED"} for x in readiness))

    authorization = value.get("authorization") or {}
    ck("authorization_state", s(authorization.get("state")) in {"PENDING_CUTOVER_AUTHORIZATION", "APPROVED_FOR_EXPLICIT_EXECUTION_MILESTONE", "REJECTED", "REVOKED"})
    ck("authorization_never_issues_permit", authorization.get("executionPermitIssued") is False and authorization.get("productionActivationEnabled") is False)

    drill = value.get("rollbackDrill") or {}
    ck("rollback_drill_simulation_only", s(drill.get("mode")) == "SIMULATION_ONLY")
    ck("rollback_drill_no_write", drill.get("productionWritePerformed") is False and drill.get("automaticRollbackEnabled") is False and drill.get("rollbackExecutionAuthorized") is False)
    ck("rollback_drill_steps", [s(x.get("step")) for x in drill.get("steps") or []] == list((policy.get("rollback_drill") or {}).get("required_steps") or []))

    executor = value.get("executorBoundary") or {}
    ck("executor_required", executor.get("authenticatedExecutorRequired") is True)
    ck("executor_unbound", executor.get("authenticatedExecutorBound") is False)
    ck("execution_disabled", executor.get("executionEnabled") is False and executor.get("dryRunOnly") is True)
    ck("short_lived_session_spec", executor.get("shortLivedSessionRequired") is True and int(executor.get("maxSessionTtlSeconds") or 0) == 900)
    ck("executor_claims", list(executor.get("identityClaimsRequired") or []) == list((policy.get("executor_boundary") or {}).get("identity_claims_required") or []))
    ck("executor_two_phase", executor.get("prepareCommitSeparationRequired") is True)
    ck("executor_audit_rollback", executor.get("idempotencyKeyRequired") is True and executor.get("auditTrailRequired") is True and executor.get("rollbackPlanRequired") is True and executor.get("postDeployVerificationRequired") is True)
    ck("no_platform_mutation", executor.get("providerBindingEnabled") is False and executor.get("platformMutationAllowed") is False)
    ck("no_production_activation", executor.get("productionActivationEnabled") is False and executor.get("executionPermitIssued") is False)
    ck("no_automatic_cutover", executor.get("automaticCutoverEnabled") is False and executor.get("automaticRollbackEnabled") is False)
    ck("future_idempotency_key", bool(s(executor.get("futureExecutionIdempotencyKey"))))

    safety = value.get("safety") or {}
    ck("preproduction_only", safety.get("preproductionOnly") is True)
    ck("production_untouched", all(safety.get(k) is False for k in ("productionCutoverAuthorized", "productionDataMartWritten", "productionUiModified", "productionDeploymentPerformed", "platformMutationAllowed", "authenticatedExecutorBound", "executionEnabled", "executionPermitIssued", "automaticCutoverEnabled", "automaticRollbackEnabled")))

    if s(value.get("status")) == "READY_FOR_EXPLICIT_APPROVAL":
        ck("ready_requires_all_gates", all(s(x.get("status")) == "PASS" for x in upstream) and all(s(x.get("status")) == "PASS" for x in readiness))
        ck("ready_not_preapproved", s(authorization.get("state")) == "PENDING_CUTOVER_AUTHORIZATION")
    if s(value.get("status")) == "APPROVED_NOT_EXECUTABLE":
        ck("approved_requires_all_gates", all(s(x.get("status")) == "PASS" for x in upstream) and all(s(x.get("status")) == "PASS" for x in readiness))
        ck("approved_state", s(authorization.get("state")) == "APPROVED_FOR_EXPLICIT_EXECUTION_MILESTONE")
        ck("approved_still_not_executable", executor.get("executionPermitIssued") is False and executor.get("executionEnabled") is False)

    failed = [x for x in checks if x["status"] == "FAIL"]
    return {"status": "PASS" if not failed else "FAIL", "failedCheckCount": len(failed), "checks": checks}


def build_cutover_authorization_event_command(control: Mapping[str, Any], *, action: str, authorized_by: str, authorized_at: str, note: str = "") -> Dict[str, Any]:
    if s(control.get("status")) not in {"READY_FOR_EXPLICIT_APPROVAL", "APPROVED_NOT_EXECUTABLE"}:
        raise ValueError("production cutover plan is not authorization-eligible")
    action = s(action).upper()
    authorized_by = s(authorized_by)
    authorized_at = s(authorized_at)
    note = s(note)
    if not authorized_by:
        raise ValueError("authorizedBy is required")
    _time(authorized_at)
    authorization = control.get("authorization") or {}
    available = [s(x) for x in authorization.get("availableActions") or []]
    if action not in available:
        raise ValueError(f"action {action!r} is not available for cutover authorization state {authorization.get('state')!r}")
    plan_fp = s(control.get("cutoverPlanFingerprint"))
    core = {"action": action, "cutoverPlanFingerprint": plan_fp, "authorizedAt": authorized_at, "authorizedBy": authorized_by, "note": note}
    event = {"eventId": "cutover_auth_evt_" + _sha(core)[:18], **core}
    return {
        "status": "READY_TO_APPLY",
        "expectedCutoverAuthorizationLedgerFingerprint": s(control.get("cutoverAuthorizationLedgerFingerprint")),
        "expectedCutoverPlanFingerprint": plan_fp,
        "event": event,
        "executionPermitIssued": False,
        "executionEnabled": False,
        "platformMutationAllowed": False,
        "productionActivationEnabled": False,
    }


def apply_cutover_authorization_event_command(authorization_ledger: Mapping[str, Any], *, command: Mapping[str, Any], expected_ledger_fingerprint: str, apply: bool = False) -> Dict[str, Any]:
    current_fp = cutover_authorization_ledger_fingerprint(authorization_ledger)
    expected = s(expected_ledger_fingerprint)
    if not expected or current_fp != expected:
        raise ValueError("stale production cutover authorization ledger fingerprint")
    if s(command.get("expectedCutoverAuthorizationLedgerFingerprint")) != expected:
        raise ValueError("command expected ledger fingerprint mismatch")
    event = dict(command.get("event") or {})
    if not event:
        raise ValueError("cutover authorization command event missing")
    if command.get("executionPermitIssued") is not False or command.get("executionEnabled") is not False:
        raise ValueError("cutover authorization command cannot enable execution")
    if command.get("platformMutationAllowed") is not False or command.get("productionActivationEnabled") is not False:
        raise ValueError("cutover authorization command cannot mutate production")
    if not apply:
        return {"status": "DRY_RUN", "currentLedgerFingerprint": current_fp, "event": event, "ledgerModified": False, "executionPermitIssued": False, "productionActivationEnabled": False}
    updated = {"version": s(authorization_ledger.get("version")), "ledger_name": s(authorization_ledger.get("ledger_name")), "events": list(authorization_ledger.get("events") or []) + [event]}
    _authorization_events(updated)
    return {"status": "APPLIED", "previousLedgerFingerprint": current_fp, "newLedgerFingerprint": cutover_authorization_ledger_fingerprint(updated), "ledger": updated, "ledgerModified": True, "executionPermitIssued": False, "productionActivationEnabled": False}


def bind_production_cutover_control_artifact(*, ads_output_dir: str | Path, native_output_dir: str | Path, output_dir: str | Path, contract_path: str | Path, readiness_evidence_path: str | Path, authorization_events_path: str | Path, repo_root: str | Path, period: str, head_sha: str, staging_run_id: str) -> Dict[str, Any]:
    ads_dir = Path(ads_output_dir)
    native_dir = Path(native_output_dir)
    out = Path(output_dir)
    contract = _read_json(contract_path)
    action_authorization = _read_json(ads_dir / "ads_action_authorization.json")
    native_summary = _read_json(native_dir.parent / f"multi_shop_native_v2_summary_{period}.json")
    readiness = _read_json(readiness_evidence_path)
    ledger = _read_json(authorization_events_path)
    control = build_production_cutover_control(action_authorization=action_authorization, native_summary=native_summary, readiness_evidence=readiness, authorization_ledger=ledger, contract=contract, repo_root=repo_root, period=period, head_sha=head_sha, staging_run_id=staging_run_id)
    qa = validate_production_cutover_control(control, contract=contract)
    if qa["status"] != "PASS":
        raise ValueError(f"Production Cutover Control QA failed: {qa['failedCheckCount']} checks")
    out.mkdir(parents=True, exist_ok=True)
    _write_json(out / "production_cutover_control.json", control)
    _write_json(out / "production_cutover_control_qa.json", qa)
    _write_json(out / "production_cutover_rollback_drill.json", control["rollbackDrill"])
    return {
        "status": "PASS",
        "productionCutoverControlStatus": control["status"],
        "productionCutoverControlFingerprint": control["productionCutoverControlFingerprint"],
        "cutoverPlanFingerprint": control["cutoverPlanFingerprint"],
        "readinessEvidenceFingerprint": control["readinessEvidenceFingerprint"],
        "cutoverAuthorizationLedgerFingerprint": control["cutoverAuthorizationLedgerFingerprint"],
        "blockerCount": len(control["blockers"]),
        "blockers": list(control["blockers"]),
        "rollbackDrillStatus": control["rollbackDrill"]["status"],
        "authenticatedExecutorBound": False,
        "executionEnabled": False,
        "executionPermitIssued": False,
        "platformMutationAllowed": False,
        "productionActivationEnabled": False,
        "qaStatus": qa["status"],
        "qaCheckCount": len(qa["checks"]),
        "qaFailedCheckCount": qa["failedCheckCount"],
    }
