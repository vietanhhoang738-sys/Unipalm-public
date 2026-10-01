"""Product v36 short-name presentation adapter.

This layer never mutates canonical Product titles or Product Intelligence
semantics. It builds a deterministic shop-scoped display-name map from the
canonical Product destination payload, applies collision guards, and replaces
only operator-facing labels in the generated Native artifact.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Mapping

from . import ui_v2_product_compact_signals as _compact
from .product_short_name import RULE_VERSION, short_name_for_product


PRODUCT_SHORT_NAME_PATCH_VERSION = "native-product-intelligence-v36-short-names"

SHORT_NAME_STYLE = r"""
/* V36: factor evidence must remain readable; never crop the contribution text. */
.product-signal>div:first-child{min-width:0}
.product-hero:has(.product-signal) .product-signal-driver{
  display:inline-block;
  max-width:100%;
  white-space:normal;
  overflow:visible;
  text-overflow:clip;
  line-height:1.35;
  overflow-wrap:anywhere;
}
.product-short-name{letter-spacing:-.005em}
"""


def _product_destination(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    return ((payload.get("destinations") or {}).get("product") or {})


def _candidate_products(scope: Mapping[str, Any]):
    seen = set()
    horizons = scope.get("horizons") or {}
    for key in ("oneMonth", "threeMonths", "sixMonths", "year"):
        horizon = horizons.get(key) or {}
        for product in horizon.get("products") or []:
            pid = str(product.get("productId") or "").strip()
            if pid and pid not in seen:
                seen.add(pid)
                yield product
    for signal in (scope.get("structuralIntelligence") or {}).get("signals") or []:
        pid = str(signal.get("productId") or "").strip()
        if pid and pid not in seen:
            seen.add(pid)
            yield signal


def build_short_name_map(payload: Mapping[str, Any]) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """Return shop -> productId -> safe display-name record.

    A collision never silently merges two listings. We append SKU first; if the
    same SKU is still reused by multiple listing IDs, a short product-id suffix
    is added as the final disambiguator.
    """
    result: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for sid, scope in (_product_destination(payload).get("shops") or {}).items():
        records: Dict[str, Dict[str, Any]] = {}
        for product in _candidate_products(scope):
            pid = str(product.get("productId") or "").strip()
            if not pid:
                continue
            resolved = short_name_for_product(product)
            records[pid] = {**resolved, "displayName": resolved["shortName"]}

        groups = defaultdict(list)
        for pid, rec in records.items():
            groups[rec["displayName"]].append(pid)
        for display_name, pids in groups.items():
            if len(pids) < 2:
                continue
            for pid in pids:
                rec = records[pid]
                sku = str(rec.get("parentSku") or "").strip()
                suffix = sku or pid[-6:]
                rec["displayName"] = f"{display_name} · {suffix}"
                rec["collisionGuardApplied"] = True

        second_groups = defaultdict(list)
        for pid, rec in records.items():
            second_groups[rec["displayName"]].append(pid)
        for display_name, pids in second_groups.items():
            if len(pids) < 2:
                continue
            for pid in pids:
                records[pid]["displayName"] = f"{display_name} · {pid[-4:]}"
                records[pid]["collisionGuardApplied"] = True

        result[str(sid)] = records
    return result


def _runtime_for_map(name_map: Mapping[str, Any]) -> str:
    encoded = json.dumps(name_map, ensure_ascii=False, separators=(",", ":"))
    return r"""
