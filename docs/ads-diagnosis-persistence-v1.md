# Ads Diagnosis Persistence / Multi-window Confirmation v1

Validation date: **2026-09-30**  
Status: **PREPRODUCTION / VALIDATED / FAIL-CLOSED**  
Final staging validation: **run #535 — 36668916624 — PASS**

## Purpose

Dynamic Ads Diagnosis answers: **“What diagnosis is supported in this context-compatible comparison?”**

Diagnosis Persistence answers the narrower second question:

> **“Has the same diagnosis repeated across independent, comparable observation windows strongly enough to be considered persistent?”**

This layer is deliberately placed after Dynamic Ads Diagnosis. It does not create a diagnosis from raw Ads signals and it does not create Smart Issues.

## Position in the Ads intelligence flow

`Canonical Ads facts`
→ `Ads evidence / product signals`
→ `Business Context Qualification`
→ `Dynamic Ads Diagnosis`
→ **`Diagnosis Persistence / Multi-window Confirmation`**
→ `UI Payload`
→ `Financial v38 + Dynamic Diagnosis + Persistence presentation wrappers`

The locked Ads Financial v38, Context Qualification and Dynamic Diagnosis v1 layers remain unchanged.

## Input boundary

Persistence may consume only:

- `dynamicDiagnosis.items`;
- observations whose Ads snapshot is READY;
- observations whose Business Context result is `CONTEXT_COMPATIBLE`;
- observations whose Dynamic Diagnosis status is `READY` or `NO_MATERIAL_DIAGNOSIS`.

It may not consume raw `signals` or recreate a diagnosis independently.

Blocked context windows are excluded rather than treated as negative evidence because they are not comparable.

A context-compatible `NO_MATERIAL_DIAGNOSIS` window is valid negative evidence and therefore counts as a miss.

## Independence rule

Persistence confirmation is **same-shop, same-scope, same-current-context-signature, non-overlapping-window only**.

This is critical for rolling scopes. Two adjacent rolling 7-day windows may share six of seven days. Treating both as independent observations would create false confirmation. The resolver therefore selects observation windows backward in time and requires every selected older window to end before the newer selected window begins.

Cross-scope confirmation is forbidden in v1. A daily diagnosis cannot confirm a weekly diagnosis and vice versa.

## Confirmation policy

Policy contract: `config/ads_diagnosis_persistence_contract.json`

- lookback: up to **3 independent eligible observations**;
- minimum supporting observations: **2**;
- minimum support ratio: **2/3**;
- same product required;
- same diagnosis kind required;
- any opposite diagnosis kind for the same product inside the eligible lookback blocks confirmation.

### States

**CONFIRMED**  
At least two independent eligible windows support the same product + same diagnosis kind, support ratio is at least 2/3, and no opposite direction exists.

**ONE_OFF**  
Enough independent comparable observations exist, but the diagnosis does not repeat strongly enough.

**CONFLICTED**  
An opposite diagnosis kind appears for the same product in the eligible lookback. Even if two observations support the current direction, the conflict blocks confirmation.

**FIRST_OBSERVATION**  
There are not yet enough independent comparable windows to judge persistence.

## Real candidate result — September 2026

The final validated candidate evaluated **116 Dynamic Diagnosis items**:

| State | Count | Share |
| --- | ---: | ---: |
| CONFIRMED | 1 | 0.9% |
| ONE_OFF | 57 | 49.1% |
| CONFLICTED | 31 | 26.7% |
| FIRST_OBSERVATION | 27 | 23.3% |

By current shop identity:

- SYT+: 79 evaluated, **1 CONFIRMED**;
- Mall: 37 evaluated, **0 CONFIRMED**.

The low confirmation rate is intentional evidence, not a reason to loosen the rule. A large share of diagnoses either fails to repeat in the next comparable observations or reverses direction. Promoting those signals would make a future Smart Issue system noisy and overconfident.

### Confirmed example

Current shop identity: SYT+  
Scope: **day**  
Observation: **2026-09-11**  
Product: **Găng tay Air S5 Plus** (`41433706033`)  
Diagnosis: **PROBLEM**

