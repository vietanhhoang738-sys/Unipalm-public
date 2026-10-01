"""Read-only Recommendation / Action Authorization panel for Native V2 PREPRODUCTION.

Consumes ads_action_authorization.json only at the Native presentation boundary.
It can display proposals and authorization state, but it cannot append approval
events, bind an executor, execute an action, or mutate any platform/system state.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Mapping

ADS_ACTION_AUTHORIZATION_UI_VERSION = "ads-action-authorization-ui-v1"
GENERIC_ACTION = "VALIDATE_EVIDENCE_BEFORE_CHANGE"

ACTION_AUTHORIZATION_STYLE = r"""
/* ads-action-authorization-ui-v1 */
.ads-action-auth{display:grid;gap:14px;padding:20px;border:1px solid var(--line);border-radius:14px;background:var(--surface)}
.ads-action-auth-head{display:flex;align-items:flex-start;justify-content:space-between;gap:14px;flex-wrap:wrap}.ads-action-auth-head h3{margin:0;font-size:16px;color:var(--ink)}.ads-action-auth-sub{margin-top:5px;font-size:10px;line-height:1.5;color:var(--muted)}
.ads-action-auth-badges{display:flex;gap:6px;flex-wrap:wrap}.ads-action-auth-badge{display:inline-flex;padding:5px 8px;border:1px solid var(--line);border-radius:7px;background:var(--soft);font-size:8px;font-weight:800;color:var(--muted)}
.ads-action-auth-metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}.ads-action-auth-metric{padding:12px;border:1px solid var(--line);border-radius:10px;background:var(--soft)}.ads-action-auth-metric b{display:block;font-size:18px;color:var(--ink)}.ads-action-auth-metric span{display:block;margin-top:4px;font-size:8.5px;color:var(--muted)}
.ads-action-auth-list{display:grid;gap:10px}.ads-action-auth-card{padding:14px;border:1px solid var(--line);border-radius:11px;background:var(--surface)}.ads-action-auth-card-top{display:flex;justify-content:space-between;align-items:flex-start;gap:12px}.ads-action-auth-card h4{margin:0;font-size:11px;line-height:1.4;color:var(--text)}.ads-action-auth-state{font-size:8px;font-weight:850;color:var(--muted);white-space:nowrap}.ads-action-auth-copy{margin-top:7px;font-size:9px;line-height:1.5;color:var(--muted)}
.ads-action-auth-chips{display:flex;gap:6px;flex-wrap:wrap;margin-top:9px}.ads-action-auth-chip{display:inline-flex;padding:5px 7px;border:1px solid var(--line);border-radius:7px;background:var(--soft);font-size:8px;font-weight:750;color:var(--text)}
.ads-action-auth-detail{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin-top:10px}.ads-action-auth-detail div{padding:9px;border:1px solid var(--line);border-radius:8px;background:var(--soft);font-size:8.5px;line-height:1.45;color:var(--muted)}.ads-action-auth-detail b{display:block;margin-bottom:4px;color:var(--text)}
.ads-action-auth-empty{padding:16px;border:1px dashed var(--line);border-radius:10px;background:var(--soft);font-size:9.5px;line-height:1.55;color:var(--muted)}.ads-action-auth-foot{padding-top:10px;border-top:1px solid var(--line);font-size:8.5px;line-height:1.5;color:var(--muted2)}
@media(max-width:780px){.ads-action-auth-metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.ads-action-auth-detail{grid-template-columns:1fr}}@media(max-width:480px){.ads-action-auth-metrics{grid-template-columns:1fr}.ads-action-auth-card-top{display:block}.ads-action-auth-state{display:block;margin-top:5px}}
"""


def _s(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _read_json(path: str | Path) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _ui_policy(contract: Mapping[str, Any]) -> Dict[str, Any]:
    if _s(contract.get("status")) != "PREPRODUCTION_UI_CONTRACT":
        raise ValueError("Action Authorization UI contract must remain PREPRODUCTION")
    if _s(contract.get("layer_name")) != "ads_action_authorization_ui_v1":
        raise ValueError("unexpected Action Authorization UI layer")
    policy = dict(contract.get("action_authorization_ui") or {})
    required_true = (
        "enabled", "presentation_only", "read_only", "selected_shop_only",
        "action_authorization_fingerprint_required", "review_workflow_fingerprint_match_required",
        "alert_policy_fingerprint_match_required", "registry_fingerprint_match_required",
        "ads_intelligence_fingerprint_match_required", "authorization_ledger_fingerprint_required",
        "issue_epoch_binding_required", "proposal_fingerprint_required",
        "attributed_driver_required_for_targeted_review",
    )
    if any(policy.get(key) is not True for key in required_true):
        raise ValueError("Action Authorization UI safety requirement missing")
    forbidden_true = (
        "authenticated_executor_bound", "execution_enabled", "ui_execution_enabled",
        "provider_binding_enabled", "platform_mutation_allowed", "automatic_execution_enabled",
        "automatic_issue_transition_enabled", "automatic_issue_resolution_enabled",
        "automatic_actions_enabled", "causal_claims_enabled", "production_activation_enabled",
        "raw_ads_signal_binding_enabled",
    )
    if any(bool(policy.get(key)) for key in forbidden_true):
        raise ValueError("unsafe Action Authorization UI flag")
    if _s(policy.get("input_source")) != "ads_action_authorization.json":
        raise ValueError("unexpected Action Authorization UI input source")
    return policy


def validate_action_authorization_for_ui(
    action_authorization: Mapping[str, Any], *, payload: Mapping[str, Any],
    review_workflow: Mapping[str, Any], alert_policy: Mapping[str, Any],
    contract: Mapping[str, Any]
) -> Dict[str, Any]:
    _ui_policy(contract)
    if _s(action_authorization.get("status")) not in {"READY", "READY_EMPTY"}:
        raise ValueError("Action Authorization sidecar is not ready")
    if not _s(action_authorization.get("actionAuthorizationFingerprint")):
        raise ValueError("Action Authorization fingerprint missing")
    if not _s(action_authorization.get("authorizationLedgerFingerprint")):
        raise ValueError("Action Authorization ledger fingerprint missing")
    if action_authorization.get("doesNotModifyAdsIntelligenceFingerprint") is not True:
        raise ValueError("Action Authorization must preserve Ads Intelligence fingerprint")

    ads = ((payload.get("destinations") or {}).get("ads") or {})
    meta = ads.get("meta") or {}
    ads_fp = _s(meta.get("adsIntelligenceFingerprint"))
    registry_fp = _s(meta.get("adsSmartIssueRegistryFingerprint"))
    if not ads_fp or _s(action_authorization.get("adsIntelligenceFingerprint")) != ads_fp:
        raise ValueError("Action Authorization UI Ads fingerprint mismatch")
    if not registry_fp or _s(action_authorization.get("adsSmartIssueRegistryFingerprint")) != registry_fp:
        raise ValueError("Action Authorization UI Registry fingerprint mismatch")
    if _s(action_authorization.get("sourceRegistryFingerprint")) != registry_fp:
        raise ValueError("Action Authorization source Registry lineage mismatch")
    if _s(action_authorization.get("sourceReviewWorkflowFingerprint")) != _s(review_workflow.get("workflowFingerprint")):
        raise ValueError("Action Authorization source workflow fingerprint mismatch")
    if _s(action_authorization.get("sourceOperatorLedgerFingerprint")) != _s(review_workflow.get("operatorLedgerFingerprint")):
        raise ValueError("Action Authorization source operator ledger fingerprint mismatch")
    if _s(action_authorization.get("sourceAlertPolicyFingerprint")) != _s(alert_policy.get("alertPolicyFingerprint")):
        raise ValueError("Action Authorization source Alert Policy fingerprint mismatch")

    execution = action_authorization.get("executionBoundary") or {}
    if execution.get("authenticatedExecutorRequired") is not True:
        raise ValueError("Action Authorization UI requires authenticated executor boundary")
    if execution.get("dryRunOnly") is not True:
        raise ValueError("Action Authorization v1 execution boundary must remain dry-run-only")
    for key in (
        "authenticatedExecutorBound", "executionEnabled", "providerBindingEnabled",
        "platformMutationAllowed", "productionActivationEnabled",
    ):
        if execution.get(key) is not False:
            raise ValueError(f"unsafe Action Authorization execution flag: {key}")

    safety = action_authorization.get("safety") or {}
    if safety.get("humanPromotedIssueRequired") is not True or safety.get("targetedReviewRequiresAttributedDriver") is not True:
        raise ValueError("Action Authorization UI human/attribution gates missing")
    for key in (
        "prescriptiveRecommendationsEnabled", "automaticExecutionEnabled", "authenticatedExecutorBound",
        "providerBindingEnabled", "platformMutationAllowed", "automaticIssueTransitionEnabled",
        "automaticIssueResolutionEnabled", "automaticActionsEnabled", "causalClaimsEnabled",
        "productionActivationEnabled",
    ):
        if safety.get(key) is not False:
            raise ValueError(f"unsafe Action Authorization safety flag: {key}")

    shops = action_authorization.get("shops") or {}
    ads_shops = ads.get("shops") or {}
    workflow_shops = review_workflow.get("shops") or {}
    alert_shops = alert_policy.get("shops") or {}
    if set(shops) != set(ads_shops) or set(shops) != set(workflow_shops) or set(shops) != set(alert_shops):
        raise ValueError("Action Authorization shop scope mismatch")

    seen = set()
    proposal_count = 0
    suppressed_count = 0
    auth_counts = {"PENDING_AUTHORIZATION": 0, "APPROVED_REVIEW_ONLY": 0, "REJECTED": 0, "REVOKED": 0}
    sanitized_shops: Dict[str, Any] = {}
    for shop_id, block in shops.items():
        proposals = list(block.get("proposals") or [])
        suppressed = list(block.get("suppressedIssues") or [])
        if int(block.get("proposalCount") or 0) != len(proposals):
            raise ValueError(f"Action Authorization proposal count mismatch for {shop_id}")
        if int(block.get("suppressedIssueCount") or 0) != len(suppressed):
            raise ValueError(f"Action Authorization suppressed count mismatch for {shop_id}")
        safe_proposals = []
        for proposal in proposals:
            pid = _s(proposal.get("proposalId"))
            if not pid or pid in seen:
                raise ValueError(f"duplicate/missing Action Authorization proposalId: {pid!r}")
            seen.add(pid)
            if _s(proposal.get("shopId")) != shop_id:
                raise ValueError("Action Authorization proposal shop mismatch")
            if not _s(proposal.get("issueId")) or not _s(proposal.get("issueEpoch")) or not _s(proposal.get("proposalFingerprint")):
                raise ValueError("Action Authorization proposal identity/fingerprint incomplete")
            if _s(proposal.get("status")) != "REVIEW_OPTION" or _s(proposal.get("executionMode")) != "HUMAN_REVIEW_ONLY":
                raise ValueError("Action Authorization UI may render review options only")
            if proposal.get("requiresHumanReview") is not True:
                raise ValueError("Action Authorization proposal human review gate missing")
            for key in ("prescriptiveRecommendation", "platformMutationAllowed", "automaticExecutionEligible", "automaticAlertEligible", "causalClaimEligible"):
                if proposal.get(key) is not False:
                    raise ValueError(f"unsafe Action Authorization proposal flag: {key}")
            if not all(proposal.get(k) for k in ("whyRelevant", "prerequisites", "kpisToMonitor", "verificationChecks", "stopOrReversalChecks", "uncertainty")):
                raise ValueError("Action Authorization proposal review metadata incomplete")
            if _s(proposal.get("actionType")) != GENERIC_ACTION:
                top = proposal.get("topDriver") or {}
                if _s(proposal.get("attributionStatus")) != "ATTRIBUTED" or not _s(top.get("metric")) or top.get("contributionValue") in (None, ""):
                    raise ValueError("targeted Action Authorization proposal lacks explicit quantified attribution")

            auth = proposal.get("authorization") or {}
            state = _s(auth.get("state"))
            if state not in auth_counts:
                raise ValueError(f"unsupported Action Authorization state: {state!r}")
            auth_counts[state] += 1
            proposal_execution = proposal.get("executionBoundary") or {}
            if proposal_execution.get("authenticatedExecutorRequired") is not True or proposal_execution.get("dryRunOnly") is not True:
                raise ValueError("Action Authorization proposal executor boundary missing")
            for key in ("authenticatedExecutorBound", "executionEnabled", "providerBindingEnabled", "platformMutationAllowed", "productionActivationEnabled", "authorizationPermitIssued"):
                if proposal_execution.get(key) is not False:
                    raise ValueError(f"unsafe proposal execution flag: {key}")
            if not _s(proposal_execution.get("idempotencyKey")):
                raise ValueError("Action Authorization idempotency key missing")
            safe_proposals.append(json.loads(json.dumps(proposal)))

        proposal_count += len(proposals)
        suppressed_count += len(suppressed)
        sanitized_shops[shop_id] = {
            "displayName": _s(block.get("displayName")),
            "proposals": safe_proposals,
            "proposalCount": len(safe_proposals),
            "suppressedIssues": json.loads(json.dumps(suppressed)),
            "suppressedIssueCount": len(suppressed),
        }

    if int(action_authorization.get("proposalCount") or 0) != proposal_count:
        raise ValueError("Action Authorization total proposal count mismatch")
    if int(action_authorization.get("suppressedIssueCount") or 0) != suppressed_count:
        raise ValueError("Action Authorization total suppressed count mismatch")
    source_counts = action_authorization.get("authorizationStateCounts") or {}
    for key, value in auth_counts.items():
        if int(source_counts.get(key) or 0) != value:
            raise ValueError(f"Action Authorization state count mismatch: {key}")

    return {
        "status": _s(action_authorization.get("status")),
        "mode": _s(action_authorization.get("mode")),
        "actionAuthorizationFingerprint": _s(action_authorization.get("actionAuthorizationFingerprint")),
        "authorizationLedgerFingerprint": _s(action_authorization.get("authorizationLedgerFingerprint")),
        "sourceReviewWorkflowFingerprint": _s(action_authorization.get("sourceReviewWorkflowFingerprint")),
        "sourceAlertPolicyFingerprint": _s(action_authorization.get("sourceAlertPolicyFingerprint")),
        "sourceRegistryFingerprint": registry_fp,
        "sourceOperatorLedgerFingerprint": _s(action_authorization.get("sourceOperatorLedgerFingerprint")),
        "adsIntelligenceFingerprint": ads_fp,
        "proposalCount": proposal_count,
        "suppressedIssueCount": suppressed_count,
        "authorizationStateCounts": auth_counts,
        "shops": sanitized_shops,
        "executionBoundary": json.loads(json.dumps(execution)),
        "safety": json.loads(json.dumps(safety)),
        "readOnly": True,
        "presentationOnly": True,
    }


def load_action_authorization_for_ui(
    *, action_authorization_path: str | Path, payload: Mapping[str, Any],
    review_workflow: Mapping[str, Any], alert_policy: Mapping[str, Any],
    contract_path: str | Path
) -> Dict[str, Any]:
    return validate_action_authorization_for_ui(
        _read_json(action_authorization_path), payload=payload,
        review_workflow=review_workflow, alert_policy=alert_policy,
        contract=_read_json(contract_path),
    )


ACTION_AUTHORIZATION_RUNTIME = r"""
/* ads-action-authorization-ui-v1 */
(function(){
  const q=new URLSearchParams(location.search); if(q.get("destination")!=="ads")return;
  const B=window.UNIPALM_SCOPE_BUNDLE||{},S=window.UNIPALM_NATIVE_SCOPE||{},A=B.smartIssueActionAuthorization||{};
  const root=document.querySelector(".ads-destination"); if(!root||!A.shops)return;
  const shop=A.shops[S.shop]||{},rows=shop.proposals||[],suppressed=shop.suppressedIssues||[];
  const esc=v=>String(v??"").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[m]));
  const pending=rows.filter(x=>(x.authorization||{}).state==='PENDING_AUTHORIZATION').length;
  const approved=rows.filter(x=>(x.authorization||{}).state==='APPROVED_REVIEW_ONLY').length;
  const targeted=rows.filter(x=>x.actionType!=='VALIDATE_EVIDENCE_BEFORE_CHANGE').length;
  const chips=x=>((x.authorization||{}).availableActions||[]).map(a=>'<span class="ads-action-auth-chip">'+esc(a)+' · command only</span>').join('');
  const list=x=>(x||[]).slice(0,3).map(v=>esc(v)).join(' · ');
  const cards=rows.map(p=>{
    const auth=p.authorization||{},ex=p.executionBoundary||{};
    const driver=p.topDriver&&p.topDriver.metric?'<span class="ads-action-auth-chip">ATTRIBUTED · '+esc(p.topDriver.label||p.topDriver.metric)+'</span>':'';
    return '<div class="ads-action-auth-card"><div class="ads-action-auth-card-top"><h4>'+esc(p.title||p.actionType||'Review option')+'</h4><span class="ads-action-auth-state">'+esc(auth.state||'PENDING_AUTHORIZATION')+'</span></div><div class="ads-action-auth-copy">'+esc(p.whyRelevant||'')+'</div><div class="ads-action-auth-chips"><span class="ads-action-auth-chip">'+esc(p.actionType||'')+'</span>'+driver+chips(p)+'</div><div class="ads-action-auth-detail"><div><b>Prerequisites</b>'+list(p.prerequisites)+'</div><div><b>Verification / stop</b>'+list((p.verificationChecks||[]).concat(p.stopOrReversalChecks||[]))+'</div></div><div class="ads-action-auth-copy">Execution: '+esc(ex.status||'BLOCKED')+' · idempotency key present · platform mutation OFF.</div></div>';
  }).join('');
  const empty=!rows.length?'<div class="ads-action-auth-empty"><b>Chưa có action proposal nào cần authorization ở shop này.</b><br>Proposal chỉ sinh từ Smart Issue đã human-promote; targeted review chỉ xuất hiện khi có quantified attribution.</div>':'';
  const html='<section class="ads-action-auth"><div class="ads-action-auth-head"><div><h3>Recommendation / Action Authorization</h3><div class="ads-action-auth-sub">Authorization chỉ kiểm soát review option. APPROVE ở v1 vẫn không cấp quyền execution.</div></div><div class="ads-action-auth-badges"><span class="ads-action-auth-badge">PREPRODUCTION</span><span class="ads-action-auth-badge">READ ONLY</span><span class="ads-action-auth-badge">EXECUTION OFF</span><span class="ads-action-auth-badge">HUMAN APPROVAL REQUIRED</span></div></div><div class="ads-action-auth-metrics"><div class="ads-action-auth-metric"><b>'+String(rows.length)+'</b><span>Proposals</span></div><div class="ads-action-auth-metric"><b>'+String(pending)+'</b><span>Pending authorization</span></div><div class="ads-action-auth-metric"><b>'+String(approved)+'</b><span>Approved · review only</span></div><div class="ads-action-auth-metric"><b>'+String(targeted)+'</b><span>Attributed targeted reviews</span></div></div>'+empty+(rows.length?'<div class="ads-action-auth-list">'+cards+'</div>':'')+'<div class="ads-action-auth-foot">UI không ghi authorization ledger và không gọi executor. Mọi provider binding, platform mutation, automatic action và production activation vẫn bị khóa; execution chỉ có thể được xây như một capability riêng có authenticated control plane, audit trail và rollback.</div></section>';
  root.insertAdjacentHTML("beforeend",html);
})();
"""


def _validate_action_authorization_artifact(output_dir: Any) -> None:
    html = (Path(output_dir) / "command_center_v2_multi_shop_native_template.html").read_text(encoding="utf-8")
    required = (
        ADS_ACTION_AUTHORIZATION_UI_VERSION,
        "Recommendation / Action Authorization", "READ ONLY", "EXECUTION OFF",
        "HUMAN APPROVAL REQUIRED", "APPROVE ở v1 vẫn không cấp quyền execution",
        "smartIssueActionAuthorization",
        "Chưa có action proposal nào cần authorization ở shop này.",
        "UI không ghi authorization ledger và không gọi executor",
    )
    missing = [token for token in required if token not in html]
    if missing:
        raise ValueError(f"Action Authorization UI artifact checks missing: {missing}")
    forbidden = (
        "fetch(", "XMLHttpRequest", "--apply", "executeAction(", "runAction(",
        "sendAction(", "platformMutationAllowed:true", "const rawSignals=snap.signals||[]",
    )
    leaked = [token for token in forbidden if token in html]
    if leaked:
        raise ValueError(f"Action Authorization UI contains forbidden execution/mutation path: {leaked}")
