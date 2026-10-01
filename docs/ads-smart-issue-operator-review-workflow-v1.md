# Ads Smart Issue Operator Review Workflow v1

Validation date: **2026-09-30**  
Status: **PREPRODUCTION / VALIDATED / LOCKED / FAIL-CLOSED**  
Original full staging validation: **run #555 — 36675310524 — PASS**  
Maintainability revalidation: **run #558 — 36691022729 — PASS**

## Purpose

Smart Issue Registry v1 safely stores human-reviewed issue state, but its append-only JSON ledger is a low-level interface.

Operator Review Workflow v1 adds an operational sidecar that answers:

> **“Given the current review queue and Smart Issue states, exactly which actions may an operator take, and how can that decision be converted into one valid append-only review event without bypassing safety?”**

This layer deliberately does **not** change the locked Smart Issue Registry / Ads Intelligence fingerprint.

## Position in the flow

`Ads evidence`
→ `Context Qualification`
→ `Dynamic Diagnosis`
→ `Persistence`
→ `Smart Issue Candidate`
→ `Smart Issue Registry / Human Review Promotion`
→ **`Operator Review Workflow sidecar`**

The sidecar produces `ads_smart_issue_review_workflow.json` and a separate workflow fingerprint.

## Operational-state source

Canonical mutable review state now lives at:

`ops/ads_smart_issue_review_events.json`

The old compatibility ledger under `config/` has been removed. `config/` owns contracts/registries/configuration; `ops/` owns this mutable human review state.

## State-valid actions

### Candidate review queue

`PENDING_REVIEW`, `DEFERRED`, `DISMISSED`:

- `PROMOTE`
- `DEFER`
- `DISMISS`

`REOPEN_REVIEW_REQUIRED`:

- `REOPEN`

### Existing Smart Issues

`OPEN`:

- `ACKNOWLEDGE`
- `MONITOR`
- `RESOLVE`

`ACKNOWLEDGED`:

- `MONITOR`
- `RESOLVE`

`MONITORING`:

- `MONITOR`
- `RESOLVE`

`RESOLVED`:

- `REOPEN`

Any action outside the current state contract fails closed.

## Review command contract

Utility: `automation/ads_smart_issue_review_command.py`

A valid command requires:

- exactly one target: `candidateKey` or `issueId`;
- explicit `reviewedBy`;
- timezone-aware `reviewedAt`;
- current `operatorLedgerFingerprint` from the generated workflow;
- an action currently allowed for that target state.

Event IDs are deterministic from the expected ledger fingerprint + action + target + reviewer + timestamp + note.

For `PROMOTE`, the tool captures the promotion candidate snapshot from the current validated review queue. The operator does not manually recreate the snapshot.

## Dry-run and append-only safety

Ledger writing is never implicit.

The CLI is dry-run by default. The review event is appended only when the operator explicitly provides `--apply`.

Before append, the current ledger fingerprint must match the workflow's expected ledger fingerprint. If another review event changed the ledger after the operator loaded the workflow, the command fails closed and the workflow must be rebuilt.

This prevents stale-view overwrites and accidental concurrent review decisions.

## Sidecar fingerprint rule

Operator Review Workflow is operational metadata, not new Ads evidence.

Therefore it has its own fingerprint but must **not** change:

- `adsSmartIssueRegistryFingerprint`;
- `adsIntelligenceFingerprint`.

Locked lineage:

- Smart Issue Registry / Ads Intelligence:  
  `234cfc09d01a2418384bf23ea7dabbaf641f92e26cf8d2765ac32e12f50b1448`
- Operator Review Workflow:  
  `314921dc35393c169454559b7378effbfb1d2f0c35b2b5b82f663bcc97c4bc9a`
- validated raw-ledger concurrency fingerprint for the current empty ledger:  
  `a5a99966fbd29c99d0264b89772e768401f9e8d0c7707c27d2e872b5d650970d`

Run #558 reconfirmed that moving the ledger source to `ops/` did not change Registry/Ads or workflow fingerprints.

## Current September 2026 result

Smart Issue Candidate v1 currently has no eligible candidates, therefore:

- review queue: **0**;
- current Smart Issues: **0**;
- candidate actions: **0**;
- issue actions: **0**;
- workflow status: **`READY_EMPTY`**.

This is a valid operational state. The workflow is ready to expose actions automatically as soon as a qualifying candidate or human-promoted issue exists.

## QA evidence

Original run #555:

- core compile/tests: PASS;
- complete PREPRODUCTION chain: PASS;
- Operator Review Workflow QA: **13 checks / 0 failures**;
- Registry/Ads fingerprint unchanged.

Maintainability run #558:

- complete PREPRODUCTION chain: PASS;
- Registry QA: **18 / 0 failed**;
- Native QA: **33 / 0 failed**;
- Operator Review Workflow fingerprint unchanged;
- production safety remained disabled.

## Safety boundary

Operator Review Workflow v1 does **not**:

- automatically promote a candidate;
- automatically transition an issue;
- automatically resolve an issue;
- write a ledger without explicit `--apply`;
- overwrite a ledger after its expected fingerprint becomes stale;
- send automatic alerts;
- execute automatic Ads actions;
- mutate Shopee/TikTok Ads;
- make causal claims;
- activate production.

All automatic promotion, transitions, resolution, alerts and actions remain disabled.

## Next architectural milestone

Do **not** deepen the existing exact-string Native V2 wrapper chain by attaching the Review Console directly to it.

The next structural milestone is **Native V2 Extension Composition v1**: introduce explicit composable presentation extension slots/hooks while preserving the current rendered behavior and locked upstream contracts.

After that boundary is validated, build **Smart Issue Review Console / Command Center Workflow UI v1** on top of the governed Operator Review Workflow. UI decisions must continue to route through the validated review-command contract rather than direct Registry/ledger mutation.

Alert Policy remains a separate later milestone for human-promoted open issues.
