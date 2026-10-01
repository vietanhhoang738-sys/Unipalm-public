"""Build a native multi-shop PREPRODUCTION Command Center from production V2.

The production V2 template is always read as source and never modified. A
deterministic patch adds native scope controls and a compare view while keeping
the existing V2 renderer for Portfolio and Shop scopes.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import re
from pathlib import Path
from typing import Any, Dict, Mapping

from .semantic_payload import _sha256_json
from .ui_artifact import DATA_MARKER
from .ui_v2_compat import (
    V2_COMPATIBILITY_PATCH_VERSION,
    _s,
    _to_v2_payload,
    derive_v2_compat_template,
    validate_v2_template,
)


NATIVE_PATCH_VERSION="native-production-shadow-mode-v28"
SCOPE_BUNDLE_MARKER="/*__UNIPALM_SCOPE_BUNDLE__*/"

PRESENTATION_CONTRACT_PATH=Path(__file__).resolve().parents[2]/"config"/"ui_v2_presentation_contract.json"


def _presentation_contract() -> Dict[str,Any]:
    data=_read_json(PRESENTATION_CONTRACT_PATH)
    if _s(data.get("status"))!="UI_V2_HARD_CONTRACT":
        raise ValueError("UI V2 presentation contract is not active")
    return data


def _present_product(row: Mapping[str,Any]) -> Dict[str,Any]:
    out=dict(row)
    name=_s(row.get("productName")).strip()
    sku=_s(row.get("resolvedParentSku")).strip() or _s(row.get("productSkuObserved")).strip()
    out["displayName"]=name or "Chưa xác định tên sản phẩm"
    out["secondarySku"]=sku
    out["productNamingState"]="RESOLVED_NAME" if name else "MISSING_PRODUCT_NAME"
    return out


def _present_product_block(block: Mapping[str,Any]) -> Dict[str,Any]:
    out=dict(block or {})
    out["topProducts"]=[_present_product(x) for x in (block or {}).get("topProducts") or []]
    return out


def _present_compare_horizons(horizons: Mapping[str,Any]) -> Dict[str,Any]:
    out={}
    for key,h in (horizons or {}).items():
        item=dict(h or {})
        ads=dict(item.get("adsProducts") or {})
        ads["left"]=_present_product_block(ads.get("left") or {})
        ads["right"]=_present_product_block(ads.get("right") or {})
        item["adsProducts"]=ads
        out[key]=item
    return out


def _present_product_mtd(product_mtd: Mapping[str,Any]) -> Dict[str,Any]:
    out=dict(product_mtd or {})
    out["left"]=_present_product_block(out.get("left") or {})
    out["right"]=_present_product_block(out.get("right") or {})
    return out


def _presentation_checks(bundle: Mapping[str,Any]) -> Dict[str,Any]:
    contract=_presentation_contract()
    typography=contract.get("typography") or {}
    language=contract.get("language_system") or {}
    naming=contract.get("product_naming_system") or {}
    forbidden=list(language.get("forbidden_visible_phrases") or [])
    copy_hits=[x for x in forbidden if x in NATIVE_RUNTIME]
    naming_errors=[]
    for pair in bundle.get("comparePairs") or []:
        blocks=[]
        for h in (pair.get("horizons") or {}).values():
            ads=h.get("adsProducts") or {}
            blocks.extend([ads.get("left") or {},ads.get("right") or {}])
        pm=pair.get("productMtd") or {}
        blocks.extend([pm.get("left") or {},pm.get("right") or {}])
        for block in blocks:
            for product in block.get("topProducts") or []:
                pname=_s(product.get("productName")).strip()
                display=_s(product.get("displayName")).strip()
                sku=_s(product.get("secondarySku")).strip()
                pid=_s(product.get("productId")).strip()
                if pname and display!=pname:
                    naming_errors.append({"productId":pid,"reason":"primary_not_product_name"})
                if pname and display in {sku,pid}:
                    naming_errors.append({"productId":pid,"reason":"identifier_used_as_primary"})
                if not pname and display!=_s(naming.get("missing_name_label")):
                    naming_errors.append({"productId":pid,"reason":"missing_name_fallback_invalid"})
    design=contract.get("design_language") or {}
    design_rules=design.get("rules") or {}
    allowed_literals={str(x).lower() for x in (design.get("allowed_foundation_color_literals") or [])}
    literal_colors={x.lower() for x in re.findall(r"#[0-9a-fA-F]{3,8}\\b",NATIVE_STYLE)}
    return {
        "contractVersion":_s(contract.get("version")),
        "fontInter":_s(typography.get("primary_font"))=="Inter",
        "nativeDoesNotOverrideFont":"font-family" not in NATIVE_STYLE,
        "nativeUsesOnlyFoundationPalette":literal_colors.issubset(allowed_literals),
        "nativeLiteralColors":sorted(literal_colors),
        "sharedDesignLanguageActive":bool(design) and bool(design_rules.get("destination_specific_information_architecture")),
        "forbiddenVisibleCopyHits":copy_hits,
        "productNamingErrors":naming_errors,
    }



def _read_json(path: Path) -> Dict[str,Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path,value: Any) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(
        json.dumps(value,ensure_ascii=False,indent=2,sort_keys=True),
        encoding="utf-8",
    )


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _js(value: Any) -> str:
    return json.dumps(
        value,ensure_ascii=False,sort_keys=True,separators=(",",":")
    ).replace("</","<\/")


def _bundle_from_payload(payload: Mapping[str,Any]) -> Dict[str,Any]:
    shops=list((payload.get("selector") or {}).get("shops") or [])
    period=_s((payload.get("meta") or {}).get("period"))
    portfolio=payload.get("portfolio") or {}

    portfolio_v2=_to_v2_payload(
        scope_label="Toàn hệ thống",
        daily=portfolio.get("daily") or [],
        coverage=portfolio.get("coverage") or {},
        period=period,
        historical_context=portfolio.get("historicalContext") or {},
    )

    shop_views={}
    for shop in shops:
        sid=_s(shop.get("shopId"))
        scope=(payload.get("shops") or {}).get(sid) or {}
        shop_views[sid]={
            "coverage":scope.get("coverage") or {},
            "semanticPolicy":scope.get("semanticPolicy") or {},
            "productCoverage":scope.get("productCoverage") or {},
            "v2Payload":_to_v2_payload(
                scope_label=_s(shop.get("displayName")) or sid,
                daily=scope.get("daily") or [],
                coverage=scope.get("coverage") or {},
                period=period,
                shop_meta=shop,
                historical_context=scope.get("historicalContext") or {},
            ),
        }

    compare_pairs=[]
    for pair in (payload.get("compare") or {}).get("pairs") or []:
        scope=pair.get("scope") or {}
        left_id=_s(scope.get("leftShopId"))
        right_id=_s(scope.get("rightShopId"))
        coverage=pair.get("coverage") or {}
        compare_pairs.append({
            "compareId":_s(pair.get("compareId")),
            "leftShopId":left_id,
            "rightShopId":right_id,
            "coverage":coverage,
            "defaultHorizon":_s(pair.get("defaultHorizon")) or "mtd",
            "horizonOrder":pair.get("horizonOrder") or ["latestDay","last7","mtd"],
            "horizons":_present_compare_horizons(pair.get("horizons") or {}),
            "productMtd":_present_product_mtd(pair.get("productMtd") or {}),
        })

    return {
        "period":period,
        "shops":shops,
        "shadowModeV1":dict(payload.get("shadowModeV1") or {}),
        "portfolio":{
            "coverage":portfolio.get("coverage") or {},
            "v2Payload":portfolio_v2,
        },
        "shopViews":shop_views,
        "comparePairs":compare_pairs,
    }


NATIVE_STYLE=r"""
/* Native multi-shop PREPRODUCTION extension.
   Production V2 owns the visual system; this layer styles only scope controls
   and comparison-specific content that has no V2 primitive. */
