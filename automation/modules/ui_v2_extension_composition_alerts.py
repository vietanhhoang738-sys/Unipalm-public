"""Canonical Native V2 composition v1.2 with read-only Alert Policy UI.

Composition v1.1 remains immutable. This additive layer binds the validated
Alert Policy sidecar only at the Native presentation boundary while preserving
one base compatibility bridge and one Native build.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Mapping, Tuple

from . import ui_v2_extension_composition_canonical as _previous
from . import ui_v2_ads_alert_policy as _alert

NATIVE_EXTENSION_COMPOSITION_VERSION = "native-v2-extension-composition-v1.2"
EXTENSION_ORDER = _previous.EXTENSION_ORDER + ("ads_smart_issue_alert_policy",)
BASE_COMPATIBILITY_BRIDGE_COUNT = _previous.BASE_COMPATIBILITY_BRIDGE_COUNT
PLAN = _previous._base.NativeExtensionPlan(
    version=NATIVE_EXTENSION_COMPOSITION_VERSION,
    extension_ids=EXTENSION_ORDER,
    native_patch_version=_previous.PLAN.native_patch_version,
    compatibility_bridge_count=BASE_COMPATIBILITY_BRIDGE_COUNT,
)


def lineage_markers() -> Tuple[str, ...]:
    return (NATIVE_EXTENSION_COMPOSITION_VERSION,) + _previous.lineage_markers() + (
        _alert.ADS_SMART_ISSUE_ALERT_POLICY_UI_VERSION,
    )


def lineage_comment() -> str:
    lines = ["/* UNIPALM_NATIVE_EXTENSION_LINEAGE_V12"]
    lines.extend(f" * {marker}" for marker in lineage_markers())
    lines.append(" */")
    return "\n".join(lines)


def compose_effective_style() -> str:
    return _previous.compose_effective_style() + "\n" + _alert.ALERT_POLICY_STYLE


def compose_effective_runtime(payload: Mapping[str, Any]) -> str:
    return (
        lineage_comment()
        + "\n"
        + _previous.compose_effective_runtime(payload)
        + "\n"
        + _alert.ALERT_POLICY_RUNTIME
    )


def _validate_lineage_artifact(output_dir: Any) -> None:
    html = (Path(output_dir) / "command_center_v2_multi_shop_native_template.html").read_text(encoding="utf-8")
    required = ("UNIPALM_NATIVE_EXTENSION_LINEAGE_V12",) + lineage_markers()
    missing = [token for token in required if token not in html]
    if missing:
        raise ValueError(f"Native v1.2 extension lineage markers missing: {missing}")


def build_native_v2_multi_shop(
    *,
    payload_dir: Any,
    v2_template_path: Any,
    output_dir: Any,
    review_workflow_path: Any,
    review_console_contract_path: Any,
    alert_policy_path: Any,
    alert_policy_ui_contract_path: Any,
) -> Dict[str, Any]:
    payload_path = Path(payload_dir) / "ui_payload.json"
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    base = _previous._base
    base._product._validate_product_payload(payload)
    base._ads._validate_ads_payload(payload)

    review_workflow = _previous._review_console.load_review_workflow_for_console(
        workflow_path=review_workflow_path,
        payload=payload,
        contract_path=review_console_contract_path,
    )
    alert_policy = _alert.load_alert_policy_for_ui(
        alert_policy_path=alert_policy_path,
        payload=payload,
        review_workflow=review_workflow,
        contract_path=alert_policy_ui_contract_path,
    )

    style = compose_effective_style()
    runtime = compose_effective_runtime(payload)
    native = base._native
    original_bundle = native._bundle_from_payload
    original_style = native.NATIVE_STYLE
    original_runtime = native.NATIVE_RUNTIME
    original_version = native.NATIVE_PATCH_VERSION

    if original_bundle is not base._BASE_BUNDLE_FROM_PAYLOAD:
        raise ValueError("Native base bundle adapter was already patched before v1.2 composition")

    def bundle_with_alert_policy(source_payload: Mapping[str, Any]) -> Dict[str, Any]:
        bundle = base._bundle_with_extensions(source_payload)
        bundle["smartIssueReviewWorkflow"] = review_workflow
        bundle["smartIssueAlertPolicy"] = alert_policy
        return bundle

    native._bundle_from_payload = bundle_with_alert_policy
    native.NATIVE_STYLE = style
    native.NATIVE_RUNTIME = runtime
    native.NATIVE_PATCH_VERSION = PLAN.native_patch_version
    try:
        result = native.build_native_v2_multi_shop(
            payload_dir=payload_dir,
            v2_template_path=v2_template_path,
            output_dir=output_dir,
        )
    finally:
        native._bundle_from_payload = original_bundle
        native.NATIVE_STYLE = original_style
        native.NATIVE_RUNTIME = original_runtime
        native.NATIVE_PATCH_VERSION = original_version

    if result.get("nativePatchVersion") != PLAN.native_patch_version:
        raise ValueError("composed Native patch version missing from v1.2 lineage")

    base._operator._validate_semantic_artifact(output_dir)
    base._product._validate_product_artifact(output_dir)
    base._short._validate_v36_artifact(output_dir)
    base._ads._validate_ads_artifact(output_dir)
    base._polish._validate_polished_artifact(output_dir)
    base._diagnosis._validate_dynamic_diagnosis_artifact(output_dir)
    base._persistence._validate_persistence_artifact(output_dir)
    base._candidate._validate_smart_issue_candidate_artifact(output_dir)
    base._registry._validate_registry_artifact(output_dir)
    base._validate_composition_artifact(output_dir)
    _previous._review_console._validate_review_console_artifact(output_dir)
    _previous._validate_lineage_artifact(output_dir)
    _alert._validate_alert_policy_artifact(output_dir)
    _validate_lineage_artifact(output_dir)

    product_map = base._short.build_short_name_map(payload)
    ads_map = base._ads.build_ads_short_name_map(payload)
    result.update({
        "nativeExtensionCompositionReady": True,
        "nativeExtensionCompositionVersion": PLAN.version,
        "nativeExtensionIds": list(PLAN.extension_ids),
        "nativeExtensionCompatibilityBridgeCount": PLAN.compatibility_bridge_count,
        "nativeExtensionLineageReady": True,
        "nativeExtensionLineageMarkers": list(lineage_markers()),
        "legacyNestedWrapperBuildPathUsed": False,
        "productDestinationReady": True,
        "productShortNameReady": True,
        "productShortNameRuleVersion": base._short.RULE_VERSION,
        "productShortNameShopCount": len(product_map),
        "adsDestinationReady": True,
        "adsShortNameShopCount": len(ads_map),
        "adsFinancialUiReady": True,
        "adsFinancialPolishReady": True,
        "adsFinancialPolishVersion": base._polish.ADS_FINANCIAL_POLISH_VERSION,
        "adsFinancialOperatorLanguageReady": True,
        "adsEntityScopeReady": True,
        "adsGroupRuleVersion": base._financial.ADS_GROUP_RULE_VERSION,
        "adsDynamicDiagnosisUiReady": True,
        "adsDynamicDiagnosisUiVersion": base._diagnosis.ADS_DYNAMIC_DIAGNOSIS_UI_VERSION,
        "adsDiagnosisConsumesQualifiedSignalsOnly": True,
        "adsDiagnosisPersistenceUiReady": True,
        "adsDiagnosisPersistenceUiVersion": base._persistence.ADS_DIAGNOSIS_PERSISTENCE_UI_VERSION,
        "adsSmartIssueCandidateUiReady": True,
        "adsSmartIssueCandidateUiVersion": base._candidate.ADS_SMART_ISSUE_CANDIDATE_UI_VERSION,
        "adsSmartIssueRegistryUiReady": True,
        "adsSmartIssueRegistryUiVersion": base._registry.ADS_SMART_ISSUE_REGISTRY_UI_VERSION,
        "adsSmartIssueReviewConsoleUiReady": True,
        "adsSmartIssueReviewConsoleUiVersion": _previous._review_console.ADS_SMART_ISSUE_REVIEW_CONSOLE_UI_VERSION,
        "adsSmartIssueReviewConsoleReadOnly": True,
        "adsSmartIssueReviewWorkflowFingerprint": review_workflow["workflowFingerprint"],
        "adsSmartIssueOperatorLedgerFingerprint": review_workflow["operatorLedgerFingerprint"],
        "adsSmartIssueReviewQueueCount": review_workflow["reviewQueueCount"],
        "adsSmartIssueReviewIssueCount": review_workflow["issueCount"],
        "adsSmartIssueAlertPolicyUiReady": True,
        "adsSmartIssueAlertPolicyUiVersion": _alert.ADS_SMART_ISSUE_ALERT_POLICY_UI_VERSION,
        "adsSmartIssueAlertPolicyReadOnly": True,
        "adsSmartIssueAlertPolicyFingerprint": alert_policy["alertPolicyFingerprint"],
        "adsSmartIssueAlertDeliveryLedgerFingerprint": alert_policy["deliveryLedgerFingerprint"],
        "adsSmartIssueEligibleAlertCount": alert_policy["eligibleAlertCount"],
        "adsSmartIssueSuppressedAlertIssueCount": alert_policy["suppressedIssueCount"],
        "adsSmartIssueAlertDeliveryEnabled": False,
        "adsSmartIssueAlertAutomaticDeliveryEnabled": False,
        "adsSmartIssueAlertProviderBindingEnabled": False,
        "adsSmartIssueHumanReviewEnabled": True,
        "adsHumanPromotedSmartIssuesEnabled": True,
        "adsSmartIssueCandidatesEnabled": True,
        "adsSmartIssuesEnabled": True,
        "adsSmartIssueAutomaticAlertsEnabled": False,
        "adsSmartIssueAutomaticActionsEnabled": False,
    })
    return result
