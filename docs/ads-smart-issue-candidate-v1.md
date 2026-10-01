# Ads Smart Issue Candidate Policy v1

Validation date: **2026-09-30**  
Status: **PREPRODUCTION / VALIDATED / FAIL-CLOSED**  
Final staging validation: **run #542 — 36670436931 — PASS**

## Purpose

Diagnosis Persistence answers:

> **“Has the same diagnosis repeated across independent, comparable windows strongly enough to be considered persistent?”**

Smart Issue Candidate Policy asks the next, stricter question:

> **“Is this persistent diagnosis still recent and economically material enough to deserve operator attention as a candidate issue?”**

`CONFIRMED` persistence is necessary but is not sufficient.

This layer does not create a Smart Issue. It only emits a PREPRODUCTION candidate for human/operator review.

## Position in the Ads intelligence flow

`Canonical Ads facts`
→ `Ads evidence / product signals`
→ `Business Context Qualification`
→ `Dynamic Ads Diagnosis`
→ `Diagnosis Persistence / Multi-window Confirmation`
→ **`Smart Issue Candidate Policy`**
→ `UI Payload`
→ `Native V2 presentation wrappers`

All locked upstream layers remain unchanged.

## Input boundary

The candidate resolver may consume only:

- `dynamicDiagnosis.items.persistence`;
- persistence state **CONFIRMED**;
- the evidence already attached to that diagnosis.

It may not:

- use raw Ads signals to create a new diagnosis;
- override a Persistence result;
- infer causal loss;
- create an alert or action.

## Why “economic exposure”, not “economic loss”

The existing Ads `priorityScore` already combines:

- spend share;
- absolute ROAS movement;
- signal confidence.

Smart Issue Candidate v1 therefore does not create another overlapping impact score.

The second gate is named **economic exposure** and uses observed facts only:

- current Ads spend;
- current attributed sales;
- spend share;
- scope-specific spend floor.

These fields are never converted into a counterfactual “lost revenue” or “lost profit” estimate. The contract explicitly records `economicExposureIsLossEstimate = false`.

## Candidate gates

Policy contract: `config/ads_smart_issue_candidate_contract.json`

### Gate 1 — Persistence

Required state:

`CONFIRMED`

`ONE_OFF`, `CONFLICTED` and `FIRST_OBSERVATION` can never become a candidate in v1.

### Gate 2 — Materiality

The diagnosis must satisfy both:

- `priorityScore >= 55`;
- `abs(ROAS delta) >= 25%`.

The `55` threshold corresponds to at least the current MEDIUM diagnosis tier. A persistent WATCH-level diagnosis is not automatically important enough for issue promotion.

### Gate 3 — Economic exposure

Required:

- spend share >= **5%**;
- and either current spend is above the scope-specific floor or spend share is at least **10%**.

Scope spend floors:

| Scope | Minimum current Ads spend |
| --- | ---: |
| day | 100,000 VND |
| week | 500,000 VND |
| month | 2,000,000 VND |
| year | 5,000,000 VND |

The 10% share override prevents the absolute floor from hiding a genuinely dominant product in a smaller shop/window.

### Gate 4 — Recency

Recency is anchored to the shop's latest READY daily Ads evidence date, not wall-clock runtime time.

Maximum evidence age:

| Scope | Maximum age |
| --- | ---: |
| day | 3 days |
| week | 10 days |
| month | 45 days |
| year | 400 days |

This prevents an old confirmed diagnosis from remaining an active issue candidate merely because historical persistence was once proven.

### Gate 5 — Stable-key deduplication

Candidate identity is stable over:

- shopId;
- productId;
- diagnosis kind;
- scope;
- current Business Context signature.

Only one active candidate may exist for the same stable key. The newest material occurrence wins.

### Gate 6 — Lifecycle and cooldown

Lifecycle states:

- `NEW`;
- `CONTINUING`;
- `REOPENED`;
- `COOLDOWN_SUPPRESSED`.

Continuity / reopen cooldown windows:

| Scope | Continuing gap | Reopen cooldown |
| --- | ---: | ---: |
| day | <= 3 days | <= 7 days |
| week | <= 10 days | <= 21 days |
| month | <= 45 days | <= 60 days |
| year | <= 400 days | <= 450 days |

If a signal disappears long enough to be a new episode but returns inside the cooldown, the reopen candidate is suppressed rather than generating issue churn.

## Candidate decision statuses

The backend may produce evaluation states such as:

- `ELIGIBLE`;
- `BLOCKED_MATERIALITY`;
- `BLOCKED_ECONOMIC_EXPOSURE`;
- `BLOCKED_RECENCY`;
- `DUPLICATE_SUPPRESSED`;
- `COOLDOWN_SUPPRESSED`.

Only `ELIGIBLE` is copied into the shop-level `smartIssueCandidates` list.

## Real September 2026 result

Final run #542 reproduced the previously locked Persistence result:

