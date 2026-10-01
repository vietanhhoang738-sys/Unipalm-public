"""Compact Product structural-signal presentation for PREPRODUCTION.

This patch is intentionally presentation-only. Product Intelligence semantics,
payload contracts and v34 artifact validation remain unchanged.
"""
from __future__ import annotations

from typing import Any

from . import ui_v2_product_destination as _product

PRODUCT_COMPACT_SIGNAL_PATCH_VERSION = "native-product-intelligence-v35-compact-signals"

COMPACT_SIGNAL_STYLE = r"""
/* Keep the Product hero compact when structural signals exist.
   The default v34 layout is preserved when history is insufficient. */
.product-hero:has(.product-signal){
  grid-template-columns:minmax(0,1.55fr) minmax(280px,.85fr);
  grid-template-areas:"summary state" "signals signals";
  align-items:start;
}
.product-hero:has(.product-signal) .product-hero-main{grid-area:summary;min-width:0}
.product-hero:has(.product-signal) .product-hero-side{display:contents}
.product-hero:has(.product-signal) .product-history-state{
  grid-area:state;
  align-self:start;
  margin:20px 20px 0;
}
.product-hero:has(.product-signal) .product-signal-list{
  grid-area:signals;
  display:grid;
  grid-template-columns:repeat(4,minmax(0,1fr));
  gap:10px;
  margin:0;
  padding:16px 20px 18px;
  border-top:1px solid var(--line);
  background:var(--soft);
}
.product-hero:has(.product-signal) .product-signal{
  min-width:0;
  min-height:108px;
  padding:13px 14px;
  border:1px solid var(--line);
  border-radius:12px;
  background:var(--surface);
  box-shadow:var(--shadow);
  align-content:start;
}
.product-hero:has(.product-signal) .product-signal:first-child{border-top:1px solid var(--line)}
.product-hero:has(.product-signal) .product-signal-name{
  display:-webkit-box;
  -webkit-box-orient:vertical;
  -webkit-line-clamp:2;
  overflow:hidden;
  min-height:2.8em;
}
.product-hero:has(.product-signal) .product-signal-meta{
  white-space:nowrap;
  overflow:hidden;
  text-overflow:ellipsis;
}
.product-hero:has(.product-signal) .product-signal-driver{
  max-width:100%;
  white-space:nowrap;
  overflow:hidden;
  text-overflow:ellipsis;
}
.product-hero:has(.product-signal) .product-causality-note{
  grid-column:1/-1;
  margin:2px 0 0;
  padding-top:10px;
}
@media(max-width:1180px){
  .product-hero:has(.product-signal) .product-signal-list{grid-template-columns:repeat(2,minmax(0,1fr))}
}
@media(max-width:1050px){
  .product-hero:has(.product-signal){
    grid-template-columns:1fr;
    grid-template-areas:"summary" "state" "signals";
  }
  .product-hero:has(.product-signal) .product-history-state{margin:0 20px 18px}
}
@media(max-width:680px){
  .product-hero:has(.product-signal) .product-signal-list{grid-template-columns:1fr;padding:14px}
  .product-hero:has(.product-signal) .product-history-state{margin:0 14px 14px}
}
"""

COMPACT_SIGNAL_RUNTIME = r"""
(function(){
  const q=new URLSearchParams(location.search);
  if(q.get("destination")!=="product")return;
  const B=window.UNIPALM_SCOPE_BUNDLE||{},S=window.UNIPALM_NATIVE_SCOPE||{};
  const P=B.productDestination||{},scope=(P.shops||{})[S.shop]||{};
  const intel=scope.structuralIntelligence||{};
  if(intel.status!=="READY")return;
  const signals=(intel.signals||[]).slice(0,4);
  if(!signals.length)return;
  const problems=signals.filter(x=>x.type==="Vấn đề").length;
  const opportunities=signals.filter(x=>x.type==="Cơ hội").length;
  const title=document.querySelector(".product-history-state b");
  if(!title)return;
  if(problems&&opportunities)title.textContent=problems+" cần chú ý · "+opportunities+" cơ hội";
  else if(problems)title.textContent=problems+" sản phẩm có tín hiệu cần chú ý";
  else if(opportunities)title.textContent=opportunities+" cơ hội tăng trưởng cấu trúc";
  else title.textContent=signals.length+" tín hiệu cấu trúc nổi bật";
})();
"""


def build_native_v2_multi_shop(*, payload_dir: Any, v2_template_path: Any, output_dir: Any):
    """Build v34 Product artifact with the compact structural-signal presentation."""
    original_style = _product.PRODUCT_STYLE
    original_runtime = _product.PRODUCT_RUNTIME
    original_version = _product.PRODUCT_NATIVE_PATCH_VERSION
    _product.PRODUCT_STYLE = original_style + "\n" + COMPACT_SIGNAL_STYLE
    _product.PRODUCT_RUNTIME = original_runtime + "\n" + COMPACT_SIGNAL_RUNTIME
    _product.PRODUCT_NATIVE_PATCH_VERSION = PRODUCT_COMPACT_SIGNAL_PATCH_VERSION
    try:
        result = _product.build_native_v2_multi_shop(
            payload_dir=payload_dir,
            v2_template_path=v2_template_path,
            output_dir=output_dir,
        )
        if result.get("nativePatchVersion") != PRODUCT_COMPACT_SIGNAL_PATCH_VERSION:
            raise ValueError("Compact Product signal patch version missing from lineage")
        return result
    finally:
        _product.PRODUCT_STYLE = original_style
        _product.PRODUCT_RUNTIME = original_runtime
        _product.PRODUCT_NATIVE_PATCH_VERSION = original_version
