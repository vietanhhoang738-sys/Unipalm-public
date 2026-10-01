# Dynamic Ads Diagnosis v1 — 2026-09-30

Status: **PREPRODUCTION / VALIDATED / FAIL-CLOSED**

This layer continues Dynamic Ads Intelligence after Business Context Qualification. It does not reopen the locked Ads Financial v38 foundation and does not enable automatic alerts, automatic actions, platform mutation or causal claims.

## Position in the Ads flow

`Canonical Ads facts → Ads evidence/signals → Business Context Qualification → Dynamic Ads Diagnosis → UI Payload → Financial v38 + diagnosis wrapper`

The locked Ads facts, ratios, product signals and ROAS identity/Shapley decomposition remain unchanged.

## Contract isolation

Dynamic Diagnosis has its own contract:

- `config/ads_dynamic_diagnosis_contract.json`
- layer: `multi_shop_ads_dynamic_diagnosis_v1`
- version: `1.0`

The locked Ads / Context contract remains:

- `config/ads_intelligence_contract.json`
- version: `1.2`

This isolation is intentional. The first implementation briefly placed diagnosis policy inside the Ads contract, which changed the base Ads fingerprint even though canonical Ads facts had not changed. That candidate was rejected. The final implementation restores the locked Ads contract and fingerprints before adding the downstream diagnosis fingerprint.

## Input contract

Dynamic Diagnosis may consume only:

- `qualifiedSignals`;
- a READY equal-length comparison;
- `CONTEXT_COMPATIBLE` Business Context qualification.

It must never promote raw `signals` directly into diagnosis.

If context is `CONTEXT_DIFFERENT` or `CONTEXT_UNKNOWN`, raw numerical evidence remains available but diagnosis is blocked.

## Diagnosis states

- `READY` — at least one context-qualified signal was promoted into diagnosis.
- `NO_MATERIAL_DIAGNOSIS` — context is compatible but no signal crossed the existing Ads materiality thresholds.
- `BLOCKED_COMPARISON_NOT_READY` — there is no trusted equivalent comparison period.
- `BLOCKED_CONTEXT_DIFFERENT` — current and reference periods have different exact-date sale context profiles.
- `BLOCKED_CONTEXT_UNKNOWN` — matching sale context cannot be established.

## Diagnosis item

A diagnosis item is deterministic and product-scoped. It contains:

- problem/opportunity type;
- product identity and commercial name;
- priority tier and score;
- confidence tier;
- ROAS change;
- spend share;
- spend change;
- Ads sales change;
- current ROAS / spend / Ads sales;
- operator-facing headline and evidence summary;
- `reviewFocus` — an operator check to perform, not a platform action.

Every item is explicitly:

- `evidenceOnly = true`;
- `causalClaim = false`;
- `automaticAlertEligible = false`;
- `automaticActionEligible = false`.

## Priority policy

Existing Ads `priorityScore` remains authoritative.

- `HIGH`: score >= 75
- `MEDIUM`: score >= 55
- `WATCH`: below 55

Dynamic Diagnosis does not manufacture a second independent score.

## UI binding

Financial v38 remains locked.

An additive wrapper `ads-dynamic-diagnosis-ui-v1` changes only the effective Ads Intelligence Desk binding:

- the Desk consumes `dynamicDiagnosis.items`;
- it no longer consumes `snap.signals` directly;
- when diagnosis is blocked, the Desk shows the blocking reason;
- when context is compatible but no material signal exists, the Desk explicitly states that no diagnosis is available;
- financial metrics, equation, charts, funnel, cost benchmarks, entity scopes and v38 page order remain unchanged.

## Fingerprint lineage

The Ads lineage is now separated into:

1. base Ads Intelligence fingerprint;
2. Ads Context Qualification fingerprint;
3. Dynamic Ads Diagnosis fingerprint;
4. final Ads Intelligence fingerprint consumed by UI Payload.

This allows diagnosis-policy changes to be detected without pretending the underlying Ads facts changed.

## Validated checkpoint — run #525

Final validation:

- workflow run: `36665424074` / #525 — **SUCCESS**
- branch head validated: `a6620b3b8b80bf87bb786b5efeb15adccb61f3a9`
- period: `2026-09`
- Dynamic Diagnosis QA: **PASS**
- Dynamic Diagnosis QA checks: **1,564**
- failed Dynamic Diagnosis checks: **0**
- Native V2 QA: **33 / 33 PASS**

