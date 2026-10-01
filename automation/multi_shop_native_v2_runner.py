#!/usr/bin/env python3
"""Build native V2-derived multi-shop PREPRODUCTION template."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from modules.ui_v2_extension_composition_action_authorization import build_native_v2_multi_shop


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--month",required=True)
    ap.add_argument("--payload-dir",default="payload_artifacts")
    ap.add_argument("--ads-intelligence-dir",default="ads_intelligence_artifacts")
    ap.add_argument("--review-console-contract",default="config/ads_smart_issue_review_console_contract.json")
    ap.add_argument("--alert-policy-ui-contract",default="config/ads_alert_policy_ui_contract.json")
    ap.add_argument("--action-authorization-ui-contract",default="config/ads_action_authorization_ui_contract.json")
    ap.add_argument("--output-dir",default="native_v2_artifacts")
    ap.add_argument("--v2-template",default="automation/command_center_v2_template.html")
    args=ap.parse_args()

    if not re.fullmatch(r"\d{4}-\d{2}",args.month):
        raise ValueError("--month must be YYYY-MM")

    out=Path(args.output_dir)/args.month
    ads_dir=Path(args.ads_intelligence_dir)/args.month
    workflow_path=ads_dir/"ads_smart_issue_review_workflow.json"
    alert_policy_path=ads_dir/"ads_alert_policy.json"
    action_authorization_path=ads_dir/"ads_action_authorization.json"
    result=build_native_v2_multi_shop(
        payload_dir=Path(args.payload_dir)/args.month,
        v2_template_path=args.v2_template,
        output_dir=out,
        review_workflow_path=workflow_path,
        review_console_contract_path=args.review_console_contract,
        alert_policy_path=alert_policy_path,
        alert_policy_ui_contract_path=args.alert_policy_ui_contract,
        action_authorization_path=action_authorization_path,
        action_authorization_ui_contract_path=args.action_authorization_ui_contract,
    )

    root=Path(args.output_dir)
    root.mkdir(parents=True,exist_ok=True)
    summary={
        "status":"PASS",
        "period":args.month,
        "native_v2_ready":True,
        "native_extension_composition_ready":bool(result.get("nativeExtensionCompositionReady")),
        "native_extension_composition_version":result.get("nativeExtensionCompositionVersion"),
        "native_extension_ids":result.get("nativeExtensionIds") or [],
        "native_extension_compatibility_bridge_count":result.get("nativeExtensionCompatibilityBridgeCount"),
        "native_extension_lineage_ready":bool(result.get("nativeExtensionLineageReady")),
        "native_extension_lineage_markers":result.get("nativeExtensionLineageMarkers") or [],
        "legacy_nested_wrapper_build_path_used":bool(result.get("legacyNestedWrapperBuildPathUsed")),
        "product_destination_ready":bool(result.get("productDestinationReady")),
        "product_short_name_ready":bool(result.get("productShortNameReady")),
        "product_short_name_rule_version":result.get("productShortNameRuleVersion"),
        "ads_destination_ready":bool(result.get("adsDestinationReady")),
        "ads_financial_ui_ready":bool(result.get("adsFinancialUiReady")),
        "ads_financial_polish_ready":bool(result.get("adsFinancialPolishReady")),
        "ads_financial_polish_version":result.get("adsFinancialPolishVersion"),
        "ads_entity_scope_ready":bool(result.get("adsEntityScopeReady")),
        "ads_group_rule_version":result.get("adsGroupRuleVersion"),
        "ads_dynamic_diagnosis_ui_ready":bool(result.get("adsDynamicDiagnosisUiReady")),
        "ads_dynamic_diagnosis_ui_version":result.get("adsDynamicDiagnosisUiVersion"),
        "ads_diagnosis_consumes_qualified_signals_only":bool(result.get("adsDiagnosisConsumesQualifiedSignalsOnly")),
        "ads_diagnosis_persistence_ui_ready":bool(result.get("adsDiagnosisPersistenceUiReady")),
        "ads_diagnosis_persistence_ui_version":result.get("adsDiagnosisPersistenceUiVersion"),
        "ads_smart_issue_candidate_ui_ready":bool(result.get("adsSmartIssueCandidateUiReady")),
        "ads_smart_issue_candidate_ui_version":result.get("adsSmartIssueCandidateUiVersion"),
        "ads_smart_issue_registry_ui_ready":bool(result.get("adsSmartIssueRegistryUiReady")),
        "ads_smart_issue_registry_ui_version":result.get("adsSmartIssueRegistryUiVersion"),
        "ads_smart_issue_review_console_ui_ready":bool(result.get("adsSmartIssueReviewConsoleUiReady")),
        "ads_smart_issue_review_console_ui_version":result.get("adsSmartIssueReviewConsoleUiVersion"),
        "ads_smart_issue_review_console_read_only":bool(result.get("adsSmartIssueReviewConsoleReadOnly")),
        "ads_smart_issue_review_workflow_fingerprint":result.get("adsSmartIssueReviewWorkflowFingerprint"),
        "ads_smart_issue_operator_ledger_fingerprint":result.get("adsSmartIssueOperatorLedgerFingerprint"),
        "ads_smart_issue_review_queue_count":result.get("adsSmartIssueReviewQueueCount"),
        "ads_smart_issue_review_issue_count":result.get("adsSmartIssueReviewIssueCount"),
        "ads_smart_issue_alert_policy_ui_ready":bool(result.get("adsSmartIssueAlertPolicyUiReady")),
        "ads_smart_issue_alert_policy_ui_version":result.get("adsSmartIssueAlertPolicyUiVersion"),
        "ads_smart_issue_alert_policy_read_only":bool(result.get("adsSmartIssueAlertPolicyReadOnly")),
        "ads_smart_issue_alert_policy_fingerprint":result.get("adsSmartIssueAlertPolicyFingerprint"),
        "ads_smart_issue_alert_delivery_ledger_fingerprint":result.get("adsSmartIssueAlertDeliveryLedgerFingerprint"),
        "ads_smart_issue_eligible_alert_count":result.get("adsSmartIssueEligibleAlertCount"),
        "ads_smart_issue_suppressed_alert_issue_count":result.get("adsSmartIssueSuppressedAlertIssueCount"),
        "ads_smart_issue_alert_delivery_enabled":bool(result.get("adsSmartIssueAlertDeliveryEnabled")),
        "ads_smart_issue_alert_automatic_delivery_enabled":bool(result.get("adsSmartIssueAlertAutomaticDeliveryEnabled")),
        "ads_smart_issue_alert_provider_binding_enabled":bool(result.get("adsSmartIssueAlertProviderBindingEnabled")),
        "ads_action_authorization_ui_ready":bool(result.get("adsActionAuthorizationUiReady")),
        "ads_action_authorization_ui_version":result.get("adsActionAuthorizationUiVersion"),
        "ads_action_authorization_read_only":bool(result.get("adsActionAuthorizationReadOnly")),
        "ads_action_authorization_fingerprint":result.get("adsActionAuthorizationFingerprint"),
        "ads_action_authorization_ledger_fingerprint":result.get("adsActionAuthorizationLedgerFingerprint"),
        "ads_action_authorization_proposal_count":result.get("adsActionAuthorizationProposalCount"),
        "ads_action_authorization_suppressed_issue_count":result.get("adsActionAuthorizationSuppressedIssueCount"),
        "ads_action_authorization_state_counts":result.get("adsActionAuthorizationStateCounts") or {},
        "ads_action_authorization_authenticated_executor_bound":bool(result.get("adsActionAuthorizationAuthenticatedExecutorBound")),
        "ads_action_authorization_execution_enabled":bool(result.get("adsActionAuthorizationExecutionEnabled")),
        "ads_action_authorization_provider_binding_enabled":bool(result.get("adsActionAuthorizationProviderBindingEnabled")),
        "ads_action_authorization_platform_mutation_allowed":bool(result.get("adsActionAuthorizationPlatformMutationAllowed")),
        "ads_action_authorization_production_activation_enabled":bool(result.get("adsActionAuthorizationProductionActivationEnabled")),
        "ads_smart_issue_human_review_enabled":bool(result.get("adsSmartIssueHumanReviewEnabled")),
        "ads_human_promoted_smart_issues_enabled":bool(result.get("adsHumanPromotedSmartIssuesEnabled")),
        "ads_smart_issue_candidates_enabled":bool(result.get("adsSmartIssueCandidatesEnabled")),
        "ads_smart_issues_enabled":bool(result.get("adsSmartIssuesEnabled")),
        "ads_smart_issue_automatic_alerts_enabled":bool(result.get("adsSmartIssueAutomaticAlertsEnabled")),
        "ads_smart_issue_automatic_actions_enabled":bool(result.get("adsSmartIssueAutomaticActionsEnabled")),
        "source_payload_build_fingerprint":result["sourcePayloadBuildFingerprint"],
        "source_semantic_fingerprint":result["sourceSemanticFingerprint"],
        "source_v2_template_sha256":result["sourceV2TemplateSha256"],
        "native_patch_version":result["nativePatchVersion"],
        "v2_compatibility_patch_version":result["v2CompatibilityPatchVersion"],
        "native_build_fingerprint":result["nativeBuildFingerprint"],
        "selected_shop_count":result["selectedShopCount"],
        "compare_pair_count":result["comparePairCount"],
        "safety":result["safety"],
    }
    (root/f"multi_shop_native_v2_summary_{args.month}.json").write_text(
        json.dumps(summary,ensure_ascii=False,indent=2,sort_keys=True),
        encoding="utf-8",
    )
    print(json.dumps(summary,ensure_ascii=False))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
