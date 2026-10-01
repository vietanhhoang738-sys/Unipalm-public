"""Native V2 Product destination for PREPRODUCTION.

Product is a single-shop diagnostic workspace. The production V2 template stays
read-only; this wrapper extends the validated Native artifact with Product
navigation, monthly-family time scopes and evidence-bound Product Intelligence.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Mapping

from . import ui_v2_native as _native
from . import ui_v2_operator_copy_review as _operator

PRODUCT_NATIVE_PATCH_VERSION = "native-product-intelligence-v34"

PRODUCT_STYLE = r"""
/* Product destination: shared V2 tokens only. */
.product-destination{display:grid;gap:18px;margin-top:4px}
.product-hero{display:grid;grid-template-columns:minmax(0,1.55fr) minmax(280px,.85fr);border:1px solid var(--line);border-radius:16px;background:var(--surface);overflow:hidden}
.product-hero-main{padding:24px 26px}.product-hero-side{padding:20px;border-left:1px solid var(--line);background:var(--soft)}
.product-eyebrow{font-size:10px;font-weight:700;color:var(--muted);letter-spacing:.02em}.product-headline{margin-top:10px;font-size:24px;line-height:1.24;font-weight:720;letter-spacing:-.02em;color:var(--ink)}
.product-copy{margin-top:8px;font-size:11px;line-height:1.55;color:var(--muted)}
.product-history-state{padding:14px;border:1px solid var(--line);border-radius:12px;background:var(--surface)}.product-history-state b{display:block;font-size:12px;color:var(--ink)}.product-history-state span{display:block;margin-top:6px;font-size:10px;line-height:1.5;color:var(--muted)}
.product-history-lineage{margin-top:8px;font-size:8.5px;color:var(--muted2);line-height:1.45}
.product-horizon-tabs{display:flex;gap:6px;flex-wrap:wrap}.product-horizon-tab{border:1px solid var(--line);background:var(--surface);color:var(--muted);padding:8px 11px;border-radius:9px;font-size:10px;font-weight:700;cursor:pointer}.product-horizon-tab.active{background:var(--green);border-color:var(--green);color:#fff}.product-horizon-tab:disabled{opacity:.42;cursor:not-allowed}
.product-kpis{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:12px}.product-kpi{padding:15px;border:1px solid var(--line);border-radius:13px;background:var(--surface)}.product-kpi-label{font-size:9.5px;color:var(--muted2);font-weight:700}.product-kpi-value{margin-top:9px;font-size:21px;line-height:1.1;font-weight:730;color:var(--ink);font-variant-numeric:tabular-nums}.product-kpi-note{margin-top:6px;font-size:9px;color:var(--muted)}
.product-grid-2{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}.product-card{padding:20px;border:1px solid var(--line);border-radius:14px;background:var(--surface)}.product-card h3{margin:0;font-size:16px;color:var(--ink)}.product-card-sub{margin-top:5px;font-size:10px;line-height:1.5;color:var(--muted)}
.product-concentration{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:9px;margin-top:16px}.product-concentration div{padding:12px;border-radius:10px;background:var(--soft)}.product-concentration b{display:block;font-size:18px;color:var(--ink)}.product-concentration span{display:block;margin-top:4px;font-size:9px;color:var(--muted)}
.product-funnel{display:grid;gap:10px;margin-top:16px}.product-funnel-row{display:grid;grid-template-columns:118px 90px minmax(80px,1fr);gap:10px;align-items:center;font-size:10px}.product-funnel-row b{color:var(--text)}.product-funnel-row strong{text-align:right;color:var(--ink);font-variant-numeric:tabular-nums}.product-funnel-track{height:7px;border-radius:999px;background:var(--line);overflow:hidden}.product-funnel-track i{display:block;height:100%;border-radius:999px;background:var(--green)}
.product-signal-list{display:grid;gap:9px;margin-top:14px}.product-signal{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:12px;padding:11px 0;border-top:1px solid var(--line)}.product-signal:first-child{border-top:0}.product-signal-name{font-size:10.5px;font-weight:700;color:var(--text);line-height:1.4}.product-signal-meta{margin-top:4px;font-size:9px;color:var(--muted);line-height:1.45}.product-signal-driver{display:inline-flex;margin-top:6px;padding:4px 7px;border:1px solid var(--line);border-radius:7px;background:var(--surface);font-size:8.5px;color:var(--muted)}.product-signal-value{text-align:right;font-size:10px;font-weight:750}.product-signal-value.down{color:var(--red)}.product-signal-value.up{color:var(--green)}
.product-causality-note{margin-top:10px;padding-top:9px;border-top:1px solid var(--line);font-size:8.5px;line-height:1.45;color:var(--muted2)}
.product-table-tools{display:flex;align-items:center;gap:10px;justify-content:space-between;margin-top:14px}.product-search{width:min(320px,100%);border:1px solid var(--line);border-radius:9px;background:var(--surface);color:var(--text);padding:8px 10px;font-size:10px}.product-table-wrap{overflow:auto;margin-top:10px}.product-table{width:100%;min-width:900px;border-collapse:separate;border-spacing:0;font-size:9.5px}.product-table th{position:sticky;top:0;background:var(--surface);color:var(--muted2);font-size:8.5px;text-align:right;padding:10px 9px;border-bottom:1px solid var(--line)}.product-table th:first-child,.product-table td:first-child{text-align:left}.product-table td{padding:11px 9px;border-bottom:1px solid var(--line);text-align:right;font-variant-numeric:tabular-nums}.product-table tbody tr:hover td{background:var(--soft)}.product-name{max-width:300px;font-weight:700;color:var(--text);line-height:1.4}.product-sku{margin-top:3px;font-size:8.5px;color:var(--muted2)}
@media(max-width:1050px){.product-hero{grid-template-columns:1fr}.product-hero-side{border-left:0;border-top:1px solid var(--line)}.product-kpis{grid-template-columns:repeat(3,minmax(0,1fr))}}
@media(max-width:760px){.product-grid-2{grid-template-columns:1fr}.product-kpis{grid-template-columns:repeat(2,minmax(0,1fr))}.product-hero-main{padding:20px}.product-funnel-row{grid-template-columns:100px 76px minmax(60px,1fr)}}
"""

PRODUCT_RUNTIME = r"""
(function(){
  const q=new URLSearchParams(location.search);
  if(q.get("destination")!=="product")return;
  const B=window.UNIPALM_SCOPE_BUNDLE||{},S=window.UNIPALM_NATIVE_SCOPE||{};
  const P=B.productDestination||{},shops=B.shops||[],byId=Object.fromEntries(shops.map(x=>[x.shopId,x]));
  const scope=(P.shops||{})[S.shop]||{};
  const header=document.querySelector(".header"),main=document.querySelector(".main"),bar=document.querySelector(".native-scope-bar"),nav=document.querySelector(".nav");
  if(!header||!main||!bar||!scope)return;
  const esc=v=>String(v??"").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[m]));
  const nv=new Intl.NumberFormat("vi-VN",{maximumFractionDigits:1}),n0=new Intl.NumberFormat("vi-VN",{maximumFractionDigits:0});
  const money=v=>{const x=Number(v||0),a=Math.abs(x),sg=x<0?"-":"";if(a>=1e9)return sg+nv.format(a/1e9)+"tỷ đ";if(a>=1e6)return sg+nv.format(a/1e6)+"tr đ";if(a>=1e3)return sg+nv.format(a/1e3)+"k đ";return sg+n0.format(a)+" đ"};
  const pct=v=>nv.format(Number(v||0)*100)+"%",roas=v=>nv.format(Number(v||0))+"x",num=v=>n0.format(Number(v||0));
  const labels={oneMonth:"1 tháng",threeMonths:"3 tháng",sixMonths:"6 tháng",year:"Năm"};
  const driverLabels={productClicks:"Lượt nhấp sản phẩm",cvr:"CVR",aov:"AOV"};
  const shopName=byId[S.shop]?.displayName||scope.displayName||S.shop;
  function go(params){const u=new URL(location.href);Object.entries(params).forEach(([k,v])=>u.searchParams.set(k,v));location.href=u.toString()}

  if(nav){
    let productNav=nav.querySelector('[data-native-destination="product"]');
    if(!productNav){productNav=document.createElement("button");productNav.type="button";productNav.textContent="Sản phẩm";productNav.dataset.nativeDestination="product";nav.appendChild(productNav)}
    productNav.onclick=()=>go({destination:"product",scope:"shop",shop:S.shop});
    nav.querySelectorAll("button").forEach(b=>b.classList.remove("active"));productNav.classList.add("active");
    const commandNav=nav.querySelector('[data-native-destination="command-center"]');
    if(commandNav){commandNav.onclick=()=>{const u=new URL(location.href);u.searchParams.delete("destination");u.searchParams.set("scope","portfolio");location.href=u.toString()}}
    const compareNav=nav.querySelector('[data-native-destination="compare"]');
    if(compareNav){compareNav.onclick=()=>{const u=new URL(location.href);u.searchParams.delete("destination");u.searchParams.set("scope","compare");location.href=u.toString()}}
  }

  const order=scope.timeScopeOrder||["oneMonth","threeMonths","sixMonths","year"],horizons=scope.horizons||{};
  let key=q.get("productHorizon")||"threeMonths";
  if(!horizons[key]||horizons[key].status!=="READY")key=order.find(k=>horizons[k]?.status==="READY")||"oneMonth";
  const H=horizons[key]||{},summary=H.summary||{},products=H.products||[],intel=scope.structuralIntelligence||{},history=scope.historyLineage||{};
  const opts=shops.map(x=>'<option value="'+esc(x.shopId)+'">'+esc(x.displayName||x.shopId)+'</option>').join("");
  const tabs=order.map(k=>{const h=horizons[k]||{},ready=h.status==="READY";return '<button class="product-horizon-tab '+(k===key?"active":"")+'" data-product-horizon="'+esc(k)+'" '+(ready?"":"disabled")+' title="'+(ready?"":('Thiếu: '+esc((h.missingMonths||[]).join(", "))))+'">'+esc(labels[k]||k)+'</button>'}).join("");
  bar.innerHTML='<span class="native-preprod">PREPRODUCTION</span><div class="native-picker"><label for="productShopSelect">SHOP</label><select id="productShopSelect">'+opts+'</select></div><div class="product-horizon-tabs" aria-label="Kỳ xem sản phẩm">'+tabs+'</div><div class="native-lineage">Sản phẩm · Theo tháng</div>';
  const shopSelect=document.getElementById("productShopSelect");if(shopSelect){shopSelect.value=S.shop;shopSelect.onchange=e=>go({destination:"product",scope:"shop",shop:e.target.value,productHorizon:key})}
  bar.querySelectorAll("[data-product-horizon]").forEach(b=>b.onclick=()=>go({destination:"product",scope:"shop",shop:S.shop,productHorizon:b.dataset.productHorizon}));

  const title=header.querySelector("h1"),subtitle=header.querySelector("p");if(title)title.textContent="Sản phẩm · "+shopName;if(subtitle)subtitle.textContent="Hiệu quả sản phẩm · "+labels[key]+" · dữ liệu theo tháng";
  Array.from(main.children).forEach(el=>{if(el!==header&&el!==bar)el.style.display="none"});

  const top3=Number(summary.top3GmvShare||0),structReady=intel.status==="READY";
  let attentionTitle="Chưa đủ lịch sử cho xu hướng cấu trúc",attentionCopy="Chưa có đủ 6 tháng hoàn tất đã xác thực để mở phân tích cấu trúc.";
  let signalHtml="";
  if(structReady){
    const signals=(intel.signals||[]).slice(0,4);const problems=signals.filter(x=>x.type==="Vấn đề");const opportunities=signals.filter(x=>x.type==="Cơ hội");
    attentionTitle=problems.length?problems.length+" sản phẩm có tín hiệu cần chú ý":(opportunities.length?opportunities.length+" cơ hội tăng trưởng cấu trúc":"Chưa có tín hiệu cấu trúc nổi bật");
    attentionCopy="So sánh 3 tháng hoàn tất gần nhất với 3 tháng hoàn tất trước đó; tháng hiện tại chỉ dùng đối chiếu bổ sung.";
    signalHtml=signals.map(x=>{
      const a=x.driverAttribution||{},top=(a.driverContributions||[])[0]||{},driver=driverLabels[a.topDriverMetric]||a.topDriverMetric||"Chưa đủ yếu tố";
      const share=top.contributionShareOfModeledGap;
      const shareText=(share===null||share===undefined)?"":(" · đóng góp "+pct(share));
      return '<div class="product-signal"><div><div class="product-signal-name">'+esc(x.productName||"Chưa xác định tên sản phẩm")+'</div><div class="product-signal-meta">'+esc(x.resolvedParentSku||"")+' · Điểm ưu tiên '+nv.format(x.priorityScore||0)+'</div><span class="product-signal-driver">Yếu tố chính: '+esc(driver)+esc(shareText)+'</span></div><div class="product-signal-value '+(Number(x.gmvDelta||0)<0?"down":"up")+'">'+(Number(x.gmvDelta||0)>0?"+":"")+pct(x.gmvDelta||0)+'</div></div>';
    }).join("");
    signalHtml+='<div class="product-causality-note">Mức đóng góp được phân rã theo GMV = Lượt nhấp sản phẩm × CVR × AOV; đây không phải kết luận quan hệ nhân quả.</div>';
  }else if(intel.status==="INSUFFICIENT_OPERATING_HISTORY"){
    attentionTitle="Shop chưa đủ tuổi dữ liệu cho phân tích cấu trúc";
    attentionCopy="Shop chưa có đủ 6 tháng vận hành hoàn tất. Các tháng trước khi shop hoạt động không được coi là dữ liệu thiếu và hệ thống không tạo tín hiệu giả.";
    signalHtml='<div class="product-copy">Phân tích cấu trúc sẽ tự mở khi shop tích lũy đủ 6 tháng vận hành hoàn tất đã được xác thực.</div>';
  }else{
    const missing=(intel.missingMonths||[]).join(", ");
    attentionTitle="Thiếu lịch sử đã xác thực cho phân tích cấu trúc";
    attentionCopy="Shop đã hoạt động trước cửa sổ lịch sử tin cậy nhưng chưa đủ 6 tháng hoàn tất để so sánh cấu trúc.";
    signalHtml='<div class="product-copy">'+(missing?('Thiếu các tháng: '+esc(missing)+'. '):'')+'Hệ thống không tạo vấn đề/cơ hội cấu trúc khi bằng chứng chưa đủ.</div>';
  }
  const canonical=(history.canonicalSemanticMonths||[]).length,backfill=(history.semanticBackfillMonths||[]).length;
  const lineageCopy='Nguồn lịch sử: '+num(canonical)+' tháng dữ liệu chuẩn'+(backfill?(' + '+num(backfill)+' tháng lịch sử sản phẩm đã xác thực'):'')+'.';

  const funnel=[
    ["Lượt xem",summary.productViews||0,1],
    ["Lượt nhấp",summary.productClicks||0,summary.productViews?summary.productClicks/summary.productViews:0],
    ["Thêm giỏ",summary.addToCartVisits||0,summary.productVisits?summary.addToCartVisits/summary.productVisits:0],
    ["Đơn đã đặt",summary.placedOrders||0,summary.productClicks?summary.placedOrders/summary.productClicks:0],
  ];
  const maxF=Math.max(...funnel.map(x=>Number(x[1]||0)),1);
  const funnelHtml=funnel.map((x,idx)=>'<div class="product-funnel-row"><b>'+esc(x[0])+'</b><strong>'+num(x[1])+(idx?'<span style="display:block;font-size:8px;color:var(--muted)">'+pct(x[2])+'</span>':'')+'</strong><span class="product-funnel-track"><i style="width:'+Math.max(3,Number(x[1]||0)/maxF*100)+'%"></i></span></div>').join("");
  const totalGmv=Number(summary.placedGmv||0);
  const rows=products.map(p=>'<tr data-product-search="'+esc(((p.productName||"")+" "+(p.resolvedParentSku||p.productSkuObserved||"")).toLowerCase())+'"><td><div class="product-name">'+esc(p.productName||"Chưa xác định tên sản phẩm")+'</div><div class="product-sku">'+esc(p.resolvedParentSku||p.productSkuObserved||"")+'</div></td><td>'+money(p.placed_gmv)+'</td><td>'+pct(totalGmv?Number(p.placed_gmv||0)/totalGmv:0)+'</td><td>'+num(p.placed_orders)+'</td><td>'+pct(p.ctr)+'</td><td>'+pct(p.atcRate)+'</td><td>'+money(p.ads_spend)+'</td><td>'+roas(p.roas)+'</td></tr>').join("");

  const view=document.createElement("section");view.className="product-destination";view.innerHTML=
    '<section class="product-hero"><div class="product-hero-main"><div class="product-eyebrow">Tóm tắt sản phẩm · '+esc(labels[key])+'</div><div class="product-headline">'+money(summary.placedGmv)+' GMV từ '+num(summary.productCount)+' sản phẩm</div><div class="product-copy">Top 3 sản phẩm đóng góp '+pct(top3)+' GMV. Đọc phân tích và cấu trúc danh mục trước khi đi xuống từng SKU.</div><div class="product-history-lineage">'+esc(lineageCopy)+'</div></div><aside class="product-hero-side"><div class="product-history-state"><b>'+esc(attentionTitle)+'</b><span>'+esc(attentionCopy)+'</span></div><div class="product-signal-list">'+signalHtml+'</div></aside></section>'+
    '<section class="product-kpis"><div class="product-kpi"><div class="product-kpi-label">GMV đặt hàng</div><div class="product-kpi-value">'+money(summary.placedGmv)+'</div><div class="product-kpi-note">'+esc(labels[key])+'</div></div><div class="product-kpi"><div class="product-kpi-label">Đơn đã đặt</div><div class="product-kpi-value">'+num(summary.placedOrders)+'</div><div class="product-kpi-note">AOV '+money(summary.placedAov)+'</div></div><div class="product-kpi"><div class="product-kpi-label">CTR sản phẩm</div><div class="product-kpi-value">'+pct(summary.ctr)+'</div><div class="product-kpi-note">'+num(summary.productClicks)+' lượt nhấp</div></div><div class="product-kpi"><div class="product-kpi-label">Tỷ lệ thêm giỏ</div><div class="product-kpi-value">'+pct(summary.atcRate)+'</div><div class="product-kpi-note">'+num(summary.addToCartVisits)+' lượt</div></div><div class="product-kpi"><div class="product-kpi-label">ROAS sản phẩm</div><div class="product-kpi-value">'+roas(summary.roas)+'</div><div class="product-kpi-note">Chi tiêu Ads '+money(summary.adsSpend)+'</div></div></section>'+
    '<section class="product-grid-2"><div class="product-card"><h3>Cơ cấu danh mục</h3><div class="product-card-sub">Mức độ tập trung GMV trong shop đang chọn.</div><div class="product-concentration"><div><b>'+pct(summary.top1GmvShare)+'</b><span>Top 1 GMV</span></div><div><b>'+pct(summary.top3GmvShare)+'</b><span>Top 3 GMV</span></div><div><b>'+pct(summary.top5GmvShare)+'</b><span>Top 5 GMV</span></div></div></div><div class="product-card"><h3>Hiệu quả funnel sản phẩm</h3><div class="product-card-sub">Các tầng được tổng hợp theo đúng cấu trúc dữ liệu theo tháng.</div><div class="product-funnel">'+funnelHtml+'</div></div></section>'+
    '<section class="product-card"><h3>Chi tiết sản phẩm</h3><div class="product-card-sub">Tên sản phẩm là nhãn chính; SKU chỉ là định danh phụ. Số liệu theo shop và kỳ đang chọn.</div><div class="product-table-tools"><input id="productSearch" class="product-search" type="search" placeholder="Tìm tên sản phẩm hoặc SKU"><span class="product-copy">'+num(products.length)+' sản phẩm</span></div><div class="product-table-wrap"><table class="product-table"><thead><tr><th>Sản phẩm</th><th>GMV</th><th>Tỷ trọng</th><th>Đơn</th><th>CTR</th><th>Thêm giỏ</th><th>Chi tiêu Ads</th><th>ROAS</th></tr></thead><tbody>'+rows+'</tbody></table></div></section>';
  main.appendChild(view);
  const search=document.getElementById("productSearch");if(search)search.oninput=e=>{const term=String(e.target.value||"").trim().toLowerCase();view.querySelectorAll("[data-product-search]").forEach(r=>r.style.display=!term||r.dataset.productSearch.includes(term)?"":"none")};
})();
"""


def _bundle_with_product(payload: Mapping[str, Any]) -> Dict[str, Any]:
    base = _ORIGINAL_BUNDLE(payload)
    product = ((payload.get("destinations") or {}).get("product") or {})
    base["productDestination"] = product
    return base


def _validate_product_payload(payload: Mapping[str, Any]) -> None:
    product = ((payload.get("destinations") or {}).get("product") or {})
    scope = product.get("scopePolicy") or {}
    if not product:
        raise ValueError("Product destination payload missing")
    if not bool(scope.get("singleShopOnly")) or bool(scope.get("compareAllowed")):
        raise ValueError("Product Native destination must be single-shop only")
    if str(scope.get("canonicalSourceGrain")) != "MONTHLY" or not bool(scope.get("dayWeekForbidden")):
        raise ValueError("Product Native destination must remain monthly-grain")
    if list(scope.get("allowedTimeScopes") or []) != ["oneMonth", "threeMonths", "sixMonths", "year"]:
        raise ValueError("Product time-scope contract mismatch")
    for sid, shop in (product.get("shops") or {}).items():
        if shop.get("compareAllowed") is not False or str(shop.get("sourceGrain")) != "MONTHLY":
            raise ValueError(f"unsafe Product scope for {sid}")
        for horizon in (shop.get("horizons") or {}).values():
            if str(horizon.get("status")) == "INSUFFICIENT_HISTORY" and list(horizon.get("products") or []):
                raise ValueError(f"Product unavailable horizon contains rows for {sid}")
        intel = shop.get("structuralIntelligence") or {}
        if str(intel.get("status")) == "READY":
            if str(intel.get("currentPartialMonthRole")) != "CORROBORATING_ONLY_NOT_SCORED":
                raise ValueError(f"Product structural MTD role invalid for {sid}")
            for signal in intel.get("signals") or []:
                if bool(signal.get("causalClaim")):
                    raise ValueError(f"Product causal claim leaked for {sid}")
                attr = signal.get("driverAttribution") or {}
                if str(attr.get("status")) == "ATTRIBUTED" and bool(attr.get("causalClaim")):
                    raise ValueError(f"Product attribution causal claim leaked for {sid}")


def _validate_product_artifact(output_dir: Any) -> None:
    html = (Path(output_dir) / "command_center_v2_multi_shop_native_template.html").read_text(encoding="utf-8")
    required = (
        "Sản phẩm", "destination\")!==\"product", "productHorizon", "1 tháng", "3 tháng", "6 tháng",
        "Tóm tắt sản phẩm", "Cơ cấu danh mục", "Hiệu quả funnel sản phẩm", "Chi tiết sản phẩm",
        "So sánh 3 tháng hoàn tất gần nhất", "tháng hiện tại chỉ dùng đối chiếu bổ sung",
        "Shop chưa đủ tuổi dữ liệu cho phân tích cấu trúc", "Yếu tố chính:",
        "GMV = Lượt nhấp sản phẩm × CVR × AOV", "không phải kết luận quan hệ nhân quả",
        ".product-destination{", ".product-signal-driver{",
    )
    missing = [x for x in required if x not in html]
    if missing:
        raise ValueError(f"Product Native artifact checks missing: {missing}")
    if 'data-native-scope="compare"' in html:
        raise ValueError("Product must not add compare as a domain scope")


_ORIGINAL_BUNDLE = _native._bundle_from_payload


def build_native_v2_multi_shop(*, payload_dir: Any, v2_template_path: Any, output_dir: Any):
    payload_path = Path(payload_dir) / "ui_payload.json"
    import json
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    _validate_product_payload(payload)

    original_bundle = _native._bundle_from_payload
    original_style = _native.NATIVE_STYLE
    original_runtime = _native.NATIVE_RUNTIME
    original_version = _operator.OPERATOR_COPY_PATCH_VERSION
    _native._bundle_from_payload = _bundle_with_product
    _native.NATIVE_STYLE = original_style + "\n" + PRODUCT_STYLE
    _native.NATIVE_RUNTIME = original_runtime + "\n" + PRODUCT_RUNTIME
    _operator.OPERATOR_COPY_PATCH_VERSION = PRODUCT_NATIVE_PATCH_VERSION
    try:
        result = _operator.build_native_v2_multi_shop(
            payload_dir=payload_dir,
            v2_template_path=v2_template_path,
            output_dir=output_dir,
        )
        if result.get("nativePatchVersion") != PRODUCT_NATIVE_PATCH_VERSION:
            raise ValueError("Product Native patch version missing from lineage")
        _validate_product_artifact(output_dir)
        result["productDestinationReady"] = True
        return result
    finally:
        _native._bundle_from_payload = original_bundle
        _native.NATIVE_STYLE = original_style
        _native.NATIVE_RUNTIME = original_runtime
        _operator.OPERATOR_COPY_PATCH_VERSION = original_version