- total Persistence CONFIRMED diagnosis items: **1**;
- SYT+: **1**;
- Mall: **0**.

Smart Issue Candidate result:

- active candidates: **0**;
- Smart Issues created: **0**.

### Why the one CONFIRMED diagnosis was rejected

Shop: **SYT+**  
Product: **Găng tay Air S5 Plus** (`41433706033`)  
Scope: **day**  
Confirmed observation: **2026-09-11**

Persistence remained valid:

- state: `CONFIRMED`;
- support: 3/3 independent context-equivalent observations.

Candidate evidence:

- priority score: **50.0053**;
- required priority: **55**;
- absolute ROAS delta: **100%**;
- current Ads spend: **21,255 VND**;
- daily spend floor: **100,000 VND**;
- spend share: **5.01%**;
- high-share override: **10%**;
- latest trusted daily Ads evidence: **2026-09-27**;
- evidence age: **16 days**.

Primary result:

`BLOCKED_MATERIALITY`

Recorded exposure blockers:

- `PRIORITY_BELOW_MINIMUM`;
- `SPEND_EXPOSURE_BELOW_SCOPE_FLOOR`.

The 16-day age also shows why the diagnosis is not operationally current for the daily recency policy. The resolver uses fail-closed ordered gates; it does not promote a historical confirmed signal simply because persistence was proven.

This is the intended distinction:

**persistent ≠ material ≠ current ≠ issue-worthy**.

## UI behavior

Presentation wrapper:

`ads-smart-issue-candidate-ui-v1`

The Financial v38, Dynamic Diagnosis and Persistence wrappers remain intact.

When and only when `smartIssueCandidate.eligible == true`, the diagnosis card may show a compact badge:

`Ứng viên Smart Issue · Mới / Đang tiếp diễn / Mở lại · n ngày`

Run #542 has zero eligible candidates, so no real diagnosis card is promoted by current data.

The Desk still consumes `dynamicDiagnosis.items`; raw `snap.signals` is not restored.

## Fingerprint lineage

Final run #542 reproduced all locked upstream fingerprints exactly:

1. Base Ads Intelligence  
   `a1faa4cf2e4c9403452fb47d62504a516b4a8d2eaedff7ebe78dcf5a2220f79b`
2. Business Context Qualification  
   `23cb81876a955fca122ab6d2ad55711682972a6ddc50afc20de9ec77c5157dfc`
3. Dynamic Ads Diagnosis  
   `4daab89d26c877e858c39b462b6599234b14c39a18e37f5ce373b9e1aae9b4a2`
4. Diagnosis Persistence  
   `4b4cf0fb8fea41db6e1b7c6e470347bc0c212b554774ec6068e743359513dabd`
5. Smart Issue Candidate / final Ads Intelligence  
   `2373ef01716950719a6bc16be046e7bb456cde74d5f4b436c05cd5605a6a05e7`

`preSmartIssueAdsIntelligenceFingerprint` exactly equals the locked Persistence fingerprint, proving this policy is an additive downstream layer.

## QA evidence

Final staging run #542:

- core compile: PASS;
- repository unit tests: PASS;
- Staging: PASS;
- Processed: PASS;
- durable Drive publish: PASS / NOOP where fingerprints matched;
- Semantic: PASS;
- Business Context: PASS;
- Historical Intelligence: PASS;
- Product Intelligence: PASS;
- Ads Intelligence + Context + Diagnosis + Persistence + Smart Issue Candidate: PASS;
- Smart Issue Candidate QA: **19 checks / 0 failures**;
- UI Payload: PASS;
- Native V2: PASS;
- Native QA: **33 checks / 0 failures**.

Native presentation lineage now ends with:

- `native-ads-financial-v38`;
- `ads-financial-polish-v2`;
- `ads-dynamic-diagnosis-ui-v1`;
- `ads-diagnosis-persistence-ui-v1`;
- `ads-smart-issue-candidate-ui-v1`.

## Safety boundary

Candidate v1 enables **candidate qualification only**.

It does **not**:

- create a Smart Issue record;
- open/close an operator issue;
- send a notification;
- trigger an alert;
- recommend an automatic bid/budget change;
- execute an action;
- mutate Shopee/TikTok Ads;
- make a causal claim;
- authorize production activation.

Validated capability state:

- `adsSmartIssueCandidatesEnabled = true`;
- `adsSmartIssuesEnabled = false`;
- `adsSmartIssueAutomaticAlertsEnabled = false`;
- `adsSmartIssueAutomaticActionsEnabled = false`.

## Next logical milestone

The next layer should be a **Smart Issue Registry / Human Review Promotion Policy**.

That layer should create an actual durable issue only after an eligible candidate passes an explicit promotion boundary. It should own persistent issue IDs, OPEN / ACKNOWLEDGED / MONITORING / RESOLVED states, operator notes, evidence refresh, reopen history and final deduplication across refresh runs.

Alerts and automatic actions should remain a later, separate authorization layer.
