"""Operator-language polish + semantic safety QA for Intelligence-first PREPRODUCTION.

This wrapper keeps the approved v30 Intelligence-first visual structure, replaces
backend-oriented wording with operator-facing Vietnamese, and validates safety
from artifact state/semantics instead of exact visible phrases.

The production V2 template remains read-only. All changes participate in Native
fingerprint lineage.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from . import ui_v2_native_review as _review


OPERATOR_COPY_PATCH_VERSION = "native-production-shadow-mode-v32"

_COPY_REPLACEMENTS = {
    "Dùng số liệu để xác nhận quy mô sau khi đã đọc phần Intelligence.":
        "Số liệu chi tiết để kiểm tra và xác nhận diễn biến ở trên.",
    "So sánh định lượng khả dụng; mức độ bất thường chỉ được kết luận khi các evidence gate cho phép.":
        "Có thể so sánh định lượng; chỉ kết luận bất thường khi dữ liệu đủ bằng chứng.",
    "Có Smart Issue cần chú ý": "Có vấn đề cần chú ý",
    "Smart Issue đã vượt qua các evidence gate hiện tại.":
        "Vấn đề đã vượt qua các ngưỡng bằng chứng hiện tại.",
    'badge:(issue.severityLevel||"ISSUE")+" · "+n0.format(conf*100)+"% confidence",':
        'badge:(issue.severityLevel||"ISSUE")+" · Tin cậy "+n0.format(conf*100)+"%",',
    "Intelligence giữ fail-closed: có thể đọc diễn biến và yếu tố tác động, nhưng chưa mở Smart Issue.":
        "Có thể đọc diễn biến và yếu tố tác động, nhưng chưa đủ bằng chứng để xác nhận đây là biến động bất thường.",
    "Evidence gate đang chặn": "Chưa đủ bằng chứng",
    "Không có Smart Issue đủ điều kiện trong kỳ đang xem.":
        "Chưa có vấn đề nào đủ bằng chứng để mở theo dõi ưu tiên.",
    "Không có Smart Issue": "Không có vấn đề ưu tiên",
    "Xác minh evidence trước khi thay đổi": "Xác minh dữ liệu trước khi thay đổi",
    "Review option cho người vận hành; không phải lệnh tự động và không cho phép platform mutation.":
        "Đây là bước kiểm tra dành cho người vận hành; không phải lệnh tự động và không thay đổi dữ liệu trên sàn.",
    "Chưa phát sinh hành động cần review": "Chưa có bước kiểm tra được đề xuất",
    "Hệ thống không tự đề xuất thay đổi khi Smart Issue hoặc evidence chưa đủ điều kiện.":
        "Hệ thống không tự đề xuất thay đổi khi chưa có vấn đề đủ bằng chứng.",
    "Intelligence ưu tiên diễn giải trước, số liệu chi tiết ở phía dưới.":
        "Đọc diễn biến và yếu tố tác động trước khi xem số liệu chi tiết.",
}

_STRUCTURAL_ARTIFACT_TOKENS = (
    "intelligenceBrief",
    "Tóm tắt vận hành",
    "Cần chú ý",
    "Nên kiểm tra",
    "Chỉ số chính",
    ".intel-brief{",
    "intelligence-first-command-center",
    "reviewOptions",
)

# Safety is validated from machine state embedded in the artifact, not from UI copy.
_SEMANTIC_SAFETY_TOKENS = (
    '"mode":"PREPRODUCTION_OBSERVE_ONLY"',
    '"platformMutationAllowed":false',
    '"productionWritesEnabled":false',
    '"actionRecommendationsEnabled":false',
    '"automaticAlertsEnabled":false',
    '"operationalDiagnosisEnabled":false',
    '"causalClaimsEnabled":false',
)

_FORBIDDEN_DIRECTIVES = (
    "CHANGE_BID",
    "CHANGE_BUDGET",
    "CHANGE_PRICE",
    "CHANGE_PROMOTION",
    "PAUSE_CAMPAIGN",
    "PUBLISH_LISTING_CHANGE",
    "CONTACT_CUSTOMER_AUTOMATICALLY",
)


def _polish_runtime(runtime: str) -> str:
    polished = runtime
    for old, new in _COPY_REPLACEMENTS.items():
        if old not in polished:
            raise ValueError(f"operator-copy anchor missing: {old}")
        polished = polished.replace(old, new, 1)
    return polished


def _validate_semantic_artifact(output_dir: Any) -> None:
    html_path = Path(output_dir) / "command_center_v2_multi_shop_native_template.html"
    html = html_path.read_text(encoding="utf-8")

    missing_structure = [x for x in _STRUCTURAL_ARTIFACT_TOKENS if x not in html]
    if missing_structure:
        raise ValueError(
            f"intelligence-first structural checks missing: {missing_structure}"
        )

    missing_safety = [x for x in _SEMANTIC_SAFETY_TOKENS if x not in html]
    if missing_safety:
        raise ValueError(
            f"intelligence-first semantic safety checks missing: {missing_safety}"
        )

    forbidden = [x for x in _FORBIDDEN_DIRECTIVES if x in html]
    if forbidden:
        raise ValueError(
            f"forbidden execution directives leaked into intelligence artifact: {forbidden}"
        )


def build_native_v2_multi_shop(*, payload_dir: Any, v2_template_path: Any, output_dir: Any):
    """Build v32 using v30 visual structure with operator copy and semantic QA.

    We deliberately bypass the older v30 post-build copy-marker assertions. The
    v30 style/runtime patch functions are still reused, but safety acceptance is
    now based on embedded PREPRODUCTION state and capability flags.
    """
    native = _review._native
    original_style = native.NATIVE_STYLE
    original_runtime = native.NATIVE_RUNTIME
    original_version = native.NATIVE_PATCH_VERSION
    original_review_runtime = _review.INTELLIGENCE_FIRST_RUNTIME

    polished_runtime = _polish_runtime(original_review_runtime)
    _review.INTELLIGENCE_FIRST_RUNTIME = polished_runtime

    native.NATIVE_STYLE = _review._patched_style(original_style)
    native.NATIVE_RUNTIME = _review._patched_runtime(original_runtime)
    native.NATIVE_PATCH_VERSION = OPERATOR_COPY_PATCH_VERSION

    try:
        result = native.build_native_v2_multi_shop(
            payload_dir=payload_dir,
            v2_template_path=v2_template_path,
            output_dir=output_dir,
        )
        if result.get("nativePatchVersion") != OPERATOR_COPY_PATCH_VERSION:
            raise ValueError("operator-copy patch version missing from Native lineage")
        _validate_semantic_artifact(output_dir)
        return result
    finally:
        _review.INTELLIGENCE_FIRST_RUNTIME = original_review_runtime
        native.NATIVE_STYLE = original_style
        native.NATIVE_RUNTIME = original_runtime
        native.NATIVE_PATCH_VERSION = original_version
