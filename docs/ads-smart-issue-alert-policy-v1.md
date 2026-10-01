# Smart Issue Alert Policy v1

Status: **VALIDATED / LOCKED — 100% PREPRODUCTION**

## Purpose

Alert Policy v1 is the policy layer between a human-reviewed Smart Issue and any future notification delivery capability. It decides whether an already human-promoted Smart Issue is alert-worthy, how severe it is, which channel class would be appropriate, and whether dedupe/cooldown should suppress delivery.

It does **not** send a notification, mutate platform state, promote a candidate, change issue state, resolve an issue, or make causal claims.

## Boundary

Canonical flow:

```text
Smart Issue Candidate
  -> Human Review Registry
  -> Operator Review Workflow
  -> Alert Policy v1
       -> policy eligibility
       -> severity
       -> routing recommendation
       -> dedupe / cooldown
       -> alert intent
  -> Native V2 read-only presentation
```

Alert Policy consumes only `ads_smart_issue_review_workflow.json`. Raw Diagnosis, Candidate and unreviewed Registry candidates cannot bypass the human-review boundary.

## Eligibility policy

A Smart Issue is eligible only when all of the following are true:

- it was created through explicit human review;
- kind is `PROBLEM`;
- issue state is `OPEN`;
- the latest issue event is `PROMOTE` or `REOPEN`;
- its promotion-time priority satisfies a configured severity threshold.

`OPPORTUNITY` issues are non-interruptive in v1. `ACKNOWLEDGED`, `MONITORING` and `RESOLVED` issues are suppressed.

Repeated reminder generation is disabled.

## Severity and routing

### HIGH

- priority tier: `HIGH`;
- minimum priority score: `75`;
- recommended channel classes: `COMMAND_CENTER`, `OPERATOR_NOTIFICATION`;
- external-channel cooldown: `24h`.

### MEDIUM

- priority tier: `MEDIUM`;
- minimum priority score: `55`;
- recommended channel class: `COMMAND_CENTER`;
- cooldown metadata: `72h`.

`COMMAND_CENTER` is presentation-only. `OPERATOR_NOTIFICATION` is a recommendation class only; provider binding and delivery are disabled in v1.

## Dedupe and cooldown

Deterministic alert key:

```text
shopId + issueId + triggerEventId + severity
```

Delivery dedupe is scoped to `alertKey + channelClass`.

Only a ledger event with status `DELIVERED` can start cooldown. A failed or absent delivery does not pretend that the operator was notified. A `REOPEN` event creates a new issue epoch and may bypass the prior epoch cooldown.

Mutable delivery evidence lives in `ops/ads_alert_delivery_events.json`; it is operational state, not a normative contract.

## Outputs

Backend sidecar: `ads_alert_policy.json`.

Key fields include:

- `alertPolicyFingerprint`;
- source Review Workflow / Registry / Operator ledger fingerprints;
- delivery ledger fingerprint;
- eligible alert count;
- suppressed issue count;
- severity counts;
- per-shop eligible alert intents and suppression reasons;
- routing and dedupe policy;
- delivery and safety flags.

The sidecar explicitly preserves the locked `adsIntelligenceFingerprint`.

## Native presentation

Native composition `native-v2-extension-composition-v1.2` adds `ads_smart_issue_alert_policy` as extension #12, after the locked Review Console extension.

The Alert Policy panel is read-only and selected-shop scoped. It displays policy state, HIGH/MEDIUM counts, suppressed count, routing recommendation and explicit `DELIVERY OFF` / `HUMAN-PROMOTED ONLY` safety badges.

Canonical `ui_payload.json` is not extended with the Alert Policy sidecar. The sidecar is validated and bound only at the Native presentation boundary.

## Safety invariants

The following must remain false in v1:

- candidate alerting;
- repeated reminders;
- automatic issue promotion;
- automatic state transition;
- automatic issue resolution;
- automatic delivery;
- provider binding;
- automatic actions;
- causal claims;
- production activation.

Presentation code must not contain direct notification/provider calls, browser ledger writes, `fetch`, XHR, or raw Ads signal rebinding.

## Change guide

Change policy thresholds/routing/dedupe only through:

- `config/ads_alert_policy_contract.json`;
- `automation/modules/ads_alert_policy.py`;
- `automation/tests/test_ads_alert_policy.py`.

Change presentation only through:

- `config/ads_alert_policy_ui_contract.json`;
- `automation/modules/ui_v2_ads_alert_policy.py`;
- `automation/modules/ui_v2_extension_composition_alerts.py`;
- corresponding UI/composition tests.

Do not change Candidate, Registry or Operator Review Workflow merely to alter Alert Policy behavior. A delivery provider or authenticated notification sender must be introduced as a separate authorized capability/version, not by turning this policy or static Native UI into a sender.

## Validation checkpoint

See `docs/audits/ads-smart-issue-alert-policy-v1-checkpoint.md`.
