import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from modules.production_readiness_hardening import (
    bind_production_readiness_artifact,
    build_production_readiness_hardening,
    build_release_candidate_html,
    rehearse_deployment_and_rollback,
    validate_production_readiness_hardening,
)


ROOT = Path(__file__).resolve().parents[2]


class ProductionReadinessHardeningTest(unittest.TestCase):
    def _contract(self):
        return json.loads((ROOT / "config/production_readiness_hardening_contract.json").read_text(encoding="utf-8"))

    def _native_summary(self):
        return {
            "status": "PASS",
            "native_v2_ready": True,
            "selected_shop_count": 2,
            "native_extension_composition_version": "native-v2-extension-composition-v1.3",
            "native_extension_ids": ["base", "ads_action_authorization"],
            "source_semantic_fingerprint": "semantic-fp",
            "source_payload_build_fingerprint": "payload-fp",
            "native_build_fingerprint": "native-fp",
            "source_v2_template_sha256": "template-sha",
            "ads_action_authorization_ui_ready": True,
            "ads_action_authorization_read_only": True,
            "ads_action_authorization_execution_enabled": False,
            "ads_action_authorization_platform_mutation_allowed": False,
            "ads_action_authorization_production_activation_enabled": False,
            "safety": {
                "productionCutoverAuthorized": False,
                "productionDataMartWritten": False,
                "productionDeploymentPerformed": False,
                "productionIndexModified": False,
            },
        }

    def _html(self):
        return """<!doctype html><html><head><title>Native</title></head><body>
<script>window.UNIPALM_SCOPE_BUNDLE={};window.UNIPALM_NATIVE_SCOPE={};</script>
<!-- native-v2-extension-composition-v1.3 -->
<!-- ads-action-authorization-ui-v1 -->
</body></html>"""

    def _probe(self, protected=False):
        return {
            "observedAt": "2026-10-01T12:00:00+07:00",
            "legacyCompileStatus": "PASS",
            "legacyDependencyTestsStatus": "PASS",
            "legacySourceProcessorDryRunStatus": "PASS",
            "legacySourceProcessorProductionWritePerformed": False,
            "legacyReliableEnd": "2026-09-30",
            "configurationValidationStatus": "PASS",
            "readOnlyProductionSourceAccessStatus": "PASS",
            "secretValuesPersisted": False,
            "productionUrlHealthStatus": "PASS",
            "successfulHttpProbes": 3,
            "productionHttpStatus": 200,
            "exactCurrentBuildMarkerPresent": True,
            "productionBranch": "main",
            "mainBranchProtected": protected,
            "serverSideDirectPushRestricted": protected,
        }

    def _build(self, *, probe=None, html=None, contract=None):
        return build_production_readiness_hardening(
            native_summary=self._native_summary(),
            native_html=html or self._html(),
            production_baseline_bytes=b"<html><head><meta name='unipalm-build' content='legacy'></head><body>legacy</body></html>",
            external_probe=probe or self._probe(False),
            contract=contract or self._contract(),
            period="2026-09",
            source_run_id="36811937549",
            source_head_sha="648c38a8d0adf7efb5c42ae759ab666fb62ac713",
        )

    def test_seven_objective_gates_pass_but_unprotected_main_blocks_governance_gate(self):
        value = self._build()
        self.assertEqual(value["status"], "BLOCKED_EXTERNAL_GOVERNANCE")
        self.assertEqual(value["passCount"], 7)
        self.assertEqual(value["blockedCount"], 1)
        blocked = [x for x in value["checks"] if x["status"] == "BLOCKED"]
        self.assertEqual([x["name"] for x in blocked], ["repository_deployment_guard_verified"])
        self.assertFalse(blocked[0]["evidenceCandidate"]["ready"])
        qa = validate_production_readiness_hardening(value, contract=self._contract())
        self.assertEqual(qa["status"], "PASS")

    def test_protected_main_allows_readiness_candidate_to_reach_cutover_control_reevaluation(self):
        value = self._build(probe=self._probe(True))
        self.assertEqual(value["status"], "READY_FOR_CUTOVER_CONTROL_REEVALUATION")
        self.assertEqual(value["passCount"], 8)
        self.assertEqual(value["blockedCount"], 0)
        self.assertTrue(all(x["evidenceCandidate"]["ready"] for x in value["checks"]))

    def test_release_candidate_is_deterministic_and_injects_monitoring_lineage(self):
        kwargs = dict(period="2026-09", source_run_id="1", source_head_sha="abc")
        a = build_release_candidate_html(self._html(), self._native_summary(), **kwargs)
        b = build_release_candidate_html(self._html(), self._native_summary(), **kwargs)
        self.assertEqual(a["releaseCandidateFingerprint"], b["releaseCandidateFingerprint"])
        self.assertEqual(a["releaseCandidateSha256"], b["releaseCandidateSha256"])
        for name in ("unipalm-release-candidate", "unipalm-native-build", "unipalm-semantic-build", "unipalm-cutover-source-run"):
            self.assertIn(f'name="{name}"', a["html"])

    def test_isolated_rehearsal_restores_exact_legacy_baseline(self):
        value = rehearse_deployment_and_rollback(baseline_bytes=b"legacy", candidate_bytes=b"candidate")
        self.assertEqual(value["status"], "PASS")
        self.assertTrue(value["candidateByteVerified"])
        self.assertTrue(value["rollbackExactBaselineHashVerified"])
        self.assertFalse(value["repositoryWritePerformed"])
        self.assertFalse(value["productionWritePerformed"])
        self.assertEqual(value["baselineSha256"], value["restoredBaselineSha256"])

    def test_network_runtime_primitive_blocks_static_data_and_ui_binding(self):
        value = self._build(html=self._html().replace("</body>", "<script>fetch('/api')</script></body>"))
        states = {x["name"]: x["status"] for x in value["checks"]}
        self.assertEqual(states["production_data_binding_validated"], "BLOCKED")
        self.assertEqual(states["production_ui_binding_validated"], "BLOCKED")
        self.assertEqual(states["deployment_dry_run_validated"], "BLOCKED")
        self.assertEqual(value["status"], "BLOCKED_READINESS")

    def test_legacy_runtime_or_monitor_failure_stays_blocked(self):
        probe = self._probe(True)
        probe["legacySourceProcessorDryRunStatus"] = "FAIL"
        probe["productionUrlHealthStatus"] = "FAIL"
        probe["successfulHttpProbes"] = 1
        value = self._build(probe=probe)
        states = {x["name"]: x["status"] for x in value["checks"]}
        self.assertEqual(states["legacy_rollback_runtime_verified"], "BLOCKED")
        self.assertEqual(states["monitoring_readiness_validated"], "BLOCKED")
        self.assertEqual(value["status"], "BLOCKED_READINESS")

    def test_unsafe_contract_cannot_enable_production_activation(self):
        contract = deepcopy(self._contract())
        contract["production_readiness_hardening"]["production_activation_enabled"] = True
        with self.assertRaisesRegex(ValueError, "cannot activate production"):
            self._build(contract=contract)

    def test_binding_writes_only_preproduction_evidence_package(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            native = root / "native"
            (native / "2026-09").mkdir(parents=True)
            (native / "multi_shop_native_v2_summary_2026-09.json").write_text(json.dumps(self._native_summary()), encoding="utf-8")
            (native / "2026-09" / "command_center_v2_multi_shop_native_template.html").write_text(self._html(), encoding="utf-8")
            baseline = root / "baseline.html"
            baseline.write_text("<html><head></head><body>legacy</body></html>", encoding="utf-8")
            probe = root / "probe.json"
            probe.write_text(json.dumps(self._probe(False)), encoding="utf-8")
            out = root / "out"
            result = bind_production_readiness_artifact(
                native_summary_path=native / "multi_shop_native_v2_summary_2026-09.json",
                native_html_path=native / "2026-09" / "command_center_v2_multi_shop_native_template.html",
                production_baseline_path=baseline,
                external_probe_path=probe,
                contract_path=ROOT / "config/production_readiness_hardening_contract.json",
                output_dir=out,
                period="2026-09",
                source_run_id="36811937549",
                source_head_sha="648c38a",
            )
            self.assertEqual(result["status"], "PASS")
            self.assertTrue((out / "release_candidate_index.html").exists())
            self.assertTrue((out / "production_readiness_hardening.json").exists())
            self.assertTrue((out / "production_cutover_evidence_candidate.json").exists())
            artifact = result["artifact"]
            self.assertFalse(artifact["safety"]["productionWritePerformed"])
            self.assertFalse(artifact["safety"]["repositoryWritePerformed"])
            self.assertFalse(artifact["safety"]["productionDeploymentPerformed"])


if __name__ == "__main__":
    unittest.main()