.native-scope-bar{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin:0 0 18px;padding:11px 12px;border:1px solid var(--line);border-radius:14px;background:var(--surface);box-shadow:var(--shadow)}
.native-sidebar-rail{position:fixed;left:0;top:16px;width:250px;height:calc(100vh - 32px);z-index:70;transition:transform .18s ease,box-shadow .18s ease;transform:translateX(0)}
.native-sidebar-rail .sidebar{display:flex!important;position:relative!important;left:auto!important;top:auto!important;bottom:auto!important;width:200px!important;min-width:200px!important;height:calc(80vh - 25.6px)!important;min-height:0!important;max-height:calc(80vh - 25.6px)!important;overflow-y:auto;overscroll-behavior:contain;transform:scale(1.25);transform-origin:top left}
.native-sidebar-rail.unpinned{transform:translateX(-100%);box-shadow:none}.native-sidebar-rail.unpinned.peek,.native-sidebar-rail.unpinned:hover{transform:translateX(0);box-shadow:18px 0 42px rgba(17,24,20,.16)}
.native-sidebar-hover-active{display:block!important;position:fixed!important;left:0!important;top:0!important;bottom:0!important;width:16px!important;z-index:69!important}
.native-shop-identity{display:inline-flex;align-items:center;gap:8px;min-height:30px;padding:4px 8px;border:1px solid var(--line);border-radius:10px;background:var(--surface)}
.native-shop-name{font-size:9px;font-weight:800;color:var(--text)}
.native-shop-badge{display:inline-flex;align-items:center;min-height:22px;padding:0 9px;border-radius:6px;color:#fff;font-size:8.5px;font-weight:800;white-space:nowrap}
.native-shop-badge.preferred{background:#ee4d2d}.native-shop-badge.mall{background:#d0011b}
.native-preprod{display:inline-flex;align-items:center;padding:7px 10px;border-radius:999px;background:var(--amber-bg);color:var(--amber);font-size:9px;font-weight:800;letter-spacing:.02em}
.native-tabs{display:flex;gap:6px;flex-wrap:wrap}.native-tab{border:1px solid var(--line);background:var(--surface);padding:8px 11px;border-radius:9px;font-size:10px;font-weight:700;color:var(--muted);cursor:pointer}.native-tab.active{background:var(--green);border-color:var(--green);color:#fff}
.native-picker{display:flex;align-items:center;gap:6px}.native-picker label{font-size:9px;color:var(--muted);font-weight:700}.native-picker select{border:1px solid var(--line);background:var(--surface);color:var(--text);padding:7px 9px;border-radius:9px;font-size:10px}.native-hidden{display:none!important}
.native-lineage{margin-left:auto;color:var(--muted2);font-size:8.5px}.native-compare{display:none}.native-compare.open{display:block}

.compare-period-grid{margin-top:0}.compare-period-card .period-value{font-size:28px}.compare-period-card .period-compare{margin-left:12px}
.compare-kpi-peer{margin-top:8px;color:var(--muted2);font-size:8.5px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.compare-pulse .pulse-label{display:flex;align-items:center;gap:8px}.compare-pulse .pulse-label:before{content:"";width:6px;height:6px;border-radius:50%;background:#b7e0cc}
.compare-lead-list{display:grid;gap:10px;margin-top:20px}.compare-lead-row{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:12px;align-items:center;padding:11px 12px;border-radius:11px;background:var(--soft);font-size:9.5px}.compare-lead-row b{font-size:10px}.compare-lead-row span{font-weight:750}.native-lead-left{color:var(--blue)}.native-lead-right{color:var(--green)}.native-lead-even{color:var(--muted)}

.native-table-wrap{overflow-x:auto}.native-table{width:100%;border-collapse:separate;border-spacing:0;font-size:9.5px;min-width:620px}.native-table th{color:var(--muted2);font-size:8px;font-weight:700;text-align:right;padding:11px 9px;border-bottom:1px solid var(--line);background:var(--surface)}.native-table th:first-child,.native-table td:first-child{text-align:left}.native-table td{text-align:right;padding:11px 9px;border-bottom:1px solid var(--line);font-variant-numeric:tabular-nums}.native-table tbody tr:nth-child(odd) td{background:var(--soft)}.native-table tbody tr:hover td{background:var(--green-bg)}.native-table tr:last-child td{border-bottom:0}.native-table td:not(:first-child){font-weight:650}.native-table .metric{font-weight:750;color:var(--text)}.native-traffic-table{min-width:760px}
.native-table-shop-head{display:inline-flex;align-items:center;justify-content:flex-end;gap:6px;flex-wrap:wrap}.native-table-shop-head .native-shop-badge{min-height:18px;padding:0 7px;font-size:7.5px}
.compare-table-card{padding:23px 24px}.compare-table-card .native-table{min-width:560px}.compare-finance-grid{align-items:start;margin-top:0}.compare-finance-grid>.card{height:100%}

.compare-product-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px;width:100%;min-width:0}.compare-product-panel.card{padding:19px 20px}.compare-product-panel h4{margin:0;font-size:13px;color:var(--ink);display:flex;align-items:center;gap:8px;flex-wrap:wrap}.compare-product-panel h4 .native-shop-badge{min-height:18px;padding:0 7px;font-size:7.5px}
.native-concentration{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin:16px 0 12px}.native-concentration div{background:var(--soft);border-radius:9px;padding:9px}.native-concentration b{display:block;font-size:13px}.native-concentration span{font-size:8px;color:var(--muted2)}
.native-product-list{display:grid;gap:8px}.native-product-item{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:10px;padding-top:8px;border-top:1px solid var(--line);font-size:8.5px}.native-product-item:first-child{border-top:0}.native-product-name{display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:2;overflow:hidden;line-height:1.35}.native-product-meta{margin-top:4px;font-size:7.5px;color:var(--muted2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.native-product-value{text-align:right;font-weight:700}
.compare-footnote{margin-top:18px;padding:0 2px}

body[data-theme="dark"] .native-scope-bar{background:var(--surface);border-color:var(--line)}body[data-theme="dark"] .native-picker select{background:var(--surface);color:var(--text)}body[data-theme="dark"] .compare-lead-row{background:var(--soft)}body[data-theme="dark"] .compare-product-panel h4{color:var(--ink)}
@media(max-width:1180px){.native-sidebar-rail{display:none}.native-sidebar-hover-active{display:none!important}.native-lineage{width:100%;margin-left:0}.compare-product-grid{grid-template-columns:1fr}.compare-period-card .period-value{font-size:26px}}
@media(max-width:760px){.native-scope-bar{align-items:flex-start;padding:10px;gap:8px}.native-tabs{flex:1;min-width:0}.native-tab{padding:7px 9px}.native-picker{width:100%;flex-wrap:wrap}.native-picker select{flex:1;min-width:0}.native-lineage{display:none}.native-concentration{grid-template-columns:repeat(3,minmax(0,1fr))}}
"""


def _bootstrap(bundle: Mapping[str,Any],payload_fp: str,semantic_fp: str,v2_sha: str) -> str:
    return f"""
window.UNIPALM_SCOPE_BUNDLE={_js(bundle)};
window.UNIPALM_NATIVE_META={_js({
    "status":"PREPRODUCTION",
    "payloadBuildFingerprint":payload_fp,
    "semanticBuildFingerprint":semantic_fp,
    "sourceV2TemplateSha256":v2_sha,
    "nativePatchVersion":NATIVE_PATCH_VERSION,
    "v2CompatibilityPatchVersion":V2_COMPATIBILITY_PATCH_VERSION,
})};
(function(){{
  const B=window.UNIPALM_SCOPE_BUNDLE||{{}};
  const p=new URLSearchParams(location.search);
  const shops=B.shops||[];
  const valid=id=>shops.some(x=>x.shopId===id);
  let scope=p.get("scope")||"portfolio";
  let shop=p.get("shop")||shops[0]?.shopId||"";
  if(!valid(shop))shop=shops[0]?.shopId||"";
  let left=p.get("left")||shops[0]?.shopId||"";
  let right=p.get("right")||shops.find(x=>x.shopId!==left)?.shopId||left;
  if(!valid(left))left=shops[0]?.shopId||"";
  if(!valid(right)||right===left)right=shops.find(x=>x.shopId!==left)?.shopId||left;
  if(!["portfolio","shop","compare"].includes(scope))scope="portfolio";
  let horizon=p.get("horizon")||"mtd";
  if(!["latestDay","last7","mtd"].includes(horizon))horizon="mtd";
  window.UNIPALM_NATIVE_SCOPE={{scope,shop,left,right,horizon}};
  if(scope==="shop"){{
    window.UNIPALM_DATA=(B.shopViews&&B.shopViews[shop]&&B.shopViews[shop].v2Payload)||B.portfolio.v2Payload;
  }}else if(scope==="compare"){{
    window.UNIPALM_DATA=B.portfolio.v2Payload;
  }}else{{
    window.UNIPALM_DATA=B.portfolio.v2Payload;
  }}
}})();
"""


NATIVE_RUNTIME=r"""
(function(){
  const B=window.UNIPALM_SCOPE_BUNDLE||{},S=window.UNIPALM_NATIVE_SCOPE||{},M=window.UNIPALM_NATIVE_META||{};
  const shops=B.shops||[],byId=Object.fromEntries(shops.map(x=>[x.shopId,x]));
  const header=document.querySelector(".header"),main=document.querySelector(".main"),app=document.querySelector(".app");
  if(!header||!main||!app)return;
  const esc=v=>String(v??"").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[m]));
  const nv=new Intl.NumberFormat("vi-VN",{maximumFractionDigits:1}),n0=new Intl.NumberFormat("vi-VN",{maximumFractionDigits:0});
  const compactMoney=v=>{const n=Number(v||0),a=Math.abs(n),sign=n<0?"-":"";if(a>=1e9)return sign+nv.format(a/1e9)+"tỷ đ";if(a>=1e6)return sign+nv.format(a/1e6)+"tr đ";return sign+n0.format(a)+" đ"};
  const fmt={
    money:v=>typeof money==="function"?money(Number(v||0)):compactMoney(v),
    moneyFull:v=>typeof moneyFull==="function"?moneyFull(Number(v||0)):n0.format(Number(v||0))+" đ",
    int:v=>n0.format(Number(v||0)),
    pct:v=>nv.format(Number(v||0)*100)+"%",
    roas:v=>nv.format(Number(v||0))+"x",
  };
  const deltaPct=(rv,lv)=>lv?rv/lv-1:null;
  const deltaText=(rv,lv)=>{const d=deltaPct(rv,lv);return d===null?"—":((d>0?"+":"")+nv.format(d*100)+"%")};
  const fmtDate=iso=>{if(!iso)return "";const p=String(iso).slice(0,10).split("-");return p.length===3?p[2]+"/"+p[1]:String(iso)};
  const shopBadgeHtml=shop=>{
    const badge=(shop||{}).shopBadge||{},kind=String(badge.kind||"").trim(),label=String(badge.label||"").trim();
    return kind&&label?'<span class="native-shop-badge '+esc(kind)+'">'+esc(label)+'</span>':"";
  };

  const destination=S.scope==="compare"?"compare":"command-center";
  const nav=document.querySelector(".nav");
  let commandNav=null,compareNav=null;
  if(nav){
    commandNav=Array.from(nav.querySelectorAll("button")).find(b=>b.textContent.trim()==="Command Center")||nav.querySelector("button");
    if(commandNav){
      commandNav.dataset.nativeDestination="command-center";
      commandNav.onclick=()=>go({scope:"portfolio"});
    }
    compareNav=nav.querySelector('[data-native-destination="compare"]');
    if(!compareNav){
      compareNav=document.createElement("button");
      compareNav.type="button";
      compareNav.textContent="So sánh Shop";
      compareNav.dataset.nativeDestination="compare";
      if(commandNav&&commandNav.nextSibling)nav.insertBefore(compareNav,commandNav.nextSibling);
      else nav.appendChild(compareNav);
    }
    compareNav.onclick=()=>go({scope:"compare",left:S.left,right:S.right,horizon:S.horizon});
    nav.querySelectorAll("button").forEach(b=>b.classList.remove("active"));
    (destination==="compare"?compareNav:commandNav)?.classList.add("active");
  }

  const bar=document.createElement("div");
  bar.className="native-scope-bar";
  const commandControls=
    '<div class="native-tabs" role="group" aria-label="Phạm vi Command Center">'+
      '<button type="button" class="native-tab" data-native-scope="portfolio" aria-pressed="false">Toàn hệ thống</button>'+
      '<button type="button" class="native-tab" data-native-scope="shop" aria-pressed="false">Theo shop</button>'+
    '</div>'+
    '<div class="native-picker" id="nativeShopPicker"><label for="nativeShopSelect">SHOP</label><select id="nativeShopSelect"></select></div>';
  const compareControls=
    '<div class="native-picker" id="nativeComparePicker">'+
      '<div class="native-shop-identity"><span class="native-shop-name">SHOP A</span><span id="nativeLeftBadge"></span><select id="nativeLeftSelect" aria-label="Shop A"></select></div>'+
      '<span class="native-shop-name">VS</span>'+
      '<div class="native-shop-identity"><span class="native-shop-name">SHOP B</span><span id="nativeRightBadge"></span><select id="nativeRightSelect" aria-label="Shop B"></select></div>'+
    '</div>';
  bar.innerHTML='<span class="native-preprod">PREPRODUCTION</span>'+
    (destination==="compare"?compareControls:commandControls)+
    '<div class="native-lineage">Payload '+String(M.payloadBuildFingerprint||"").slice(0,10)+' · V2 '+String(M.sourceV2TemplateSha256||"").slice(0,10)+'</div>';
  header.insertAdjacentElement("afterend",bar);

  const opts=shops.map(x=>'<option value="'+esc(x.shopId)+'">'+esc(x.displayName||x.shopId)+'</option>').join("");
  if(destination==="command-center"){
    const shopSelect=document.getElementById("nativeShopSelect");
    if(shopSelect){shopSelect.innerHTML=opts;shopSelect.value=S.shop;shopSelect.onchange=e=>go({scope:"shop",shop:e.target.value})}
    document.querySelectorAll("[data-native-scope]").forEach(b=>{
      const active=b.dataset.nativeScope===S.scope;
      b.classList.toggle("active",active);
      b.setAttribute("aria-pressed",active?"true":"false");
      b.onclick=()=>go({scope:b.dataset.nativeScope});
    });
    const picker=document.getElementById("nativeShopPicker");
    if(picker)picker.classList.toggle("native-hidden",S.scope!=="shop");
  }else{
    const leftSelect=document.getElementById("nativeLeftSelect"),rightSelect=document.getElementById("nativeRightSelect");
    if(leftSelect&&rightSelect){
      leftSelect.innerHTML=opts;rightSelect.innerHTML=opts;
      leftSelect.value=S.left;rightSelect.value=S.right;
      const leftBadge=document.getElementById("nativeLeftBadge"),rightBadge=document.getElementById("nativeRightBadge");
      if(leftBadge)leftBadge.innerHTML=shopBadgeHtml(byId[S.left]);
      if(rightBadge)rightBadge.innerHTML=shopBadgeHtml(byId[S.right]);
      leftSelect.onchange=e=>{let right=S.right;if(right===e.target.value)right=shops.find(x=>x.shopId!==e.target.value)?.shopId||right;go({scope:"compare",left:e.target.value,right,horizon:S.horizon})};
      rightSelect.onchange=e=>{let left=S.left;if(left===e.target.value)left=shops.find(x=>x.shopId!==e.target.value)?.shopId||left;go({scope:"compare",left,right:e.target.value,horizon:S.horizon})};
    }
  }

  function go(next){const u=new URL(location.href);Object.entries(next).forEach(([k,v])=>u.searchParams.set(k,v));location.href=u.toString()}

  const appShell=document.querySelector(".app"),sidebar=document.querySelector(".sidebar"),hoverZone=document.getElementById("sidebarHoverZone");
  let sidebarRail=document.querySelector(".native-sidebar-rail");
  if(appShell&&sidebar&&!sidebarRail){
    sidebarRail=document.createElement("div");
    sidebarRail.className="native-sidebar-rail";
    document.body.insertBefore(sidebarRail,document.body.firstChild);
    sidebarRail.appendChild(sidebar);
    if(hoverZone)document.body.appendChild(hoverZone);
  }
  function syncSidebarRailMode(){
    if(!appShell||!sidebarRail)return;
    const unpinned=appShell.classList.contains("sidebar-unpinned");
    const peek=appShell.classList.contains("sidebar-peek");
    sidebarRail.classList.toggle("unpinned",unpinned);
    sidebarRail.classList.toggle("peek",unpinned&&peek);
    if(hoverZone)hoverZone.classList.toggle("native-sidebar-hover-active",unpinned);
  }
  if(appShell)new MutationObserver(syncSidebarRailMode).observe(appShell,{attributes:true,attributeFilter:["class"]});
  syncSidebarRailMode();

  const title=header.querySelector("h1"),subtitle=header.querySelector("p");
  if(S.scope==="portfolio"){if(title)title.textContent="Command Center · Toàn hệ thống";if(subtitle)subtitle.textContent="Tổng hợp tất cả shop · cùng cửa sổ dữ liệu đã đối soát";return}
  if(S.scope==="shop"){if(title)title.textContent="Command Center · "+(byId[S.shop]?.displayName||S.shop);if(subtitle)subtitle.textContent="Phạm vi shop · Command Center V2";return}

  if(title)title.textContent="So sánh Shop";
  if(subtitle)subtitle.textContent="Phân tích chênh lệch kết quả kinh doanh giữa hai shop trên cùng kỳ dữ liệu";
  const pair=(B.comparePairs||[]).find(x=>(x.leftShopId===S.left&&x.rightShopId===S.right)||(x.leftShopId===S.right&&x.rightShopId===S.left));
  if(!pair)return;
  const reversed=pair.leftShopId!==S.left;
  const leftName=byId[S.left]?.displayName||S.left,rightName=byId[S.right]?.displayName||S.right;
  const leftBadgeHtml=shopBadgeHtml(byId[S.left]),rightBadgeHtml=shopBadgeHtml(byId[S.right]);
  const shopHead=(name,badge)=>'<span class="native-table-shop-head"><span>'+esc(name)+'</span>'+badge+'</span>';
  const horizons=pair.horizons||{};
  if(!Object.keys(horizons).length)return;
  const order=(pair.horizonOrder||["latestDay","last7","mtd"]).filter(k=>horizons[k]);
  const horizonKey=horizons[S.horizon]?S.horizon:(pair.defaultHorizon&&horizons[pair.defaultHorizon]?pair.defaultHorizon:order[order.length-1]);
  const H=horizons[horizonKey];
  const lh=reversed?(H.rightHeadline||{}):(H.leftHeadline||{}),rh=reversed?(H.leftHeadline||{}):(H.rightHeadline||{});
  function metric(key){const m=(H.metrics||{})[key]||{};return reversed?{leftValue:Number(m.rightValue||0),rightValue:Number(m.leftValue||0)}:{leftValue:Number(m.leftValue||0),rightValue:Number(m.rightValue||0)}}
  function compareKpi(label,key,type){
    const m=metric(key),lv=m.leftValue,rv=m.rightValue,d=rv-lv;
    return '<div class="kpi"><div class="label">'+esc(label)+' · '+esc(leftName)+'</div><div class="value">'+fmt[type](lv)+'</div><div class="compare-kpi-peer">'+esc(rightName)+' · '+fmt[type](rv)+'</div><div class="delta '+(d>0?"up":d<0?"down":"neutral")+'">'+esc(rightName)+' so với '+esc(leftName)+' '+deltaText(rv,lv)+'</div></div>';
  }
  function tableRow(label,key,type){
    const m=metric(key),lv=m.leftValue,rv=m.rightValue;
    return '<tr><td class="metric">'+esc(label)+'</td><td>'+fmt[type](lv)+'</td><td>'+fmt[type](rv)+'</td><td>'+deltaText(rv,lv)+'</td></tr>';
  }
  function leader(label,key,better){
    const m=metric(key),lv=m.leftValue,rv=m.rightValue;
    let lead="Ngang nhau",cls="native-lead-even";
    if(Math.abs(rv-lv)>1e-9){
      const rightBetter=better==="low"?rv<lv:rv>lv;
      lead=rightBetter?rightName:leftName;cls=rightBetter?"native-lead-right":"native-lead-left";
    }
    return '<div class="compare-lead-row"><b>'+esc(label)+'</b><span class="'+cls+'">'+esc(lead)+'</span></div>';
  }
  function compareTableCard(title,sub,rows){
    return '<section class="card compare-table-card"><h3>'+esc(title)+'</h3><div class="card-sub">'+esc(sub)+'</div><div class="native-table-wrap" style="margin-top:16px"><table class="native-table"><thead><tr><th>Chỉ số</th><th>'+shopHead(leftName,leftBadgeHtml)+'</th><th>'+shopHead(rightName,rightBadgeHtml)+'</th><th>'+esc(rightName)+' so với '+esc(leftName)+'</th></tr></thead><tbody>'+rows+'</tbody></table></div></section>';
  }
  function productPanel(shopId,name,data,mode){
    data=data||{};const ps=data.topProducts||[];
    const shares=mode==="ads"
      ?[["Top 1",data.top1AdsSalesShare],["Top 3",data.top3AdsSalesShare],["Top 5",data.top5AdsSalesShare]]
      :[["Top 1",data.top1GmvShare],["Top 3",data.top3GmvShare],["Top 5",data.top5GmvShare]];
    const items=ps.map(p=>'<div class="native-product-item"><div><div class="native-product-name" title="'+esc(p.displayName||"Chưa xác định tên sản phẩm")+'">'+esc(p.displayName||"Chưa xác định tên sản phẩm")+'</div>'+(p.secondarySku?'<div class="native-product-meta">SKU: '+esc(p.secondarySku)+'</div>':'')+'</div><div class="native-product-value">'+(mode==="ads"?fmt.money(p.adsAttributedSales)+' · '+fmt.roas(p.roas):fmt.money(p.confirmedGmv)+' · '+fmt.pct(p.confirmedGmvShare))+'</div></div>').join("");
    return '<section class="card compare-product-panel"><h4>'+esc(name)+shopBadgeHtml(byId[shopId])+'</h4><div class="native-concentration">'+shares.map(x=>'<div><b>'+fmt.pct(x[1]||0)+'</b><span>'+x[0]+'</span></div>').join("")+'</div><div class="native-product-list">'+(items||'<div class="card-sub">Chưa có dữ liệu sản phẩm trong kỳ.</div>')+'</div></section>';
  }

  if(subtitle)subtitle.textContent="Phân tích hai shop · cùng kỳ dữ liệu "+H.coverage.windowStart+" → "+H.coverage.windowEnd;
  Array.from(main.children).forEach(el=>{if(el!==header&&el!==bar)el.style.display="none"});
  const view=document.createElement("section");view.className="native-compare open";

  const periodCards='<div class="period-grid compare-period-grid">'+order.map(k=>{
    const h=horizons[k]||{},m=(h.metrics||{}).placedGmv||{};
    const lm=reversed?Number(m.rightValue||0):Number(m.leftValue||0),rm=reversed?Number(m.leftValue||0):Number(m.rightValue||0);
    const cov=h.coverage||{};
    const dateLabel=cov.windowStart===cov.windowEnd?fmtDate(cov.windowEnd):fmtDate(cov.windowStart)+"–"+fmtDate(cov.windowEnd);
    const d=deltaPct(rm,lm);
    return '<button class="period-card compare-period-card '+(k===horizonKey?"active":"")+'" data-compare-horizon="'+esc(k)+'" aria-pressed="'+(k===horizonKey?"true":"false")+'">'+
      '<div class="period-title">'+esc(h.label||k)+' · '+esc(dateLabel)+'</div>'+
      '<div class="period-value">'+fmt.moneyFull(lm)+'</div>'+
      '<div><span class="period-delta '+(Number(d||0)>=0?"up":"down")+'">'+(d===null?"—":((d>0?"+":"")+nv.format(d*100)+"%"))+'</span><span class="period-compare">'+esc(rightName)+' '+fmt.moneyFull(rm)+'</span></div>'+
      '<div class="period-note">GMV '+esc(leftName)+' · cùng kỳ dữ liệu</div></button>';
  }).join("")+'</div>';
  const headlineCards=[
    ["GMV","placedGmv","money"],["Đơn hàng","placedOrders","int"],["AOV","placedAov","money"],
    ["CVR","placedCvr","pct"],["Doanh thu thuần","netSalesAfterCancel","money"],["ROAS Ads","roas","roas"]
  ].map(x=>compareKpi(...x)).join("");

  const driverLabels={productClicks:"Lượt nhấp sản phẩm",placedCvr:"CVR",placedAov:"AOV"};
  const rawDriver=H.driverDecomposition||{};
  const drivers=(rawDriver.drivers||[]).map(x=>({...x,displayLabel:driverLabels[x.key]||x.key,effectValueRightVsLeft:reversed?-Number(x.effectValueRightVsLeft||0):Number(x.effectValueRightVsLeft||0)}));
  const topDriver=drivers.slice().sort((a,b)=>Math.abs(b.effectValueRightVsLeft)-Math.abs(a.effectValueRightVsLeft))[0];
  function betterName(key,better){
    const m=metric(key),lv=m.leftValue,rv=m.rightValue;
    if(Math.abs(rv-lv)<=1e-9)return "hai shop tương đương";
    const rightBetter=better==="low"?rv<lv:rv>lv;
    return rightBetter?rightName:leftName;
  }
  const gmvMetric=metric("placedGmv"),gmvDelta=deltaPct(gmvMetric.rightValue,gmvMetric.leftValue);
  const scaleSentence=gmvMetric.leftValue===gmvMetric.rightValue
    ?'Quy mô GMV của hai shop đang tương đương trong kỳ.'
    :(gmvMetric.rightValue>gmvMetric.leftValue
      ?'<strong>'+esc(rightName)+'</strong> đang dẫn về GMV; GMV '+esc(rightName)+' cao hơn '+esc(leftName)+' '+Math.abs(Number(gmvDelta||0)*100).toLocaleString("vi-VN",{maximumFractionDigits:1})+'%.'
      :'<strong>'+esc(leftName)+'</strong> đang dẫn về GMV; GMV '+esc(rightName)+' thấp hơn '+esc(leftName)+' '+Math.abs(Number(gmvDelta||0)*100).toLocaleString("vi-VN",{maximumFractionDigits:1})+'%.');
  const dimensionDefs=[
    ["CVR","placedCvr","high"],["ROAS","roas","high"],["AOV","placedAov","high"],
    ["chi phí nền tảng","totalPlatformCostRatio","low"],["tỷ lệ doanh thu hủy","cancelledSalesRate","low"]
  ];
  const leftStrengths=[],rightStrengths=[];
  dimensionDefs.forEach(x=>{
    const lead=betterName(x[1],x[2]);
    if(lead===leftName)leftStrengths.push(x[0]);
    if(lead===rightName)rightStrengths.push(x[0]);
  });
  const strengthParts=[];
  if(leftStrengths.length)strengthParts.push('<strong>'+esc(leftName)+'</strong> dẫn về '+esc(leftStrengths.join(", ")));
  if(rightStrengths.length)strengthParts.push('<strong>'+esc(rightName)+'</strong> dẫn về '+esc(rightStrengths.join(", ")));
  const strengthSentence=strengthParts.length?strengthParts.join('; ')+'.':'Các chỉ số hiệu suất chính đang tương đương.';
  const driverAdvantage=topDriver?(topDriver.effectValueRightVsLeft>=0?rightName:leftName):"";
  const driverSentence=topDriver
    ?'Yếu tố tạo chênh lệch lớn nhất là <strong>'+esc(topDriver.displayLabel)+'</strong>, đóng góp khoảng '+fmt.money(Math.abs(topDriver.effectValueRightVsLeft))+' vào lợi thế của <strong>'+esc(driverAdvantage)+'</strong>.'
    :'Chưa đủ dữ liệu để xác định yếu tố chính tạo ra chênh lệch GMV.';
  const leadSummary=leader("Quy mô GMV","placedGmv","high")+leader("Đơn hàng","placedOrders","high")+leader("CVR","placedCvr","high")+leader("AOV","placedAov","high")+leader("ROAS","roas","high")+leader("Chi phí nền tảng","totalPlatformCostRatio","low")+leader("Tỷ lệ doanh thu hủy","cancelledSalesRate","low");

  const revenueRows=
    tableRow("GMV đặt hàng","placedGmv","money")+tableRow("GMV xác nhận","confirmedGmv","money")+tableRow("GMV thanh toán","paidGmv","money")+
    tableRow("Doanh thu hủy","cancelledSales","money")+tableRow("Tỷ lệ doanh thu hủy / GMV","cancelledSalesRate","pct")+
    tableRow("Doanh thu hoàn/trả","returnedRefundedSales","money")+tableRow("Tỷ lệ hoàn/trả / GMV","returnedRefundedSalesRate","pct")+
    tableRow("Doanh thu thuần sau hủy","netSalesAfterCancel","money");

  const costRows=
    tableRow("Phí cố định","fixedFee","money")+tableRow("Phí dịch vụ","serviceFee","money")+tableRow("Phí giao dịch","transactionFee","money")+
    tableRow("Tổng phí đơn hàng","orderFees","money")+tableRow("Phí đơn hàng / Doanh thu thuần","orderFeeRatio","pct")+
    tableRow("Chi phí Ads / Doanh thu thuần","adsSpendToNetSales","pct")+tableRow("Tỷ lệ chi phí nền tảng","totalPlatformCostRatio","pct");

  const adsRows=
    tableRow("Chi phí Ads","adsSpend","money")+tableRow("Doanh thu từ Ads","adsAttributedSales","money")+
    tableRow("Tỷ trọng doanh thu Ads / GMV","adsAttributedShareOfPlacedGmv","pct")+tableRow("ROAS","roas","roas")+
    tableRow("Ads CTR","adsCtr","pct")+tableRow("Ads CVR","adsCvr","pct");

  const trafficRaw=H.traffic||{left:[],right:[]};
  const tl=reversed?(trafficRaw.right||[]):(trafficRaw.left||[]),tr=reversed?(trafficRaw.left||[]):(trafficRaw.right||[]);
  const tmap=new Map();
  tl.forEach(x=>{const k=x.channelGroup||x.trafficSource;tmap.set(k,{left:x,right:null})});
  tr.forEach(x=>{const k=x.channelGroup||x.trafficSource;const row=tmap.get(k)||{left:null,right:null};row.right=x;tmap.set(k,row)});
  const trafficRows=Array.from(tmap.entries()).sort((a,b)=>Number((b[1].left?.sales||0)+(b[1].right?.sales||0))-Number((a[1].left?.sales||0)+(a[1].right?.sales||0))).map(([k,v])=>{
    const l=v.left||{},r=v.right||{};
    return '<tr><td class="metric">'+esc(k)+'</td><td>'+fmt.money(l.sales)+'</td><td>'+fmt.pct(l.salesShareOfTraffic)+'</td><td>'+fmt.pct(l.conversionRate)+'</td><td>'+fmt.money(r.sales)+'</td><td>'+fmt.pct(r.salesShareOfTraffic)+'</td><td>'+fmt.pct(r.conversionRate)+'</td></tr>';
  }).join("");

  const adp=H.adsProducts||{},adLeft=reversed?(adp.right||{}):(adp.left||{}),adRight=reversed?(adp.left||{}):(adp.right||{});
  const pm=pair.productMtd||{},pmLeft=reversed?(pm.right||{}):(pm.left||{}),pmRight=reversed?(pm.left||{}):(pm.right||{});
  const businessProducts=horizonKey==="mtd"
    ?'<div class="section-title"><h3>Cơ cấu doanh số sản phẩm · Tháng này</h3><p>Dữ liệu doanh số sản phẩm được tổng hợp theo tháng. Sản phẩm của từng shop được giữ độc lập.</p></div><div class="compare-product-grid">'+productPanel(S.left,leftName,pmLeft,"business")+productPanel(S.right,rightName,pmRight,"business")+'</div>'
    :'<div class="section-title"><h3>Cơ cấu doanh số sản phẩm · Tháng này</h3><p>Không hiển thị theo kỳ '+esc(H.label||horizonKey)+' vì doanh số sản phẩm hiện được tổng hợp theo tháng. Chuyển sang “Tháng này” để xem cơ cấu doanh số mà không tạo so sánh lệch.</p></div><section class="card"><div class="issue-empty">Chỉ có dữ liệu sản phẩm theo tháng ở nguồn hiện tại.</div></section>';

  view.innerHTML=
    periodCards+
    '<section class="pulse compare-pulse"><div class="pulse-label">Diễn biến so sánh</div><h2>'+scaleSentence+'</h2><p>'+strengthSentence+' '+driverSentence+'</p><p class="good">Không xếp hạng tổng thể; chỉ đọc lợi thế theo từng khía cạnh trên cùng kỳ dữ liệu.</p><div class="confidence">Cùng kỳ dữ liệu</div></section>'+
    '<div class="selection">Đang xem: '+esc(H.label||horizonKey)+' · '+esc(fmtDate(H.coverage.windowStart))+(H.coverage.windowStart===H.coverage.windowEnd?'':'–'+esc(fmtDate(H.coverage.windowEnd)))+'</div>'+
    '<div class="kpi-grid">'+headlineCards+'</div>'+
    '<div class="content-grid compare-overview-grid">'+
      '<section class="card"><h3>Vì sao GMV khác nhau?</h3><div class="card-sub">Phân rã chênh lệch GMV theo Lượt nhấp sản phẩm × CVR × AOV.</div><div class="driver-list" id="nativeGapDrivers"></div><div class="support"><b>Cơ sở phân tích</b><span>Tổng tác động của các yếu tố đã được đối soát với chênh lệch GMV của hai shop trong cùng kỳ dữ liệu.</span></div></section>'+
      '<section class="card"><h3>Shop dẫn theo từng khía cạnh</h3><div class="card-sub">Không gom thành một điểm số hay xếp hạng tổng thể.</div><div class="compare-lead-list">'+leadSummary+'</div></section>'+
    '</div>'+
    '<div class="section-title"><h3>Doanh thu & chất lượng đơn hàng</h3><p>Đặt hàng → Xác nhận/Thanh toán → Hủy/Hoàn → Doanh thu thuần.</p></div>'+
    compareTableCard("Funnel doanh thu","Đọc cùng một luồng doanh thu giữa hai shop.",revenueRows)+
    '<div class="section-title"><h3>Chi phí & hiệu quả Ads</h3><p>Đặt cấu trúc phí cạnh hiệu suất quảng cáo để nhìn được tăng trưởng có đang mua bằng chi phí hay không.</p></div>'+
    '<div class="content-grid compare-finance-grid">'+
      compareTableCard("Cơ cấu chi phí","Phí đơn hàng và Ads so với doanh thu thuần.",costRows)+
      compareTableCard("Hiệu quả quảng cáo","Quy mô chi tiêu và hiệu suất Ads.",adsRows)+
    '</div>'+
    '<div class="section-title"><h3>Nguồn truy cập & chuyển đổi</h3><p>So sánh các nhóm nguồn truy cập trên cùng kỳ dữ liệu.</p></div>'+
    '<section class="card compare-table-card"><div class="native-table-wrap"><table class="native-table native-traffic-table"><thead><tr><th>Nguồn</th><th>'+shopHead(leftName,leftBadgeHtml)+'<br>Doanh thu</th><th>Tỷ trọng</th><th>CVR</th><th>'+shopHead(rightName,rightBadgeHtml)+'<br>Doanh thu</th><th>Tỷ trọng</th><th>CVR</th></tr></thead><tbody>'+trafficRows+'</tbody></table></div></section>'+
    '<div class="section-title"><h3>Hiệu quả quảng cáo theo sản phẩm</h3><p>Tỷ trọng doanh thu từ Ads theo sản phẩm trong cùng kỳ dữ liệu.</p></div>'+
    '<div class="compare-product-grid">'+productPanel(S.left,leftName,adLeft,"ads")+productPanel(S.right,rightName,adRight,"ads")+'</div>'+
    businessProducts+
    '<div class="card-sub compare-footnote">Kết quả kinh doanh, chi phí, Ads và nguồn truy cập dùng cùng kỳ dữ liệu. Doanh số theo sản phẩm hiện chỉ hiển thị ở kỳ Tháng này; sản phẩm giữa các shop được giữ độc lập.</div>';
  main.appendChild(view);

  const maxEffect=Math.max(1,...drivers.map(x=>Math.abs(x.effectValueRightVsLeft)));
  const driverBox=document.getElementById("nativeGapDrivers");
  if(driverBox)driverBox.innerHTML=drivers.length?drivers.map(x=>'<div class="driver-row"><b>'+esc(x.displayLabel)+'</b><span class="effect '+(x.effectValueRightVsLeft>=0?"up":"down")+'">'+(x.effectValueRightVsLeft>=0?"+":"")+fmt.money(x.effectValueRightVsLeft)+'</span><span class="driver-note">'+esc(x.effectValueRightVsLeft>=0?rightName:leftName)+' được lợi</span><span class="track"><i class="'+(x.effectValueRightVsLeft<0?"neg":"")+'" style="width:'+Math.max(5,Math.round(Math.abs(x.effectValueRightVsLeft)/maxEffect*100))+'%"></i></span></div>').join(""):'<div class="issue-empty">Chưa đủ dữ liệu để phân rã chênh lệch GMV.</div>';

  document.querySelectorAll("[data-compare-horizon]").forEach(b=>b.onclick=()=>go({scope:"compare",left:S.left,right:S.right,horizon:b.dataset.compareHorizon}));
})();
"""


def _patch_native_template(v2_source: str,bundle: Mapping[str,Any],payload_fp: str,semantic_fp: str,v2_sha: str) -> str:
    derived=derive_v2_compat_template(v2_source)
    if "</style>" not in derived:
        raise ValueError("V2 style closing tag not found")
    derived=derived.replace("</style>",NATIVE_STYLE+"\n</style>",1)

    nav_anchor='<button class="active">Command Center</button>'
    nav_patch='<button class="active" data-native-destination="command-center">Command Center</button><button data-native-destination="compare">So sánh Shop</button>'
    if nav_anchor not in derived:
        raise ValueError("V2 sidebar Command Center nav anchor not found")
    derived=derived.replace(nav_anchor,nav_patch,1)

    bootstrap=_bootstrap(bundle,payload_fp,semantic_fp,v2_sha)
    if DATA_MARKER not in derived:
        raise ValueError("V2 data marker not found")
    derived=derived.replace(DATA_MARKER,bootstrap,1)

    if "</body>" not in derived:
        raise ValueError("V2 body closing tag not found")
    derived=derived.replace("</body>","<script>"+NATIVE_RUNTIME+"</script>\n</body>",1)
    derived=derived.replace(
        "<title>Unipalm Command Center V2 — D2</title>",
        "<title>Unipalm Command Center V2 — Multi-Shop PREPRODUCTION</title>",
        1,
    )
    return derived


def build_native_v2_multi_shop(
    *,
    payload_dir: str|Path,
    v2_template_path: str|Path,
    output_dir: str|Path,
) -> Dict[str,Any]:
    payload_dir=Path(payload_dir)
    v2_template_path=Path(v2_template_path)
    output_dir=Path(output_dir)

    payload=_read_json(payload_dir/"ui_payload.json")
    manifest=_read_json(payload_dir/"payload_manifest.json")
    qa=_read_json(payload_dir/"payload_qa_report.json")
    if qa.get("status")!="PASS" or not bool(qa.get("payloadReady")):
        raise ValueError("UI payload QA is not PASS/ready")

    payload_fp=_s(manifest.get("payloadBuildFingerprint"))
    semantic_fp=_s(manifest.get("sourceSemanticFingerprint"))
    if payload_fp!=_s(qa.get("payloadBuildFingerprint")):
        raise ValueError("payload fingerprint mismatch")
    if semantic_fp!=_s(qa.get("sourceSemanticFingerprint")):
        raise ValueError("semantic fingerprint mismatch")
    if _sha256_json(payload)!=_s(manifest.get("payloadSha256")):
        raise ValueError("canonical UI payload hash mismatch")

    safety=payload.get("safety") or {}
    if any(bool(safety.get(x)) for x in (
        "productionDataMartWritten","productionUiModified","legacyPayloadPublished",
        "productionCutoverAuthorized","productionActivationEnabled",
    )):
        raise ValueError("unsafe payload cannot be used for native V2")

    source=v2_template_path.read_text(encoding="utf-8")
    v2_checks=validate_v2_template(source)
    if not all(v2_checks.values()):
        raise ValueError(f"production V2 foundation invalid: {v2_checks}")
    source_sha=_sha256_bytes(source.encode("utf-8"))

    bundle=_bundle_from_payload(payload)
    html=_patch_native_template(source,bundle,payload_fp,semantic_fp,source_sha)
    html_bytes=html.encode("utf-8")
    html_sha=_sha256_bytes(html_bytes)
    build_fp=_sha256_json({
        "payloadBuildFingerprint":payload_fp,
        "sourceV2Sha256":source_sha,
        "nativePatchVersion":NATIVE_PATCH_VERSION,
        "presentationContractVersion":_presentation_contract().get("version"),
        "v2CompatibilityPatchVersion":V2_COMPATIBILITY_PATCH_VERSION,
        "htmlSha256":html_sha,
    })

    checks=[]
    def ck(name,ok,detail=None):
        checks.append({"name":name,"status":"PASS" if ok else "FAIL","detail":detail or {}})
    ck("payload_qa_pass",True)
    ck("production_v2_foundation_pass",all(v2_checks.values()),v2_checks)
    ck("production_v2_source_unchanged",_sha256_bytes(v2_template_path.read_bytes())==source_sha)
    ck("native_destination_architecture",all(x in html for x in (
        'data-native-destination="command-center"',
        'data-native-destination="compare"',
        'So sánh Shop',
        'data-native-scope="portfolio"',
        'data-native-scope="shop"',
    )) and 'data-native-scope="compare"' not in html)
    ck("native_accessibility_semantics",all(x in html for x in (
        'aria-label="Phạm vi Command Center"',
        'aria-pressed="false"',
        'label for="nativeShopSelect"',
        'aria-label="Shop A"',
        'aria-label="Shop B"',
    )))
    ck("compare_v2_visual_primitives",all(x in html for x in (
        'period-grid compare-period-grid',
        'period-card compare-period-card',
        'pulse compare-pulse',
        'class="kpi-grid"',
        'content-grid compare-overview-grid',
        'class="section-title"',
        'card compare-table-card',
        'class="driver-list"',
        'class="driver-row"',
    )))
    ck("compare_business_workspace",all(x in html for x in (
        'data-compare-horizon',
        'Diễn biến so sánh',
        'Doanh thu & chất lượng đơn hàng',
        'Funnel doanh thu',
        'Cơ cấu chi phí',
        'Hiệu quả quảng cáo',
        'Nguồn truy cập & chuyển đổi',
        'Hiệu quả quảng cáo theo sản phẩm',
        'Cơ cấu doanh số sản phẩm · Tháng này',
    )))
    ck("compare_uses_contract_horizons_only",all(
        set((p.get("horizons") or {}).keys())=={"latestDay","last7","mtd"}
        for p in bundle["comparePairs"]
    ))
    ck("compare_bundle_has_no_duplicate_v2_payloads",all(
        "leftV2Payload" not in p and "rightV2Payload" not in p
        for p in bundle["comparePairs"]
    ))
    presentation=_presentation_checks(bundle)
    ck("ui_v2_inter_typography",presentation["fontInter"] and presentation["nativeDoesNotOverrideFont"],presentation)
    ck("ui_v2_shared_design_language",
       presentation["sharedDesignLanguageActive"]
       and presentation["nativeUsesOnlyFoundationPalette"],
       presentation)
    ck("ui_v2_language_system",not presentation["forbiddenVisibleCopyHits"],presentation)
    ck("ui_v2_operator_wording",all(x in html for x in (
        'Phân tích hai shop · cùng kỳ dữ liệu',
        'Chỉ số',
        'Chi phí nền tảng',
        'Tỷ lệ doanh thu hủy',
        'Lượt nhấp sản phẩm',
    )))
    ck("compare_business_pulse",all(x in html for x in (
        'Diễn biến so sánh',
        'Yếu tố tạo chênh lệch lớn nhất là <strong>',
        'Không xếp hạng tổng thể',
        '["CVR","placedCvr","high"]',
        '["ROAS","roas","high"]',
    )))
    ck("compare_no_parallel_visual_shell",all(x not in NATIVE_RUNTIME for x in (
        '<div class="native-compare-grid">',
        '<div class="native-compare-card">',
        '<section class="native-section">',
        '<div class="native-period-tabs"',
    )))
    ck("command_center_scope_renderer_passthrough",all(x in NATIVE_RUNTIME for x in (
        'if(S.scope==="portfolio"){if(title)title.textContent=',
        'if(S.scope==="shop"){if(title)title.textContent=',
        'const destination=S.scope==="compare"?"compare":"command-center"',
    )))
    ck("compare_is_separate_destination",all(x in NATIVE_RUNTIME for x in (
        'compareNav.textContent="So sánh Shop"',
        'compareNav.dataset.nativeDestination="compare"',
        'commandNav.dataset.nativeDestination="command-center"',
    )))
    ck("portfolio_is_all_shops_view",all(x in NATIVE_RUNTIME for x in (
        'Toàn hệ thống',
        'Tổng hợp tất cả shop',
    )))
    portfolio_v2=(bundle.get("portfolio") or {}).get("v2Payload") or {}
    portfolio_cc=portfolio_v2.get("commandCenter") or {}
    portfolio_periods=portfolio_cc.get("periods") or {}
    portfolio_sources=(portfolio_v2.get("health") or {}).get("sources") or []
    ck(
        "portfolio_semantic_binding",
        _s((portfolio_cc.get("labels") or {}).get("yesterday")).startswith("Ngày gần nhất")
        and bool(portfolio_sources)
        and _s(portfolio_sources[0].get("name"))=="Toàn hệ thống"
        and all(
            not bool((p.get("current") or {}).get("visitsAvailable"))
            for p in portfolio_periods.values()
        )
        and all(
            (not bool(p.get("comparisonAvailable")))
            or (
                bool((p.get("comparisonCoverage") or {}).get("currentComplete"))
                and bool((p.get("comparisonCoverage") or {}).get("previousComplete"))
            )
            for p in portfolio_periods.values()
        ),
        {
            "latestLabel":(portfolio_cc.get("labels") or {}).get("yesterday"),
            "sourceName":portfolio_sources[0].get("name") if portfolio_sources else "",
            "periodCount":len(portfolio_periods),
        },
    )
    shop_semantic_errors=[]
    for sid,view in (bundle.get("shopViews") or {}).items():
        cc=((view.get("v2Payload") or {}).get("commandCenter") or {})
        periods=cc.get("periods") or {}
        latest=periods.get("yesterday") or {}
        last7=periods.get("last7") or {}
        mtd=periods.get("mtd") or {}
        policy=view.get("semanticPolicy") or {}
        product_coverage=view.get("productCoverage") or {}
        if not bool((latest.get("current") or {}).get("visitsAvailable")):
            shop_semantic_errors.append((sid,"latest_day_visits_unavailable"))
        if bool((last7.get("current") or {}).get("visitsAvailable")):
            shop_semantic_errors.append((sid,"last7_visits_summed"))
        if bool((mtd.get("current") or {}).get("visitsAvailable")):
            shop_semantic_errors.append((sid,"mtd_visits_summed"))
        if _s(policy.get("multiDayUniquePolicy"))!="DAILY_ONLY_DO_NOT_SUM":
            shop_semantic_errors.append((sid,"shop_unique_policy"))
        if _s(product_coverage.get("alignment"))!="SOURCE_MTD_SHOP_SCOPE_ONLY":
            shop_semantic_errors.append((sid,"product_alignment"))
        for key,p in periods.items():
            if bool(p.get("comparisonAvailable")) and not (
                bool((p.get("comparisonCoverage") or {}).get("currentComplete"))
                and bool((p.get("comparisonCoverage") or {}).get("previousComplete"))
            ):
                shop_semantic_errors.append((sid,key,"comparison_window"))
    ck(
        "shop_semantic_binding",
        not shop_semantic_errors,
        {"errors":shop_semantic_errors[:20]},
    )
    ck("sidebar_viewport_rail",all(x in NATIVE_STYLE for x in (
        '.native-sidebar-rail{position:fixed',
        'top:16px',
        'height:calc(100vh - 32px)',
        '.native-sidebar-rail.unpinned',
        '.native-sidebar-rail.unpinned.peek',
        '.native-sidebar-hover-active',
    )) and all(x in NATIVE_RUNTIME for x in (
        'document.body.insertBefore(sidebarRail,document.body.firstChild)',
        'sidebarRail.appendChild(sidebar)',
        'document.body.appendChild(hoverZone)',
        'syncSidebarRailMode',
        'sidebarRail.classList.toggle("unpinned",unpinned)',
        'hoverZone.classList.toggle("native-sidebar-hover-active",unpinned)',
    )) and 'window.scrollY' not in NATIVE_RUNTIME)
    ck("compare_shop_identity_badges",all(x in NATIVE_RUNTIME for x in (
        'nativeLeftBadge',
        'nativeRightBadge',
        'shopBadgeHtml',
    )) and all(x in NATIVE_STYLE for x in (
        '.native-shop-badge.preferred',
        '.native-shop-badge.mall',
    )))
    ck("compare_shop_identity_propagated",all(x in NATIVE_RUNTIME for x in (
        'shopHead(leftName,leftBadgeHtml)',
        'shopHead(rightName,rightBadgeHtml)',
        'productPanel(S.left,leftName',
        'productPanel(S.right,rightName',
    )) and '.native-table-shop-head' in NATIVE_STYLE)
    ck("compare_no_repeated_badge_legends",'compare-card-legend' not in NATIVE_RUNTIME and 'compare-card-legend' not in NATIVE_STYLE)
    ck("sidebar_unpin_position_continuity",all(x in NATIVE_STYLE for x in (
        '.native-sidebar-rail.unpinned{transform:translateX(-100%)',
        '.native-sidebar-rail.unpinned.peek',
    )) and 'sidebarRail.classList.toggle("peek",unpinned&&peek)' in NATIVE_RUNTIME)
    ck("legacy_compare_visual_css_removed",all(x not in NATIVE_STYLE for x in (
        '.native-compare-card',
        '.native-section{',
        '.native-period-tabs',
        '.native-two-col',
        '.native-exec-summary',
        '.native-driver-track',
    )))
    ck("ui_v2_product_naming_system",not presentation["productNamingErrors"],presentation)
    ck("registry_shop_scope_complete",set(bundle["shopViews"])=={_s(x.get("shopId")) for x in bundle["shops"]})
    expected_pairs=len(bundle["shops"])*(len(bundle["shops"])-1)//2
    ck("compare_pairs_complete",len(bundle["comparePairs"])==expected_pairs,{"expected":expected_pairs,"actual":len(bundle["comparePairs"])})
    ck("production_binding_absent",not bool((payload.get("capabilities") or {}).get("productionUiBinding")))
    shadow=bundle.get("shadowModeV1") or {}
    activation=shadow.get("activationControls") or {}
    shadow_capability=bool((payload.get("capabilities") or {}).get("productionCutoverShadowMode"))
    ck("shadow_mode_bound_without_activation",(
        (not shadow_capability and not shadow)
        or (
            shadow_capability
            and _s(shadow.get("mode"))=="PREPRODUCTION_OBSERVE_ONLY"
            and not bool(activation.get("productionActivationAllowed"))
            and not bool(activation.get("automaticCutoverEnabled"))
            and not bool(activation.get("cutoverAuthorized"))
            and not bool((payload.get("capabilities") or {}).get("productionCutover"))
        )
    ),{"status":_s(shadow.get("status")),"capability":shadow_capability})
    ck("preproduction_marked","PREPRODUCTION" in html)
    ck("v2_visual_foundation_preserved",all(x in html for x in (
        'id="sidebarPin"',"transform:scale(1.25)",'[data-theme="dark"]','class="pulse"','id="kpiGrid"'
    )))

    failed=[x for x in checks if x["status"]=="FAIL"]
    if failed:
        raise ValueError(f"native V2 QA failed: {[x['name'] for x in failed]}")

    output_dir.mkdir(parents=True,exist_ok=True)
    template_out=output_dir/"command_center_v2_multi_shop_native_template.html"
    template_out.write_text(html,encoding="utf-8")
    manifest_out={
        "layer":"command_center_v2_multi_shop_native",
        "status":"PREPRODUCTION",
        "period":bundle["period"],
        "sourcePayloadBuildFingerprint":payload_fp,
        "sourceSemanticFingerprint":semantic_fp,
        "sourceV2TemplateSha256":source_sha,
        "nativePatchVersion":NATIVE_PATCH_VERSION,
        "v2CompatibilityPatchVersion":V2_COMPATIBILITY_PATCH_VERSION,
        "nativeBuildFingerprint":build_fp,
        "htmlSha256":html_sha,
        "selectedShopCount":len(bundle["shops"]),
        "comparePairCount":len(bundle["comparePairs"]),
        "file":template_out.name,
        "safety":{
            "productionV2TemplateModified":False,
            "productionIndexModified":False,
            "productionDataMartWritten":False,
            "productionDeploymentPerformed":False,
            "productionCutoverAuthorized":False,
        },
    }
    _write_json(output_dir/"native_v2_manifest.json",manifest_out)
    qa_out={
        "status":"PASS",
        "nativeV2Ready":True,
        "checks":checks,
        "failedCheckCount":0,
        **{k:manifest_out[k] for k in (
            "period","sourcePayloadBuildFingerprint","sourceSemanticFingerprint",
            "sourceV2TemplateSha256","nativePatchVersion","v2CompatibilityPatchVersion",
            "nativeBuildFingerprint","selectedShopCount","comparePairCount","safety"
        )},
    }
    _write_json(output_dir/"native_v2_qa_report.json",qa_out)
    return qa_out
