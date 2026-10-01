"""Read-only Smart Issue Review Console for Native V2 PREPRODUCTION.

The console consumes the validated Operator Review Workflow sidecar at the
presentation boundary. It never writes the append-only review ledger and never
changes Ads Intelligence / Smart Issue Registry fingerprints.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Mapping


ADS_SMART_ISSUE_REVIEW_CONSOLE_UI_VERSION = "ads-smart-issue-review-console-ui-v1"

CANDIDATE_ACTIONS = {
    "PENDING_REVIEW": ["PROMOTE", "DEFER", "DISMISS"],
    "DEFERRED": ["PROMOTE", "DEFER", "DISMISS"],
    "DISMISSED": ["PROMOTE", "DEFER", "DISMISS"],
    "REOPEN_REVIEW_REQUIRED": ["REOPEN"],
}
ISSUE_ACTIONS = {
    "OPEN": ["ACKNOWLEDGE", "MONITOR", "RESOLVE"],
    "ACKNOWLEDGED": ["MONITOR", "RESOLVE"],
    "MONITORING": ["MONITOR", "RESOLVE"],
    "RESOLVED": ["REOPEN"],
}
ACTION_LABELS = {
    "PROMOTE": "Mở Smart Issue",
    "DEFER": "Hoãn review",
    "DISMISS": "Bỏ qua",
    "REOPEN": "Mở lại",
    "ACKNOWLEDGE": "Đã nhận",
    "MONITOR": "Theo dõi",
    "RESOLVE": "Đánh dấu đã xử lý",
}

REVIEW_CONSOLE_STYLE = r"""
/* ads-smart-issue-review-console-ui-v1 */
.ads-review-console{display:grid;gap:14px;padding:20px;border:1px solid var(--line);border-radius:14px;background:var(--surface)}
.ads-review-console-head{display:flex;align-items:flex-start;justify-content:space-between;gap:14px;flex-wrap:wrap}.ads-review-console-head h3{margin:0;font-size:16px;color:var(--ink)}.ads-review-console-sub{margin-top:5px;font-size:10px;line-height:1.5;color:var(--muted)}
.ads-review-console-badges{display:flex;gap:6px;flex-wrap:wrap}.ads-review-console-badge{display:inline-flex;padding:5px 8px;border:1px solid var(--line);border-radius:7px;background:var(--soft);font-size:8px;font-weight:800;color:var(--muted)}
.ads-review-console-metrics{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}.ads-review-console-metric{padding:12px;border:1px solid var(--line);border-radius:10px;background:var(--soft)}.ads-review-console-metric b{display:block;font-size:18px;color:var(--ink)}.ads-review-console-metric span{display:block;margin-top:4px;font-size:8.5px;color:var(--muted)}
.ads-review-console-list{display:grid;gap:10px}.ads-review-console-card{padding:13px;border:1px solid var(--line);border-radius:11px;background:var(--surface)}.ads-review-console-card-top{display:flex;justify-content:space-between;gap:12px;align-items:flex-start}.ads-review-console-card b{font-size:11px;line-height:1.4;color:var(--text)}.ads-review-console-state{font-size:8px;font-weight:800;color:var(--muted);white-space:nowrap}.ads-review-console-copy{margin-top:6px;font-size:9px;line-height:1.45;color:var(--muted)}
.ads-review-console-actions{display:flex;gap:6px;flex-wrap:wrap;margin-top:9px}.ads-review-console-action{display:inline-flex;padding:5px 7px;border:1px solid var(--line);border-radius:7px;background:var(--soft);font-size:8px;font-weight:750;color:var(--text)}
.ads-review-console-preview{margin-top:9px;padding:9px;border:1px dashed var(--line);border-radius:8px;font-size:8px;line-height:1.5;color:var(--muted);word-break:break-word}.ads-review-console-empty{padding:16px;border:1px dashed var(--line);border-radius:10px;background:var(--soft);font-size:9.5px;line-height:1.55;color:var(--muted)}
.ads-review-console-foot{padding-top:10px;border-top:1px solid var(--line);font-size:8.5px;line-height:1.5;color:var(--muted2)}
@media(max-width:680px){.ads-review-console-metrics{grid-template-columns:1fr}.ads-review-console-card-top{display:block}.ads-review-console-state{display:block;margin-top:5px}}
"""


def _s(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _read_json(path: str | Path) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _policy(contract: Mapping[str, Any]) -> Dict[str, Any]:
    if _s(contract.get("status")) != "PREPRODUCTION_UI_CONTRACT":
        raise ValueError("Smart Issue Review Console contract must remain PREPRODUCTION")
    policy = dict(contract.get("review_console_policy") or {})
    required_true = (
        "enabled",
        "presentation_only",
        "read_only",
        "command_preview_only",
        "explicit_human_review_required",
        "available_actions_from_workflow_only",
        "selected_shop_only",
        "workflow_fingerprint_required",
        "registry_fingerprint_match_required",
        "operator_ledger_fingerprint_required",
    )
    if any(not bool(policy.get(key)) for key in required_true):
        raise ValueError("Review Console safety requirement missing")
    forbidden = (
        "ui_writes_review_ledger",
        "automatic_promotion_enabled",
        "automatic_state_transition_enabled",
        "automatic_issue_resolution_enabled",
        "automatic_alerts_enabled",
        "automatic_actions_enabled",
        "production_activation_enabled",
    )
    if any(bool(policy.get(key)) for key in forbidden):
        raise ValueError("unsafe Review Console policy")
    if _s(policy.get("input_source")) != "ads_smart_issue_review_workflow.json":
        raise ValueError("unexpected Review Console input source")
    return policy


def validate_review_workflow_for_console(
    workflow: Mapping[str, Any], *, payload: Mapping[str, Any], contract: Mapping[str, Any]
) -> Dict[str, Any]:
    """Fail closed unless the sidecar matches the locked Ads/Registry lineage."""
    _policy(contract)
    if _s(workflow.get("status")) not in {"READY", "READY_EMPTY"}:
        raise ValueError("operator review workflow is not ready")
    if not _s(workflow.get("workflowFingerprint")):
        raise ValueError("operator review workflow fingerprint missing")
    if not _s(workflow.get("operatorLedgerFingerprint")):
        raise ValueError("operator ledger fingerprint missing")
    if workflow.get("doesNotModifyAdsIntelligenceFingerprint") is not True:
        raise ValueError("review workflow must not modify Ads Intelligence fingerprint")

    ads = ((payload.get("destinations") or {}).get("ads") or {})
    meta = ads.get("meta") or {}
    ads_fp = _s(meta.get("adsIntelligenceFingerprint"))
    registry_fp = _s(meta.get("adsSmartIssueRegistryFingerprint"))
    if not ads_fp or _s(workflow.get("adsIntelligenceFingerprint")) != ads_fp:
        raise ValueError("Review Console Ads fingerprint mismatch")
    if not registry_fp or _s(workflow.get("sourceRegistryFingerprint")) != registry_fp:
        raise ValueError("Review Console Registry fingerprint mismatch")
    if _s(workflow.get("adsSmartIssueRegistryFingerprint")) != registry_fp:
        raise ValueError("Review Console sidecar Registry lineage mismatch")

    safety = workflow.get("safety") or {}
    if not bool(safety.get("explicitHumanReviewRequired")) or not bool(safety.get("appendOnly")):
        raise ValueError("human-review/append-only safety missing")
    for key in (
        "automaticPromotionEnabled",
        "automaticStateTransitionEnabled",
        "automaticIssueResolutionEnabled",
        "automaticAlertsEnabled",
        "automaticActionsEnabled",
        "causalClaimsEnabled",
        "productionActivationEnabled",
    ):
        if safety.get(key) is not False:
            raise ValueError(f"unsafe operator workflow safety flag: {key}")

    shops = workflow.get("shops") or {}
    ads_shops = ads.get("shops") or {}
    if set(shops) != set(ads_shops):
        raise ValueError("Review Console shop scope differs from Ads destination")

    queue_count = 0
    issue_count = 0
    candidate_action_count = 0
    issue_action_count = 0
    for shop_id, block in shops.items():
        queue = list(block.get("reviewQueue") or [])
        issues = list(block.get("issues") or [])
        if int(block.get("reviewQueueCount") or 0) != len(queue):
            raise ValueError(f"Review Console queue count mismatch for {shop_id}")
        if int(block.get("issueCount") or 0) != len(issues):
            raise ValueError(f"Review Console issue count mismatch for {shop_id}")
        queue_count += len(queue)
        issue_count += len(issues)
        for row in queue:
            state = _s(row.get("reviewState"))
            actions = [_s(x) for x in row.get("availableActions") or []]
            if not _s(row.get("candidateKey")) or actions != CANDIDATE_ACTIONS.get(state):
                raise ValueError(f"invalid candidate review state/actions for {shop_id}: {state!r}")
            if row.get("humanDecisionRequired") is not True or row.get("automaticPromotion") is not False:
                raise ValueError("candidate human-review gate missing")
            candidate_action_count += len(actions)
        for issue in issues:
            state = _s(issue.get("state"))
            actions = [_s(x) for x in issue.get("availableActions") or []]
            if not _s(issue.get("issueId")) or actions != ISSUE_ACTIONS.get(state):
                raise ValueError(f"invalid issue state/actions for {shop_id}: {state!r}")
            if issue.get("explicitOperatorEventRequired") is not True or issue.get("automaticStateTransition") is not False:
                raise ValueError("issue human-review gate missing")
            issue_action_count += len(actions)

    if int(workflow.get("candidateActionCount") or 0) != candidate_action_count:
        raise ValueError("candidate action count mismatch")
    if int(workflow.get("issueActionCount") or 0) != issue_action_count:
        raise ValueError("issue action count mismatch")

    return {
        "status": _s(workflow.get("status")),
        "mode": _s(workflow.get("mode")),
        "workflowFingerprint": _s(workflow.get("workflowFingerprint")),
        "sourceRegistryFingerprint": registry_fp,
        "operatorLedgerFingerprint": _s(workflow.get("operatorLedgerFingerprint")),
        "candidateActionCount": candidate_action_count,
        "issueActionCount": issue_action_count,
        "reviewQueueCount": queue_count,
        "issueCount": issue_count,
        "shops": json.loads(json.dumps(shops)),
        "commandContract": json.loads(json.dumps(workflow.get("commandContract") or {})),
        "safety": json.loads(json.dumps(safety)),
        "readOnly": True,
        "commandPreviewOnly": True,
    }


def load_review_workflow_for_console(
    *, workflow_path: str | Path, payload: Mapping[str, Any], contract_path: str | Path
) -> Dict[str, Any]:
    return validate_review_workflow_for_console(
        _read_json(workflow_path), payload=payload, contract=_read_json(contract_path)
    )


def review_console_runtime() -> str:
    labels = json.dumps(ACTION_LABELS, ensure_ascii=False, separators=(",", ":"))
    return r"""
