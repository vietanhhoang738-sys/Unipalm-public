"""Smart Issue candidate presentation wrapper for the validated Ads Desk.

This layer is downstream of Diagnosis Persistence UI v1. It only marks an Ads
Diagnosis card when the backend candidate policy says it is eligible. It does
not create a Smart Issue, alert or action.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from . import ui_v2_ads_diagnosis_persistence as _persistence


ADS_SMART_ISSUE_CANDIDATE_UI_VERSION = "ads-smart-issue-candidate-ui-v1"

SMART_ISSUE_CANDIDATE_STYLE = r"""
/* ads-smart-issue-candidate-ui-v1 */
.ads-desk-smart-candidate{display:inline-flex!important;width:max-content;margin-top:6px!important;padding:4px 7px;border:1px solid var(--line);border-radius:6px;background:var(--surface);font-size:7.5px!important;font-weight:800!important;color:var(--text)!important}
.ads-desk-smart-candidate.risk{color:var(--red)!important}.ads-desk-smart-candidate.opportunity{color:var(--green)!important}
"""

_NEW_DESK_SUB = _persistence._NEW_DESK_SUB + " Ứng viên Smart Issue chỉ được đánh dấu khi tín hiệu đã xác nhận còn đủ mới và đủ lớn để đáng xem xét vận hành."


def _enhanced_candidate_card() -> str:
    old = _persistence._enhanced_signal_card()
    needle = "</span></div>').join('')"
    if needle not in old:
        raise ValueError("Diagnosis Persistence signal card shape changed; Smart Issue wrapper refused to patch")
    replacement = (
        "</span>'+((sig.smartIssueCandidate||{}).eligible?'<span class=\"ads-desk-smart-candidate '+"
        "(sig.kind==='PROBLEM'?'risk':'opportunity')+'\">Ứng viên Smart Issue · '+"
        "esc(((sig.smartIssueCandidate||{}).lifecycleState==='CONTINUING'?'Đang tiếp diễn':((sig.smartIssueCandidate||{}).lifecycleState==='REOPENED'?'Mở lại':'Mới')))+"
        "' · '+String((sig.smartIssueCandidate||{}).evidenceAgeDays||0)+' ngày</span>':'')+'</div>').join('')"
    )
    return old.replace(needle, replacement)


def smart_issue_runtime_from_persistence(runtime: str) -> str:
    old_card = _persistence._enhanced_signal_card()
    new_card = _enhanced_candidate_card()
    if old_card not in runtime:
        raise ValueError("Diagnosis Persistence runtime shape changed; Smart Issue wrapper refused to patch")
    runtime = runtime.replace(old_card, new_card)
    if _persistence._NEW_DESK_SUB not in runtime:
        raise ValueError("Diagnosis Persistence Desk copy changed; Smart Issue wrapper refused to patch")
    runtime = runtime.replace(_persistence._NEW_DESK_SUB, _NEW_DESK_SUB)
    return runtime


def effective_smart_issue_candidate_runtime(entity_map: Mapping[str, Any]) -> str:
    return smart_issue_runtime_from_persistence(_persistence.effective_persistence_runtime(entity_map))


def _validate_smart_issue_candidate_artifact(output_dir: Any) -> None:
    html = (Path(output_dir) / "command_center_v2_multi_shop_native_template.html").read_text(encoding="utf-8")
    required = (
        ADS_SMART_ISSUE_CANDIDATE_UI_VERSION,
        "Chẩn đoán chỉ xuất hiện khi hai kỳ có bối cảnh bán hàng tương đồng.",
        "Độ bền chỉ được xác nhận bằng các cửa sổ độc lập cùng scope và cùng bối cảnh.",
        "Ứng viên Smart Issue chỉ được đánh dấu khi tín hiệu đã xác nhận còn đủ mới và đủ lớn để đáng xem xét vận hành.",
        "Ứng viên Smart Issue",
        "smartIssueCandidate",
        "evidenceAgeDays",
        "lifecycleState",
        ".ads-desk-smart-candidate{",
    )
    missing = [token for token in required if token not in html]
    if missing:
        raise ValueError(f"Smart Issue candidate UI artifact checks missing: {missing}")
    forbidden = (
        "const rawSignals=snap.signals||[]",
        "Tự động xử lý",
        "Tự động cảnh báo",
    )
    leaked = [token for token in forbidden if token in html]
    if leaked:
        raise ValueError(f"unsafe Smart Issue candidate presentation leaked: {leaked}")


def build_native_v2_multi_shop(*, payload_dir: Any, v2_template_path: Any, output_dir: Any):
    original_transform = _persistence.persistence_runtime_from_diagnosis
    original_style = _persistence.PERSISTENCE_STYLE

    def transform_with_candidates(diagnosis_runtime: str) -> str:
        return smart_issue_runtime_from_persistence(original_transform(diagnosis_runtime))

    _persistence.persistence_runtime_from_diagnosis = transform_with_candidates
    _persistence.PERSISTENCE_STYLE = original_style + "\n" + SMART_ISSUE_CANDIDATE_STYLE
    try:
        result = _persistence.build_native_v2_multi_shop(
            payload_dir=payload_dir,
            v2_template_path=v2_template_path,
            output_dir=output_dir,
        )
        _validate_smart_issue_candidate_artifact(output_dir)
        result["adsSmartIssueCandidateUiReady"] = True
        result["adsSmartIssueCandidateUiVersion"] = ADS_SMART_ISSUE_CANDIDATE_UI_VERSION
        result["adsSmartIssueCandidatesEnabled"] = True
        result["adsSmartIssuesEnabled"] = False
        result["adsSmartIssueAutomaticAlertsEnabled"] = False
        result["adsSmartIssueAutomaticActionsEnabled"] = False
        return result
    finally:
        _persistence.persistence_runtime_from_diagnosis = original_transform
        _persistence.PERSISTENCE_STYLE = original_style
