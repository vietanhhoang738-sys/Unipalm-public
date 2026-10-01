"""Financial-analysis presentation layer for Ads V2 PREPRODUCTION.

This adapter sits on top of the validated Ads v37 foundation. It does not change
Ads facts or intelligence semantics. Instead it changes information architecture:
operators read the numbers/charts first and consult the standalone Intelligence
Desk at the bottom.

The page supports three in-shop entity scopes (Shop / Product group / Product)
and day/week/month/year time scopes. Group/product projections are recomputed
from canonical daily product facts already carried by Ads Intelligence; ratios
are never averaged.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Mapping

from . import ui_v2_ads_destination as _ads
from .product_short_name import short_name_for_product

ADS_FINANCIAL_PATCH_VERSION = "native-ads-financial-v38"
ADS_GROUP_RULE_VERSION = "ads-product-group-v1"


def _s(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _ads_group(product: Mapping[str, Any]) -> str:
    name = _s(product.get("productName") or product.get("product_name"))
    low = name.casefold()
    if "cặp đôi" in low or re.search(r"\bcombo\s*\d*\b", low):
        return "Cặp đôi / Combo"
    resolved = short_name_for_product({
        "productName": name,
        "resolvedParentSku": product.get("productSku") or product.get("resolvedParentSku"),
        "productId": product.get("productId"),
    })
    category = _s(resolved.get("category"))
    if category in {"Khẩu trang", "Găng tay", "Ống tay"}:
        return category
    return "Khác"


def build_ads_entity_map(payload: Mapping[str, Any]) -> Dict[str, Dict[str, Dict[str, Any]]]:
    base = _ads.build_ads_short_name_map(payload)
    destination = ((payload.get("destinations") or {}).get("ads") or {})
    result: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for sid, scope in (destination.get("shops") or {}).items():
        records = {pid: dict(value) for pid, value in (base.get(str(sid)) or {}).items()}
        for scope_key in ("day", "week", "month", "year"):
            for snap in ((((scope.get("periods") or {}).get(scope_key) or {}).get("snapshots") or {}).values()):
                for product in snap.get("products") or []:
                    pid = _s(product.get("productId"))
                    if not pid:
                        continue
                    rec = records.setdefault(pid, {})
                    rec["group"] = _ads_group(product)
                    rec["groupRuleVersion"] = ADS_GROUP_RULE_VERSION
                    rec.setdefault("fullName", _s(product.get("productName")))
                    rec.setdefault("displayName", _s(product.get("productName")) or pid)
                    rec.setdefault("parentSku", _s(product.get("productSku")))
        result[str(sid)] = records
    return result


FINANCIAL_STYLE = r"""
/* Ads Financial UI v38. No font-family override: typography is inherited from
   the project-wide Inter foundation. */
