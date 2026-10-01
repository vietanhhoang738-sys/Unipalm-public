"""Human-review / Intelligence-first patch for PREPRODUCTION Native V2.

The production V2 template remains read-only. This wrapper preserves the v29
finance-table canary fix and layers the v30 Command Center Intelligence-first
presentation on top of the canonical Native builder. All changes participate in
the Native V2 fingerprint and QA lineage.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from . import ui_v2_native as _native


INTELLIGENCE_FIRST_PATCH_VERSION = "native-production-shadow-mode-v30"
# Backward-compatible alias used by existing review tooling/tests.
HUMAN_VISUAL_PATCH_VERSION = INTELLIGENCE_FIRST_PATCH_VERSION

_FINANCE_GRID_OLD = ".compare-finance-grid{align-items:start;margin-top:0}"
_FINANCE_GRID_NEW = ".compare-finance-grid{grid-template-columns:1fr;align-items:start;margin-top:0}"

INTELLIGENCE_FIRST_STYLE = r"""
/* Command Center Intelligence-first visual pilot.
   Uses only the shared V2 tokens; Compare destination remains unchanged. */
.intelligence-first-command-center .pulse:not(.compare-pulse){display:none!important}
.intelligence-first-command-center .period-grid{gap:14px;margin-top:18px}
.intelligence-first-command-center .period-card{min-height:126px;border-radius:14px;padding:17px 18px;box-shadow:none}
.intelligence-first-command-center .period-card:hover{transform:none;border-color:var(--muted2)}
.intelligence-first-command-center .period-card.active{box-shadow:none}
.intelligence-first-command-center .period-title{font-size:11.5px;line-height:1.35;font-weight:650}
.intelligence-first-command-center .period-value{font-size:27px;line-height:1.08;margin-top:11px}
.intelligence-first-command-center .period-delta{display:inline-block;font-size:11.5px;line-height:1.3;margin-top:10px}
.intelligence-first-command-center .period-compare{display:block;margin:4px 0 0;font-size:10.5px;line-height:1.4}
.intelligence-first-command-center .period-note{font-size:10.5px;line-height:1.5;margin-top:9px}
.intelligence-first-command-center .selection{margin-top:16px;background:var(--soft);color:var(--text)}
.intelligence-first-command-center .kpi-grid{gap:12px;margin-top:12px}
.intelligence-first-command-center .kpi{min-height:108px;border-radius:14px;padding:15px 15px;box-shadow:none}
.intelligence-first-command-center .kpi .label{font-size:10.5px;line-height:1.35}
.intelligence-first-command-center .kpi .value{font-size:24px;line-height:1.08;margin-top:12px}
.intelligence-first-command-center .kpi .delta{font-size:10.5px;line-height:1.45;margin-top:11px}
.intelligence-first-command-center .card{box-shadow:none}
.intelligence-first-command-center .content-grid{margin-top:24px}
.intelligence-first-command-center .card h3{font-size:17px;line-height:1.3}
.intelligence-first-command-center .card-sub{font-size:10.5px;line-height:1.5}

