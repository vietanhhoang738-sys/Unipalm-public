# Recommendation / Action Authorization v1 — Validation Checkpoint

Date: **2026-10-01**  
Milestone state: **VALIDATED / LOCKED — 100% PREPRODUCTION**

## Scope locked by this checkpoint

This checkpoint validates the v1 control boundary from human-promoted Smart Issue to bounded review proposal and explicit operator authorization state.

The milestone intentionally stops before execution. No authenticated executor, provider binding, platform mutation or production activation is enabled.

## Functional evidence

### Backend policy / ledger

Validated capabilities:
- human-promoted Smart Issue required;
- eligible active issue states only;
- generic evidence-validation review option;
- targeted review only from quantified `ATTRIBUTED` driver evidence;
- maximum two proposals per issue;
- deterministic proposal ID/fingerprint;
- exact issue-epoch binding;
- append-only `APPROVE / REJECT / REVOKE` ledger;
- stale expected-ledger fingerprint fails closed;
- old authorization cannot bind a new issue epoch;
- deterministic execution idempotency key;
- audit-trail and rollback metadata required;
- APPROVE remains `APPROVED_REVIEW_ONLY`.

Synthetic/backend tests: PASS.

Real-data Action Authorization Replay #1 / `36809200022`: PASS.

Integrated backend full staging #592 / `36810351226`: PASS end-to-end.

### Native V2 presentation

Native composition v1.3 is strictly additive over locked v1.2:
- composition: `native-v2-extension-composition-v1.3`;
- 13 unique extensions;
- extension #13: `ads_action_authorization`;
- exactly one base compatibility bridge;
- legacy nested-wrapper build path: false;
- locked Native patch remains `native-ads-financial-v38`.

Real-data Native replay #21 / `36811763385`: PASS.

Final full staging #598 / `36811937549`, head `648c38a8d0adf7efb5c42ae759ab666fb62ac713`: PASS end-to-end.

Final artifact QA:
- Action Authorization QA: **22/22 PASS**, 0 failures;
- UI Payload QA: **42/42 PASS**, 0 failures;
- Native QA: **33/33 PASS**, 0 failures;
- overall Ads Intelligence QA: PASS, 0 failures.

## Final artifact identity

Current September data lineage after the completed 28–30/09 source refresh:
- Semantic fingerprint: `00f96406d52414e9a2d201a7ba3eada8dccc57b9deeced0fd38e97558569de20`;
- Ads Intelligence / Smart Issue Registry fingerprint: `bfc579acbfd05edc842a45d4c8b0dcf5677d8eaf9462c47ecb17b7fca22bca54`;
- Operator Review Workflow fingerprint: `2e0a8f9924bf6b980789764baad4cfc618fd7df95e5ad58308e3f46634f8aff0`;
- Alert Policy fingerprint: `da056580f7d2de3198387b1dc4d9649b95c59f208e8121e0c4bc034639a8bf0c`;
- Action Authorization fingerprint: `c091ab68545012c49a2bf9e8de0e814c8b8113909800e8559e183e667178b501`;
- authorization ledger fingerprint: `c417e44fdec7bd95ba3092aa648cfa50712d4e817113d7c3f1913ce4971b2b78`;
- UI Payload build fingerprint: `53cf875fff27d5bb153f68f5ebb34adc107a979e5705624e74c4b2ebdcb239f9`;
- Native v1.3 build fingerprint: `94179a3764a8008b4441945932140df2a13bb3d77c0b006819839c0705bbceab`.

These monthly data fingerprints supersede the earlier September checkpoint identity because the RAW source gained valid 28–30/09 data. The contract and safety gates did not change to force the new fingerprints.

## Real-state result

Current Action Authorization state:
- status: `READY_EMPTY`;
- proposal count: 0;
- suppressed issue count: 0;
- PENDING: 0;
- APPROVED_REVIEW_ONLY: 0;
- REJECTED: 0;
- REVOKED: 0.

This is expected because the real Operator Review Workflow currently has no human-promoted Smart Issue. No threshold, issue gate or attribution rule was lowered to create synthetic production-like state.

## Canonical payload isolation

Final `ui_payload.json` contains none of:
- `smartIssueActionAuthorization`;
- `ads_action_authorization`;
- `actionAuthorizationFingerprint`;
- `Recommendation / Action Authorization`;
- `ads-action-authorization-ui-v1`.

The sidecar is validated and bound only during Native build. Canonical business/presentation payload semantics therefore remain isolated from mutable authorization control state.

## Safety audit

Final Action Authorization execution boundary:
- `authenticatedExecutorRequired = true`;
- `authenticatedExecutorBound = false`;
- `executionEnabled = false`;
- `dryRunOnly = true`;
- `providerBindingEnabled = false`;
- `platformMutationAllowed = false`;
- `productionActivationEnabled = false`.

Native presentation additionally contains no browser execution/write primitive such as:
- `fetch(`;
- `XMLHttpRequest`;
- `--apply`;
- `executeAction(`;
- `runAction(`;
- `sendAction(`;
- raw Ads signal binding.

Native production safety remains false:
- production cutover not authorized;
- production Data Mart not written;
- production deployment not performed;
- production `index.html` not modified;
- production V2 source template not modified.

## RAW identity incident classification

Backend staging #591 was blocked because the RAW shop-ID guard observed Mall identity inside a SYT+ Ads input. The user confirmed this was their own accidental data placement and corrected it. It was **not a system defect**.

The correct system behavior was fail-closed rejection. A subsequent read-only RAW identity audit confirmed the corrected current source set, followed by successful full staging #592 and #598. No shop-isolation or parser guard was weakened.

## Maintainability boundary

Canonical files for future maintenance:
- backend policy: `automation/modules/ads_action_authorization.py`;
- backend runner: `automation/multi_shop_ads_action_authorization_runner.py`;
- operator ledger command: `automation/ads_action_authorization_command.py`;
- normative contract: `config/ads_action_authorization_contract.json`;
- mutable ledger: `ops/ads_action_authorization_events.json`;
- read-only Native UI: `automation/modules/ui_v2_ads_action_authorization.py`;
- UI contract: `config/ads_action_authorization_ui_contract.json`;
- canonical composition entrypoint: `automation/modules/ui_v2_extension_composition_action_authorization.py`;
- Native runner: `automation/multi_shop_native_v2_runner.py`.

Rollback boundary:
- revert canonical Native composition from v1.3 to validated v1.2 to remove only the Action Authorization presentation extension;
- Action Authorization sidecar can be removed from staging orchestration without rewriting locked Ads Intelligence or Alert Policy outputs;
- mutable authorization ledger remains separate under `ops/`.

## Deferred by design

Not authorized by this checkpoint:
- authenticated executor/control session;
- provider/platform credentials;
- execution permits;
- platform mutation;
- notification/provider action delivery;
- retry/reconciliation of platform writes;
- automated rollback execution;
- production cutover.

These require an explicit future milestone and must not be inferred from `APPROVED_REVIEW_ONLY`.
