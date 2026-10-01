# Native V2 Extension Composition v1

Status: **LOCKED_V1**  
Environment: **PREPRODUCTION**  
Validated: **2026-09-30**

## Purpose

Native V2 previously accumulated presentation capabilities through a chain of wrapper builders that temporarily monkey-patched one another. That architecture preserved output but created a fragile coupling surface: an exact runtime-string anchor or patch terminator changed in one layer could break multiple downstream presentation wrappers.

Extension Composition v1 replaces the canonical build path with one explicit, ordered composition boundary while preserving the locked Product/Ads/Diagnosis/Persistence/Smart Issue presentation behavior and all upstream business/intelligence contracts.

This is a structural presentation refactor only. It does not redefine business facts, thresholds, diagnosis logic, Smart Issue policy, platform state, or production authorization.

## Canonical entrypoint

Runner:

`automation/multi_shop_native_v2_runner.py`

Canonical composer:

`automation/modules/ui_v2_extension_composition_canonical.py`

Compatibility/reference composer:

`automation/modules/ui_v2_extension_composition.py`

The canonical runner must call the canonical composer. Existing older wrapper modules remain available as locked compatibility/reference surfaces, but the canonical build path must not recursively call their `build_native_v2_multi_shop` functions.

## Explicit extension order

The v1 order is deterministic:

1. `intelligence_first_operator_copy`
2. `product_destination`
3. `product_compact_signals`
4. `product_short_names`
5. `ads_destination`
6. `ads_financial`
7. `ads_dynamic_diagnosis`
8. `ads_diagnosis_persistence`
9. `ads_smart_issue_candidate`
10. `ads_smart_issue_registry`

The order is part of the compatibility surface. Reordering requires explicit validation because later contributions assume earlier destination/runtime capabilities already exist.

## Base compatibility bridge

v1 intentionally retains exactly **one** temporary compatibility bridge at the base `ui_v2_native` boundary because the locked base builder does not yet expose first-class style/runtime/bundle hook parameters.

Policy:

- bridge count must equal `1`;
- original Native globals/bundle adapter must be restored in `finally`;
- an already-patched base bundle fails closed;
- no nested Registry/Candidate/Persistence/Diagnosis wrapper build path is allowed;
- adding another compatibility bridge is not allowed by convenience.

A future Native core-hook migration may remove the final bridge, but that is a separate versioned milestone.

## Artifact lineage

Behavioral equivalence alone is insufficient. The final HTML also carries deterministic provenance under:

`UNIPALM_NATIVE_EXTENSION_LINEAGE`

Current lineage includes:

- `native-v2-extension-composition-v1`
- `native-product-intelligence-v34`
- `native-product-intelligence-v35-compact-signals`
- `native-product-intelligence-v36-short-names`
- `product-short-name-v1`
- `native-ads-intelligence-v37`
- `native-ads-financial-v38`
- `ads-financial-polish-v2`
- `ads-dynamic-diagnosis-ui-v1`
- `ads-diagnosis-persistence-ui-v1`
- `ads-smart-issue-candidate-ui-v1`
- `ads-smart-issue-registry-ui-v1`

The lineage markers are additive evidence. They never replace locked artifact validators.

## Locked validators remain authoritative

The canonical composer reuses the existing validators unchanged for:

- operator/semantic presentation;
- Product destination;
- Product short-name v36;
- Ads destination;
- Ads financial polish;
- Dynamic Diagnosis;
- Diagnosis Persistence;
- Smart Issue Candidate;
- Smart Issue Registry;
- composition-specific safety/lineage checks.

A migration is invalid if it requires weakening an existing validator merely to make the new architecture pass.

## Locked operator-facing evidence gates

The composed artifact must preserve these sentences exactly:

- `Chẩn đoán chỉ xuất hiện khi hai kỳ có bối cảnh bán hàng tương đồng.`
- `Độ bền chỉ được xác nhận bằng các cửa sổ độc lập cùng scope và cùng bối cảnh.`
- `Ứng viên Smart Issue chỉ được đánh dấu khi tín hiệu đã xác nhận còn đủ mới và đủ lớn để đáng xem xét vận hành.`
- `Smart Issue chỉ được mở hoặc đổi trạng thái sau một review event rõ ràng của operator; candidate không tự chuyển thành issue.`

Forbidden presentation leakage includes:

- `const rawSignals=snap.signals||[]`
- `autoPromoteSmartIssue`
- copy implying automatic Smart Issue opening/action.

## Regression protection

Primary tests:

- `automation/tests/test_ui_v2_extension_composition.py`
- `automation/tests/test_ui_v2_extension_composition_canonical.py`

Replay workflow:

`.github/workflows/native-v2-composition-replay.yml`

