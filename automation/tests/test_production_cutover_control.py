import copy
import json
import tempfile
import unittest
from pathlib import Path

from modules.production_cutover_control import (
    apply_cutover_authorization_event_command,
    build_cutover_authorization_event_command,
    build_production_cutover_control,
    cutover_authorization_ledger_fingerprint,
    validate_production_cutover_control,
)


ROOT = Path(__file__).resolve().parents[2]


def load_contract():
    return json.loads((ROOT / "config/production_cutover_control_contract.json").read_text(encoding="utf-8"))


def action_authorization():
    return {
        "status": "READY_EMPTY",
        "actionAuthorizationFingerprint": "aa-fp",
        "authorizationLedgerFingerprint": "aa-ledger-fp",
        "executionBoundary": {
            "authenticatedExecutorRequired": True,
            "authenticatedExecutorBound": False,
            "executionEnabled": False,
            "dryRunOnly": True,
            "providerBindingEnabled": False,
            "platformMutationAllowed": False,
            "productionActivationEnabled": False,
        },
        "safety": {
            "automaticExecutionEnabled": False,
            "platformMutationAllowed": False,
            "productionActivationEnabled": False,
        },
    }


def native_summary():
    return {
        "status": "PASS",
        "native_v2_ready": True,
        "native_extension_composition_ready": True,
        "native_extension_composition_version": "native-v2-extension-composition-v1.3",
        "native_extension_compatibility_bridge_count": 1,
        "legacy_nested_wrapper_build_path_used": False,
        "native_extension_ids": ["ads_action_authorization"],
        "ads_action_authorization_ui_ready": True,
        "ads_action_authorization_read_only": True,
        "ads_action_authorization_fingerprint": "aa-fp",
        "ads_action_authorization_authenticated_executor_bound": False,
        "ads_action_authorization_execution_enabled": False,
        "ads_action_authorization_provider_binding_enabled": False,
        "ads_action_authorization_platform_mutation_allowed": False,
        "ads_action_authorization_production_activation_enabled": False,
        "selected_shop_count": 2,
        "source_payload_build_fingerprint": "payload-fp",
        "source_semantic_fingerprint": "semantic-fp",
        "native_build_fingerprint": "native-fp",
        "source_v2_template_sha256": "template-sha",
        "safety": {
            "productionCutoverAuthorized": False,
            "productionDataMartWritten": False,
            "productionDeploymentPerformed": False,
            "productionIndexModified": False,
            "productionV2TemplateModified": False,
        },
    }


def readiness(contract, ready=False):
    checks = {}
    for name in contract["cutover_control"]["required_readiness_checks"]:
        checks[name] = {
            "ready": ready,
            "evidence": f"evidence:{name}" if ready else "",
            "reviewedBy": "operator@example.com" if ready else "",
            "reviewedAt": "2026-10-01T12:00:00+07:00" if ready else "",
        }
    return {"version": "1.0", "evidence_name": "production_cutover_readiness_evidence", "checks": checks}


def empty_ledger():
    return {"version": "1.0", "ledger_name": "production_cutover_authorization_events", "events": []}


