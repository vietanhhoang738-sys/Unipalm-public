"""Native V2 Ads destination for PREPRODUCTION.

Ads is a single-shop operational workspace with day/week/month/year scopes.
The validated Product/Command Center layers stay intact; this wrapper adds the
Ads destination, reuses deterministic Product short names, and keeps every
recommendation/effect statement evidence-bound and non-causal.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Mapping

from . import ui_v2_product_short_names as _product_short
from .product_short_name import short_name_for_product


ADS_NATIVE_PATCH_VERSION = "native-ads-intelligence-v37"

ADS_STYLE = r"""
.ads-destination{display:grid;gap:18px;margin-top:4px}
.ads-hero{display:grid;grid-template-columns:minmax(0,1.45fr) minmax(300px,.8fr);border:1px solid var(--line);border-radius:16px;background:var(--surface);overflow:hidden}
.ads-hero-main{padding:24px 26px}.ads-hero-side{padding:20px;border-left:1px solid var(--line);background:var(--soft)}
.ads-eyebrow{font-size:10px;font-weight:700;color:var(--muted);letter-spacing:.02em}.ads-headline{margin-top:10px;font-size:24px;line-height:1.24;font-weight:720;letter-spacing:-.02em;color:var(--ink)}
.ads-copy{margin-top:8px;font-size:11px;line-height:1.55;color:var(--muted)}.ads-status{padding:14px;border:1px solid var(--line);border-radius:12px;background:var(--surface)}.ads-status b{display:block;font-size:12px;color:var(--ink)}.ads-status span{display:block;margin-top:6px;font-size:10px;line-height:1.5;color:var(--muted)}
.ads-scope-tabs{display:flex;gap:6px;flex-wrap:wrap}.ads-scope-tab{border:1px solid var(--line);background:var(--surface);color:var(--muted);padding:8px 11px;border-radius:9px;font-size:10px;font-weight:700;cursor:pointer}.ads-scope-tab.active{background:var(--green);border-color:var(--green);color:#fff}.ads-scope-tab:disabled{opacity:.42;cursor:not-allowed}.ads-option-select{min-width:150px}
.ads-kpis{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:12px}.ads-kpi{padding:15px;border:1px solid var(--line);border-radius:13px;background:var(--surface)}.ads-kpi-label{font-size:9.5px;color:var(--muted2);font-weight:700}.ads-kpi-value{margin-top:9px;font-size:20px;line-height:1.1;font-weight:730;color:var(--ink);font-variant-numeric:tabular-nums}.ads-kpi-note{margin-top:6px;font-size:9px;color:var(--muted);line-height:1.4}.ads-kpi-delta.up{color:var(--green)}.ads-kpi-delta.down{color:var(--red)}
.ads-grid-2{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}.ads-card{padding:20px;border:1px solid var(--line);border-radius:14px;background:var(--surface)}.ads-card h3{margin:0;font-size:16px;color:var(--ink)}.ads-card-sub{margin-top:5px;font-size:10px;line-height:1.5;color:var(--muted)}
.ads-driver-list{display:grid;gap:8px;margin-top:15px}.ads-driver-row{display:grid;grid-template-columns:100px minmax(0,1fr) 92px;gap:10px;align-items:center}.ads-driver-name{font-size:10px;font-weight:700;color:var(--text)}.ads-driver-track{height:7px;border-radius:999px;background:var(--line);overflow:hidden}.ads-driver-track i{display:block;height:100%;border-radius:999px;background:var(--green)}.ads-driver-track i.negative{background:var(--red)}.ads-driver-value{text-align:right;font-size:10px;font-weight:750;font-variant-numeric:tabular-nums}.ads-method{margin-top:12px;padding-top:10px;border-top:1px solid var(--line);font-size:8.5px;line-height:1.45;color:var(--muted2)}
.ads-trend{display:flex;align-items:flex-end;gap:4px;height:112px;margin-top:18px;padding-top:10px}.ads-trend-day{flex:1;min-width:3px;border-radius:4px 4px 1px 1px;background:var(--green);opacity:.78}.ads-trend-label{margin-top:8px;display:flex;justify-content:space-between;font-size:8.5px;color:var(--muted2)}
.ads-signal-strip{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}.ads-signal{min-width:0;padding:14px;border:1px solid var(--line);border-radius:12px;background:var(--surface)}.ads-signal-name{font-size:10.5px;font-weight:700;color:var(--text);line-height:1.4;display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:2;overflow:hidden;min-height:2.8em}.ads-signal-meta{margin-top:5px;font-size:9px;color:var(--muted);line-height:1.4}.ads-signal-value{margin-top:10px;font-size:18px;font-weight:750;font-variant-numeric:tabular-nums}.ads-signal-value.up{color:var(--green)}.ads-signal-value.down{color:var(--red)}.ads-signal-pill{display:inline-block;margin-top:7px;padding:4px 7px;border:1px solid var(--line);border-radius:7px;font-size:8.5px;line-height:1.35;color:var(--muted);background:var(--soft)}
.ads-table-tools{display:flex;align-items:center;gap:10px;justify-content:space-between;margin-top:14px}.ads-search{width:min(320px,100%);border:1px solid var(--line);border-radius:9px;background:var(--surface);color:var(--text);padding:8px 10px;font-size:10px}.ads-table-wrap{overflow:auto;margin-top:10px}.ads-table{width:100%;min-width:930px;border-collapse:separate;border-spacing:0;font-size:9.5px}.ads-table th{position:sticky;top:0;background:var(--surface);color:var(--muted2);font-size:8.5px;text-align:right;padding:10px 9px;border-bottom:1px solid var(--line)}.ads-table th:first-child,.ads-table td:first-child{text-align:left}.ads-table td{padding:11px 9px;border-bottom:1px solid var(--line);text-align:right;font-variant-numeric:tabular-nums}.ads-table tbody tr:hover td{background:var(--soft)}.ads-product-name{max-width:280px;font-weight:700;color:var(--text);line-height:1.4}.ads-product-sku{margin-top:3px;font-size:8.5px;color:var(--muted2)}
@media(max-width:1180px){.ads-kpis{grid-template-columns:repeat(3,minmax(0,1fr))}.ads-signal-strip{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:900px){.ads-hero{grid-template-columns:1fr}.ads-hero-side{border-left:0;border-top:1px solid var(--line)}.ads-grid-2{grid-template-columns:1fr}}
@media(max-width:680px){.ads-kpis{grid-template-columns:repeat(2,minmax(0,1fr))}.ads-signal-strip{grid-template-columns:1fr}.ads-hero-main{padding:20px}.ads-driver-row{grid-template-columns:90px minmax(0,1fr) 74px}}
"""


def _ads_destination(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    return ((payload.get("destinations") or {}).get("ads") or {})


def _candidate_ads_products(scope: Mapping[str, Any]):
    seen = set()
    periods = scope.get("periods") or {}
    for scope_key in ("day", "week", "month", "year"):
        for snap in ((periods.get(scope_key) or {}).get("snapshots") or {}).values():
            for product in snap.get("products") or []:
                pid = str(product.get("productId") or "").strip()
                if pid and pid not in seen:
                    seen.add(pid); yield product
            for signal in snap.get("signals") or []:
                pid = str(signal.get("productId") or "").strip()
                if pid and pid not in seen:
                    seen.add(pid); yield signal


def build_ads_short_name_map(payload: Mapping[str, Any]) -> Dict[str, Dict[str, Dict[str, Any]]]:
    result: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for sid, scope in (_ads_destination(payload).get("shops") or {}).items():
        records: Dict[str, Dict[str, Any]] = {}
        for product in _candidate_ads_products(scope):
            pid = str(product.get("productId") or "").strip()
            normalized = {
                "productId": pid,
                "productName": product.get("productName"),
                "resolvedParentSku": product.get("productSku"),
            }
            resolved = short_name_for_product(normalized)
            records[pid] = {**resolved, "displayName": resolved["shortName"]}
        groups = defaultdict(list)
        for pid, rec in records.items():
            groups[rec["displayName"]].append(pid)
        for display_name, pids in groups.items():
            if len(pids) < 2:
                continue
            for pid in pids:
                rec = records[pid]; suffix = str(rec.get("parentSku") or "").strip() or pid[-6:]
                rec["displayName"] = f"{display_name} · {suffix}"
                rec["collisionGuardApplied"] = True
        result[str(sid)] = records
    return result


def _validate_ads_payload(payload: Mapping[str, Any]) -> None:
    ads = _ads_destination(payload)
    scope = ads.get("scopePolicy") or {}
    if not ads:
        raise ValueError("Ads destination payload missing")
    if not bool(scope.get("singleShopOnly")) or bool(scope.get("compareAllowed")):
        raise ValueError("Ads Native destination must remain single-shop only")
    if str(scope.get("canonicalSourceGrain")) != "DAILY":
        raise ValueError("Ads Native destination must remain daily-grain")
    if list(scope.get("allowedTimeScopes") or []) != ["day", "week", "month", "year"]:
        raise ValueError("Ads Native time-scope contract mismatch")
    for sid, shop in (ads.get("shops") or {}).items():
        if shop.get("compareAllowed") is not False or str(shop.get("sourceGrain")) != "DAILY":
            raise ValueError(f"unsafe Ads scope for {sid}")
        for scope_key in ("day", "week", "month", "year"):
            for snap in (((shop.get("periods") or {}).get(scope_key) or {}).get("snapshots") or {}).values():
                if bool(snap.get("causalClaim")):
                    raise ValueError(f"Ads causal claim leaked for {sid}")
                if bool((snap.get("driverAttribution") or {}).get("causalClaim")):
                    raise ValueError(f"Ads driver causal claim leaked for {sid}")
                if any(bool(x.get("causalClaim")) for x in snap.get("signals") or []):
                    raise ValueError(f"Ads signal causal claim leaked for {sid}")


def _ads_runtime(name_map: Mapping[str, Any]) -> str:
    encoded = json.dumps(name_map, ensure_ascii=False, separators=(",", ":"))
    return r"""
(function(){
  const q=new URLSearchParams(location.search),nav=document.querySelector(".nav");
  const B=window.UNIPALM_SCOPE_BUNDLE||{},S=window.UNIPALM_NATIVE_SCOPE||{},SHORT=__ADS_SHORT_MAP__;
  const shops=B.shops||[];
  const go=params=>{const u=new URL(location.href);Object.entries(params).forEach(([k,v])=>u.searchParams.set(k,v));location.href=u.toString()};
  if(nav){
    let adsNav=nav.querySelector('[data-native-destination="ads"]');
    if(!adsNav){adsNav=document.createElement("button");adsNav.type="button";adsNav.textContent="Ads";adsNav.dataset.nativeDestination="ads";nav.appendChild(adsNav)}
    adsNav.onclick=()=>go({destination:"ads",scope:"shop",shop:S.shop||shops[0]?.shopId||""});
  }
  if(q.get("destination")!=="ads")return;
  const A=B.adsDestination||{},scope=(A.shops||{})[S.shop]||{},periods=scope.periods||{};
  const header=document.querySelector(".header"),main=document.querySelector(".main"),bar=document.querySelector(".native-scope-bar");
  if(!header||!main||!bar||!scope.scope)return;
  const esc=v=>String(v??"").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[m]));
  const nv=new Intl.NumberFormat("vi-VN",{maximumFractionDigits:1}),n0=new Intl.NumberFormat("vi-VN",{maximumFractionDigits:0});
  const money=v=>{const x=Number(v||0),a=Math.abs(x),sg=x<0?"-":"";if(a>=1e9)return sg+nv.format(a/1e9)+"tỷ đ";if(a>=1e6)return sg+nv.format(a/1e6)+"tr đ";if(a>=1e3)return sg+nv.format(a/1e3)+"k đ";return sg+n0.format(a)+" đ"};
  const pct=v=>nv.format(Number(v||0)*100)+"%",num=v=>n0.format(Number(v||0)),xnum=v=>nv.format(Number(v||0))+"x";
  const scopeLabels={day:"Ngày",week:"Tuần",month:"Tháng",year:"Năm"};
  const driverLabels={cvr:"CVR Ads",adsAov:"AOV Ads",cpc:"CPC"};
  const shopName=shops.find(x=>x.shopId===S.shop)?.displayName||scope.displayName||S.shop;
  const readyOptions=k=>{const block=periods[k]||{},opts=(k==="year"?(block.readyOptions||[]):(block.options||[]));return opts.filter(o=>(block.snapshots||{})[o]?.status==="READY")};
  let adsScope=q.get("adsScope")||"week";
  if(!readyOptions(adsScope).length)adsScope=["week","month","day","year"].find(k=>readyOptions(k).length)||"day";
  const opts=readyOptions(adsScope);let adsOption=q.get("adsOption")||opts[opts.length-1];if(!opts.includes(adsOption))adsOption=opts[opts.length-1];
  const snap=((periods[adsScope]||{}).snapshots||{})[adsOption]||{},sm=snap.summary||{},d=snap.deltas||{};
  const formatOption=(k,o)=>{if(k==="day")return new Date(o+"T00:00:00").toLocaleDateString("vi-VN");if(k==="week")return "7 ngày đến "+new Date(o+"T00:00:00").toLocaleDateString("vi-VN");if(k==="month")return o.slice(5)+"/"+o.slice(0,4);return o};
  const tabs=["day","week","month","year"].map(k=>'<button class="ads-scope-tab '+(k===adsScope?"active":"")+'" data-ads-scope="'+k+'" '+(readyOptions(k).length?"":"disabled")+'>'+scopeLabels[k]+'</button>').join("");
  const optionHtml=opts.slice().reverse().map(o=>'<option value="'+esc(o)+'">'+esc(formatOption(adsScope,o))+'</option>').join("");
  const shopOpts=shops.map(x=>'<option value="'+esc(x.shopId)+'">'+esc(x.displayName||x.shopId)+'</option>').join("");
  bar.innerHTML='<span class="native-preprod">PREPRODUCTION</span><div class="native-picker"><label>SHOP</label><select id="adsShopSelect">'+shopOpts+'</select></div><div class="ads-scope-tabs">'+tabs+'</div><div class="native-picker"><label>KỲ</label><select id="adsOptionSelect" class="ads-option-select">'+optionHtml+'</select></div><div class="native-lineage">Ads · Daily</div>';
  const shopSel=document.getElementById("adsShopSelect");if(shopSel){shopSel.value=S.shop;shopSel.onchange=e=>go({destination:"ads",scope:"shop",shop:e.target.value,adsScope:adsScope})}
  const optSel=document.getElementById("adsOptionSelect");if(optSel){optSel.value=adsOption;optSel.onchange=e=>go({destination:"ads",scope:"shop",shop:S.shop,adsScope:adsScope,adsOption:e.target.value})}
  bar.querySelectorAll("[data-ads-scope]").forEach(b=>b.onclick=()=>{const k=b.dataset.adsScope,oo=readyOptions(k);if(oo.length)go({destination:"ads",scope:"shop",shop:S.shop,adsScope:k,adsOption:oo[oo.length-1]})});
  if(nav){nav.querySelectorAll("button").forEach(b=>b.classList.remove("active"));nav.querySelector('[data-native-destination="ads"]')?.classList.add("active");const p=nav.querySelector('[data-native-destination="product"]');if(p)p.onclick=()=>go({destination:"product",scope:"shop",shop:S.shop});const c=nav.querySelector('[data-native-destination="command-center"]');if(c)c.onclick=()=>{const u=new URL(location.href);u.searchParams.delete("destination");u.searchParams.set("scope","portfolio");location.href=u.toString()};const cp=nav.querySelector('[data-native-destination="compare"]');if(cp)cp.onclick=()=>{const u=new URL(location.href);u.searchParams.delete("destination");u.searchParams.set("scope","compare");location.href=u.toString()}}
  const title=header.querySelector("h1"),subtitle=header.querySelector("p");if(title)title.textContent="Ads · "+shopName;if(subtitle)subtitle.textContent="Hiệu quả quảng cáo · "+formatOption(adsScope,adsOption)+" · dữ liệu theo ngày";
  Array.from(main.children).forEach(el=>{if(el!==header&&el!==bar)el.style.display="none"});
  const deltaText=v=>v===null||v===undefined?"Chưa đủ kỳ trước":((Number(v)>0?"+":"")+pct(v));
  const deltaClass=v=>v===null||v===undefined?"":(Number(v)>0?"up":(Number(v)<0?"down":""));
  const compReady=snap.comparisonStatus==="READY";
  const signals=(snap.signals||[]).slice(0,4),problems=signals.filter(x=>x.type==="Vấn đề").length,opps=signals.filter(x=>x.type==="Cơ hội").length;
  let stateTitle="Chưa đủ lịch sử để so sánh",stateCopy="Kỳ đang chọn có dữ liệu Ads hợp lệ, nhưng chưa đủ một kỳ trước tương đương để đánh giá thay đổi.";
  if(compReady){stateTitle=signals.length?(problems+(problems&&opps?" cần chú ý · ":" cần chú ý")+(opps?opps+" cơ hội":"")):"Chưa có thay đổi Ads nổi bật";stateCopy="So với kỳ liền trước có cùng độ dài. Ưu tiên tín hiệu có tỷ trọng chi tiêu đủ lớn thay vì chỉ nhìn ROAS tuyệt đối."}
  const nameFor=p=>{const rec=(SHORT[S.shop]||{})[String(p.productId||"")];return rec?.displayName||p.productName||"Sản phẩm chưa xác định"};
  const signalHtml=signals.map(x=>'<article class="ads-signal"><div class="ads-signal-name" title="'+esc(x.productName||"")+'">'+esc(nameFor(x))+'</div><div class="ads-signal-meta">'+esc(x.productSku||"")+' · '+pct(x.spendShare||0)+' chi tiêu</div><div class="ads-signal-value '+(Number(x.roasDelta||0)>=0?"up":"down")+'">'+(Number(x.roasDelta||0)>0?"+":"")+pct(x.roasDelta||0)+' ROAS</div><span class="ads-signal-pill">Chi tiêu '+deltaText(x.spendDelta)+' · Doanh số Ads '+deltaText(x.salesDelta)+'</span></article>').join("");
  const attr=snap.driverAttribution||{},drivers=attr.driverContributions||[],maxDriver=Math.max(...drivers.map(x=>Math.abs(Number(x.contributionValue||0))),.0001);
  const driverHtml=drivers.map(x=>'<div class="ads-driver-row"><span class="ads-driver-name">'+esc(driverLabels[x.driverMetric]||x.driverMetric)+'</span><span class="ads-driver-track"><i class="'+(Number(x.contributionValue||0)<0?"negative":"")+'" style="width:'+Math.max(4,Math.abs(Number(x.contributionValue||0))/maxDriver*100)+'%"></i></span><strong class="ads-driver-value">'+(Number(x.contributionValue||0)>0?"+":"")+nv.format(Number(x.contributionValue||0))+'x</strong></div>').join("");
  const series=snap.dailySeries||[],maxSpend=Math.max(...series.map(x=>Number(x.adSpend||0)),1),trend=series.map(x=>'<i class="ads-trend-day" style="height:'+Math.max(4,Number(x.adSpend||0)/maxSpend*100)+'%" title="'+esc(x.dataDate)+' · '+money(x.adSpend)+'"></i>').join("");
  const products=snap.products||[],totalSpend=Number(sm.adSpend||0),rows=products.map(p=>'<tr data-ads-search="'+esc(((p.productName||"")+" "+(p.productSku||"")+" "+nameFor(p)).toLowerCase())+'"><td><div class="ads-product-name" title="'+esc(p.productName||"")+'">'+esc(nameFor(p))+'</div><div class="ads-product-sku">'+esc(p.productSku||"")+'</div></td><td>'+money(p.adSpend)+'</td><td>'+pct(totalSpend?Number(p.adSpend||0)/totalSpend:0)+'</td><td>'+money(p.attributedSales)+'</td><td>'+xnum(p.roas)+'</td><td>'+money(p.cpc)+'</td><td>'+money(p.cpa)+'</td><td>'+pct(p.cvr)+'</td></tr>').join("");
  const view=document.createElement("section");view.className="ads-destination";view.innerHTML=
    '<section class="ads-hero"><div class="ads-hero-main"><div class="ads-eyebrow">Tóm tắt hiệu quả quảng cáo · '+esc(scopeLabels[adsScope])+'</div><div class="ads-headline">'+money(sm.adSpend)+' chi tiêu → '+money(sm.attributedSales)+' doanh số Ads</div><div class="ads-copy">ROAS '+xnum(sm.roas)+(compReady?(' · '+deltaText(d.roas)+' so với kỳ trước'):' · chưa đủ kỳ trước để so sánh')+'.</div></div><aside class="ads-hero-side"><div class="ads-status"><b>'+esc(stateTitle)+'</b><span>'+esc(stateCopy)+'</span></div></aside></section>'+
    (signals.length?'<section class="ads-signal-strip">'+signalHtml+'</section>':'')+
    '<section class="ads-kpis"><div class="ads-kpi"><div class="ads-kpi-label">Chi tiêu Ads</div><div class="ads-kpi-value">'+money(sm.adSpend)+'</div><div class="ads-kpi-note ads-kpi-delta '+deltaClass(d.adSpend)+'">'+deltaText(d.adSpend)+'</div></div><div class="ads-kpi"><div class="ads-kpi-label">Doanh số Ads</div><div class="ads-kpi-value">'+money(sm.attributedSales)+'</div><div class="ads-kpi-note ads-kpi-delta '+deltaClass(d.attributedSales)+'">'+deltaText(d.attributedSales)+'</div></div><div class="ads-kpi"><div class="ads-kpi-label">ROAS</div><div class="ads-kpi-value">'+xnum(sm.roas)+'</div><div class="ads-kpi-note ads-kpi-delta '+deltaClass(d.roas)+'">'+deltaText(d.roas)+'</div></div><div class="ads-kpi"><div class="ads-kpi-label">CPC</div><div class="ads-kpi-value">'+money(sm.cpc)+'</div><div class="ads-kpi-note ads-kpi-delta '+deltaClass(d.cpc)+'">'+deltaText(d.cpc)+'</div></div><div class="ads-kpi"><div class="ads-kpi-label">CPA</div><div class="ads-kpi-value">'+money(sm.cpa)+'</div><div class="ads-kpi-note ads-kpi-delta '+deltaClass(d.cpa)+'">'+deltaText(d.cpa)+'</div></div><div class="ads-kpi"><div class="ads-kpi-label">CVR Ads</div><div class="ads-kpi-value">'+pct(sm.cvr)+'</div><div class="ads-kpi-note ads-kpi-delta '+deltaClass(d.cvr)+'">'+deltaText(d.cvr)+'</div></div></section>'+
    '<section class="ads-grid-2"><div class="ads-card"><h3>Yếu tố ảnh hưởng ROAS</h3><div class="ads-card-sub">Phân rã thay đổi ROAS so với kỳ trước có cùng độ dài.</div><div class="ads-driver-list">'+(driverHtml||'<div class="ads-copy">Chưa đủ dữ liệu để phân rã kỳ so sánh.</div>')+'</div><div class="ads-method">Mức đóng góp được phân rã theo ROAS = CVR Ads × AOV Ads / CPC; đây không phải kết luận quan hệ nhân quả.</div></div><div class="ads-card"><h3>Nhịp chi tiêu theo ngày</h3><div class="ads-card-sub">Chi tiêu Ads trong kỳ đang chọn; dùng để nhận diện ngày tăng/giảm ngân sách.</div><div class="ads-trend">'+trend+'</div><div class="ads-trend-label"><span>'+esc(snap.coverageStart||"")+'</span><span>'+esc(snap.coverageEnd||"")+'</span></div></div></section>'+
    '<section class="ads-card"><h3>Hiệu quả theo sản phẩm</h3><div class="ads-card-sub">Xếp theo chi tiêu. ROAS/CPA/CVR được tính lại từ additive facts, không lấy trung bình tỷ lệ ngày.</div><div class="ads-table-tools"><input id="adsSearch" class="ads-search" type="search" placeholder="Tìm sản phẩm hoặc SKU"><span class="ads-copy">'+num(products.length)+' sản phẩm có Ads</span></div><div class="ads-table-wrap"><table class="ads-table"><thead><tr><th>Sản phẩm</th><th>Chi tiêu</th><th>Tỷ trọng</th><th>Doanh số Ads</th><th>ROAS</th><th>CPC</th><th>CPA</th><th>CVR</th></tr></thead><tbody>'+rows+'</tbody></table></div></section>';
  main.appendChild(view);
  const search=document.getElementById("adsSearch");if(search)search.oninput=e=>{const term=String(e.target.value||"").trim().toLowerCase();view.querySelectorAll("[data-ads-search]").forEach(r=>r.style.display=!term||r.dataset.adsSearch.includes(term)?"":"none")};
})();
""".replace("__ADS_SHORT_MAP__", encoded)


def _validate_ads_artifact(output_dir: Any) -> None:
    html = (Path(output_dir) / "command_center_v2_multi_shop_native_template.html").read_text(encoding="utf-8")
    required = (
        ADS_NATIVE_PATCH_VERSION, "destination\")!==\"ads", "Tóm tắt hiệu quả quảng cáo",
        "Ngày", "Tuần", "Tháng", "Năm", "Yếu tố ảnh hưởng ROAS", "Nhịp chi tiêu theo ngày",
        "Hiệu quả theo sản phẩm", "ROAS = CVR Ads × AOV Ads / CPC", "không phải kết luận quan hệ nhân quả",
        ".ads-destination{", ".ads-signal-strip{",
    )
    missing = [token for token in required if token not in html]
    if missing:
        raise ValueError(f"Ads Native artifact checks missing: {missing}")


def build_native_v2_multi_shop(*, payload_dir: Any, v2_template_path: Any, output_dir: Any):
    payload_path = Path(payload_dir) / "ui_payload.json"
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    _validate_ads_payload(payload)
    ads_map = build_ads_short_name_map(payload)

    product_module = _product_short._compact._product
    original_bundle = product_module._bundle_with_product
    original_style = _product_short.SHORT_NAME_STYLE
    original_runtime_fn = _product_short._runtime_for_map
    original_version = _product_short.PRODUCT_SHORT_NAME_PATCH_VERSION

    def bundle_with_ads(source_payload):
        base = original_bundle(source_payload)
        base["adsDestination"] = ((source_payload.get("destinations") or {}).get("ads") or {})
        return base

    def runtime_with_ads(product_map):
        return original_runtime_fn(product_map) + "\n" + _ads_runtime(ads_map)

    product_module._bundle_with_product = bundle_with_ads
    _product_short.SHORT_NAME_STYLE = original_style + "\n" + ADS_STYLE
    _product_short._runtime_for_map = runtime_with_ads
    _product_short.PRODUCT_SHORT_NAME_PATCH_VERSION = ADS_NATIVE_PATCH_VERSION
    try:
        result = _product_short.build_native_v2_multi_shop(
            payload_dir=payload_dir,
            v2_template_path=v2_template_path,
            output_dir=output_dir,
        )
        if result.get("nativePatchVersion") != ADS_NATIVE_PATCH_VERSION:
            raise ValueError("Ads Native patch version missing from lineage")
        _validate_ads_artifact(output_dir)
        result["adsDestinationReady"] = True
        result["adsShortNameShopCount"] = len(ads_map)
        return result
    finally:
        product_module._bundle_with_product = original_bundle
        _product_short.SHORT_NAME_STYLE = original_style
        _product_short._runtime_for_map = original_runtime_fn
        _product_short.PRODUCT_SHORT_NAME_PATCH_VERSION = original_version