.intel-brief{display:grid;grid-template-columns:minmax(0,1.55fr) minmax(270px,.75fr);gap:0;margin-top:4px;border:1px solid var(--line);border-radius:16px;background:var(--surface);box-shadow:none;overflow:hidden}
.intel-main{padding:24px 26px;min-width:0}
.intel-side{padding:20px;border-left:1px solid var(--line);background:var(--soft);display:grid;align-content:start;gap:12px}
.intel-eyebrow{display:flex;align-items:center;gap:8px;color:var(--muted);font-size:10.5px;font-weight:700;letter-spacing:.02em}
.intel-eyebrow:before{content:"";width:7px;height:7px;border-radius:50%;background:var(--green)}
.intel-headline{margin-top:13px;color:var(--ink);font-size:25px;line-height:1.22;font-weight:720;letter-spacing:-.025em}
.intel-subline{margin-top:8px;color:var(--muted);font-size:11.5px;line-height:1.55}
.intel-context{margin-top:13px;padding:10px 12px;border-radius:10px;background:var(--soft);color:var(--text);font-size:10.5px;line-height:1.5}
.intel-context b{color:var(--ink)}
.intel-drivers{display:grid;gap:10px;margin-top:19px}
.intel-driver{display:grid;grid-template-columns:116px 72px 92px minmax(80px,1fr);gap:10px;align-items:center;min-width:0}
.intel-driver-name{font-size:10.5px;font-weight:700;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.intel-driver-delta{font-size:10px;font-weight:650}
.intel-driver-effect{text-align:right;font-size:10.5px;font-weight:720;font-variant-numeric:tabular-nums}
.intel-driver-track{height:6px;border-radius:999px;background:var(--line);overflow:hidden}
.intel-driver-track i{display:block;height:100%;border-radius:999px;background:var(--green)}
.intel-driver-track i.neg{background:var(--red)}
.intel-driver-empty{padding:12px 0 2px;color:var(--muted);font-size:10.5px;line-height:1.5}
.intel-side-block{padding:14px;border:1px solid var(--line);border-radius:12px;background:var(--surface)}
.intel-side-label{font-size:9.5px;color:var(--muted2);font-weight:700;text-transform:uppercase;letter-spacing:.04em}
.intel-side-title{margin-top:8px;color:var(--ink);font-size:12.5px;line-height:1.4;font-weight:720}
.intel-side-copy{margin-top:6px;color:var(--muted);font-size:10px;line-height:1.5}
.intel-status{display:inline-flex;align-items:center;gap:6px;margin-top:9px;padding:6px 8px;border-radius:999px;background:var(--green-bg);color:var(--green);font-size:9px;font-weight:700}
.intel-status.guard{background:var(--amber-bg);color:var(--amber)}
.intel-status.issue{background:var(--red-bg);color:var(--red)}
.intel-section-head{margin:22px 0 0}
.intel-section-head h3{margin:0;color:var(--ink);font-size:16px;line-height:1.3}
.intel-section-head p{margin:5px 0 0;color:var(--muted2);font-size:10px;line-height:1.45}
body[data-theme="dark"].intelligence-first-command-center .intel-side{background:var(--soft)}
@media(max-width:980px){.intel-brief{grid-template-columns:1fr}.intel-side{border-left:0;border-top:1px solid var(--line);grid-template-columns:repeat(2,minmax(0,1fr))}.intel-driver{grid-template-columns:108px 66px 86px minmax(70px,1fr)}}
@media(max-width:700px){.intel-main{padding:20px}.intel-side{grid-template-columns:1fr}.intel-headline{font-size:22px}.intel-driver{grid-template-columns:1fr auto auto}.intel-driver-track{grid-column:1/-1}.intelligence-first-command-center .period-grid{grid-template-columns:1fr}.intelligence-first-command-center .kpi-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
"""

INTELLIGENCE_FIRST_RUNTIME = r"""
(function(){
  const S=window.UNIPALM_NATIVE_SCOPE||{};
  if(S.scope==="compare")return;
  const P=window.UNIPALM_DATA||{},CC=P.commandCenter||{},periods=CC.periods||{};
  const periodGrid=document.getElementById("periodGrid");
  const kpiGrid=document.getElementById("kpiGrid");
  if(!periodGrid||!kpiGrid||!Object.keys(periods).length)return;

  document.body.classList.add("intelligence-first-command-center");

  const esc=v=>String(v??"").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[m]));
  const nv=new Intl.NumberFormat("vi-VN",{maximumFractionDigits:1});
  const n0=new Intl.NumberFormat("vi-VN",{maximumFractionDigits:0});
  const pct=v=>v===null||v===undefined?"—":((Number(v)>0?"+":"")+nv.format(Number(v)*100)+"%");
  const compactMoney=v=>{
    const n=Number(v||0),a=Math.abs(n),sign=n<0?"-":"";
    if(a>=1e9)return sign+nv.format(a/1e9)+"tỷ đ";
    if(a>=1e6)return sign+nv.format(a/1e6)+"tr đ";
    if(a>=1e3)return sign+nv.format(a/1e3)+"k đ";
    return sign+n0.format(a)+" đ";
  };
  const shortDriver=k=>({productClicks:"Lượt nhấp sản phẩm",cvr:"CVR",aov:"AOV"}[k]||k||"Yếu tố");

  const brief=document.createElement("section");
  brief.id="intelligenceBrief";
  brief.className="intel-brief";
  periodGrid.parentNode.insertBefore(brief,periodGrid);

  const metricHead=document.createElement("div");
  metricHead.className="intel-section-head";
  metricHead.innerHTML="<h3>Chỉ số chính</h3><p>Dùng số liệu để xác nhận quy mô sau khi đã đọc phần Intelligence.</p>";
  kpiGrid.parentNode.insertBefore(metricHead,kpiGrid);

  function selectedKey(){
    const active=periodGrid.querySelector("[data-period].active");
    return active&&active.dataset.period&&periods[active.dataset.period]?active.dataset.period:"yesterday";
  }

  function issueRank(i){
    const s=String(i&&i.severityLevel||"").toUpperCase();
    return s==="HIGH"?3:s==="MEDIUM"?2:1;
  }

  function contextText(raw){
    const hc=raw.historicalComparator||{},q=String(hc.contextQualification||"");
    if(q==="CONTEXT_DIFFERENT")return "Bối cảnh kỳ tham chiếu khác hiện tại — dùng chênh lệch để đọc diễn biến, không suy ra nguyên nhân.";
    if(q==="CONTEXT_COMPATIBLE")return "Bối cảnh kỳ tham chiếu tương đồng; chênh lệch có giá trị tham khảo tốt hơn.";
    if(!raw.comparisonAvailable)return "Chưa đủ kỳ dữ liệu tương thích để so sánh.";
    return "So sánh định lượng khả dụng; mức độ bất thường chỉ được kết luận khi các evidence gate cho phép.";
  }

  function attentionState(raw){
    const smart=raw.smartIssues||{},issues=(smart.issues||[]).slice().sort((a,b)=>issueRank(b)-issueRank(a));
    if(issues.length){
      const issue=issues[0],conf=Number(issue.confidenceScore||0);
      return {
        cls:"issue",
        title:issue.label?issue.label+" cần chú ý":"Có Smart Issue cần chú ý",
        copy:issue.summary||"Smart Issue đã vượt qua các evidence gate hiện tại.",
        badge:(issue.severityLevel||"ISSUE")+" · "+n0.format(conf*100)+"% confidence",
        issue
      };
    }
    const hc=raw.historicalComparator||{};
    if(String(hc.anomalyEligibilityStatus||"")==="ANOMALY_BLOCKED"){
      return {
        cls:"guard",
        title:"Chưa đủ bằng chứng để kết luận bất thường",
        copy:"Intelligence giữ fail-closed: có thể đọc diễn biến và yếu tố tác động, nhưng chưa mở Smart Issue.",
        badge:"Evidence gate đang chặn",
        issue:null
      };
    }
    return {
      cls:"",
      title:"Chưa có vấn đề đạt ngưỡng cần xử lý",
      copy:"Không có Smart Issue đủ điều kiện trong kỳ đang xem.",
      badge:"Không có Smart Issue",
      issue:null
    };
  }

  function actionState(attention){
    const options=attention.issue&&(attention.issue.reviewOptions||[]);
    if(options&&options.length){
      const o=options[0]||{};
      return {
        title:o.title||"Xác minh evidence trước khi thay đổi",
        copy:"Review option cho người vận hành; không phải lệnh tự động và không cho phép platform mutation."
      };
    }
    return {
      title:"Chưa phát sinh hành động cần review",
      copy:"Hệ thống không tự đề xuất thay đổi khi Smart Issue hoặc evidence chưa đủ điều kiện."
    };
  }

  function renderIntelligence(){
    const key=selectedKey(),raw=periods[key]||{},cur=raw.current||{},delta=raw.delta||{};
    const active=periodGrid.querySelector("[data-period].active");
    const periodTitle=active?.querySelector(".period-title")?.textContent?.trim()||"Kỳ đang xem";
    const compareText=active?.querySelector(".period-compare")?.textContent?.trim()||"so với kỳ tham chiếu";
    const gmvDelta=delta.gmv;
    const hasDelta=raw.comparisonAvailable&&gmvDelta!==null&&gmvDelta!==undefined;
    const direction=Number(gmvDelta)>=0?"tăng":"giảm";
    const headline=hasDelta
      ?"GMV "+direction+" "+nv.format(Math.abs(Number(gmvDelta))*100)+"% "+compareText
      :"Chưa đủ dữ liệu để đánh giá diễn biến GMV";
    const attention=attentionState(raw),action=actionState(attention);
    const drivers=((raw.drivers||{}).status==="READY"?(raw.drivers||{}).drivers||[]:[]).slice(0,3);
    const driverHtml=drivers.length?drivers.map(d=>{
      const effect=Number(d.effectValue||0),share=Math.max(6,Math.min(100,Number(d.shareOfAbsoluteEffects||0)*100));
      const neg=effect<0;
      return '<div class="intel-driver">'+
        '<div class="intel-driver-name" title="'+esc(d.label||shortDriver(d.key))+'">'+esc(shortDriver(d.key))+'</div>'+
        '<div class="intel-driver-delta '+(Number(d.deltaPct||0)<0?"down":"up")+'">'+esc(pct(d.deltaPct))+'</div>'+
        '<div class="intel-driver-effect '+(neg?"down":"up")+'">'+esc((effect>0?"+":"")+compactMoney(effect))+'</div>'+
        '<span class="intel-driver-track"><i class="'+(neg?"neg":"")+'" style="width:'+share+'%"></i></span>'+
      '</div>';
    }).join(""):'<div class="intel-driver-empty">Chưa đủ dữ liệu để phân rã tác động của Lượt nhấp sản phẩm × CVR × AOV.</div>';

    brief.innerHTML=
      '<div class="intel-main">'+
        '<div class="intel-eyebrow">Tóm tắt vận hành · '+esc(periodTitle)+'</div>'+
        '<div class="intel-headline">'+esc(headline)+'</div>'+
        '<div class="intel-subline">GMV hiện tại <b>'+esc(compactMoney(cur.gmv))+'</b> · Intelligence ưu tiên diễn giải trước, số liệu chi tiết ở phía dưới.</div>'+
        '<div class="intel-context"><b>Cơ sở phân tích</b> · '+esc(contextText(raw))+'</div>'+
        '<div class="intel-drivers">'+driverHtml+'</div>'+
      '</div>'+
      '<aside class="intel-side">'+
        '<div class="intel-side-block">'+
          '<div class="intel-side-label">Cần chú ý</div>'+
          '<div class="intel-side-title">'+esc(attention.title)+'</div>'+
          '<div class="intel-side-copy">'+esc(attention.copy)+'</div>'+
          '<span class="intel-status '+esc(attention.cls)+'">'+esc(attention.badge)+'</span>'+
        '</div>'+
        '<div class="intel-side-block">'+
          '<div class="intel-side-label">Nên kiểm tra</div>'+
          '<div class="intel-side-title">'+esc(action.title)+'</div>'+
          '<div class="intel-side-copy">'+esc(action.copy)+'</div>'+
        '</div>'+
      '</aside>';
  }

  periodGrid.addEventListener("click",function(e){
    if(e.target&&e.target.closest&&e.target.closest("[data-period]")){
      setTimeout(renderIntelligence,0);
    }
  },true);
  renderIntelligence();
})();
"""


def _patched_style(style: str) -> str:
    """Apply reviewed Compare fix plus Intelligence-first Command Center styling."""
    if style.count(_FINANCE_GRID_OLD) != 1:
        raise ValueError("expected exactly one compare finance-grid style anchor")
    patched = style.replace(_FINANCE_GRID_OLD, _FINANCE_GRID_NEW, 1)
    if _FINANCE_GRID_OLD in patched or _FINANCE_GRID_NEW not in patched:
        raise ValueError("compare finance-grid visual patch did not apply cleanly")
    if ".intel-brief{" in patched:
        raise ValueError("intelligence-first style already present")
    return patched + "\n" + INTELLIGENCE_FIRST_STYLE


def _patched_runtime(runtime: str) -> str:
    """Append an evidence-bound intelligence presentation after canonical render."""
    if "intelligenceBrief" in runtime:
        raise ValueError("intelligence-first runtime already present")
    if 'const destination=S.scope==="compare"?"compare":"command-center"' not in runtime:
        raise ValueError("native destination runtime anchor missing")
    return runtime + "\n" + INTELLIGENCE_FIRST_RUNTIME


def build_native_v2_multi_shop(*, payload_dir: Any, v2_template_path: Any, output_dir: Any):
    """Run canonical builder with reviewed v30 Intelligence-first patch in lineage."""
    original_style = _native.NATIVE_STYLE
    original_runtime = _native.NATIVE_RUNTIME
    original_version = _native.NATIVE_PATCH_VERSION
    _native.NATIVE_STYLE = _patched_style(original_style)
    _native.NATIVE_RUNTIME = _patched_runtime(original_runtime)
    _native.NATIVE_PATCH_VERSION = INTELLIGENCE_FIRST_PATCH_VERSION
    try:
        result = _native.build_native_v2_multi_shop(
            payload_dir=payload_dir,
            v2_template_path=v2_template_path,
            output_dir=output_dir,
        )
        if result.get("nativePatchVersion") != INTELLIGENCE_FIRST_PATCH_VERSION:
            raise ValueError("intelligence-first patch version missing from Native V2 lineage")

        html_path = Path(output_dir) / "command_center_v2_multi_shop_native_template.html"
        html = html_path.read_text(encoding="utf-8")
        required = (
            "intelligenceBrief",
            "Tóm tắt vận hành",
            "Cần chú ý",
            "Nên kiểm tra",
            "Intelligence giữ fail-closed",
            "Chỉ số chính",
            ".intel-brief{",
            "intelligence-first-command-center",
        )
        missing = [x for x in required if x not in html]
        if missing:
            raise ValueError(f"intelligence-first artifact checks missing: {missing}")
        if "platform mutation" not in html:
            raise ValueError("human-review / no-mutation boundary missing from intelligence surface")
        return result
    finally:
        _native.NATIVE_STYLE = original_style
        _native.NATIVE_RUNTIME = original_runtime
        _native.NATIVE_PATCH_VERSION = original_version
