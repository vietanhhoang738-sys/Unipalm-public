"""Read-only Alert Policy panel for Native V2 PREPRODUCTION.

Consumes the validated ads_alert_policy.json sidecar at the Native presentation
boundary. The UI renders policy eligibility/routing only; it never delivers an
alert, writes a ledger, or mutates Smart Issue state.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Mapping

ADS_SMART_ISSUE_ALERT_POLICY_UI_VERSION = "ads-smart-issue-alert-policy-ui-v1"

ALERT_POLICY_STYLE = r"""
/* ads-smart-issue-alert-policy-ui-v1 */
.ads-alert-policy{display:grid;gap:14px;padding:20px;border:1px solid var(--line);border-radius:14px;background:var(--surface)}
.ads-alert-policy-head{display:flex;align-items:flex-start;justify-content:space-between;gap:14px;flex-wrap:wrap}.ads-alert-policy-head h3{margin:0;font-size:16px;color:var(--ink)}.ads-alert-policy-sub{margin-top:5px;font-size:10px;line-height:1.5;color:var(--muted)}
.ads-alert-policy-badges{display:flex;gap:6px;flex-wrap:wrap}.ads-alert-policy-badge{display:inline-flex;padding:5px 8px;border:1px solid var(--line);border-radius:7px;background:var(--soft);font-size:8px;font-weight:800;color:var(--muted)}
.ads-alert-policy-metrics{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}.ads-alert-policy-metric{padding:12px;border:1px solid var(--line);border-radius:10px;background:var(--soft)}.ads-alert-policy-metric b{display:block;font-size:18px;color:var(--ink)}.ads-alert-policy-metric span{display:block;margin-top:4px;font-size:8.5px;color:var(--muted)}
.ads-alert-policy-list{display:grid;gap:10px}.ads-alert-policy-card{padding:13px;border:1px solid var(--line);border-radius:11px;background:var(--surface)}.ads-alert-policy-card-top{display:flex;justify-content:space-between;gap:12px;align-items:flex-start}.ads-alert-policy-card b{font-size:11px;line-height:1.4;color:var(--text)}.ads-alert-policy-sev{font-size:8px;font-weight:850;color:var(--muted);white-space:nowrap}.ads-alert-policy-copy{margin-top:6px;font-size:9px;line-height:1.45;color:var(--muted)}
.ads-alert-policy-route{display:flex;gap:6px;flex-wrap:wrap;margin-top:9px}.ads-alert-policy-route span{display:inline-flex;padding:5px 7px;border:1px solid var(--line);border-radius:7px;background:var(--soft);font-size:8px;font-weight:750;color:var(--text)}
.ads-alert-policy-empty{padding:16px;border:1px dashed var(--line);border-radius:10px;background:var(--soft);font-size:9.5px;line-height:1.55;color:var(--muted)}.ads-alert-policy-foot{padding-top:10px;border-top:1px solid var(--line);font-size:8.5px;line-height:1.5;color:var(--muted2)}
@media(max-width:680px){.ads-alert-policy-metrics{grid-template-columns:1fr}.ads-alert-policy-card-top{display:block}.ads-alert-policy-sev{display:block;margin-top:5px}}
"""


def _s(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _read_json(path: str | Path) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _ui_policy(contract: Mapping[str, Any]) -> Dict[str, Any]:
    if _s(contract.get("status")) != "PREPRODUCTION_UI_CONTRACT":
        raise ValueError("Alert Policy UI contract must remain PREPRODUCTION")
    policy = dict(contract.get("alert_policy_ui") or {})
    required_true = (
        "enabled", "presentation_only", "read_only", "selected_shop_only",
        "alert_policy_fingerprint_required", "review_workflow_fingerprint_match_required",
        "registry_fingerprint_match_required", "operator_ledger_fingerprint_match_required",
        "delivery_ledger_fingerprint_required",
    )
    if any(not bool(policy.get(k)) for k in required_true):
        raise ValueError("Alert Policy UI safety requirement missing")
    forbidden_true = (
        "provider_binding_enabled", "ui_delivery_enabled", "automatic_delivery_enabled",
        "automatic_promotion_enabled", "automatic_state_transition_enabled",
        "automatic_issue_resolution_enabled", "automatic_actions_enabled",
        "causal_claims_enabled", "production_activation_enabled", "raw_ads_signal_binding_enabled",
    )
    if any(bool(policy.get(k)) for k in forbidden_true):
        raise ValueError("unsafe Alert Policy UI flag")
    if _s(policy.get("input_source")) != "ads_alert_policy.json":
        raise ValueError("unexpected Alert Policy UI input source")
    return policy


def validate_alert_policy_for_ui(
    alert_policy: Mapping[str, Any], *, payload: Mapping[str, Any],
    review_workflow: Mapping[str, Any], contract: Mapping[str, Any]
) -> Dict[str, Any]:
    _ui_policy(contract)
    if _s(alert_policy.get("status")) not in {"READY", "READY_EMPTY"}:
        raise ValueError("Alert Policy sidecar is not ready")
    if not _s(alert_policy.get("alertPolicyFingerprint")):
        raise ValueError("Alert Policy fingerprint missing")
    if not _s(alert_policy.get("deliveryLedgerFingerprint")):
        raise ValueError("Alert delivery ledger fingerprint missing")
    if alert_policy.get("doesNotModifyAdsIntelligenceFingerprint") is not True:
        raise ValueError("Alert Policy must preserve Ads Intelligence fingerprint")

    ads = ((payload.get("destinations") or {}).get("ads") or {})
    meta = ads.get("meta") or {}
    ads_fp = _s(meta.get("adsIntelligenceFingerprint"))
    registry_fp = _s(meta.get("adsSmartIssueRegistryFingerprint"))
    if not ads_fp or _s(alert_policy.get("adsIntelligenceFingerprint")) != ads_fp:
        raise ValueError("Alert Policy UI Ads fingerprint mismatch")
    if not registry_fp or _s(alert_policy.get("adsSmartIssueRegistryFingerprint")) != registry_fp:
        raise ValueError("Alert Policy UI Registry fingerprint mismatch")
    if _s(alert_policy.get("sourceRegistryFingerprint")) != registry_fp:
        raise ValueError("Alert Policy source Registry lineage mismatch")
    if _s(alert_policy.get("sourceReviewWorkflowFingerprint")) != _s(review_workflow.get("workflowFingerprint")):
        raise ValueError("Alert Policy source workflow fingerprint mismatch")
    if _s(alert_policy.get("sourceOperatorLedgerFingerprint")) != _s(review_workflow.get("operatorLedgerFingerprint")):
        raise ValueError("Alert Policy operator ledger lineage mismatch")

    delivery = alert_policy.get("delivery") or {}
    if any(delivery.get(k) is not False for k in ("enabled", "automaticDeliveryEnabled", "providerBindingEnabled")):
        raise ValueError("Alert Policy delivery must remain disabled")
    if delivery.get("commandCenterPresentationOnly") is not True:
        raise ValueError("Alert Policy Command Center must be presentation-only")
    safety = alert_policy.get("safety") or {}
    if safety.get("humanPromotedIssueRequired") is not True:
        raise ValueError("Alert Policy human-promoted gate missing")
    for key in (
        "candidateAlertingEnabled", "repeatedRemindersEnabled", "automaticIssuePromotionEnabled",
        "automaticIssueTransitionEnabled", "automaticIssueResolutionEnabled", "automaticDeliveryEnabled",
        "automaticActionsEnabled", "causalClaimsEnabled", "productionActivationEnabled",
    ):
        if safety.get(key) is not False:
            raise ValueError(f"unsafe Alert Policy safety flag: {key}")

    shops = alert_policy.get("shops") or {}
    ads_shops = ads.get("shops") or {}
    workflow_shops = review_workflow.get("shops") or {}
    if set(shops) != set(ads_shops) or set(shops) != set(workflow_shops):
        raise ValueError("Alert Policy shop scope mismatch")

    eligible = 0
    suppressed = 0
    high = 0
    medium = 0
    seen = set()
    sanitized_shops: Dict[str, Any] = {}
    for shop_id, block in shops.items():
        alerts = list(block.get("eligibleAlerts") or [])
        suppressed_rows = list(block.get("suppressedIssues") or [])
        if int(block.get("eligibleAlertCount") or 0) != len(alerts):
            raise ValueError(f"Alert Policy eligible count mismatch for {shop_id}")
        if int(block.get("suppressedIssueCount") or 0) != len(suppressed_rows):
            raise ValueError(f"Alert Policy suppressed count mismatch for {shop_id}")
        for row in alerts:
            key = _s(row.get("alertKey"))
            sev = _s(row.get("severity"))
            if not key or key in seen:
                raise ValueError(f"duplicate/missing Alert Policy alertKey for {shop_id}")
            seen.add(key)
            if _s(row.get("shopId")) != shop_id or _s(row.get("kind")) != "PROBLEM":
                raise ValueError("Alert Policy UI may only render shop-scoped PROBLEM alerts")
            if sev not in {"HIGH", "MEDIUM"}:
                raise ValueError(f"unsupported Alert Policy severity: {sev!r}")
            if row.get("policyEligible") is not True or row.get("deliveryEnabled") is not False or row.get("automaticDelivery") is not False:
                raise ValueError("Alert Policy eligible row safety mismatch")
            if row.get("evidenceOnly") is not True or row.get("causalClaim") is not False:
                raise ValueError("Alert Policy evidence/noncausal requirement missing")
            eligible += 1
            high += int(sev == "HIGH")
            medium += int(sev == "MEDIUM")
        suppressed += len(suppressed_rows)
        sanitized_shops[shop_id] = {
            "displayName": _s(block.get("displayName")),
            "eligibleAlerts": json.loads(json.dumps(alerts)),
            "suppressedIssues": json.loads(json.dumps(suppressed_rows)),
            "eligibleAlertCount": len(alerts),
            "suppressedIssueCount": len(suppressed_rows),
        }

    if int(alert_policy.get("eligibleAlertCount") or 0) != eligible:
        raise ValueError("Alert Policy total eligible count mismatch")
    if int(alert_policy.get("suppressedIssueCount") or 0) != suppressed:
        raise ValueError("Alert Policy total suppressed count mismatch")
    counts = alert_policy.get("severityCounts") or {}
    if int(counts.get("HIGH") or 0) != high or int(counts.get("MEDIUM") or 0) != medium:
        raise ValueError("Alert Policy severity counts mismatch")

    return {
        "status": _s(alert_policy.get("status")),
        "mode": _s(alert_policy.get("mode")),
        "alertPolicyFingerprint": _s(alert_policy.get("alertPolicyFingerprint")),
        "sourceReviewWorkflowFingerprint": _s(alert_policy.get("sourceReviewWorkflowFingerprint")),
        "sourceRegistryFingerprint": registry_fp,
        "sourceOperatorLedgerFingerprint": _s(alert_policy.get("sourceOperatorLedgerFingerprint")),
        "deliveryLedgerFingerprint": _s(alert_policy.get("deliveryLedgerFingerprint")),
        "eligibleAlertCount": eligible,
        "suppressedIssueCount": suppressed,
        "severityCounts": {"HIGH": high, "MEDIUM": medium},
        "shops": sanitized_shops,
        "routingPolicy": json.loads(json.dumps(alert_policy.get("routingPolicy") or {})),
        "delivery": json.loads(json.dumps(delivery)),
        "safety": json.loads(json.dumps(safety)),
        "readOnly": True,
        "presentationOnly": True,
    }


def load_alert_policy_for_ui(
    *, alert_policy_path: str | Path, payload: Mapping[str, Any],
    review_workflow: Mapping[str, Any], contract_path: str | Path
) -> Dict[str, Any]:
    return validate_alert_policy_for_ui(
        _read_json(alert_policy_path), payload=payload, review_workflow=review_workflow,
        contract=_read_json(contract_path),
    )


ALERT_POLICY_RUNTIME = r"""
/* ads-smart-issue-alert-policy-ui-v1 */
(function(){
  const q=new URLSearchParams(location.search); if(q.get("destination")!=="ads")return;
  const B=window.UNIPALM_SCOPE_BUNDLE||{},S=window.UNIPALM_NATIVE_SCOPE||{},P=B.smartIssueAlertPolicy||{};
  const root=document.querySelector(".ads-destination"); if(!root||!P.shops)return;
  const shop=P.shops[S.shop]||{},alerts=shop.eligibleAlerts||[],suppressed=shop.suppressedIssues||[];
  const esc=v=>String(v??"").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[m]));
  const high=alerts.filter(x=>x.severity==='HIGH').length,medium=alerts.filter(x=>x.severity==='MEDIUM').length;
  const routes=x=>(x.recommendedChannelClasses||[]).map(c=>'<span>'+esc(c==='COMMAND_CENTER'?'Command Center':'Operator notification · chưa bật')+'</span>').join('');
  const cards=alerts.map(a=>'<div class="ads-alert-policy-card"><div class="ads-alert-policy-card-top"><b>'+esc(a.headline||a.productName||a.issueId||'Smart Issue')+'</b><span class="ads-alert-policy-sev">'+esc(a.severity||'—')+'</span></div><div class="ads-alert-policy-copy">'+esc(a.productName||'')+(a.productName?' · ':'')+esc(a.triggerAction||'')+' · policy eligible, delivery vẫn tắt.</div><div class="ads-alert-policy-route">'+routes(a)+'</div></div>').join('');
  const empty=!alerts.length?'<div class="ads-alert-policy-empty"><b>Không có Smart Issue nào đủ điều kiện cảnh báo ở shop này.</b><br>Alert Policy không tạo alert từ candidate và không tự gửi notification.</div>':'';
  const html='<section class="ads-alert-policy"><div class="ads-alert-policy-head"><div><h3>Alert Policy</h3><div class="ads-alert-policy-sub">Chỉ Smart Issue PROBLEM đã được human-promote mới có thể đủ điều kiện interruptive alert.</div></div><div class="ads-alert-policy-badges"><span class="ads-alert-policy-badge">PREPRODUCTION</span><span class="ads-alert-policy-badge">DELIVERY OFF</span><span class="ads-alert-policy-badge">HUMAN-PROMOTED ONLY</span></div></div><div class="ads-alert-policy-metrics"><div class="ads-alert-policy-metric"><b>'+String(high)+'</b><span>HIGH</span></div><div class="ads-alert-policy-metric"><b>'+String(medium)+'</b><span>MEDIUM</span></div><div class="ads-alert-policy-metric"><b>'+String(suppressed.length)+'</b><span>Suppressed</span></div></div>'+empty+(alerts.length?'<div class="ads-alert-policy-list">'+cards+'</div>':'')+'<div class="ads-alert-policy-foot">Policy chỉ quyết định eligibility, severity, routing, dedupe và cooldown. Notification delivery/provider binding chưa được bật; không có automatic action hoặc platform mutation.</div></section>';
  root.insertAdjacentHTML("beforeend",html);
})();
"""


def _validate_alert_policy_artifact(output_dir: Any) -> None:
    html = (Path(output_dir) / "command_center_v2_multi_shop_native_template.html").read_text(encoding="utf-8")
    required = (
        ADS_SMART_ISSUE_ALERT_POLICY_UI_VERSION,
        "Alert Policy", "DELIVERY OFF", "HUMAN-PROMOTED ONLY",
        "Không có Smart Issue nào đủ điều kiện cảnh báo ở shop này.",
        "smartIssueAlertPolicy", "Notification delivery/provider binding chưa được bật",
    )
    missing = [token for token in required if token not in html]
    if missing:
        raise ValueError(f"Alert Policy UI artifact checks missing: {missing}")
    forbidden = (
        "fetch(", "XMLHttpRequest", "--apply", "autoPromoteSmartIssue",
        "const rawSignals=snap.signals||[]", "sendNotification(", "sendAlert(",
    )
    leaked = [token for token in forbidden if token in ALERT_POLICY_RUNTIME]
    if leaked:
        raise ValueError(f"unsafe Alert Policy UI runtime leaked: {leaked}")