(function(){
  const q=new URLSearchParams(location.search);
  if(q.get("destination")!=="product")return;
  const SHORT=__SHORT_NAME_MAP__;
  const B=window.UNIPALM_SCOPE_BUNDLE||{},S=window.UNIPALM_NATIVE_SCOPE||{};
  const P=B.productDestination||{},scope=(P.shops||{})[S.shop]||{};
  const map=SHORT[S.shop]||{};
  const apply=(el,product)=>{
    if(!el||!product)return;
    const pid=String(product.productId||"");
    const rec=map[pid];
    if(!rec||!rec.displayName)return;
    const full=String(product.productName||rec.fullName||"");
    el.textContent=rec.displayName;
    el.classList.add("product-short-name");
    if(full&&full!==rec.displayName)el.title=full;
  };

  const intel=scope.structuralIntelligence||{};
  const signals=(intel.signals||[]).slice(0,4);
  document.querySelectorAll(".product-signal-name").forEach((el,idx)=>apply(el,signals[idx]));

  const order=scope.timeScopeOrder||["oneMonth","threeMonths","sixMonths","year"];
  const horizons=scope.horizons||{};
  let key=q.get("productHorizon")||"threeMonths";
  if(!horizons[key]||horizons[key].status!=="READY")key=order.find(k=>horizons[k]?.status==="READY")||"oneMonth";
  const horizon=horizons[key]||{},summary=horizon.summary||{},products=horizon.products||[];
  document.querySelectorAll(".product-table tbody tr").forEach((row,idx)=>{
    const product=products[idx];
    if(!product)return;
    const nameEl=row.querySelector(".product-name");
    apply(nameEl,product);
    const rec=map[String(product.productId||"")];
    if(rec&&row.dataset.productSearch){
      row.dataset.productSearch=(row.dataset.productSearch+" "+String(rec.displayName||"").toLowerCase()).trim();
    }
  });

  if(summary.shopMetricSource&&summary.orderSemantics==="UNIQUE_SHOP_ORDERS"){
    document.querySelectorAll(".product-kpi").forEach(card=>{
      const label=card.querySelector(".product-kpi-label"),note=card.querySelector(".product-kpi-note");
      if(!label||!note||label.textContent.trim()!=="Đơn đã đặt")return;
      if(!note.textContent.includes("· BI"))note.textContent=note.textContent.trim()+" · BI";
      card.title="Số đơn và AOV lấy từ Business Insights ở cấp shop; không cộng số đơn của từng sản phẩm.";
    });
  }
})();
""".replace("__SHORT_NAME_MAP__", encoded)


def _validate_v36_artifact(output_dir: Any) -> None:
    html = (Path(output_dir) / "command_center_v2_multi_shop_native_template.html").read_text(encoding="utf-8")
    required = (
        PRODUCT_SHORT_NAME_PATCH_VERSION,
        RULE_VERSION,
        "product-short-name",
        "displayName",
        "white-space:normal",
        "overflow-wrap:anywhere",
        'summary.orderSemantics==="UNIQUE_SHOP_ORDERS"',
        "· BI",
        "Số đơn và AOV lấy từ Business Insights ở cấp shop",
    )
    missing = [token for token in required if token not in html]
    if missing:
        raise ValueError(f"Product v36 artifact checks missing: {missing}")


def build_native_v2_multi_shop(*, payload_dir: Any, v2_template_path: Any, output_dir: Any):
    payload_path = Path(payload_dir) / "ui_payload.json"
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    name_map = build_short_name_map(payload)
    runtime = _runtime_for_map(name_map)

    original_style = _compact.COMPACT_SIGNAL_STYLE
    original_runtime = _compact.COMPACT_SIGNAL_RUNTIME
    original_version = _compact.PRODUCT_COMPACT_SIGNAL_PATCH_VERSION
    _compact.COMPACT_SIGNAL_STYLE = original_style + "\n" + SHORT_NAME_STYLE
    _compact.COMPACT_SIGNAL_RUNTIME = original_runtime + "\n" + f"/* {RULE_VERSION} */\n" + runtime
    _compact.PRODUCT_COMPACT_SIGNAL_PATCH_VERSION = PRODUCT_SHORT_NAME_PATCH_VERSION
    try:
        result = _compact.build_native_v2_multi_shop(
            payload_dir=payload_dir,
            v2_template_path=v2_template_path,
            output_dir=output_dir,
        )
        if result.get("nativePatchVersion") != PRODUCT_SHORT_NAME_PATCH_VERSION:
            raise ValueError("Product short-name patch version missing from lineage")
        _validate_v36_artifact(output_dir)
        result["productShortNameReady"] = True
        result["productShortNameRuleVersion"] = RULE_VERSION
        result["productShortNameShopCount"] = len(name_map)
        return result
    finally:
        _compact.COMPACT_SIGNAL_STYLE = original_style
        _compact.COMPACT_SIGNAL_RUNTIME = original_runtime
        _compact.PRODUCT_COMPACT_SIGNAL_PATCH_VERSION = original_version