The same problem diagnosis appears in three independent, context-equivalent daily observations:

- 2026-09-07;
- 2026-09-08;
- 2026-09-11.

All three use the same current context signature:

`PLATFORM|shopee|DOUBLE_DAY_MEGA_SALE|1|0`

Persistence result:

- support: **3/3**;
- support ratio: **100%**;
- opposite-direction observations: **0**;
- state: **CONFIRMED**.

The underlying diagnosis remains evidence-only: ROAS was down 100% in the 2026-09-11 comparison, with the product representing about 5.0% of Ads spend. The operator review focus is to inspect CPC, CVR and AOV before making any operational change. This is not a causal claim and does not authorize a budget action.

## UI behavior

Presentation wrapper: `ads-diagnosis-persistence-ui-v1`.

Financial v38 and `ads-dynamic-diagnosis-ui-v1` remain intact. Persistence only adds a compact state badge to diagnosis cards:

- `Đã xác nhận · x/y cửa sổ`
- `Một lần · x/y cửa sổ`
- `Mâu thuẫn · x/y cửa sổ`
- `Lần đầu · x/y cửa sổ`

The locked Dynamic Diagnosis Desk sentence remains unchanged, and the Persistence explanation is appended as a separate sentence.

The Desk still consumes `dynamicDiagnosis.items`; there is no raw `snap.signals` binding.

## Fingerprint lineage

Final run #535 reproduced all locked upstream fingerprints exactly:

1. Base Ads Intelligence  
   `a1faa4cf2e4c9403452fb47d62504a516b4a8d2eaedff7ebe78dcf5a2220f79b`
2. Business Context Qualification  
   `23cb81876a955fca122ab6d2ad55711682972a6ddc50afc20de9ec77c5157dfc`
3. Business Context source  
   `d4fef77fe3f18d2e9b91ea611dbcd755372fff1e9fc5e29739fb851b9a0a8cd0`
4. Dynamic Ads Diagnosis  
   `4daab89d26c877e858c39b462b6599234b14c39a18e37f5ce373b9e1aae9b4a2`
5. Diagnosis Persistence / final Ads Intelligence  
   `4b4cf0fb8fea41db6e1b7c6e470347bc0c212b554774ec6068e743359513dabd`

This proves the Persistence policy is an additive downstream layer rather than an implicit modification of the locked Ads / Context / Diagnosis foundations.

## QA evidence

Final staging run #535:

- core compile: PASS;
- repository unit tests: PASS;
- Staging: PASS;
- Processed: PASS;
- durable Drive publish: PASS / NOOP where fingerprints matched;
- Semantic: PASS;
- Business Context: PASS;
- Historical Intelligence: PASS;
- Product Intelligence: PASS;
- Ads Intelligence + Context + Diagnosis + Persistence: PASS;
- UI Payload: PASS;
- Native V2: PASS;
- Native QA: **33 checks / 0 failures**;
- Persistence QA: **1,208 checks / 0 failures**.

Native V2 lineage remains:

- `native-ads-financial-v38`;
- `ads-financial-polish-v2`;
- `ads-dynamic-diagnosis-ui-v1`;
- `ads-diagnosis-persistence-ui-v1`.

## Safety boundary

Persistence v1 does **not**:

- generate Smart Issue candidates;
- create alerts;
- create automatic actions;
- change bids or budgets;
- mutate Shopee/TikTok Ads;
- write a production Data Mart;
- modify the production V2 template;
- authorize production cutover;
- make causal claims.

All persistence items explicitly remain evidence-only and have:

- `smartIssueCandidateEligible = false`;
- `automaticAlertEligible = false`;
- `automaticActionEligible = false`;
- `causalClaim = false`.

## Next logical milestone

The next layer should be **Smart Issue Candidate Policy**, but it must consume only persistence-confirmed diagnoses and must remain separate from alert/action activation.

Before any issue is promoted, the policy should answer additional questions such as materiality, economic impact, recency, duplication/cooldown and whether the issue is still active. `CONFIRMED` should therefore be treated as a necessary input, not sufficient authorization for an operational issue or action.