Full PREPRODUCTION chain passed:

`RAW → Staging → Processed v2 → durable Drive → Semantic v2 → Business Context → Historical Intelligence → Product Intelligence → Ads Intelligence → Context Qualification → Dynamic Diagnosis → UI Payload → Native V2`

### Locked lineage reproduced

The final isolated-contract run reproduced the previously locked fingerprints exactly:

- base Ads Intelligence: `a1faa4cf2e4c9403452fb47d62504a516b4a8d2eaedff7ebe78dcf5a2220f79b`
- Ads Context Qualification: `23cb81876a955fca122ab6d2ad55711682972a6ddc50afc20de9ec77c5157dfc`
- Business Context: `d4fef77fe3f18d2e9b91ea611dbcd755372fff1e9fc5e29739fb851b9a0a8cd0`

Only the downstream diagnosis/final Ads lineage is new:

- Dynamic Ads Diagnosis / final Ads Intelligence: `4daab89d26c877e858c39b462b6599234b14c39a18e37f5ce373b9e1aae9b4a2`

This is the required evidence that the diagnosis milestone did not silently reopen the locked Ads/Context foundation.

### Real candidate behavior

Latest available snapshots remain fail-closed:

SYT+:
- latest day `2026-09-27`: `BLOCKED_CONTEXT_UNKNOWN`, 0 diagnosis items;
- latest week ending `2026-09-27`: `BLOCKED_CONTEXT_DIFFERENT`, 0 diagnosis items;
- September month: `BLOCKED_CONTEXT_DIFFERENT`, 0 diagnosis items;
- year: unavailable under the existing trusted-history rule.

Mall:
- latest day `2026-09-27`: `BLOCKED_CONTEXT_UNKNOWN`, 0 diagnosis items;
- latest week ending `2026-09-27`: `BLOCKED_CONTEXT_DIFFERENT`, 0 diagnosis items;
- September month: `BLOCKED_CONTEXT_DIFFERENT`, 0 diagnosis items;
- year: `BLOCKED_COMPARISON_NOT_READY`, 0 diagnosis items.

The layer is not permanently blocked. Historical context-compatible observations do produce diagnosis:

- SYT+: 26 READY diagnosis snapshots, 79 diagnosis items in the current trusted history;
- Mall: 14 READY diagnosis snapshots, 37 diagnosis items.

Week ending `2026-09-08` is a validated compatible example:

- SYT+: `CONTEXT_COMPATIBLE`, 5 qualified signals → 5 diagnosis items;
- Mall: `CONTEXT_COMPATIBLE`, 8 qualified signals → the top 6 diagnosis items under the configured max-item policy.

The candidate includes both problem and opportunity cases. Large percentage movements remain evidence-only; they are not interpreted as causal and are not converted into automatic actions.

### Native binding validation

Native V2 remains on:

- `native-ads-financial-v38`;
- `ads-financial-polish-v2`;
- additive diagnosis wrapper `ads-dynamic-diagnosis-ui-v1`.

Validation confirms:

- `ads_dynamic_diagnosis_ui_ready = true`;
- `ads_diagnosis_consumes_qualified_signals_only = true`;
- raw Desk binding `snap.signals` is absent;
- effective Desk binding uses `snap.dynamicDiagnosis.items`;
- production V2 template remains unmodified.

Native build fingerprint for run #525:
`3dfb9a19c5e928319d21d268057ab63940b770925fa4f3c23aa271df63e62c42`

## Safety boundary

Dynamic Ads Diagnosis v1 does not:

- write production Data Mart;
- modify the production V2 template;
- authorize production cutover;
- mutate Shopee/TikTok Ads;
- change bids or budgets;
- create alerts;
- create actions;
- make causal claims.

## Next milestone

The next logical milestone is **Diagnosis Persistence / Multi-window Confirmation Policy**: determine whether a diagnosis must repeat across multiple context-compatible observations before it may become a Smart Issue candidate.

This milestone must remain separate from automatic alert/action activation. A single compatible-period diagnosis — especially one with a very large percentage change caused by a small reference base — is evidence, not yet a durable operational issue.
