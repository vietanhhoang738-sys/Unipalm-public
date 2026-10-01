# Smart Issue Review Console / Command Center Workflow UI v1

Status: **LOCKED_V1 — PREPRODUCTION**  
Locked: **2026-09-30**

## Purpose

Provide a shop-scoped operator console for reviewing Smart Issue candidates and existing Smart Issues without allowing presentation code to mutate the review ledger, promote candidates automatically, transition issues automatically, trigger alerts/actions, or touch production.

The console is a presentation-side consumer of the already locked Smart Issue Operator Review Workflow. It does not redefine Smart Issue eligibility, Registry lifecycle rules, or allowed actions.

## Canonical flow

```text
Ads Intelligence
  -> Smart Issue Registry
  -> Operator Review Workflow sidecar
     ads_smart_issue_review_workflow.json
  -> Native V2 runner
  -> canonical Extension Composition v1.1
  -> read-only Smart Issue Review Console
  -> human operator
```

`ui_payload.json` remains independent from the Operator Review Workflow sidecar. The workflow sidecar is validated and bound only at the Native presentation boundary. This preserves the locked UI Payload and Ads/Registry fingerprints.

## Ownership

Implementation:
- `automation/modules/ui_v2_ads_smart_issue_review_console.py`
- `automation/modules/ui_v2_extension_composition_canonical.py`
- `automation/multi_shop_native_v2_runner.py`

Contract:
- `config/ads_smart_issue_review_console_contract.json`

Regression protection:
- `automation/tests/test_ui_v2_ads_smart_issue_review_console.py`
- `automation/tests/test_ui_v2_extension_composition_canonical.py`
- `.github/workflows/native-v2-composition-replay.yml`

The locked base `automation/modules/ui_v2_extension_composition.py` remains the immutable Composition v1 compatibility surface. Canonical composition is additive `native-v2-extension-composition-v1.1` and contains the original ten extensions plus `ads_smart_issue_review_console` as the eleventh extension.

## Input contract

The console accepts only a ready Operator Review Workflow sidecar whose lineage matches the Ads destination in the canonical UI Payload.

Required evidence includes:
- `workflowFingerprint` present;
- `operatorLedgerFingerprint` present;
- `adsIntelligenceFingerprint` exactly matching the Ads destination;
- `sourceRegistryFingerprint` and `adsSmartIssueRegistryFingerprint` exactly matching the Registry fingerprint exposed by the Ads destination;
- identical shop scope between workflow sidecar and Ads destination;
- explicit human-review and append-only safety flags;
- all automatic promotion, transition, resolution, alert, action, causal and production flags false.

A mismatch fails the Native build closed.

## Allowed actions

The console renders only actions already emitted by the Operator Review Workflow.

Candidate review states:
- `PENDING_REVIEW`, `DEFERRED`, `DISMISSED` -> `PROMOTE`, `DEFER`, `DISMISS`
- `REOPEN_REVIEW_REQUIRED` -> `REOPEN`

Issue states:
- `OPEN` -> `ACKNOWLEDGE`, `MONITOR`, `RESOLVE`
- `ACKNOWLEDGED` -> `MONITOR`, `RESOLVE`
- `MONITORING` -> `MONITOR`, `RESOLVE`
- `RESOLVED` -> `REOPEN`

The UI displays these as read-only action chips and a command preview. It does not execute the command.

## Write boundary

The Review Console does **not**:
- call `fetch()` or `XMLHttpRequest`;
- run the review CLI with `--apply`;
- write `ops/ads_smart_issue_review_events.json`;
- bypass the expected ledger fingerprint concurrency guard;
- create/promote/transition/resolve a Smart Issue itself;
- trigger automatic alerts/actions;
- mutate platform state or production artifacts.

Actual review writes remain owned by the locked Operator Review Workflow and require explicit operator execution with reviewer identity, timezone-aware review time, expected current ledger fingerprint, and explicit apply authorization.

## Empty-state behavior

