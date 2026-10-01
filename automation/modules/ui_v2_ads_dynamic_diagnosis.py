"""Dynamic Ads Diagnosis presentation wrapper for Financial v38.

The validated Financial v38 module remains untouched. This additive wrapper only
changes the effective Intelligence Desk so raw Ads signals are never promoted to
operator-facing diagnosis. The Desk consumes `dynamicDiagnosis.items`, which are
already context-qualified by the Ads Intelligence layer.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from . import ui_v2_ads_financial as _financial
from . import ui_v2_ads_financial_polish as _polish


ADS_DYNAMIC_DIAGNOSIS_UI_VERSION = "ads-dynamic-diagnosis-ui-v1"

DIAGNOSIS_STYLE = r"""
.ads-desk-gate{margin:0 20px 18px;padding:12px 13px;border:1px solid var(--line);border-radius:11px;background:var(--soft)}
.ads-desk-gate b{display:block;font-size:10px;color:var(--text)}.ads-desk-gate span{display:block;margin-top:5px;font-size:9px;line-height:1.5;color:var(--muted)}
.ads-desk-signal span+span{margin-top:5px}.ads-desk-priority{display:inline-flex!important;width:max-content;margin-top:6px!important;padding:3px 6px;border:1px solid var(--line);border-radius:6px;background:var(--surface);font-size:7.5px!important;font-weight:760;color:var(--muted2)!important}
"""

_RAW_SIGNAL_BINDING = "const rawSignals=snap.signals||[],signals=rawSignals.filter(sig=>entityScope==='shop'||(entityScope==='product'?String(sig.productId)===entityKey:entityRecords[String(sig.productId)]?.group===entityKey)).slice(0,4);"
_DIAGNOSIS_SIGNAL_BINDING = "const diag=snap.dynamicDiagnosis||{},rawSignals=diag.items||[],signals=rawSignals.filter(sig=>entityScope==='shop'||(entityScope==='product'?String(sig.productId)===entityKey:entityRecords[String(sig.productId)]?.group===entityKey)).slice(0,4);"

_OLD_DESK_SUB = "Tham khảo sau khi đã đọc dữ liệu và biểu đồ phía trên. Intelligence chỉ tóm tắt evidence đã có."
_NEW_DESK_SUB = "Tham khảo sau khi đã đọc dữ liệu và biểu đồ phía trên. Chẩn đoán chỉ xuất hiện khi hai kỳ có bối cảnh bán hàng tương đồng."

_OLD_SIGNAL_CARD = "signals.map(sig=>'<div class=\"ads-desk-signal '+(sig.type==='Vấn đề'?'problem':'opportunity')+'\"><b>'+esc(entityRecords[String(sig.productId)]?.displayName||sig.productName||sig.productId)+'</b><span>'+esc(sig.type)+' · ROAS '+formatDelta(sig.roasDelta)+' · Spend share '+pct(sig.spendShare)+'</span></div>').join('')"
_NEW_SIGNAL_CARD = "signals.map(sig=>'<div class=\"ads-desk-signal '+(sig.kind==='PROBLEM'?'problem':'opportunity')+'\"><b>'+esc(sig.headline||entityRecords[String(sig.productId)]?.displayName||sig.productName||'Sản phẩm chưa xác định')+'</b><span>'+esc(sig.summary||'')+'</span><span>'+esc(sig.reviewFocus||'')+'</span><span class=\"ads-desk-priority\">'+esc(sig.operatorType||'Tín hiệu')+' · Ưu tiên '+esc(sig.priorityTier==='HIGH'?'cao':(sig.priorityTier==='MEDIUM'?'vừa':'theo dõi'))+' · Độ tin cậy '+esc(sig.confidenceTier==='HIGH'?'cao':(sig.confidenceTier==='MEDIUM'?'vừa':'thấp'))+'</span></div>').join('')"

_OLD_SIGNAL_SECTION_END = "+(signals.length?'<div class=\"ads-desk-signals\">'+signals.map(sig=>'<div class=\"ads-desk-signal '+(sig.type==='Vấn đề'?'problem':'opportunity')+'\"><b>'+esc(entityRecords[String(sig.productId)]?.displayName||sig.productName||sig.productId)+'</b><span>'+esc(sig.type)+' · ROAS '+formatDelta(sig.roasDelta)+' · Spend share '+pct(sig.spendShare)+'</span></div>').join('')+'</div>':'')+'</section>';"
_NEW_SIGNAL_SECTION_END = "+(signals.length?'<div class=\"ads-desk-signals\">'+signals.map(sig=>'<div class=\"ads-desk-signal '+(sig.kind==='PROBLEM'?'problem':'opportunity')+'\"><b>'+esc(sig.headline||entityRecords[String(sig.productId)]?.displayName||sig.productName||'Sản phẩm chưa xác định')+'</b><span>'+esc(sig.summary||'')+'</span><span>'+esc(sig.reviewFocus||'')+'</span><span class=\"ads-desk-priority\">'+esc(sig.operatorType||'Tín hiệu')+' · Ưu tiên '+esc(sig.priorityTier==='HIGH'?'cao':(sig.priorityTier==='MEDIUM'?'vừa':'theo dõi'))+' · Độ tin cậy '+esc(sig.confidenceTier==='HIGH'?'cao':(sig.confidenceTier==='MEDIUM'?'vừa':'thấp'))+'</span></div>').join('')+'</div>':'<div class=\"ads-desk-gate\"><b>'+esc(diag.status==='NO_MATERIAL_DIAGNOSIS'?'Chưa có chẩn đoán nổi bật':'Chẩn đoán đang được khóa')+'</b><span>'+esc(diag.reason||'Chưa đủ bằng chứng để tạo chẩn đoán cho kỳ đang chọn.')+'</span></div>')+'</section>';"


def diagnosis_runtime_from_base(runtime: str) -> str:
    """Transform only the Intelligence Desk signal binding in Financial v38."""
    required = (_RAW_SIGNAL_BINDING, _OLD_DESK_SUB, _OLD_SIGNAL_SECTION_END)
    missing = [token[:80] for token in required if token not in runtime]
    if missing:
        raise ValueError(f"Financial v38 runtime shape changed; diagnosis wrapper refused to patch: {missing}")
    runtime = runtime.replace(_RAW_SIGNAL_BINDING, _DIAGNOSIS_SIGNAL_BINDING)
    runtime = runtime.replace(_OLD_DESK_SUB, _NEW_DESK_SUB)
    runtime = runtime.replace(_OLD_SIGNAL_SECTION_END, _NEW_SIGNAL_SECTION_END)
    if _RAW_SIGNAL_BINDING in runtime:
        raise ValueError("raw Ads signal binding leaked into Dynamic Diagnosis Desk")
    return runtime


def effective_dynamic_diagnosis_runtime(entity_map: Mapping[str, Any]) -> str:
    """Return polished operator runtime with the diagnosis-only Desk binding."""
    base = _financial._financial_runtime(entity_map)
    patched = diagnosis_runtime_from_base(base)
    replacements = (
        ("Ads Spend", "Chi tiêu Ads"),
        ("Spend share", "Tỷ trọng chi tiêu"),
        ("Cần đủ 30 ngày trusted history.", "Cần đủ 30 ngày dữ liệu Ads đã xác thực."),
        ("Chưa đủ baseline 1M", "Chưa đủ mốc so sánh 1M"),
        ("Intelligence chỉ tóm tắt evidence đã có.", "Intelligence chỉ tóm tắt bằng chứng đã có."),
        ("EVIDENCE ONLY", "THAM KHẢO"),
    )
    for source, target in replacements:
        patched = patched.replace(source, target)
    return patched


def _validate_dynamic_diagnosis_artifact(output_dir: Any) -> None:
    html = (Path(output_dir) / "command_center_v2_multi_shop_native_template.html").read_text(encoding="utf-8")
    required = (
        "Ads Intelligence Desk",
        "Chẩn đoán chỉ xuất hiện khi hai kỳ có bối cảnh bán hàng tương đồng.",
        "Chẩn đoán đang được khóa",
        "Chưa có chẩn đoán nổi bật",
        "dynamicDiagnosis",
        "reviewFocus",
        "priorityTier",
        ".ads-desk-gate{",
        ".ads-desk-priority{",
    )
    missing = [token for token in required if token not in html]
    if missing:
        raise ValueError(f"Dynamic Ads Diagnosis UI artifact checks missing: {missing}")
    forbidden = (
        "const rawSignals=snap.signals||[]",
        "Intelligence chỉ tóm tắt evidence đã có.",
    )
    leaked = [token for token in forbidden if token in html]
    if leaked:
        raise ValueError(f"raw/unqualified Ads diagnosis presentation leaked: {leaked}")


def build_native_v2_multi_shop(*, payload_dir: Any, v2_template_path: Any, output_dir: Any):
    original_runtime = _financial._financial_runtime
    original_style = _financial.FINANCIAL_STYLE

    def runtime_with_diagnosis(entity_map):
        return diagnosis_runtime_from_base(original_runtime(entity_map))

    _financial._financial_runtime = runtime_with_diagnosis
    _financial.FINANCIAL_STYLE = original_style + "\n" + DIAGNOSIS_STYLE
    try:
        result = _polish.build_native_v2_multi_shop(
            payload_dir=payload_dir,
            v2_template_path=v2_template_path,
            output_dir=output_dir,
        )
        _validate_dynamic_diagnosis_artifact(output_dir)
        result["adsDynamicDiagnosisUiReady"] = True
        result["adsDynamicDiagnosisUiVersion"] = ADS_DYNAMIC_DIAGNOSIS_UI_VERSION
        result["adsDiagnosisConsumesQualifiedSignalsOnly"] = True
        return result
    finally:
        _financial._financial_runtime = original_runtime
        _financial.FINANCIAL_STYLE = original_style
