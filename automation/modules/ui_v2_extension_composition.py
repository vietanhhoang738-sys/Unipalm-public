"""Explicit Native V2 extension composition for PREPRODUCTION.

The canonical runner uses one ordered composition plan instead of recursively
calling presentation wrappers that temporarily monkey-patch each other.
Existing wrapper modules remain as locked compatibility/reference surfaces.

The base ui_v2_native builder does not yet accept injected style/runtime/bundle
hooks, so v1 uses exactly one temporary compatibility bridge at that base
boundary. All globals are restored in ``finally`` and every locked downstream
artifact validator is reused after the build.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Mapping, Tuple

from . import ui_v2_native as _native
from . import ui_v2_native_review as _review
from . import ui_v2_operator_copy_review as _operator
from . import ui_v2_product_destination as _product
from . import ui_v2_product_compact_signals as _compact
from . import ui_v2_product_short_names as _short
from . import ui_v2_ads_destination as _ads
from . import ui_v2_ads_financial as _financial
from . import ui_v2_ads_financial_polish as _polish
from . import ui_v2_ads_dynamic_diagnosis as _diagnosis
from . import ui_v2_ads_diagnosis_persistence as _persistence
from . import ui_v2_ads_smart_issue_candidates as _candidate
from . import ui_v2_ads_smart_issue_registry as _registry


NATIVE_EXTENSION_COMPOSITION_VERSION = "native-v2-extension-composition-v1"
BASE_COMPATIBILITY_BRIDGE_COUNT = 1

# Capture the immutable base bundle adapter before the single compatibility
# bridge is installed. Calling _native._bundle_from_payload from inside the
# bridged function would recurse after reassignment.
_BASE_BUNDLE_FROM_PAYLOAD = _native._bundle_from_payload

EXTENSION_ORDER: Tuple[str, ...] = (
    "intelligence_first_operator_copy",
    "product_destination",
    "product_compact_signals",
    "product_short_names",
    "ads_destination",
    "ads_financial",
    "ads_dynamic_diagnosis",
    "ads_diagnosis_persistence",
    "ads_smart_issue_candidate",
    "ads_smart_issue_registry",
)


@dataclass(frozen=True)
class NativeExtensionPlan:
    version: str
    extension_ids: Tuple[str, ...]
    native_patch_version: str
    compatibility_bridge_count: int


PLAN = NativeExtensionPlan(
    version=NATIVE_EXTENSION_COMPOSITION_VERSION,
    extension_ids=EXTENSION_ORDER,
    native_patch_version=_financial.ADS_FINANCIAL_PATCH_VERSION,
    compatibility_bridge_count=BASE_COMPATIBILITY_BRIDGE_COUNT,
)


def _bundle_with_extensions(payload: Mapping[str, Any]) -> Dict[str, Any]:
    """Add Product and Ads destinations at one governed bundle boundary."""
    base = _BASE_BUNDLE_FROM_PAYLOAD(payload)
    destinations = payload.get("destinations") or {}
    base["productDestination"] = destinations.get("product") or {}
    base["adsDestination"] = destinations.get("ads") or {}
    return base


def _operator_runtime() -> str:
    """Return Intelligence-first runtime with locked operator-language polish."""
    return _operator._polish_runtime(_review.INTELLIGENCE_FIRST_RUNTIME)


def compose_effective_style() -> str:
    """Compose style contributions in deterministic dependency order."""
    style = _review._patched_style(_native.NATIVE_STYLE)
    contributions = (
        _product.PRODUCT_STYLE,
        _compact.COMPACT_SIGNAL_STYLE,
        _short.SHORT_NAME_STYLE,
        _ads.ADS_STYLE,
        _polish.effective_financial_style(),
        _diagnosis.DIAGNOSIS_STYLE,
        _persistence.PERSISTENCE_STYLE,
        _candidate.SMART_ISSUE_CANDIDATE_STYLE,
        _registry.SMART_ISSUE_REGISTRY_STYLE,
    )
    return style + "\n" + "\n".join(contributions)


def _integrated_signal_card() -> str:
    """Render the final Ads Desk card without chained card-string wrappers."""
    return (
        "signals.map(sig=>'<div class=\"ads-desk-signal '+(sig.kind==='PROBLEM'?'problem':'opportunity')+'\'>"
        "<b>'+esc(sig.headline||entityRecords[String(sig.productId)]?.displayName||sig.productName||'Sản phẩm chưa xác định')+'</b>"
        "<span>'+esc(sig.summary||'')+'</span>"
        "<span>'+esc(sig.reviewFocus||'')+'</span>"
        "<span class=\"ads-desk-priority\">'+esc(sig.operatorType||'Tín hiệu')+' · Ưu tiên '+"
        "esc(sig.priorityTier==='HIGH'?'cao':(sig.priorityTier==='MEDIUM'?'vừa':'theo dõi'))+' · Độ tin cậy '+"
        "esc(sig.confidenceTier==='HIGH'?'cao':(sig.confidenceTier==='MEDIUM'?'vừa':'thấp'))+'</span>"
        "<span class=\"ads-desk-persistence '+"
        "(((sig.persistence||{}).state==='CONFIRMED')?'confirmed':"
        "(((sig.persistence||{}).state==='CONFLICTED')?'conflicted':"
        "(((sig.persistence||{}).state==='FIRST_OBSERVATION')?'first':'')))+'\">'+"
        "esc(((sig.persistence||{}).state==='CONFIRMED'?'Đã xác nhận':"
        "((sig.persistence||{}).state==='CONFLICTED'?'Mâu thuẫn':"
        "((sig.persistence||{}).state==='ONE_OFF'?'Một lần':"
        "((sig.persistence||{}).state==='FIRST_OBSERVATION'?'Lần đầu':'Chưa đánh giá'))))+' · '+"
        "String((sig.persistence||{}).supportWindowCount||0)+'/'+"
        "String((sig.persistence||{}).eligibleIndependentWindowCount||0)+' cửa sổ')+'</span>'+"
        "((sig.smartIssueCandidate||{}).eligible?'<span class=\"ads-desk-smart-candidate '+"
        "(sig.kind==='PROBLEM'?'risk':'opportunity')+'\">Ứng viên Smart Issue · '+"
        "esc(((sig.smartIssueCandidate||{}).lifecycleState==='CONTINUING'?'Đang tiếp diễn':"
        "((sig.smartIssueCandidate||{}).lifecycleState==='REOPENED'?'Mở lại':'Mới'))+' · '+"
        "String((sig.smartIssueCandidate||{}).evidenceAgeDays||0)+' ngày</span>':'')+"
        "(((sig.smartIssueCandidate||{}).eligible)?('<span class=\"ads-desk-review-state '+"
        "((((sig.smartIssueCandidate||{}).humanReview||{}).state==='LINKED_ISSUE')?'issue':"
        "((((sig.smartIssueCandidate||{}).humanReview||{}).state==='REOPEN_REVIEW_REQUIRED')?'reopen':"
        "((((sig.smartIssueCandidate||{}).humanReview||{}).state==='DISMISSED')?'dismissed':'')))+'\">'+"
        "esc(((((sig.smartIssueCandidate||{}).humanReview||{}).state==='LINKED_ISSUE')?"
        "('Issue · '+((((sig.smartIssueCandidate||{}).humanReview||{}).issueState||'OPEN'))):"
        "((((sig.smartIssueCandidate||{}).humanReview||{}).state==='REOPEN_REVIEW_REQUIRED')?'Cần review mở lại':"
        "((((sig.smartIssueCandidate||{}).humanReview||{}).state==='DEFERRED')?'Đã hoãn':"
        "((((sig.smartIssueCandidate||{}).humanReview||{}).state==='DISMISSED')?'Đã bỏ qua':'Chờ review')))))+"
        "'</span>'):'')+'</div>').join('')"
    )


def _integrated_signal_section_end() -> str:
    card = _integrated_signal_card()
    return (
        "+(signals.length?'<div class=\"ads-desk-signals\">'+"
        + card
        + "+'</div>':'<div class=\"ads-desk-gate\"><b>'+"
        "esc(diag.status==='NO_MATERIAL_DIAGNOSIS'?'Chưa có chẩn đoán nổi bật':'Chẩn đoán đang được khóa')+"
        "'</b><span>'+esc(diag.reason||'Chưa đủ bằng chứng để tạo chẩn đoán cho kỳ đang chọn.')+'</span></div>')+'</section>';"
    )


def _polish_financial_runtime(runtime: str) -> str:
    replacements = (
        ("Ads Spend", "Chi tiêu Ads"),
        ("Spend share", "Tỷ trọng chi tiêu"),
        ("Cần đủ 30 ngày trusted history.", "Cần đủ 30 ngày dữ liệu Ads đã xác thực."),
        ("Chưa đủ baseline 1M", "Chưa đủ mốc so sánh 1M"),
        ("Intelligence chỉ tóm tắt evidence đã có.", "Intelligence chỉ tóm tắt bằng chứng đã có."),
        ("EVIDENCE ONLY", "THAM KHẢO"),
    )
    for source, target in replacements:
        runtime = runtime.replace(source, target)
    return runtime


def compose_integrated_financial_runtime(entity_map: Mapping[str, Any]) -> str:
    """Compose Diagnosis/Persistence/Candidate/Registry into one Desk slot."""
    runtime = _financial._financial_runtime(entity_map)
    replacements = (
        (_diagnosis._RAW_SIGNAL_BINDING, _diagnosis._DIAGNOSIS_SIGNAL_BINDING),
        (_diagnosis._OLD_DESK_SUB, _registry._NEW_DESK_SUB),
        (_diagnosis._OLD_SIGNAL_SECTION_END, _integrated_signal_section_end()),
    )
    for source, target in replacements:
        count = runtime.count(source)
        if count != 1:
            raise ValueError(
                f"Ads Financial Desk slot changed; expected one anchor, found {count}"
            )
        runtime = runtime.replace(source, target, 1)
    if _diagnosis._RAW_SIGNAL_BINDING in runtime:
        raise ValueError("raw Ads signal binding leaked into composed Desk")
    return _polish_financial_runtime(runtime)


def compose_effective_runtime(payload: Mapping[str, Any]) -> str:
    product_map = _short.build_short_name_map(payload)
    ads_map = _ads.build_ads_short_name_map(payload)
    entity_map = _financial.build_ads_entity_map(payload)
    snippets = (
        _native.NATIVE_RUNTIME,
        _operator_runtime(),
        _product.PRODUCT_RUNTIME,
        _compact.COMPACT_SIGNAL_RUNTIME,
        f"/* {_short.RULE_VERSION} */\n" + _short._runtime_for_map(product_map),
        _ads._ads_runtime(ads_map),
        compose_integrated_financial_runtime(entity_map),
    )
    return "\n".join(snippets)


def _validate_composition_artifact(output_dir: Any) -> None:
    html = (
        Path(output_dir) / "command_center_v2_multi_shop_native_template.html"
    ).read_text(encoding="utf-8")
    required = (
        "intelligenceBrief",
        "product-short-name",
        "Ads Intelligence Desk",
        "Chẩn đoán chỉ xuất hiện khi hai kỳ có bối cảnh bán hàng tương đồng.",
        "Độ bền chỉ được xác nhận bằng các cửa sổ độc lập cùng scope và cùng bối cảnh.",
        "Ứng viên Smart Issue chỉ được đánh dấu khi tín hiệu đã xác nhận còn đủ mới và đủ lớn để đáng xem xét vận hành.",
        "Smart Issue chỉ được mở hoặc đổi trạng thái sau một review event rõ ràng của operator; candidate không tự chuyển thành issue.",
        "humanReview",
    )
    missing = [token for token in required if token not in html]
    if missing:
        raise ValueError(f"Native extension composition artifact checks missing: {missing}")
    forbidden = (
        "const rawSignals=snap.signals||[]",
        "autoPromoteSmartIssue",
        "Tự động mở Smart Issue",
    )
    leaked = [token for token in forbidden if token in html]
    if leaked:
        raise ValueError(f"unsafe Native extension composition leaked: {leaked}")


def build_native_v2_multi_shop(
    *, payload_dir: Any, v2_template_path: Any, output_dir: Any
) -> Dict[str, Any]:
    """Canonical Native build using one explicit extension composition plan."""
    payload_path = Path(payload_dir) / "ui_payload.json"
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    _product._validate_product_payload(payload)
    _ads._validate_ads_payload(payload)

    style = compose_effective_style()
    runtime = compose_effective_runtime(payload)

    original_bundle = _native._bundle_from_payload
    original_style = _native.NATIVE_STYLE
    original_runtime = _native.NATIVE_RUNTIME
    original_version = _native.NATIVE_PATCH_VERSION

    if original_bundle is not _BASE_BUNDLE_FROM_PAYLOAD:
        raise ValueError("Native base bundle adapter was already patched before composition")

    _native._bundle_from_payload = _bundle_with_extensions
    _native.NATIVE_STYLE = style
    _native.NATIVE_RUNTIME = runtime
    _native.NATIVE_PATCH_VERSION = PLAN.native_patch_version
    try:
        result = _native.build_native_v2_multi_shop(
            payload_dir=payload_dir,
            v2_template_path=v2_template_path,
            output_dir=output_dir,
        )
    finally:
        _native._bundle_from_payload = original_bundle
        _native.NATIVE_STYLE = original_style
        _native.NATIVE_RUNTIME = original_runtime
        _native.NATIVE_PATCH_VERSION = original_version

    if result.get("nativePatchVersion") != PLAN.native_patch_version:
        raise ValueError("composed Native patch version missing from lineage")

    # Reuse locked validators, but never call the nested wrapper builders.
    _operator._validate_semantic_artifact(output_dir)
    _product._validate_product_artifact(output_dir)
    _short._validate_v36_artifact(output_dir)
    _ads._validate_ads_artifact(output_dir)
    _polish._validate_polished_artifact(output_dir)
    _diagnosis._validate_dynamic_diagnosis_artifact(output_dir)
    _persistence._validate_persistence_artifact(output_dir)
    _candidate._validate_smart_issue_candidate_artifact(output_dir)
    _registry._validate_registry_artifact(output_dir)
    _validate_composition_artifact(output_dir)

    product_map = _short.build_short_name_map(payload)
    ads_map = _ads.build_ads_short_name_map(payload)
    result.update(
        {
            "nativeExtensionCompositionReady": True,
            "nativeExtensionCompositionVersion": PLAN.version,
            "nativeExtensionIds": list(PLAN.extension_ids),
            "nativeExtensionCompatibilityBridgeCount": PLAN.compatibility_bridge_count,
            "legacyNestedWrapperBuildPathUsed": False,
            "productDestinationReady": True,
            "productShortNameReady": True,
            "productShortNameRuleVersion": _short.RULE_VERSION,
            "productShortNameShopCount": len(product_map),
            "adsDestinationReady": True,
            "adsShortNameShopCount": len(ads_map),
            "adsFinancialUiReady": True,
            "adsFinancialPolishReady": True,
            "adsFinancialPolishVersion": _polish.ADS_FINANCIAL_POLISH_VERSION,
            "adsFinancialOperatorLanguageReady": True,
            "adsEntityScopeReady": True,
            "adsGroupRuleVersion": _financial.ADS_GROUP_RULE_VERSION,
            "adsDynamicDiagnosisUiReady": True,
            "adsDynamicDiagnosisUiVersion": _diagnosis.ADS_DYNAMIC_DIAGNOSIS_UI_VERSION,
            "adsDiagnosisConsumesQualifiedSignalsOnly": True,
            "adsDiagnosisPersistenceUiReady": True,
            "adsDiagnosisPersistenceUiVersion": _persistence.ADS_DIAGNOSIS_PERSISTENCE_UI_VERSION,
            "adsSmartIssueCandidateUiReady": True,
            "adsSmartIssueCandidateUiVersion": _candidate.ADS_SMART_ISSUE_CANDIDATE_UI_VERSION,
            "adsSmartIssueRegistryUiReady": True,
            "adsSmartIssueRegistryUiVersion": _registry.ADS_SMART_ISSUE_REGISTRY_UI_VERSION,
            "adsSmartIssueHumanReviewEnabled": True,
            "adsHumanPromotedSmartIssuesEnabled": True,
            "adsSmartIssueCandidatesEnabled": True,
            "adsSmartIssuesEnabled": True,
            "adsSmartIssueAutomaticAlertsEnabled": False,
            "adsSmartIssueAutomaticActionsEnabled": False,
        }
    )
    return result
