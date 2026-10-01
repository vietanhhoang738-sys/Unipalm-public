"""Canonical Native V2 extension composition with explicit lineage provenance.

The locked v1 base composition remains unchanged. This canonical additive v1.1
adds the read-only Smart Issue Review Console from the operator workflow sidecar
while preserving exactly one base-Native compatibility bridge.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Mapping, Tuple

from . import ui_v2_extension_composition as _base
from . import ui_v2_ads_smart_issue_review_console as _review_console


NATIVE_EXTENSION_COMPOSITION_VERSION = "native-v2-extension-composition-v1.1"
EXTENSION_ORDER = _base.EXTENSION_ORDER + ("ads_smart_issue_review_console",)
BASE_COMPATIBILITY_BRIDGE_COUNT = _base.BASE_COMPATIBILITY_BRIDGE_COUNT
PLAN = _base.NativeExtensionPlan(
    version=NATIVE_EXTENSION_COMPOSITION_VERSION,
    extension_ids=EXTENSION_ORDER,
    native_patch_version=_base.PLAN.native_patch_version,
    compatibility_bridge_count=BASE_COMPATIBILITY_BRIDGE_COUNT,
)


def lineage_markers() -> Tuple[str, ...]:
    """Return deterministic version provenance for every composed UI layer."""
    return (
        NATIVE_EXTENSION_COMPOSITION_VERSION,
        _base.NATIVE_EXTENSION_COMPOSITION_VERSION,
        _base._product.PRODUCT_NATIVE_PATCH_VERSION,
        _base._compact.PRODUCT_COMPACT_SIGNAL_PATCH_VERSION,
        _base._short.PRODUCT_SHORT_NAME_PATCH_VERSION,
        _base._short.RULE_VERSION,
        _base._ads.ADS_NATIVE_PATCH_VERSION,
        _base._financial.ADS_FINANCIAL_PATCH_VERSION,
        _base._polish.ADS_FINANCIAL_POLISH_VERSION,
        _base._diagnosis.ADS_DYNAMIC_DIAGNOSIS_UI_VERSION,
        _base._persistence.ADS_DIAGNOSIS_PERSISTENCE_UI_VERSION,
        _base._candidate.ADS_SMART_ISSUE_CANDIDATE_UI_VERSION,
        _base._registry.ADS_SMART_ISSUE_REGISTRY_UI_VERSION,
        _review_console.ADS_SMART_ISSUE_REVIEW_CONSOLE_UI_VERSION,
    )


def lineage_comment() -> str:
    lines = ["/* UNIPALM_NATIVE_EXTENSION_LINEAGE"]
    lines.extend(f" * {marker}" for marker in lineage_markers())
    lines.append(" */")
    return "\n".join(lines)


def compose_effective_style() -> str:
    return _base.compose_effective_style() + "\n" + _review_console.REVIEW_CONSOLE_STYLE


def compose_effective_runtime(payload: Mapping[str, Any]) -> str:
    """Compose locked v1 runtime + read-only console + explicit provenance."""
    return (
        lineage_comment()
        + "\n"
        + _base.compose_effective_runtime(payload)
        + "\n"
        + _review_console.REVIEW_CONSOLE_RUNTIME
    )


def _validate_lineage_artifact(output_dir: Any) -> None:
    html = (
        Path(output_dir) / "command_center_v2_multi_shop_native_template.html"
    ).read_text(encoding="utf-8")
    required = ("UNIPALM_NATIVE_EXTENSION_LINEAGE",) + lineage_markers()
    missing = [token for token in required if token not in html]
    if missing:
        raise ValueError(f"Native extension lineage markers missing: {missing}")


def build_native_v2_multi_shop(
    *,
    payload_dir: Any,
    v2_template_path: Any,
    output_dir: Any,
    review_workflow_path: Any,
    review_console_contract_path: Any,
) -> Dict[str, Any]:
    """Build Native V2 once through one explicit ordered composition boundary."""
    payload_path = Path(payload_dir) / "ui_payload.json"
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    _base._product._validate_product_payload(payload)
    _base._ads._validate_ads_payload(payload)
    review_workflow = _review_console.load_review_workflow_for_console(
        workflow_path=review_workflow_path,
        payload=payload,
        contract_path=review_console_contract_path,
    )

    style = compose_effective_style()
    runtime = compose_effective_runtime(payload)

    native = _base._native
    original_bundle = native._bundle_from_payload
    original_style = native.NATIVE_STYLE
    original_runtime = native.NATIVE_RUNTIME
    original_version = native.NATIVE_PATCH_VERSION

    if original_bundle is not _base._BASE_BUNDLE_FROM_PAYLOAD:
        raise ValueError("Native base bundle adapter was already patched before composition")

    def bundle_with_review_console(source_payload: Mapping[str, Any]) -> Dict[str, Any]:
        bundle = _base._bundle_with_extensions(source_payload)
        bundle["smartIssueReviewWorkflow"] = review_workflow
        return bundle

    native._bundle_from_payload = bundle_with_review_console
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
        raise ValueError("composed Native patch version missing from lineage")

    _base._operator._validate_semantic_artifact(output_dir)
    _base._product._validate_product_artifact(output_dir)
    _base._short._validate_v36_artifact(output_dir)
    _base._ads._validate_ads_artifact(output_dir)
    _base._polish._validate_polished_artifact(output_dir)
    _base._diagnosis._validate_dynamic_diagnosis_artifact(output_dir)
    _base._persistence._validate_persistence_artifact(output_dir)
    _base._candidate._validate_smart_issue_candidate_artifact(output_dir)
    _base._registry._validate_registry_artifact(output_dir)
    _base._validate_composition_artifact(output_dir)
    _review_console._validate_review_console_artifact(output_dir)
    _validate_lineage_artifact(output_dir)

    product_map = _base._short.build_short_name_map(payload)
    ads_map = _base._ads.build_ads_short_name_map(payload)
    result.update(
        {
            "nativeExtensionCompositionReady": True,
            "nativeExtensionCompositionVersion": PLAN.version,
            "nativeExtensionIds": list(PLAN.extension_ids),
            "nativeExtensionCompatibilityBridgeCount": PLAN.compatibility_bridge_count,
            "nativeExtensionLineageReady": True,
            "nativeExtensionLineageMarkers": list(lineage_markers()),
            "legacyNestedWrapperBuildPathUsed": False,
            "productDestinationReady": True,
            "productShortNameReady": True,
            "productShortNameRuleVersion": _base._short.RULE_VERSION,
            "productShortNameShopCount": len(product_map),
            "adsDestinationReady": True,
            "adsShortNameShopCount": len(ads_map),
            "adsFinancialUiReady": True,
            "adsFinancialPolishReady": True,
            "adsFinancialPolishVersion": _base._polish.ADS_FINANCIAL_POLISH_VERSION,
            "adsFinancialOperatorLanguageReady": True,
            "adsEntityScopeReady": True,
            "adsGroupRuleVersion": _base._financial.ADS_GROUP_RULE_VERSION,
            "adsDynamicDiagnosisUiReady": True,
            "adsDynamicDiagnosisUiVersion": _base._diagnosis.ADS_DYNAMIC_DIAGNOSIS_UI_VERSION,
            "adsDiagnosisConsumesQualifiedSignalsOnly": True,
            "adsDiagnosisPersistenceUiReady": True,
            "adsDiagnosisPersistenceUiVersion": _base._persistence.ADS_DIAGNOSIS_PERSISTENCE_UI_VERSION,
            "adsSmartIssueCandidateUiReady": True,
            "adsSmartIssueCandidateUiVersion": _base._candidate.ADS_SMART_ISSUE_CANDIDATE_UI_VERSION,
            "adsSmartIssueRegistryUiReady": True,
            "adsSmartIssueRegistryUiVersion": _base._registry.ADS_SMART_ISSUE_REGISTRY_UI_VERSION,
            "adsSmartIssueReviewConsoleUiReady": True,
            "adsSmartIssueReviewConsoleUiVersion": _review_console.ADS_SMART_ISSUE_REVIEW_CONSOLE_UI_VERSION,
            "adsSmartIssueReviewConsoleReadOnly": True,
            "adsSmartIssueReviewWorkflowFingerprint": review_workflow["workflowFingerprint"],
            "adsSmartIssueOperatorLedgerFingerprint": review_workflow["operatorLedgerFingerprint"],
            "adsSmartIssueReviewQueueCount": review_workflow["reviewQueueCount"],
            "adsSmartIssueReviewIssueCount": review_workflow["issueCount"],
            "adsSmartIssueHumanReviewEnabled": True,
            "adsHumanPromotedSmartIssuesEnabled": True,
            "adsSmartIssueCandidatesEnabled": True,
            "adsSmartIssuesEnabled": True,
            "adsSmartIssueAutomaticAlertsEnabled": False,
            "adsSmartIssueAutomaticActionsEnabled": False,
        }
    )
    return result