The replay workflow downloads a real validated UI Payload artifact and rebuilds Native V2 through the current canonical composer. It is intentionally independent of Drive persistence so presentation migrations can be validated even when an external storage credential is unavailable.

Replay is triggered by changes to the runner, Native UI modules/tests, template, or the replay workflow itself.

## Validation evidence

### Real-payload replay

GitHub Actions **Native V2 Composition Replay run #2** / `36703100672`: **SUCCESS**.

Validated:

- real UI Payload from upstream run `36694743751`;
- composition version `native-v2-extension-composition-v1`;
- 10 unique extension IDs;
- one compatibility bridge;
- explicit lineage ready;
- legacy nested-wrapper build path not used;
- locked September Semantic fingerprint preserved;
- Native patch remains `native-ads-financial-v38`;
- automatic Smart Issue alerts/actions remain disabled.

### Full PREPRODUCTION staging

GitHub Actions **Multi-Shop Core CI & Staging QA run #570** / `36703196976`, head `52e9efba825642d10734e2166ac696a638e70e24`: **SUCCESS** end-to-end.

The run passed:

`Ingestion/Staging -> Processed v2 -> Processed Drive -> Semantic v2 -> Semantic Drive -> Business Context -> Historical Intelligence -> Product Intelligence -> Ads Intelligence -> UI Payload -> Native V2`

Architecture & Contract Guard for the staging head also passed.

## Upstream identity preservation

Run #570 artifact audit preserved the locked identities:

- Base Ads: `a1faa4cf2e4c9403452fb47d62504a516b4a8d2eaedff7ebe78dcf5a2220f79b`
- Context Qualification: `23cb81876a955fca122ab6d2ad55711682972a6ddc50afc20de9ec77c5157dfc`
- Business Context: `d4fef77fe3f18d2e9b91ea611dbcd755372fff1e9fc5e29739fb851b9a0a8cd0`
- Dynamic Diagnosis: `4daab89d26c877e858c39b462b6599234b14c39a18e37f5ce373b9e1aae9b4a2`
- Diagnosis Persistence: `4b4cf0fb8fea41db6e1b7c6e470347bc0c212b554774ec6068e743359513dabd`
- Smart Issue Candidate: `2373ef01716950719a6bc16be046e7bb456cde74d5f4b436c05cd5605a6a05e7`
- Smart Issue Registry / final Ads: `234cfc09d01a2418384bf23ea7dabbaf641f92e26cf8d2765ac32e12f50b1448`
- Operator Review Workflow: `314921dc35393c169454559b7378effbfb1d2f0c35b2b5b82f663bcc97c4bc9a`
- Registry review ledger: `f294114bb005151b50bdd96f4bbd985d365edbaba01afc8d27218dc02b3739b8`
- Operator ledger concurrency: `a5a99966fbd29c99d0264b89772e768401f9e8d0c7707c27d2e872b5d650970d`
- September Semantic: `38e12e9552fd81571b85e37f977bfbeb8feda9a1d3b7e301663f56fa28cad7f6`

The Native build fingerprint is expected to differ from the old wrapper artifact because Composition v1 adds explicit deterministic lineage to the presentation artifact. This does not change upstream business/intelligence identity.

## Durable Drive validation

Run #570 used `user_oauth` successfully after the Drive OAuth credential was refreshed.

- Processed v2: both shops `NOOP` because the same build fingerprints already existed remotely;
- Semantic v2: `NOOP` for the same Semantic fingerprint;
- storage status remained `PREPRODUCTION`;
- no production Data Mart/UI was written.

The OAuth application is still in Google `Testing` status. Credential longevity/Production OAuth setup is operational hardening debt and must not be confused with Composition correctness.

## Safety state

Run #570 confirms:

- production cutover authorized: `false`
- production deployment performed: `false`
- production V2 template modified: `false`
- production index modified: `false`
- production Data Mart written: `false`
- automatic Smart Issue alerts/actions: `false`
- platform mutation: `false`
- causal claims: `false`

## Change guide

For a new Native V2 presentation capability:

1. identify whether the capability belongs in an existing extension or requires a new registered presentation module;
2. add its style/runtime/bundle contribution through the canonical composition boundary;
3. add a stable extension ID/version marker;
4. add/extend a validator and regression test;
5. extend replay workflow invariants when the capability affects the canonical artifact;
6. run real-payload replay;
7. run full staging when the capability participates in the production-like chain;
8. verify upstream fingerprints and safety flags;
9. update documentation/checkpoint before declaring it locked.

Do **not** add another nested `build_native_v2_multi_shop` wrapper as the canonical path.

## Deferred by design

Not part of Composition v1:

- eliminating the final single base compatibility bridge;
- production deployment/cutover;
- Smart Issue Review Console interaction/control plane;
- Alert Policy;
- production OAuth/domain hardening.

These require separate milestones and separate validation evidence.
