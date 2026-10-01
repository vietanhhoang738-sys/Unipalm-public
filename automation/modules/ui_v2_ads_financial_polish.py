"""Final presentation polish for Ads Financial v38.

The Financial v38 architecture and Ads Intelligence facts remain untouched.
This wrapper normalizes only the effective operator-facing presentation that the
canonical Native runner emits: shared V2 tokens, Vietnamese-first copy and the
artifact guard used for handoff.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from . import ui_v2_ads_financial as _financial

ADS_FINANCIAL_POLISH_VERSION = "ads-financial-polish-v2"


def effective_financial_style() -> str:
    """Return the v38 stylesheet after applying only shared-foundation polish."""
    return _financial.FINANCIAL_STYLE.replace(
        "No font-family override: typography is inherited from",
        "Typography is inherited from",
    ).replace("var(--green-soft)", "var(--green-bg)")


def effective_financial_runtime(entity_map: Mapping[str, Any]) -> str:
    """Return the operator-facing v38 runtime with hard-contract wording."""
    runtime = _financial._financial_runtime(entity_map)
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


def _validate_polished_artifact(output_dir: Any) -> None:
    html = (Path(output_dir) / "command_center_v2_multi_shop_native_template.html").read_text(encoding="utf-8")
    required = (
        _financial.ADS_FINANCIAL_PATCH_VERSION,
        "Phương trình hiệu quả Ads", "GMV Ads", "Chi tiêu Ads", "AOV", "Chuyển đổi",
        "Hiển thị", "CTR", "CR", "CPC", "Click", "Diễn biến trong kỳ", "Funnel Ads",
        "Áp lực chi phí", "1W", "1M", "3M", "6M", "Phân bổ hiệu quả",
        "Bản đồ CPC × ROAS", "Ads Intelligence Desk", "Shop", "Nhóm SP", "Sản phẩm",
        ".ads-equation{", ".ads-fin-kpis{", ".ads-cost-grid{", ".ads-intelligence-desk{",
        "dữ liệu Ads đã xác thực", "THAM KHẢO",
    )
    missing = [token for token in required if token not in html]
    if missing:
        raise ValueError(f"Ads Financial polished artifact checks missing: {missing}")
    forbidden = (
        "Ads Spend", "trusted history", "Spend share", "EVIDENCE ONLY",
    )
    leaked = [token for token in forbidden if token in html]
    if leaked:
        raise ValueError(f"Ads Financial operator copy leaked forbidden wording: {leaked}")
    style = effective_financial_style()
    if "font-family:" in style:
        raise ValueError("Ads Financial polish must not declare a font family")
    if "var(--green-soft)" in style:
        raise ValueError("Ads Financial polish must use the shared V2 green background token")


def build_native_v2_multi_shop(*, payload_dir: Any, v2_template_path: Any, output_dir: Any):
    original_style = _financial.FINANCIAL_STYLE
    original_runtime = _financial._financial_runtime
    original_validator = _financial._validate_financial_artifact

    polished_style = effective_financial_style()

    # Capture the original runtime before monkey-patching to avoid recursion.
    def polished_runtime(entity_map):
        runtime = original_runtime(entity_map)
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

    _financial.FINANCIAL_STYLE = polished_style
    _financial._financial_runtime = polished_runtime
    _financial._validate_financial_artifact = _validate_polished_artifact
    try:
        result = _financial.build_native_v2_multi_shop(
            payload_dir=payload_dir,
            v2_template_path=v2_template_path,
            output_dir=output_dir,
        )
        _validate_polished_artifact(output_dir)
        result["adsFinancialPolishReady"] = True
        result["adsFinancialPolishVersion"] = ADS_FINANCIAL_POLISH_VERSION
        result["adsFinancialOperatorLanguageReady"] = True
        return result
    finally:
        _financial.FINANCIAL_STYLE = original_style
        _financial._financial_runtime = original_runtime
        _financial._validate_financial_artifact = original_validator
