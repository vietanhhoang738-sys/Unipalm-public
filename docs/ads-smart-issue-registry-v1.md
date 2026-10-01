# Ads Smart Issue Registry / Human Review Promotion v1

Validation date: **2026-09-30**  
Status: **PREPRODUCTION / VALIDATED / LOCKED / FAIL-CLOSED**  
Original full staging validation: **run #551 — 36674346169 — PASS**  
Maintainability revalidation after operator-state migration: **run #558 — 36691022729 — PASS**

## Purpose

Smart Issue Candidate v1 answers:

> **“Is a persistent Ads diagnosis sufficiently material, economically exposed and recent to deserve operator review?”**

Smart Issue Registry / Human Review Promotion v1 answers:

> **“Has an operator explicitly reviewed that candidate and decided whether it should become or remain a Smart Issue?”**

A candidate never becomes an issue automatically.

## Position in the Ads intelligence flow

`Canonical Ads facts`
→ `Business Context Qualification`
→ `Dynamic Ads Diagnosis`
→ `Diagnosis Persistence`
→ `Smart Issue Candidate Policy`
→ **`Smart Issue Registry / Human Review Promotion`**
→ `Operator Review Workflow`
→ `UI Payload`
→ `Native V2 presentation`

All lower layers remain independently fingerprinted and unchanged.

## Input boundary

Registry v1 consumes only:

- `smartIssueCandidates` emitted by Smart Issue Candidate v1;
- explicit events from the canonical operator ledger `ops/ads_smart_issue_review_events.json`;
- an append-only review-event model.

The former compatibility ledger under `config/` was removed during System Architecture & Maintainability Foundation v1. `config/` owns contracts/registries/configuration; mutable human review state is owned by `ops/`.

Registry does not consume raw Ads signals and cannot bypass Candidate qualification.

## Human review policy

Candidate review actions:

- `PROMOTE`
- `DEFER`
- `DISMISS`

An unreviewed candidate remains `PENDING_REVIEW`.

`PROMOTE` is the only event that may create a Smart Issue. Promotion requires:

- explicit `reviewedBy`;
- timezone-aware `reviewedAt`;
- stable candidate key;
- a full candidate snapshot captured at promotion time.

Automatic promotion is forbidden.

## Issue lifecycle

A promoted issue starts in `OPEN`.

Supported states:

- `OPEN`
- `ACKNOWLEDGED`
- `MONITORING`
- `RESOLVED`

Supported transition events:

- `ACKNOWLEDGE`
- `MONITOR`
- `RESOLVE`
- `REOPEN`

Invalid state transitions fail closed.

Candidate disappearance never auto-resolves an issue. If a resolved issue has a current qualifying candidate again, the candidate becomes `REOPEN_REVIEW_REQUIRED`; an explicit `REOPEN` event is still required.

## Stable identity and audit history

Smart Issue ID is deterministic from the Smart Issue Candidate key. A refresh therefore does not create a new identity for the same issue family.

Each issue stores:

- promotion snapshot;
- `eventHistory`;
- operator notes;
- `openedAt` / `openedBy`;
- `lastUpdatedAt` / `lastUpdatedBy`;
- resolution metadata;
- reopen count.

Review ledger events are ordered by `reviewedAt` and `eventId`. Duplicate event IDs fail closed.

## Current September 2026 result

Validated real data currently contains no eligible Smart Issue Candidate under Candidate v1, therefore Registry correctly contains:

| Shop | Current candidates | Review queue | Smart Issues |
| --- | ---: | ---: | ---: |
| SYT+ | 0 | 0 | 0 |
| Mall | 0 | 0 | 0 |

This is expected. Production data is not weakened merely to force a visible issue.

## UI behavior

Presentation wrapper: `ads-smart-issue-registry-ui-v1`.

It is additive downstream of:

- `native-ads-financial-v38`;
- `ads-financial-polish-v2`;
- `ads-dynamic-diagnosis-ui-v1`;
- `ads-diagnosis-persistence-ui-v1`;
- `ads-smart-issue-candidate-ui-v1`.

For an eligible candidate it may display read-only human-review states such as:

- `Chờ review`
- `Đã hoãn`
- `Đã bỏ qua`
- `Cần review mở lại`
- linked issue state.

The static PREPRODUCTION template does not contain controls that directly create or transition issues.

## Validation evidence

Original Registry validation run #551 — `36674346169`:

- core compile/tests: PASS;
- all PREPRODUCTION pipeline stages: PASS;
- Registry QA: **18 checks / 0 failures**;
- Native QA: **33 checks / 0 failures**.

Run #548 had correctly failed closed because the Registry presentation wrapper expected an obsolete Candidate-card terminator. The wrapper was repaired using a strict Candidate-specific outer-card anchor and a dedicated regression test; lower-layer validators were not weakened.

Maintainability revalidation run #558 — `36691022729`:

- full PREPRODUCTION chain: PASS;
- Registry QA: **18 / 0 failed**;
- Native QA: **33 / 0 failed**;
- review ledger source moved to `ops/`;
- Registry and all upstream Ads fingerprints remained unchanged.

## Fingerprint lineage

Locked lineage:

1. Base Ads Intelligence  
   `a1faa4cf2e4c9403452fb47d62504a516b4a8d2eaedff7ebe78dcf5a2220f79b`
2. Context Qualification  
   `23cb81876a955fca122ab6d2ad55711682972a6ddc50afc20de9ec77c5157dfc`
3. Dynamic Diagnosis  
   `4daab89d26c877e858c39b462b6599234b14c39a18e37f5ce373b9e1aae9b4a2`
4. Diagnosis Persistence  
   `4b4cf0fb8fea41db6e1b7c6e470347bc0c212b554774ec6068e743359513dabd`
5. Smart Issue Candidate  
   `2373ef01716950719a6bc16be046e7bb456cde74d5f4b436c05cd5605a6a05e7`
6. Human review ledger (empty validated ledger content)  
   `f294114bb005151b50bdd96f4bbd985d365edbaba01afc8d27218dc02b3739b8`
7. Smart Issue Registry / final Ads Intelligence  
   `234cfc09d01a2418384bf23ea7dabbaf641f92e26cf8d2765ac32e12f50b1448`

## Safety boundary

Registry v1 does **not**:

- auto-promote a candidate;
- auto-transition an issue;
- auto-resolve an issue;
- send automatic alerts;
- execute automatic Ads actions;
- mutate Shopee/TikTok Ads;
- make causal claims;
- write production Data Mart;
- modify the production V2 template;
- authorize production cutover.

Final safety remains:

- `automaticPromotionEnabled = false`;
- `automaticIssueResolutionEnabled = false`;
- `automaticAlertsEnabled = false`;
- `automaticActionsEnabled = false`;
- `causalClaimsEnabled = false`;
- `productionActivationEnabled = false`.

## Downstream status

**Smart Issue Operator Review Workflow v1 is now completed and locked.**

It consumes this Registry as a sidecar, exposes only state-valid operator actions, requires the expected current ledger fingerprint and explicit apply for ledger writes, and does not modify the locked Registry/Ads fingerprint.

Current next architectural work is not to change Registry v1. The recommended presentation milestone is **Native V2 Extension Composition v1**, followed by a Smart Issue Review Console that uses the governed Operator Review Workflow rather than mutating Registry state directly.