The current real workflow state is `READY_EMPTY` for both enabled shops. The UI intentionally renders a polished empty state rather than fabricating a candidate or lowering thresholds:

`Không có candidate hoặc Smart Issue nào cần review ở shop này.`

`Console không tự tạo issue và không tự ghi review event.`

Synthetic regression tests separately prove non-empty queue and issue rendering/state-action validation.

## Composition boundary

Canonical Native composition is now `native-v2-extension-composition-v1.1`:

```text
locked Composition v1 — 10 extensions
  + ads_smart_issue_review_console
  -> exactly one base Native compatibility bridge
  -> Base Native V2 builder
```

Invariants:
- 11 deterministic extension IDs;
- console is extension #11;
- compatibility bridge count remains exactly 1;
- `legacy_nested_wrapper_build_path_used = false`;
- locked base Native patch remains `native-ads-financial-v38`;
- explicit lineage includes both Composition v1.1 and locked Composition v1.

## Validation checkpoint

Pre-staging on commit `1c832ee90c27369a2709ef5bbb07b5f065956982`:
- Architecture & Contract Guard #45 / `36707186361`: PASS;
- core tests #576 / `36707186343`: PASS;
- real-data Native Composition Replay #9 / `36707186385`: PASS using the real UI Payload and Ads Operator Workflow artifact from staging run #570.

Final full PREPRODUCTION staging:
- run #577 / `36707308126`;
- head `1674a653184a01565412fa67fd3b544a1c2814e8`;
- Architecture & Contract Guard #47 / `36707307962`: PASS;
- complete pipeline PASS from ingestion through Processed/Drive/Semantic/Intelligence/UI Payload/Native and all evidence uploads.

Artifact audit:
- Ads Intelligence QA: **2507 checks, 0 failures**;
- UI Payload QA: **42 checks, 0 failures**;
- Native V2 QA: **33 checks, 0 failures**;
- UI Payload build fingerprint: `414d3675dda27ea473b8593bac754f2291799e9237e1db1945974f40fbde6f4f`;
- Native build fingerprint: `2b88532b953bfb7af50ae2ad988f1c22c09a7b8445cb384984c18d77d3338f72`;
- September Semantic fingerprint unchanged: `38e12e9552fd81571b85e37f977bfbeb8feda9a1d3b7e301663f56fa28cad7f6`;
- Ads / Registry fingerprint unchanged: `234cfc09d01a2418384bf23ea7dabbaf641f92e26cf8d2765ac32e12f50b1448`;
- Operator Review Workflow fingerprint unchanged: `314921dc35393c169454559b7378effbfb1d2f0c35b2b5b82f663bcc97c4bc9a`;
- operator ledger concurrency fingerprint: `a5a99966fbd29c99d0264b89772e768401f9e8d0c7707c27d2e872b5d650970d`;
- real queue count: 0;
- real issue count: 0;
- sidecar markers absent from `ui_payload.json` and present in Native HTML;
- no `fetch(`, `XMLHttpRequest`, `--apply`, `autoPromoteSmartIssue`, or raw Ads signal anti-pattern in the generated Native artifact;
- production cutover/deployment/index/template/Data Mart mutation flags remain false.

## Change guide

To change Review Console presentation or sidecar validation, start with:
1. `config/ads_smart_issue_review_console_contract.json`
2. `automation/modules/ui_v2_ads_smart_issue_review_console.py`
3. corresponding tests
4. canonical composition only if extension wiring changes

Do not edit Ads Intelligence, Candidate, Registry, or Operator Review Workflow merely to make the UI easier to render. If their business behavior must change, use their own versioned contracts and validation process.

## Recovery / rollback

Because the feature is PREPRODUCTION and additive, rollback is presentation-scoped:
- revert canonical composition/runner to the previous validated Composition v1 path;
- do not edit or roll back the review ledger to remove a UI change;
- rerun Architecture Guard + real-data replay + full staging before accepting the rollback checkpoint.

No production rollback is required because this milestone does not authorize production cutover.
