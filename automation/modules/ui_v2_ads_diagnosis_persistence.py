"""Diagnosis Persistence presentation wrapper for the validated Ads Desk.

Financial v38 and Dynamic Diagnosis UI v1 remain untouched. This additive layer
only exposes the persistence state already computed in Ads Intelligence. It does
not create Smart Issues, alerts or actions.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from . import ui_v2_ads_dynamic_diagnosis as _diagnosis


ADS_DIAGNOSIS_PERSISTENCE_UI_VERSION = "ads-diagnosis-persistence-ui-v1"

PERSISTENCE_STYLE = r"""
/* ads-diagnosis-persistence-ui-v1 */
.ads-desk-persistence{display:inline-flex!important;width:max-content;margin-top:6px!important;padding:3px 6px;border-radius:6px;background:var(--soft);font-size:7.5px!important;font-weight:780!important;color:var(--muted)!important}
.ads-desk-persistence.confirmed{background:var(--green-bg);color:var(--green)!important}.ads-desk-persistence.conflicted{color:var(--red)!important}.ads-desk-persistence.first{color:var(--muted2)!important}
"""

_NEW_DESK_SUB = "Tham khảo sau khi đã đọc dữ liệu và biểu đồ phía trên. Chẩn đoán chỉ xuất hiện khi hai kỳ có bối cảnh bán hàng tương đồng. Độ bền chỉ được xác nhận bằng các cửa sổ độc lập cùng scope và cùng bối cảnh."


def _enhanced_signal_card() -> str:
    old = _diagnosis._NEW_SIGNAL_CARD
    needle = "</span></div>').join('')"
    if needle not in old:
        raise ValueError("Dynamic Diagnosis signal card shape changed; persistence wrapper refused to patch")
    badge = (
        "</span><span class=\"ads-desk-persistence '+"
        "(((sig.persistence||{}).state==='CONFIRMED')?'confirmed':(((sig.persistence||{}).state==='CONFLICTED')?'conflicted':(((sig.persistence||{}).state==='FIRST_OBSERVATION')?'first':'')))+'\">'+"
        "esc(((sig.persistence||{}).state==='CONFIRMED'?'Đã xác nhận':((sig.persistence||{}).state==='CONFLICTED'?'Mâu thuẫn':((sig.persistence||{}).state==='ONE_OFF'?'Một lần':((sig.persistence||{}).state==='FIRST_OBSERVATION'?'Lần đầu':'Chưa đánh giá')))))+"
        "' · '+String((sig.persistence||{}).supportWindowCount||0)+'/'+String((sig.persistence||{}).eligibleIndependentWindowCount||0)+' cửa sổ')+"
        "</span></div>').join('')"
    )
    return old.replace(needle, badge)


def persistence_runtime_from_diagnosis(runtime: str) -> str:
    old_card = _diagnosis._NEW_SIGNAL_CARD
    new_card = _enhanced_signal_card()
    if old_card not in runtime:
        raise ValueError("Dynamic Diagnosis runtime shape changed; persistence wrapper refused to patch signal card")
    runtime = runtime.replace(old_card, new_card)
    if _diagnosis._NEW_DESK_SUB not in runtime:
        raise ValueError("Dynamic Diagnosis Desk copy changed; persistence wrapper refused to patch")
    runtime = runtime.replace(_diagnosis._NEW_DESK_SUB, _NEW_DESK_SUB)
    return runtime


def effective_persistence_runtime(entity_map: Mapping[str, Any]) -> str:
    return persistence_runtime_from_diagnosis(_diagnosis.effective_dynamic_diagnosis_runtime(entity_map))


def _validate_persistence_artifact(output_dir: Any) -> None:
    html = (Path(output_dir) / "command_center_v2_multi_shop_native_template.html").read_text(encoding="utf-8")
    required = (
        ADS_DIAGNOSIS_PERSISTENCE_UI_VERSION,
        "Chẩn đoán chỉ xuất hiện khi hai kỳ có bối cảnh bán hàng tương đồng.",
        "Độ bền chỉ được xác nhận bằng các cửa sổ độc lập cùng scope và cùng bối cảnh.",
        "Đã xác nhận",
        "Mâu thuẫn",
        "Một lần",
        "Lần đầu",
        "supportWindowCount",
        "eligibleIndependentWindowCount",
        ".ads-desk-persistence{",
    )
    missing = [token for token in required if token not in html]
    if missing:
        raise ValueError(f"Ads Diagnosis Persistence UI artifact checks missing: {missing}")
    forbidden = (
        "const rawSignals=snap.signals||[]",
        "Smart Issue candidate",
    )
    leaked = [token for token in forbidden if token in html]
    if leaked:
        raise ValueError(f"unsafe Ads Diagnosis Persistence presentation leaked: {leaked}")


def build_native_v2_multi_shop(*, payload_dir: Any, v2_template_path: Any, output_dir: Any):
    original_transform = _diagnosis.diagnosis_runtime_from_base
    original_style = _diagnosis.DIAGNOSIS_STYLE

    def transform_with_persistence(base_runtime: str) -> str:
        return persistence_runtime_from_diagnosis(original_transform(base_runtime))

    _diagnosis.diagnosis_runtime_from_base = transform_with_persistence
    _diagnosis.DIAGNOSIS_STYLE = original_style + "\n" + PERSISTENCE_STYLE
    try:
        result = _diagnosis.build_native_v2_multi_shop(
            payload_dir=payload_dir,
            v2_template_path=v2_template_path,
            output_dir=output_dir,
        )
        _validate_persistence_artifact(output_dir)
        result["adsDiagnosisPersistenceUiReady"] = True
        result["adsDiagnosisPersistenceUiVersion"] = ADS_DIAGNOSIS_PERSISTENCE_UI_VERSION
        result["adsSmartIssueCandidatesEnabled"] = False
        return result
    finally:
        _diagnosis.diagnosis_runtime_from_base = original_transform
        _diagnosis.DIAGNOSIS_STYLE = original_style