class ProductionCutoverControlTest(unittest.TestCase):
    def setUp(self):
        self.contract = load_contract()
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        for rel in self.contract["cutover_control"]["required_legacy_repository_paths"]:
            p = self.repo / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("retained", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def build(self, evidence=None, ledger=None, head="head-a"):
        return build_production_cutover_control(
            action_authorization=action_authorization(),
            native_summary=native_summary(),
            readiness_evidence=evidence or readiness(self.contract, False),
            authorization_ledger=ledger or empty_ledger(),
            contract=self.contract,
            repo_root=self.repo,
            period="2026-09",
            head_sha=head,
            staging_run_id="run-1",
        )

    def test_current_false_evidence_blocks_without_weakening_safety(self):
        value = self.build()
        self.assertEqual(value["status"], "BLOCKED")
        self.assertEqual(len(value["blockers"]), 8)
        self.assertEqual(value["rollbackDrill"]["status"], "DRY_RUN_PASS")
        self.assertFalse(value["executorBoundary"]["authenticatedExecutorBound"])
        self.assertFalse(value["executorBoundary"]["executionEnabled"])
        self.assertFalse(value["executorBoundary"]["executionPermitIssued"])
        self.assertFalse(value["executorBoundary"]["platformMutationAllowed"])
        self.assertFalse(value["executorBoundary"]["productionActivationEnabled"])
        qa = validate_production_cutover_control(value, contract=self.contract)
        self.assertEqual(qa["status"], "PASS", qa)

    def test_all_readiness_evidence_reaches_explicit_approval_gate_only(self):
        value = self.build(evidence=readiness(self.contract, True))
        self.assertEqual(value["status"], "READY_FOR_EXPLICIT_APPROVAL")
        self.assertEqual(value["authorization"]["state"], "PENDING_CUTOVER_AUTHORIZATION")
        self.assertFalse(value["authorization"]["executionPermitIssued"])
        self.assertFalse(value["safety"]["productionCutoverAuthorized"])

    def test_approval_is_record_only_and_still_non_executable(self):
        base = self.build(evidence=readiness(self.contract, True))
        ledger = empty_ledger()
        current_fp = cutover_authorization_ledger_fingerprint(ledger)
        command = build_cutover_authorization_event_command(
            base,
            action="APPROVE_CUTOVER_PLAN",
            authorized_by="operator@example.com",
            authorized_at="2026-10-01T12:05:00+07:00",
            note="Approve plan for a future explicit execution milestone only",
        )
        dry = apply_cutover_authorization_event_command(
            ledger, command=command, expected_ledger_fingerprint=current_fp, apply=False
        )
        self.assertEqual(dry["status"], "DRY_RUN")
        self.assertFalse(dry["ledgerModified"])
        applied = apply_cutover_authorization_event_command(
            ledger, command=command, expected_ledger_fingerprint=current_fp, apply=True
        )
        approved = self.build(evidence=readiness(self.contract, True), ledger=applied["ledger"])
        self.assertEqual(approved["status"], "APPROVED_NOT_EXECUTABLE")
        self.assertEqual(approved["authorization"]["state"], "APPROVED_FOR_EXPLICIT_EXECUTION_MILESTONE")
        self.assertFalse(approved["executorBoundary"]["executionPermitIssued"])
        self.assertFalse(approved["executorBoundary"]["executionEnabled"])
        self.assertFalse(approved["safety"]["productionCutoverAuthorized"])

    def test_authorization_is_bound_to_exact_plan_fingerprint(self):
        base = self.build(evidence=readiness(self.contract, True), head="head-a")
        ledger = empty_ledger()
        fp = cutover_authorization_ledger_fingerprint(ledger)
        command = build_cutover_authorization_event_command(
            base,
            action="APPROVE_CUTOVER_PLAN",
            authorized_by="operator@example.com",
            authorized_at="2026-10-01T12:05:00+07:00",
        )
        applied = apply_cutover_authorization_event_command(ledger, command=command, expected_ledger_fingerprint=fp, apply=True)
        changed = self.build(evidence=readiness(self.contract, True), ledger=applied["ledger"], head="head-b")
        self.assertNotEqual(changed["cutoverPlanFingerprint"], base["cutoverPlanFingerprint"])
        self.assertEqual(changed["status"], "READY_FOR_EXPLICIT_APPROVAL")
        self.assertEqual(changed["authorization"]["state"], "PENDING_CUTOVER_AUTHORIZATION")

    def test_stale_cutover_ledger_fails_closed(self):
        base = self.build(evidence=readiness(self.contract, True))
        ledger = empty_ledger()
        command = build_cutover_authorization_event_command(
            base,
            action="APPROVE_CUTOVER_PLAN",
            authorized_by="operator@example.com",
            authorized_at="2026-10-01T12:05:00+07:00",
        )
        with self.assertRaisesRegex(ValueError, "stale production cutover authorization ledger"):
            apply_cutover_authorization_event_command(
                ledger, command=command, expected_ledger_fingerprint="stale", apply=True
            )

    def test_missing_legacy_rollback_surface_blocks_drill_and_cutover(self):
        missing = self.repo / self.contract["cutover_control"]["required_legacy_repository_paths"][0]
        missing.unlink()
        value = self.build(evidence=readiness(self.contract, True))
        self.assertEqual(value["status"], "BLOCKED")
        self.assertIn("legacy_rollback_repository_surface", value["blockers"])
        self.assertEqual(value["rollbackDrill"]["status"], "BLOCKED")
        self.assertFalse(value["rollbackDrill"]["productionWritePerformed"])

    def test_ready_evidence_requires_review_metadata(self):
        evidence = readiness(self.contract, True)
        key = self.contract["cutover_control"]["required_readiness_checks"][0]
        evidence["checks"][key]["reviewedBy"] = ""
        with self.assertRaisesRegex(ValueError, "ready cutover evidence requires"):
            self.build(evidence=evidence)

    def test_unsafe_contract_cannot_bind_executor(self):
        contract = copy.deepcopy(self.contract)
        contract["cutover_control"]["executor_boundary"]["authenticated_executor_bound"] = True
        with self.assertRaisesRegex(ValueError, "executor must remain unbound"):
            build_production_cutover_control(
                action_authorization=action_authorization(),
                native_summary=native_summary(),
                readiness_evidence=readiness(contract, False),
                authorization_ledger=empty_ledger(),
                contract=contract,
                repo_root=self.repo,
                period="2026-09",
                head_sha="head-a",
                staging_run_id="run-1",
            )

    def test_native_mutation_regression_blocks_instead_of_being_normalized(self):
        native = native_summary()
        native["safety"]["productionDeploymentPerformed"] = True
        value = build_production_cutover_control(
            action_authorization=action_authorization(),
            native_summary=native,
            readiness_evidence=readiness(self.contract, True),
            authorization_ledger=empty_ledger(),
            contract=self.contract,
            repo_root=self.repo,
            period="2026-09",
            head_sha="head-a",
            staging_run_id="run-1",
        )
        self.assertEqual(value["status"], "BLOCKED")
        self.assertIn("native_production_safety", value["blockers"])


if __name__ == "__main__":
    unittest.main()