.native-scope-bar{gap:10px!important;padding:10px 14px!important;border-radius:16px!important;box-shadow:none!important;background:var(--surface)!important}
.native-picker{gap:7px!important}.native-picker label{font-size:9px!important;letter-spacing:.035em;text-transform:uppercase;color:var(--muted2)!important}
.native-picker select,.ads-fin-select{min-height:36px;border:1px solid var(--line);border-radius:10px;background:var(--surface);color:var(--text);padding:0 34px 0 11px;font:inherit;font-size:10px;font-weight:650;outline:none}
.native-picker select:focus,.ads-fin-select:focus{border-color:var(--green);box-shadow:0 0 0 3px var(--green-soft)}
.native-preprod{min-height:36px!important;padding:0 12px!important}.native-tab,.ads-scope-tab{min-height:36px!important;padding:0 13px!important;border-radius:10px!important;font:inherit!important;font-size:10px!important;font-weight:720!important;box-shadow:none!important}
.ads-financial{display:grid;gap:18px;margin-top:4px}.ads-fin-card{border:1px solid var(--line);border-radius:15px;background:var(--surface);padding:20px;min-width:0}.ads-fin-section-title{font-size:15px;font-weight:760;color:var(--ink);letter-spacing:-.01em}.ads-fin-section-sub{margin-top:5px;font-size:9.5px;line-height:1.5;color:var(--muted)}
.ads-fin-entity-tabs{display:flex;gap:5px;padding:3px;border:1px solid var(--line);border-radius:11px;background:var(--soft)}.ads-fin-entity-tab{border:0;background:transparent;color:var(--muted);min-height:30px;padding:0 10px;border-radius:8px;font:inherit;font-size:9.5px;font-weight:720;cursor:pointer}.ads-fin-entity-tab.active{background:var(--surface);color:var(--ink);box-shadow:var(--shadow)}
.ads-equation{padding:22px;border:1px solid var(--line);border-radius:16px;background:var(--surface);overflow:hidden}.ads-equation-head{display:flex;align-items:flex-start;justify-content:space-between;gap:16px}.ads-equation-title{font-size:10px;font-weight:760;color:var(--muted);letter-spacing:.035em;text-transform:uppercase}.ads-equation-result{margin-top:7px;display:flex;align-items:baseline;gap:10px;flex-wrap:wrap}.ads-equation-result strong{font-size:30px;line-height:1;font-weight:790;color:var(--ink);font-variant-numeric:tabular-nums;letter-spacing:-.035em}.ads-equation-result span{font-size:10px;font-weight:720}.ads-up{color:var(--green)!important}.ads-down{color:var(--red)!important}.ads-neutral{color:var(--muted)!important}
.ads-equation-rows{margin-top:20px;display:grid;gap:9px}.ads-eq-row{display:grid;grid-template-columns:58px minmax(0,1fr);gap:12px;align-items:center}.ads-eq-sign{font-size:18px;font-weight:800;color:var(--muted2);text-align:center}.ads-eq-expression{display:flex;align-items:center;gap:7px;flex-wrap:wrap}.ads-eq-op{font-size:13px;font-weight:760;color:var(--muted2)}.ads-metric-node{border:1px solid var(--line);border-radius:10px;background:var(--soft);padding:8px 10px;cursor:pointer;transition:border-color .14s ease,background .14s ease,transform .14s ease;min-width:82px;text-align:left}.ads-metric-node:hover{transform:translateY(-1px);border-color:var(--green)}.ads-metric-node.active{border-color:var(--green);background:var(--green-soft)}.ads-metric-node b{display:block;font-size:9px;color:var(--muted);font-weight:680}.ads-metric-node strong{display:block;margin-top:3px;font-size:13px;color:var(--ink);font-weight:760;font-variant-numeric:tabular-nums}.ads-metric-node small{display:block;margin-top:3px;font-size:8px;font-weight:720}.ads-eq-note{margin-top:13px;padding-top:11px;border-top:1px solid var(--line);font-size:8.5px;line-height:1.45;color:var(--muted2)}
.ads-fin-kpis{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:10px}.ads-fin-kpi{border:1px solid var(--line);border-radius:12px;background:var(--surface);padding:13px;cursor:pointer;min-width:0;transition:transform .12s ease,border-color .12s ease}.ads-fin-kpi:hover{transform:translateY(-1px);border-color:var(--green)}.ads-fin-kpi.active{border-color:var(--green);box-shadow:inset 0 0 0 1px var(--green)}.ads-fin-kpi-label{font-size:8.5px;color:var(--muted2);font-weight:720}.ads-fin-kpi-value{margin-top:7px;font-size:18px;line-height:1.05;font-weight:780;color:var(--ink);font-variant-numeric:tabular-nums}.ads-fin-kpi-foot{margin-top:7px;display:flex;align-items:center;gap:6px;justify-content:space-between;font-size:8px;color:var(--muted)}.ads-fin-badge{display:inline-flex;align-items:center;min-height:20px;padding:0 6px;border-radius:6px;background:var(--soft);font-size:8px;font-weight:760}
.ads-fin-grid{display:grid;grid-template-columns:minmax(0,1.35fr) minmax(300px,.65fr);gap:18px}.ads-fin-grid.equal{grid-template-columns:repeat(2,minmax(0,1fr))}.ads-chart-head{display:flex;justify-content:space-between;align-items:flex-start;gap:12px}.ads-chart-focus{font-size:9px;font-weight:760;color:var(--green)}.ads-svg-wrap{margin-top:14px;height:235px;position:relative}.ads-svg{width:100%;height:100%;overflow:visible}.ads-svg-grid{stroke:var(--line);stroke-width:1}.ads-svg-line{fill:none;stroke:var(--green);stroke-width:2.4;vector-effect:non-scaling-stroke}.ads-svg-area{fill:var(--green-soft);opacity:.55}.ads-svg-dot{fill:var(--surface);stroke:var(--green);stroke-width:2;cursor:pointer}.ads-svg-zero{stroke:var(--muted2);stroke-width:1;stroke-dasharray:3 4}.ads-chart-axis{display:flex;justify-content:space-between;margin-top:6px;font-size:8px;color:var(--muted2)}
.ads-funnel{display:grid;gap:10px;margin-top:16px}.ads-funnel-row{display:grid;grid-template-columns:94px 74px minmax(80px,1fr) 66px;gap:9px;align-items:center}.ads-funnel-label{font-size:9px;font-weight:720;color:var(--text)}.ads-funnel-value{text-align:right;font-size:9px;font-weight:760;color:var(--ink);font-variant-numeric:tabular-nums}.ads-funnel-track{height:8px;border-radius:999px;background:var(--line);overflow:hidden}.ads-funnel-track i{display:block;height:100%;border-radius:999px;background:var(--green)}.ads-funnel-delta{text-align:right;font-size:8px;font-weight:740}
.ads-cost-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin-top:15px}.ads-cost-card{border:1px solid var(--line);border-radius:11px;padding:12px;background:var(--soft)}.ads-cost-label{font-size:9px;font-weight:760;color:var(--text)}.ads-cost-current{margin-top:5px;font-size:20px;font-weight:780;color:var(--ink);font-variant-numeric:tabular-nums}.ads-cost-bench{margin-top:9px;display:grid;gap:5px}.ads-cost-row{display:grid;grid-template-columns:30px 1fr auto;gap:7px;align-items:center;font-size:8px}.ads-cost-row span:first-child{color:var(--muted2);font-weight:730}.ads-cost-bar{height:5px;background:var(--line);border-radius:999px;overflow:hidden}.ads-cost-bar i{display:block;height:100%;background:var(--green);border-radius:999px}.ads-cost-state{font-weight:760;white-space:nowrap}.ads-cost-missing{color:var(--muted2)}
.ads-breakdown-list{display:grid;gap:8px;margin-top:15px}.ads-breakdown-row{display:grid;grid-template-columns:minmax(130px,1fr) minmax(120px,1.1fr) 80px 70px;gap:10px;align-items:center;padding:7px 0;border-top:1px solid var(--line);cursor:pointer}.ads-breakdown-row:first-child{border-top:0}.ads-breakdown-name{font-size:9px;font-weight:720;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.ads-breakdown-track{height:7px;border-radius:999px;background:var(--line);overflow:hidden}.ads-breakdown-track i{display:block;height:100%;border-radius:999px;background:var(--green)}.ads-breakdown-metric{text-align:right;font-size:9px;font-weight:760;font-variant-numeric:tabular-nums}.ads-breakdown-roas{text-align:right;font-size:9px;font-weight:760}
.ads-scatter-wrap{height:230px;margin-top:12px}.ads-scatter{width:100%;height:100%}.ads-scatter-axis{stroke:var(--line);stroke-width:1}.ads-scatter-mid{stroke:var(--muted2);stroke-width:1;stroke-dasharray:3 4}.ads-scatter-dot{fill:var(--green);fill-opacity:.62;stroke:var(--surface);stroke-width:1.5;cursor:pointer}.ads-scatter-dot.risk{fill:var(--red)}
.ads-intelligence-desk{border:1px solid var(--line);border-radius:16px;background:var(--surface);overflow:hidden}.ads-desk-head{padding:18px 20px;border-bottom:1px solid var(--line);display:flex;align-items:flex-start;justify-content:space-between;gap:14px}.ads-desk-title{font-size:17px;font-weight:780;color:var(--ink)}.ads-desk-sub{margin-top:5px;font-size:9.5px;color:var(--muted);line-height:1.5}.ads-desk-grid{padding:16px 20px 20px;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}.ads-desk-item{border:1px solid var(--line);border-radius:11px;padding:13px;background:var(--soft)}.ads-desk-kicker{font-size:8px;font-weight:780;color:var(--muted2);text-transform:uppercase;letter-spacing:.04em}.ads-desk-item b{display:block;margin-top:6px;font-size:11px;line-height:1.4;color:var(--text)}.ads-desk-item p{margin:5px 0 0;font-size:9px;line-height:1.5;color:var(--muted)}.ads-desk-signals{padding:0 20px 18px;display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:9px}.ads-desk-signal{border-top:2px solid var(--line);padding:10px 0}.ads-desk-signal.problem{border-color:var(--red)}.ads-desk-signal.opportunity{border-color:var(--green)}.ads-desk-signal b{display:block;font-size:9.5px;color:var(--text);line-height:1.4}.ads-desk-signal span{display:block;margin-top:4px;font-size:8px;color:var(--muted)}
.ads-fin-hidden{display:none!important}
@media(max-width:1180px){.ads-fin-kpis{grid-template-columns:repeat(3,minmax(0,1fr))}.ads-fin-grid{grid-template-columns:1fr}.ads-desk-signals{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:760px){.ads-equation-head{display:block}.ads-eq-row{grid-template-columns:34px minmax(0,1fr)}.ads-fin-kpis{grid-template-columns:repeat(2,minmax(0,1fr))}.ads-cost-grid,.ads-desk-grid{grid-template-columns:1fr}.ads-desk-signals{grid-template-columns:1fr}.ads-breakdown-row{grid-template-columns:minmax(100px,1fr) 80px 60px}.ads-breakdown-track{display:none}}
"""


def _financial_runtime(entity_map: Mapping[str, Any]) -> str:
    encoded = json.dumps(entity_map, ensure_ascii=False, separators=(",", ":"))
    return r"""
(function(){
  const q=new URLSearchParams(location.search);if(q.get("destination")!=="ads")return;
  const B=window.UNIPALM_SCOPE_BUNDLE||{},S=window.UNIPALM_NATIVE_SCOPE||{},MAP=__ENTITY_MAP__;
  const A=B.adsDestination||{},shop=(A.shops||{})[S.shop]||{},periods=shop.periods||{},shops=B.shops||[];
  const main=document.querySelector(".main"),bar=document.querySelector(".native-scope-bar"),header=document.querySelector(".header");if(!main||!bar||!shop.scope)return;
  const old=main.querySelector(".ads-destination");if(old)old.remove();
  const esc=v=>String(v??"").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[m]));
  const nv=new Intl.NumberFormat("vi-VN",{maximumFractionDigits:1}),n0=new Intl.NumberFormat("vi-VN",{maximumFractionDigits:0});
  const money=v=>{const x=Number(v||0),a=Math.abs(x),sg=x<0?"-":"";if(a>=1e9)return sg+nv.format(a/1e9)+"tỷ đ";if(a>=1e6)return sg+nv.format(a/1e6)+"tr đ";if(a>=1e3)return sg+nv.format(a/1e3)+"k đ";return sg+n0.format(a)+" đ"};
  const pct=v=>nv.format(Number(v||0)*100)+"%",num=v=>n0.format(Number(v||0)),xnum=v=>nv.format(Number(v||0))+"x";
  const ratio=(a,b)=>Number(b||0)?Number(a||0)/Number(b||0):0,delta=(a,b)=>Number(b||0)>0?Number(a||0)/Number(b)-1:null;
  const additive=["impressions","clicks","addToCart","conversions","unitsSold","attributedSales","adSpend"];
  const recalc=t=>{const x={};additive.forEach(k=>x[k]=Number(t[k]||0));x.ctr=ratio(x.clicks,x.impressions);x.cvr=ratio(x.conversions,x.clicks);x.roas=ratio(x.attributedSales,x.adSpend);x.cpc=ratio(x.adSpend,x.clicks);x.cpm=ratio(x.adSpend*1000,x.impressions);x.cpa=ratio(x.adSpend,x.conversions);x.acos=ratio(x.adSpend,x.attributedSales);x.adsAov=ratio(x.attributedSales,x.conversions);return x};
  const sumRows=rows=>recalc(rows.reduce((a,r)=>{additive.forEach(k=>a[k]=(a[k]||0)+Number(r[k]||0));return a},{}));
  const scopeLabels={day:"Ngày",week:"Tuần",month:"Tháng",year:"Năm"};
  const shopName=shops.find(x=>x.shopId===S.shop)?.displayName||shop.displayName||S.shop;
  const readyOptions=k=>{const b=periods[k]||{},opts=k==="year"?(b.readyOptions||[]):(b.options||[]);return opts.filter(o=>(b.snapshots||{})[o]?.status==="READY")};
  let timeScope=q.get("adsScope")||"week";if(!readyOptions(timeScope).length)timeScope=["week","month","day","year"].find(k=>readyOptions(k).length)||"day";
  const timeOptions=readyOptions(timeScope),option=q.get("adsOption")&&timeOptions.includes(q.get("adsOption"))?q.get("adsOption"):timeOptions[timeOptions.length-1];
  const snap=((periods[timeScope]||{}).snapshots||{})[option]||{},daySnaps=(periods.day||{}).snapshots||{},entityRecords=MAP[S.shop]||{};
  const formatOption=(k,o)=>k==="day"?new Date(o+"T00:00:00").toLocaleDateString("vi-VN"):(k==="week"?"7 ngày đến "+new Date(o+"T00:00:00").toLocaleDateString("vi-VN"):(k==="month"?o.slice(5)+"/"+o.slice(0,4):o));
  const go=params=>{const u=new URL(location.href);Object.entries(params).forEach(([k,v])=>{if(v===null)u.searchParams.delete(k);else u.searchParams.set(k,v)});location.href=u.toString()};

  const groups=[...new Set(Object.values(entityRecords).map(x=>x.group).filter(Boolean))].sort((a,b)=>a.localeCompare(b,"vi"));
  const productIds=Object.keys(entityRecords).sort((a,b)=>String(entityRecords[a].displayName||"").localeCompare(String(entityRecords[b].displayName||""),"vi"));
  let entityScope=q.get("adsEntityScope")||"shop",entityKey=q.get("adsEntity")||"";
  if(!["shop","group","product"].includes(entityScope))entityScope="shop";
  if(entityScope==="group"&&!groups.includes(entityKey))entityKey=groups[0]||"";
  if(entityScope==="product"&&!productIds.includes(entityKey))entityKey=productIds[0]||"";
  const entityLabel=entityScope==="shop"?shopName:(entityScope==="group"?entityKey:(entityRecords[entityKey]?.displayName||entityKey));
  const entityMatches=p=>entityScope==="shop"?true:(entityScope==="group"?entityRecords[p.productId]?.group===entityKey:String(p.productId)===entityKey);
  const daily=[];Object.keys(daySnaps).sort().forEach(d=>{const ds=daySnaps[d];if(ds?.status!=="READY")return;let row;if(entityScope==="shop")row={dataDate:d,...ds.summary};else row={dataDate:d,...sumRows((ds.products||[]).filter(entityMatches))};daily.push(row)});
  const dayMap=Object.fromEntries(daily.map(x=>[x.dataDate,x]));
  const between=(start,end)=>daily.filter(x=>x.dataDate>=start&&x.dataDate<=end),curRows=between(snap.coverageStart||"",snap.coverageEnd||"");
  const current=sumRows(curRows),prevRows=snap.comparisonStatus==="READY"?between(snap.comparisonStart||"",snap.comparisonEnd||""):[],previous=prevRows.length?sumRows(prevRows):null;
  const deltas={};["attributedSales","adSpend","roas","impressions","clicks","ctr","cvr","adsAov","cpc","cpa","cpm","conversions"].forEach(k=>deltas[k]=previous?delta(current[k],previous[k]):null);
  const formatDelta=v=>v===null||v===undefined?"—":((v>0?"+":"")+pct(v)),cls=v=>v===null||v===undefined?"ads-neutral":(v>0?"ads-up":(v<0?"ads-down":"ads-neutral"));
  const costCls=(metric,v)=>{if(v===null||v===undefined)return"ads-neutral";const good=v<0;return good?"ads-up":"ads-down"};
  const allTrusted=new Set(Object.keys(daySnaps).filter(d=>daySnaps[d]?.status==="READY"));
  const dateAdd=(iso,n)=>{const d=new Date(iso+"T00:00:00");d.setDate(d.getDate()+n);return d.toISOString().slice(0,10)};
  const windowSummary=days=>{const end=snap.coverageEnd||"";if(!end)return null;const start=dateAdd(end,-days+1);let cursor=start;while(cursor<=end){if(!allTrusted.has(cursor))return null;cursor=dateAdd(cursor,1)}return sumRows(between(start,end))};
  const benchmarks={w1:windowSummary(7),m1:windowSummary(30),m3:windowSummary(90),m6:windowSummary(180)};

  const shortFor=p=>entityRecords[String(p.productId)]?.displayName||p.productName||p.productId,groupFor=p=>entityRecords[String(p.productId)]?.group||"Khác";
  const currentProducts=snap.products||[];
  const constituents=entityScope==="shop"?groups.map(g=>({key:g,label:g,kind:"group",summary:sumRows(currentProducts.filter(p=>groupFor(p)===g))})):(entityScope==="group"?currentProducts.filter(p=>groupFor(p)===entityKey).map(p=>({key:String(p.productId),label:shortFor(p),kind:"product",summary:recalc(p)})):[]);
  constituents.sort((a,b)=>Number(b.summary.adSpend||0)-Number(a.summary.adSpend||0));
  const entityProducts=entityScope==="shop"?currentProducts:(entityScope==="group"?currentProducts.filter(p=>groupFor(p)===entityKey):currentProducts.filter(p=>String(p.productId)===entityKey));

  // Replace the Ads portion of the global scope bar while preserving PREPRODUCTION safety label.
  const pre=bar.querySelector(".native-preprod")?.outerHTML||'<span class="native-preprod">PREPRODUCTION</span>';
  const shopOpts=shops.map(x=>'<option value="'+esc(x.shopId)+'">'+esc(x.displayName||x.shopId)+'</option>').join("");
  const entityTabs=['shop','group','product'].map(k=>'<button class="ads-fin-entity-tab '+(entityScope===k?'active':'')+'" data-entity-scope="'+k+'">'+({shop:'Shop',group:'Nhóm SP',product:'Sản phẩm'}[k])+'</button>').join('');
  const entityOptions=entityScope==='group'?groups.map(g=>'<option value="'+esc(g)+'">'+esc(g)+'</option>').join(''):(entityScope==='product'?productIds.map(pid=>'<option value="'+esc(pid)+'">'+esc(entityRecords[pid]?.displayName||pid)+'</option>').join(''):'');
  const timeTabs=['day','week','month','year'].map(k=>'<button class="ads-scope-tab '+(timeScope===k?'active':'')+'" data-fin-time="'+k+'" '+(readyOptions(k).length?'':'disabled')+'>'+scopeLabels[k]+'</button>').join('');
  const periodOptions=timeOptions.slice().reverse().map(o=>'<option value="'+esc(o)+'">'+esc(formatOption(timeScope,o))+'</option>').join('');
  bar.innerHTML=pre+'<div class="native-picker"><label>Shop</label><select id="adsFinShop">'+shopOpts+'</select></div><div class="ads-fin-entity-tabs">'+entityTabs+'</div>'+(entityScope==='shop'?'':'<select id="adsFinEntity" class="ads-fin-select">'+entityOptions+'</select>')+'<div class="ads-scope-tabs">'+timeTabs+'</div><div class="native-picker"><label>Kỳ</label><select id="adsFinPeriod">'+periodOptions+'</select></div><div class="native-lineage">Ads · '+esc(entityLabel)+'</div>';
  bar.querySelector('#adsFinShop').value=S.shop;bar.querySelector('#adsFinShop').onchange=e=>go({shop:e.target.value,scope:'shop',adsEntityScope:'shop',adsEntity:null});
  bar.querySelectorAll('[data-entity-scope]').forEach(b=>b.onclick=()=>go({adsEntityScope:b.dataset.entityScope,adsEntity:null}));
  const es=bar.querySelector('#adsFinEntity');if(es){es.value=entityKey;es.onchange=e=>go({adsEntity:e.target.value})}
  bar.querySelectorAll('[data-fin-time]').forEach(b=>b.onclick=()=>go({adsScope:b.dataset.finTime,adsOption:null}));
  bar.querySelector('#adsFinPeriod').value=option;bar.querySelector('#adsFinPeriod').onchange=e=>go({adsOption:e.target.value});
  if(header){const h=header.querySelector('h1'),p=header.querySelector('p');if(h)h.textContent='Ads · '+entityLabel;if(p)p.textContent='Phân tích hiệu quả quảng cáo · '+scopeLabels[timeScope]+' · '+formatOption(timeScope,option)}

  let focusMetric=q.get('adsFocus')||'attributedSales';const metricMeta={attributedSales:['GMV Ads',money],adSpend:['Ads Spend',money],roas:['ROAS',xnum],adsAov:['AOV Ads',money],conversions:['Chuyển đổi',num],impressions:['Hiển thị',num],ctr:['CTR',pct],cvr:['CR',pct],cpc:['CPC',money],clicks:['Click',num],cpa:['CPA',money],cpm:['CPM',money]};if(!metricMeta[focusMetric])focusMetric='attributedSales';
  const metricNode=(key,label,formatter)=>'<button class="ads-metric-node '+(focusMetric===key?'active':'')+'" data-focus="'+key+'"><b>'+label+'</b><strong>'+formatter(current[key])+'</strong><small class="'+cls(deltas[key])+'">'+formatDelta(deltas[key])+'</small></button>';
  const equation='<section class="ads-equation"><div class="ads-equation-head"><div><div class="ads-equation-title">Phương trình hiệu quả Ads · '+esc(entityLabel)+'</div><div class="ads-equation-result"><strong>'+xnum(current.roas)+'</strong><span class="'+cls(deltas.roas)+'">ROAS '+formatDelta(deltas.roas)+' vs kỳ trước</span></div></div><div class="ads-copy">Click vào một biến để chuyển biểu đồ phân tích.</div></div><div class="ads-equation-rows">'+
    '<div class="ads-eq-row"><div class="ads-eq-sign">=</div><div class="ads-eq-expression">'+metricNode('attributedSales','GMV Ads',money)+'<span class="ads-eq-op">÷</span>'+metricNode('adSpend','Ads Spend',money)+'</div></div>'+
    '<div class="ads-eq-row"><div class="ads-eq-sign">=</div><div class="ads-eq-expression"><span class="ads-eq-op">(</span>'+metricNode('adsAov','AOV',money)+'<span class="ads-eq-op">×</span>'+metricNode('conversions','Chuyển đổi',num)+'<span class="ads-eq-op">)</span><span class="ads-eq-op">÷</span><span class="ads-eq-op">(</span>'+metricNode('cpc','CPC',money)+'<span class="ads-eq-op">×</span>'+metricNode('clicks','Click',num)+'<span class="ads-eq-op">)</span></div></div>'+
    '<div class="ads-eq-row"><div class="ads-eq-sign">=</div><div class="ads-eq-expression"><span class="ads-eq-op">(</span>'+metricNode('adsAov','AOV',money)+'<span class="ads-eq-op">×</span>'+metricNode('impressions','Hiển thị',num)+'<span class="ads-eq-op">×</span>'+metricNode('ctr','CTR',pct)+'<span class="ads-eq-op">×</span>'+metricNode('cvr','CR',pct)+'<span class="ads-eq-op">)</span><span class="ads-eq-op">÷</span><span class="ads-eq-op">(</span>'+metricNode('cpc','CPC',money)+'<span class="ads-eq-op">×</span>'+metricNode('clicks','Click',num)+'<span class="ads-eq-op">)</span></div></div></div><div class="ads-eq-note">Các vế dùng cùng additive facts và tỷ lệ được tính lại. Phương trình giúp đọc cấu trúc hiệu quả, không phải kết luận quan hệ nhân quả.</div></section>';

  const kpiKeys=['attributedSales','adSpend','roas','cpc','cpa','cpm','ctr','cvr','adsAov','impressions','clicks','conversions'];
  const kpis='<section class="ads-fin-kpis">'+kpiKeys.map(k=>{const meta=metricMeta[k];const cost=['cpc','cpa','cpm'].includes(k);return '<div class="ads-fin-kpi '+(focusMetric===k?'active':'')+'" data-focus="'+k+'"><div class="ads-fin-kpi-label">'+meta[0]+'</div><div class="ads-fin-kpi-value">'+meta[1](current[k])+'</div><div class="ads-fin-kpi-foot"><span class="ads-fin-badge '+(cost?costCls(k,deltas[k]):cls(deltas[k]))+'">'+formatDelta(deltas[k])+'</span><span>vs kỳ trước</span></div></div>'}).join('')+'</section>';

  const renderLine=(metric)=>{const rows=curRows,max=Math.max(...rows.map(r=>Number(r[metric]||0)),1),min=Math.min(...rows.map(r=>Number(r[metric]||0)),0),w=760,h=190,pad=18,span=Math.max(max-min,1);const pts=rows.map((r,i)=>{const x=pad+(rows.length===1?0:i/(rows.length-1)*(w-pad*2)),y=h-pad-(Number(r[metric]||0)-min)/span*(h-pad*2);return [x,y,r]});const path=pts.map((p,i)=>(i?'L':'M')+p[0].toFixed(1)+','+p[1].toFixed(1)).join(' ');const dots=pts.map(p=>'<circle class="ads-svg-dot" cx="'+p[0]+'" cy="'+p[1]+'" r="3"><title>'+esc(p[2].dataDate)+' · '+esc(metricMeta[metric][1](p[2][metric]))+'</title></circle>').join('');return '<svg class="ads-svg" viewBox="0 0 '+w+' '+h+'" preserveAspectRatio="none"><line class="ads-svg-grid" x1="'+pad+'" y1="'+(h*.25)+'" x2="'+(w-pad)+'" y2="'+(h*.25)+'"/><line class="ads-svg-grid" x1="'+pad+'" y1="'+(h*.5)+'" x2="'+(w-pad)+'" y2="'+(h*.5)+'"/><line class="ads-svg-grid" x1="'+pad+'" y1="'+(h*.75)+'" x2="'+(w-pad)+'" y2="'+(h*.75)+'"/><path class="ads-svg-line" d="'+path+'"/>'+dots+'</svg>'};
  const trend='<section class="ads-fin-card"><div class="ads-chart-head"><div><div class="ads-fin-section-title">Diễn biến trong kỳ</div><div class="ads-fin-section-sub">Chọn biến ở phương trình hoặc KPI để đổi góc nhìn.</div></div><div id="adsFocusLabel" class="ads-chart-focus">'+esc(metricMeta[focusMetric][0])+'</div></div><div id="adsMainChart" class="ads-svg-wrap">'+renderLine(focusMetric)+'</div><div class="ads-chart-axis"><span>'+esc(snap.coverageStart||'')+'</span><span>'+esc(snap.coverageEnd||'')+'</span></div></section>';

  const funnelMetrics=[['impressions','Hiển thị',num],['clicks','Click',num],['conversions','Chuyển đổi',num],['attributedSales','GMV Ads',money]],maxF=Math.max(...funnelMetrics.map(x=>Number(current[x[0]]||0)),1);const funnel='<section class="ads-fin-card"><div class="ads-fin-section-title">Funnel Ads</div><div class="ads-fin-section-sub">Đọc điểm gãy bằng quy mô và biến động so với kỳ trước.</div><div class="ads-funnel">'+funnelMetrics.map(([k,l,f])=>'<div class="ads-funnel-row"><span class="ads-funnel-label">'+l+'</span><span class="ads-funnel-value">'+f(current[k])+'</span><span class="ads-funnel-track"><i style="width:'+Math.max(2,Number(current[k]||0)/maxF*100)+'%"></i></span><span class="ads-funnel-delta '+cls(deltas[k])+'">'+formatDelta(deltas[k])+'</span></div>').join('')+'</div><div class="ads-eq-note">CTR '+pct(current.ctr)+' · CR '+pct(current.cvr)+' · AOV '+money(current.adsAov)+'</div></section>';

  const benchLabels={w1:'1W',m1:'1M',m3:'3M',m6:'6M'};const costMetric=(key,label)=>'<div class="ads-cost-card"><div class="ads-cost-label">'+label+'</div><div class="ads-cost-current">'+money(current[key])+'</div><div class="ads-cost-bench">'+Object.entries(benchLabels).map(([bk,bl])=>{const b=benchmarks[bk];if(!b)return '<div class="ads-cost-row"><span>'+bl+'</span><span class="ads-cost-bar"></span><strong class="ads-cost-missing">Chưa đủ dữ liệu</strong></div>';const d=delta(current[key],b[key]),width=Math.min(100,Math.max(4,Math.abs(Number(d||0))*100));return '<div class="ads-cost-row"><span>'+bl+'</span><span class="ads-cost-bar"><i style="width:'+width+'%"></i></span><strong class="ads-cost-state '+costCls(key,d)+'">'+formatDelta(d)+'</strong></div>'}).join('')+'</div></div>';
  const costs='<section class="ads-fin-card"><div class="ads-fin-section-title">Áp lực chi phí</div><div class="ads-fin-section-sub">CPC / CPA / CPM hiện tại so với các cửa sổ lịch sử có đủ coverage.</div><div class="ads-cost-grid">'+costMetric('cpc','CPC')+costMetric('cpa','CPA')+costMetric('cpm','CPM')+'</div></section>';

  const maxSpend=Math.max(...constituents.map(x=>Number(x.summary.adSpend||0)),1);const breakdown='<section class="ads-fin-card"><div class="ads-fin-section-title">Phân bổ hiệu quả</div><div class="ads-fin-section-sub">'+(entityScope==='shop'?'Theo nhóm sản phẩm; click để drill-down.':(entityScope==='group'?'Theo sản phẩm; click để drill-down.':'Sản phẩm đang chọn'))+'</div><div class="ads-breakdown-list">'+(constituents.length?constituents.slice(0,12).map(x=>'<div class="ads-breakdown-row" data-drill-kind="'+x.kind+'" data-drill-key="'+esc(x.key)+'"><span class="ads-breakdown-name" title="'+esc(x.label)+'">'+esc(x.label)+'</span><span class="ads-breakdown-track"><i style="width:'+Math.max(3,Number(x.summary.adSpend||0)/maxSpend*100)+'%"></i></span><span class="ads-breakdown-metric">'+money(x.summary.adSpend)+'</span><span class="ads-breakdown-roas '+(x.summary.roas>=current.roas?'ads-up':'ads-down')+'">'+xnum(x.summary.roas)+'</span></div>').join(''):'<div class="ads-fin-section-sub">Không có cấp phân rã thấp hơn cho scope hiện tại.</div>')+'</div></section>';

  const scatterRows=entityScope==='product'?[]:entityProducts.filter(x=>Number(x.adSpend||0)>0&&Number(x.cpc||0)>0);const scatter=(()=>{if(!scatterRows.length)return '<section class="ads-fin-card"><div class="ads-fin-section-title">Bản đồ CPC × ROAS</div><div class="ads-fin-section-sub">Scope sản phẩm không cần scatter phân rã.</div></section>';const w=520,h=220,p=24,maxX=Math.max(...scatterRows.map(x=>Number(x.cpc||0)),1),maxY=Math.max(...scatterRows.map(x=>Number(x.roas||0)),1),avgR=ratio(scatterRows.reduce((a,x)=>a+Number(x.attributedSales||0),0),scatterRows.reduce((a,x)=>a+Number(x.adSpend||0),0));const dots=scatterRows.map(x=>{const cx=p+Number(x.cpc||0)/maxX*(w-p*2),cy=h-p-Number(x.roas||0)/maxY*(h-p*2),r=Math.max(3,Math.min(12,Math.sqrt(Number(x.adSpend||0)/Math.max(1,current.adSpend))*28)),risk=Number(x.roas||0)<avgR?' risk':'';return '<circle class="ads-scatter-dot'+risk+'" cx="'+cx+'" cy="'+cy+'" r="'+r+'"><title>'+esc(shortFor(x))+' · CPC '+money(x.cpc)+' · ROAS '+xnum(x.roas)+' · Spend '+money(x.adSpend)+'</title></circle>'}).join('');return '<section class="ads-fin-card"><div class="ads-fin-section-title">Bản đồ CPC × ROAS</div><div class="ads-fin-section-sub">Mỗi điểm là một sản phẩm; kích thước phản ánh chi tiêu.</div><div class="ads-scatter-wrap"><svg class="ads-scatter" viewBox="0 0 '+w+' '+h+'"><line class="ads-scatter-axis" x1="'+p+'" y1="'+(h-p)+'" x2="'+(w-p)+'" y2="'+(h-p)+'"/><line class="ads-scatter-axis" x1="'+p+'" y1="'+p+'" x2="'+p+'" y2="'+(h-p)+'"/><line class="ads-scatter-mid" x1="'+p+'" y1="'+(h-p-avgR/maxY*(h-p*2))+'" x2="'+(w-p)+'" y2="'+(h-p-avgR/maxY*(h-p*2))+'"/>'+dots+'</svg></div><div class="ads-chart-axis"><span>CPC thấp</span><span>CPC cao</span></div></section>'})();

  const weakest=[['Hiển thị','impressions'],['CTR','ctr'],['CR','cvr'],['AOV','adsAov']].filter(x=>deltas[x[1]]!==null).sort((a,b)=>Number(deltas[a[1]])-Number(deltas[b[1]]))[0];const cost30=benchmarks.m1?delta(current.cpc,benchmarks.m1.cpc):null;const deskItems=[
    ['Kết quả','ROAS '+xnum(current.roas),previous?('So với kỳ trước '+formatDelta(deltas.roas)+'. GMV Ads '+formatDelta(deltas.attributedSales)+'.'):'Chưa đủ kỳ trước để so sánh.'],
    ['Funnel',weakest?(weakest[0]+' là biến giảm mạnh nhất'):'Chưa đủ kỳ so sánh',weakest?('Biến động '+formatDelta(deltas[weakest[1]])+' so với kỳ trước; đây là quan sát định lượng, không phải nguyên nhân.'):'Không tạo kết luận khi thiếu bằng chứng.'],
    ['Chi phí',cost30===null?'Chưa đủ baseline 1M':('CPC '+(cost30>0?'cao hơn':'thấp hơn')+' 1M'),cost30===null?'Cần đủ 30 ngày trusted history.':('Chênh '+formatDelta(cost30)+' so với cửa sổ 30 ngày hiện tại.')]
  ];
  const rawSignals=snap.signals||[],signals=rawSignals.filter(sig=>entityScope==='shop'||(entityScope==='product'?String(sig.productId)===entityKey:entityRecords[String(sig.productId)]?.group===entityKey)).slice(0,4);const desk='<section class="ads-intelligence-desk"><div class="ads-desk-head"><div><div class="ads-desk-title">Ads Intelligence Desk</div><div class="ads-desk-sub">Tham khảo sau khi đã đọc dữ liệu và biểu đồ phía trên. Intelligence chỉ tóm tắt evidence đã có.</div></div><span class="native-preprod">EVIDENCE ONLY</span></div><div class="ads-desk-grid">'+deskItems.map(x=>'<div class="ads-desk-item"><span class="ads-desk-kicker">'+esc(x[0])+'</span><b>'+esc(x[1])+'</b><p>'+esc(x[2])+'</p></div>').join('')+'</div>'+(signals.length?'<div class="ads-desk-signals">'+signals.map(sig=>'<div class="ads-desk-signal '+(sig.type==='Vấn đề'?'problem':'opportunity')+'"><b>'+esc(entityRecords[String(sig.productId)]?.displayName||sig.productName||sig.productId)+'</b><span>'+esc(sig.type)+' · ROAS '+formatDelta(sig.roasDelta)+' · Spend share '+pct(sig.spendShare)+'</span></div>').join('')+'</div>':'')+'</section>';

  const view=document.createElement('section');view.className='ads-financial';view.innerHTML=equation+kpis+'<section class="ads-fin-grid">'+trend+funnel+'</section>'+'<section class="ads-fin-grid equal">'+costs+breakdown+'</section>'+scatter+desk;main.appendChild(view);
  const activate=metric=>{if(!metricMeta[metric])return;focusMetric=metric;view.querySelectorAll('[data-focus]').forEach(el=>el.classList.toggle('active',el.dataset.focus===metric));const chart=view.querySelector('#adsMainChart'),label=view.querySelector('#adsFocusLabel');if(chart)chart.innerHTML=renderLine(metric);if(label)label.textContent=metricMeta[metric][0];};
  view.querySelectorAll('[data-focus]').forEach(el=>el.onclick=()=>activate(el.dataset.focus));
  view.querySelectorAll('[data-drill-kind]').forEach(el=>el.onclick=()=>go({adsEntityScope:el.dataset.drillKind==='group'?'group':'product',adsEntity:el.dataset.drillKey}));
})();
""".replace("__ENTITY_MAP__", encoded)


def _validate_financial_artifact(output_dir: Any) -> None:
    html = (Path(output_dir) / "command_center_v2_multi_shop_native_template.html").read_text(encoding="utf-8")
    required = (
        ADS_FINANCIAL_PATCH_VERSION,
        "Phương trình hiệu quả Ads", "GMV Ads", "Ads Spend", "AOV", "Chuyển đổi",
        "Hiển thị", "CTR", "CR", "CPC", "Click", "Diễn biến trong kỳ", "Funnel Ads",
        "Áp lực chi phí", "1W", "1M", "3M", "6M", "Phân bổ hiệu quả",
        "Bản đồ CPC × ROAS", "Ads Intelligence Desk", "Shop", "Nhóm SP", "Sản phẩm",
        ".ads-equation{", ".ads-fin-kpis{", ".ads-cost-grid{", ".ads-intelligence-desk{",
    )
    missing = [x for x in required if x not in html]
    if missing:
        raise ValueError(f"Ads Financial artifact checks missing: {missing}")
    if "font-family" in FINANCIAL_STYLE:
        raise ValueError("Ads Financial layer must inherit project typography")


def build_native_v2_multi_shop(*, payload_dir: Any, v2_template_path: Any, output_dir: Any):
    payload_path = Path(payload_dir) / "ui_payload.json"
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    entity_map = build_ads_entity_map(payload)

    original_style = _ads.ADS_STYLE
    original_runtime = _ads._ads_runtime
    original_version = _ads.ADS_NATIVE_PATCH_VERSION

    def runtime_with_financial(short_map):
        return original_runtime(short_map) + "\n" + _financial_runtime(entity_map)

    _ads.ADS_STYLE = original_style + "\n" + FINANCIAL_STYLE
    _ads._ads_runtime = runtime_with_financial
    _ads.ADS_NATIVE_PATCH_VERSION = ADS_FINANCIAL_PATCH_VERSION
    try:
        result = _ads.build_native_v2_multi_shop(
            payload_dir=payload_dir,
            v2_template_path=v2_template_path,
            output_dir=output_dir,
        )
        if result.get("nativePatchVersion") != ADS_FINANCIAL_PATCH_VERSION:
            raise ValueError("Ads Financial patch version missing from lineage")
        _validate_financial_artifact(output_dir)
        result["adsFinancialUiReady"] = True
        result["adsEntityScopeReady"] = True
        result["adsGroupRuleVersion"] = ADS_GROUP_RULE_VERSION
        return result
    finally:
        _ads.ADS_STYLE = original_style
        _ads._ads_runtime = original_runtime
        _ads.ADS_NATIVE_PATCH_VERSION = original_version