/* ads-smart-issue-review-console-ui-v1 */
(function(){
  const q=new URLSearchParams(location.search); if(q.get("destination")!=="ads")return;
  const B=window.UNIPALM_SCOPE_BUNDLE||{},S=window.UNIPALM_NATIVE_SCOPE||{},W=B.smartIssueReviewWorkflow||{};
  const root=document.querySelector(".ads-destination"); if(!root||!W.shops)return;
  const shop=W.shops[S.shop]||{},queue=shop.reviewQueue||[],issues=shop.issues||[],LABELS=__ACTION_LABELS__;
  const esc=v=>String(v??"").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[m]));
  const label=a=>LABELS[a]||a;
  const chips=xs=>(xs||[]).map(a=>'<span class="ads-review-console-action" title="Workflow action '+esc(a)+'">'+esc(label(a))+'</span>').join('');
  const shortFp=v=>{v=String(v||'');return v?v.slice(0,10)+'…':'—'};
  const preview=(kind,id,actions)=>'<div class="ads-review-console-preview"><b>Command preview</b> · target='+esc(kind)+' · id='+esc(id)+' · action ∈ ['+esc((actions||[]).join(', '))+'] · reviewer + timestamp + expected ledger fingerprint bắt buộc.</div>';
  const queueHtml=queue.map(row=>'<div class="ads-review-console-card"><div class="ads-review-console-card-top"><b>'+esc(row.headline||row.productName||row.candidateKey||'Candidate cần review')+'</b><span class="ads-review-console-state">'+esc(row.reviewState||'PENDING_REVIEW')+'</span></div><div class="ads-review-console-copy">'+esc(row.reviewFocus||row.summary||'Operator cần quyết định dựa trên evidence đã được xác nhận.')+'</div><div class="ads-review-console-actions">'+chips(row.availableActions)+'</div>'+preview('candidateKey',row.candidateKey,row.availableActions)+'</div>').join('');
  const issueHtml=issues.map(issue=>'<div class="ads-review-console-card"><div class="ads-review-console-card-top"><b>'+esc(issue.headline||issue.productName||issue.issueId||'Smart Issue')+'</b><span class="ads-review-console-state">'+esc(issue.state||'OPEN')+'</span></div><div class="ads-review-console-copy">Issue '+esc(issue.issueId||'—')+' · mọi đổi trạng thái cần operator event rõ ràng.</div><div class="ads-review-console-actions">'+chips(issue.availableActions)+'</div>'+preview('issueId',issue.issueId,issue.availableActions)+'</div>').join('');
  const empty=(!queue.length&&!issues.length)?'<div class="ads-review-console-empty"><b>Không có candidate hoặc Smart Issue nào cần review ở shop này.</b><br>Console không tự tạo issue và không tự ghi review event.</div>':'';
  const html='<section class="ads-review-console"><div class="ads-review-console-head"><div><h3>Smart Issue Review Console</h3><div class="ads-review-console-sub">Operator review workflow · chỉ hiển thị state-valid actions từ backend đã xác thực.</div></div><div class="ads-review-console-badges"><span class="ads-review-console-badge">CẦN QUYẾT ĐỊNH CỦA OPERATOR</span><span class="ads-review-console-badge">READ-ONLY</span></div></div><div class="ads-review-console-metrics"><div class="ads-review-console-metric"><b>'+String(queue.length)+'</b><span>Chờ review</span></div><div class="ads-review-console-metric"><b>'+String(issues.length)+'</b><span>Smart Issues</span></div><div class="ads-review-console-metric"><b>'+esc(shortFp(W.operatorLedgerFingerprint))+'</b><span>Ledger fingerprint</span></div></div>'+empty+(queue.length?'<div class="ads-review-console-list"><b>Review queue</b>'+queueHtml+'</div>':'')+(issues.length?'<div class="ads-review-console-list"><b>Issue workflow</b>'+issueHtml+'</div>':'')+'<div class="ads-review-console-foot">Human decision required. Console chỉ chuẩn bị action/command preview; execution vẫn đi qua operator workflow đã xác thực. Không có automatic promotion, state transition, alert hay platform action.</div></section>';
  root.insertAdjacentHTML("beforeend",html);
})();
""".replace("__ACTION_LABELS__", labels)


REVIEW_CONSOLE_RUNTIME = review_console_runtime()


def _validate_review_console_artifact(output_dir: Any) -> None:
    html = (Path(output_dir) / "command_center_v2_multi_shop_native_template.html").read_text(encoding="utf-8")
    required = (
        ADS_SMART_ISSUE_REVIEW_CONSOLE_UI_VERSION,
        "Smart Issue Review Console",
        "CẦN QUYẾT ĐỊNH CỦA OPERATOR",
        "READ-ONLY",
        "Command preview",
        "Không có candidate hoặc Smart Issue nào cần review ở shop này.",
        "Console không tự tạo issue và không tự ghi review event.",
        "smartIssueReviewWorkflow",
        "operatorLedgerFingerprint",
    )
    missing = [token for token in required if token not in html]
    if missing:
        raise ValueError(f"Smart Issue Review Console artifact checks missing: {missing}")
    runtime = REVIEW_CONSOLE_RUNTIME
    forbidden = ("fetch(", "XMLHttpRequest", "--apply", "autoPromoteSmartIssue", "const rawSignals=snap.signals||[]")
    leaked = [token for token in forbidden if token in runtime]
    if leaked:
        raise ValueError(f"unsafe Smart Issue Review Console runtime leaked: {leaked}")
