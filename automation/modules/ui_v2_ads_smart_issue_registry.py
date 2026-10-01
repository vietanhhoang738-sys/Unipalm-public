"""Human-review Smart Issue Registry presentation wrapper for Ads Desk.

This layer is downstream of Smart Issue Candidate UI v1. It surfaces only the
backend human-review state attached to an eligible candidate. It does not add
interactive promotion controls and cannot create/transition an issue from the
static PREPRODUCTION template.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from . import ui_v2_ads_smart_issue_candidates as _candidate


ADS_SMART_ISSUE_REGISTRY_UI_VERSION = "ads-smart-issue-registry-ui-v1"

SMART_ISSUE_REGISTRY_STYLE = r"""
/* ads-smart-issue-registry-ui-v1 */
.ads-desk-review-state{display:inline-flex!important;width:max-content;margin-top:6px!important;padding:4px 7px;border-radius:6px;background:var(--soft);font-size:7.5px!important;font-weight:800!important;color:var(--muted)!important}
.ads-desk-review-state.issue{background:var(--green-bg);color:var(--green)!important}.ads-desk-review-state.reopen{color:var(--red)!important}.ads-desk-review-state.dismissed{color:var(--muted2)!important}
"""

_NEW_DESK_SUB = _candidate._NEW_DESK_SUB + " Smart Issue chỉ được mở hoặc đổi trạng thái sau một review event rõ ràng của operator; candidate không tự chuyển thành issue."


def _enhanced_registry_card() -> str:
    old = _candidate._enhanced_candidate_card()
    # Candidate UI already appends its own conditional badge before the card's
    # final closing div. Patch that stable outer-card terminator instead of the
    # older Persistence-specific `</span></div>` shape.
    needle = "+'</div>').join('')"
    if old.count(needle) != 1:
        raise ValueError("Smart Issue candidate card shape changed; Registry wrapper refused to patch")
    review = (
        "+(((sig.smartIssueCandidate||{}).eligible)?('<span class=\"ads-desk-review-state '+"
        "((((sig.smartIssueCandidate||{}).humanReview||{}).state==='LINKED_ISSUE')?'issue':((((sig.smartIssueCandidate||{}).humanReview||{}).state==='REOPEN_REVIEW_REQUIRED')?'reopen':((((sig.smartIssueCandidate||{}).humanReview||{}).state==='DISMISSED')?'dismissed':'')))+'\">'+"
        "esc(((((sig.smartIssueCandidate||{}).humanReview||{}).state==='LINKED_ISSUE')?('Issue · '+((((sig.smartIssueCandidate||{}).humanReview||{}).issueState||'OPEN'))):((((sig.smartIssueCandidate||{}).humanReview||{}).state==='REOPEN_REVIEW_REQUIRED')?'Cần review mở lại':((((sig.smartIssueCandidate||{}).humanReview||{}).state==='DEFERRED')?'Đã hoãn':((((sig.smartIssueCandidate||{}).humanReview||{}).state==='DISMISSED')?'Đã bỏ qua':'Chờ review')))))+"
        "'</span>'):'')+'</div>').join('')"
    )
    return old.replace(needle, review)


def registry_runtime_from_candidate(runtime: str) -> str:
    old_card = _candidate._enhanced_candidate_card()
    new_card = _enhanced_registry_card()
    if old_card not in runtime:
        raise ValueError("Smart Issue candidate runtime shape changed; Registry wrapper refused to patch")
    runtime = runtime.replace(old_card, new_card)
    if _candidate._NEW_DESK_SUB not in runtime:
        raise ValueError("Smart Issue candidate Desk copy changed; Registry wrapper refused to patch")
    return runtime.replace(_candidate._NEW_DESK_SUB, _NEW_DESK_SUB)


def effective_smart_issue_registry_runtime(entity_map: Mapping[str, Any]) -> str:
    return registry_runtime_from_candidate(_candidate.effective_smart_issue_candidate_runtime(entity_map))


def _validate_registry_artifact(output_dir: Any) -> None:
    html = (Path(output_dir) / "command_center_v2_multi_shop_native_template.html").read_text(encoding="utf-8")
    required = (
        ADS_SMART_ISSUE_REGISTRY_UI_VERSION,
        "Ứng viên Smart Issue chỉ được đánh dấu khi tín hiệu đã xác nhận còn đủ mới và đủ lớn để đáng xem xét vận hành.",
        "Smart Issue chỉ được mở hoặc đổi trạng thái sau một review event rõ ràng của operator; candidate không tự chuyển thành issue.",
        "Chờ review",
        "Đã hoãn",
        "Đã bỏ qua",
        "Cần review mở lại",
        "humanReview",
        ".ads-desk-review-state{",
    )
    missing = [token for token in required if token not in html]
    if missing:
        raise ValueError(f"Smart Issue Registry UI artifact checks missing: {missing}")
    forbidden = (
        "const rawSignals=snap.signals||[]",
        "autoPromoteSmartIssue",
        "Tự động mở Smart Issue",
        "Tự động xử lý",
        "Tự động cảnh báo",
    )
    leaked = [token for token in forbidden if token in html]
    if leaked:
        raise ValueError(f"unsafe Smart Issue Registry presentation leaked: {leaked}")


def build_native_v2_multi_shop(*, payload_dir: Any, v2_template_path: Any, output_dir: Any):
    original_transform = _candidate.smart_issue_runtime_from_persistence
    original_style = _candidate.SMART_ISSUE_CANDIDATE_STYLE

    def transform_with_registry(persistence_runtime: str) -> str:
        return registry_runtime_from_candidate(original_transform(persistence_runtime))

    _candidate.smart_issue_runtime_from_persistence = transform_with_registry
    _candidate.SMART_ISSUE_CANDIDATE_STYLE = original_style + "\n" + SMART_ISSUE_REGISTRY_STYLE
    try:
        result = _candidate.build_native_v2_multi_shop(
            payload_dir=payload_dir,
            v2_template_path=v2_template_path,
            output_dir=output_dir,
        )
        _validate_registry_artifact(output_dir)
        result["adsSmartIssueRegistryUiReady"] = True
        result["adsSmartIssueRegistryUiVersion"] = ADS_SMART_ISSUE_REGISTRY_UI_VERSION
        result["adsSmartIssueHumanReviewEnabled"] = True
        result["adsHumanPromotedSmartIssuesEnabled"] = True
        result["adsSmartIssuesEnabled"] = True
        result["adsSmartIssueAutomaticAlertsEnabled"] = False
        result["adsSmartIssueAutomaticActionsEnabled"] = False
        return result
    finally:
        _candidate.smart_issue_runtime_from_persistence = original_transform
        _candidate.SMART_ISSUE_CANDIDATE_STYLE = original_style
