# Recommendation / Action Authorization v1

Status: **VALIDATED PREPRODUCTION**  
Scope: Ads Smart Issue operator control plane  
Production execution: **DISABLED**

## Purpose

Recommendation / Action Authorization v1 adds a fail-closed control boundary between a human-reviewed Smart Issue and any future operational mutation.

The v1 chain is:

```text
Human-promoted Smart Issue
  -> bounded review proposal
  -> explicit authorization decision
  -> execution-eligibility metadata
  -> BLOCKED: authenticated executor is not bound
```

This milestone does **not** execute Shopee/TikTok/platform actions. It does not change bid, budget, price, promotion, campaign state, listing state or customer communication.

## Source boundary

The canonical sidecar is `ads_action_authorization.json`.

It is built by:
- `automation/modules/ads_action_authorization.py`
- `automation/multi_shop_ads_action_authorization_runner.py`

Normative policy:
- `config/ads_action_authorization_contract.json`

Mutable authorization decisions:
- `ops/ads_action_authorization_events.json`

Operator command preparation/apply-to-ledger only:
- `automation/ads_action_authorization_command.py`

The sidecar consumes validated Operator Review Workflow + current Ads evidence + Alert Policy lineage. Alert eligibility is not treated as authorization.

## Proposal rules

Only an explicit human-promoted Smart Issue in an eligible active state can generate a proposal.

Every eligible issue receives the generic safe review option:
- `VALIDATE_EVIDENCE_BEFORE_CHANGE`

A targeted review option is allowed only when the source artifact contains:
- attribution status `ATTRIBUTED`;
- an allowed top-driver metric;
- a quantified non-zero contribution.

Association-only, missing or unquantified attribution never produces a targeted review.

Maximum proposals per issue: **2**.

Targeted proposal types are review scopes, not mutation directives. Direct directives such as changing bid/budget/price/promotion, pausing campaigns or publishing listing changes are forbidden in v1.

## Proposal evidence package

Every proposal carries deterministic identity and review metadata:
- `proposalId`;
- `proposalFingerprint`;
- `issueId` + `issueEpoch`;
- why the review is relevant;
- prerequisites;
- KPIs to monitor;
- verification checks;
- stop/reversal checks;
- uncertainty markers;
- human-review requirement;
- non-causal / non-prescriptive safety flags.

The issue epoch is bound to the latest Smart Issue event. A new issue epoch creates a new proposal identity, so an old approval cannot silently authorize a changed issue state/evidence epoch.

## Authorization state machine

Append-only actions:
- `APPROVE`
- `REJECT`
- `REVOKE`

States:

```text
PENDING_AUTHORIZATION
  -- APPROVE --> APPROVED_REVIEW_ONLY
  -- REJECT  --> REJECTED

APPROVED_REVIEW_ONLY
  -- REVOKE  --> REVOKED
```

`REJECTED` and `REVOKED` are terminal in v1.

An authorization event must bind:
- exact `proposalId`;
- exact `proposalFingerprint`;
- exact shop + issue;
- timezone-aware timestamp;
- explicit operator identity.

Ledger mutation requires the expected current authorization-ledger fingerprint. A stale operator view fails closed.

## APPROVE does not mean execute

`APPROVED_REVIEW_ONLY` only means an operator approved the review option. It does **not** issue an execution permit.

Even after approval, v1 remains:
- `authenticatedExecutorBound = false`
- `executionEnabled = false`
- `providerBindingEnabled = false`
- `platformMutationAllowed = false`
- `productionActivationEnabled = false`
- `authorizationPermitIssued = false`

Every proposal still carries a deterministic idempotency key plus audit/rollback requirements so a future execution capability can be built without changing the authorization model.

## Native V2 presentation

UI contract:
- `config/ads_action_authorization_ui_contract.json`

UI implementation:
- `automation/modules/ui_v2_ads_action_authorization.py`

Canonical composition:
- `automation/modules/ui_v2_extension_composition_action_authorization.py`
- version `native-v2-extension-composition-v1.3`
- 13 deterministic extensions;
- `ads_action_authorization` is extension #13;
- one base compatibility bridge;
- no legacy nested-wrapper canonical path.

The panel is presentation-only and read-only. It can show proposal state, available authorization commands and execution-block reason, but cannot write the authorization ledger or call an executor/provider.

`ads_action_authorization.json` remains outside canonical `ui_payload.json`. The sidecar is loaded and validated only at Native presentation build time.

## Fail-closed conditions

Build/validation blocks on, among others:
- Workflow / Alert Policy / Registry / Ads lineage mismatch;
- missing proposal fingerprint or issue epoch;
- targeted proposal without quantified `ATTRIBUTED` evidence;
- stale authorization event binding;
- invalid authorization transition;
- stale expected ledger fingerprint;
- executor/provider/mutation/production flag enabled;
- sidecar shop scope mismatch;
- presentation code containing browser execution/write primitives.

## Validation evidence

Backend real-data replay:
- Ads Action Authorization Replay #1 / `36809200022`: PASS.

Backend integrated staging:
- full staging #592 / `36810351226`: PASS end-to-end.

Native v1.3 real-data replay:
- Native V2 Composition Replay #21 / `36811763385`: PASS.

Final full PREPRODUCTION staging:
- run #598 / `36811937549`, head `648c38a8d0adf7efb5c42ae759ab666fb62ac713`: PASS end-to-end.
- Action Authorization QA: **22/22 PASS**.
- UI Payload QA: **42/42 PASS**.
- Native QA: **33/33 PASS**.
- Action Authorization fingerprint: `c091ab68545012c49a2bf9e8de0e814c8b8113909800e8559e183e667178b501`.
- authorization ledger fingerprint: `c417e44fdec7bd95ba3092aa648cfa50712d4e817113d7c3f1913ce4971b2b78`.
- current Native build fingerprint: `94179a3764a8008b4441945932140df2a13bb3d77c0b006819839c0705bbceab`.

Current real state is `READY_EMPTY`: no human-promoted Smart Issue exists, therefore zero action proposals are generated. Thresholds or gates were not weakened to manufacture a populated state.

## Data-refresh note

During backend validation run #591 the existing RAW shop-ID guard detected a SYT+ Ads file containing the Mall Shop ID. This was a **source-data placement mistake made by the operator/user**, not a system defect. The user corrected the RAW data. A read-only identity audit then confirmed the current SYT+ Ads files were shop-correct, and staging #592/#598 passed. No parser, shop-isolation guard or validator was weakened.

Because 28–30 September Ads data were added during that correction/update window, September data fingerprints legitimately changed. Action Authorization replay therefore validates dynamic lineage consistency and safety invariants rather than hard-coding an obsolete monthly data fingerprint.

## Deferred by design

Separate future capabilities are required for:
- authenticated executor identity/session;
- provider/platform credentials;
- execution permit issuance;
- platform mutation adapters;
- retry/reconciliation semantics;
- post-action verification against platform state;
- rollback execution;
- production cutover authorization.

None of these are enabled by Action Authorization v1.
