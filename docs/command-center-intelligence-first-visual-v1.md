# Command Center Intelligence-first Visual Pilot v1

Status: **VALIDATED PREPRODUCTION MILESTONE**  
Validated: **2026-09-26**  
Target: **Command Center (Portfolio + Shop scopes)**  
Compare destination: **preserved; only previously approved finance-table canary fix remains**  
Production cutover: **not authorized**

## Objective

Move Command Center from a metric-first dashboard toward the constitutional product mission:

`what is happening -> why -> evidence boundary -> what needs attention -> what to review -> detailed metrics`

The milestone does not create new business facts, anomaly logic, Smart Issues or Operator Action rules. It changes only how already-qualified intelligence is presented.

## Validated outcome

The Command Center now treats Intelligence as the first reading layer rather than a supporting card below raw KPIs.

The operator sees, in order:

1. **Tóm tắt vận hành** — concise interpretation of the selected period.
2. **Cơ sở phân tích** — context/evidence boundary.
3. **Yếu tố tác động** — structured driver rows with direction, percentage movement and estimated GMV effect.
4. **Cần chú ý** — Smart Issue status when qualified, or an explicit insufficient-evidence state when it is not.
5. **Nên kiểm tra** — a human-review option only when Operator Action Policy emitted one.
6. **Period selectors + Chỉ số chính** — detailed metrics remain available to verify the interpretation.
7. Existing deeper driver / issue analysis remains below for inspection.

The result is intentionally not an AI-chat surface. It is a deterministic intelligence presentation derived from canonical payload state.

## Evidence hierarchy

The presentation consumes only canonical Command Center period data already present in the UI payload:

- `current`
- `delta`
- `drivers`
- `historicalComparator`
- `smartIssues`
- `reviewOptions`

No new inference engine is added in the browser.

### Insufficient-evidence presentation

If anomaly eligibility is blocked:

- the UI may still describe factual period movement;
- the UI may show deterministic GMV driver decomposition when available;
- it explicitly says there is not enough evidence to conclude the movement is abnormal;
- it must not create a Smart Issue;
- it must not fabricate an optimization task.

Current operator-facing copy intentionally avoids backend implementation phrases such as `fail-closed`, `evidence gate` and `platform mutation`.

The underlying safety boundary is still fully enforced by machine state.

### Qualified Smart Issue

If a Smart Issue exists, the attention panel may show:

- affected KPI;
- severity;
- confidence;
- evidence-bound issue summary;
- first human review option when available.

### Review option

If a review option exists:

- it is shown as a human-review step;
- it is not represented as an automatic action;
- no platform or production mutation is enabled.

## Visual direction

The milestone follows the existing V2 Shared Design Language rather than creating a second UI system.

### Retained

- Inter;
- current V2 color tokens;
- light/dark behavior;
- navigation/sidebar grammar;
- metric/currency conventions;
- existing semantic badges;
- canonical Period selector;
- deeper analysis below the fold.

### Modernized

- Intelligence becomes the dominant first surface in Command Center;
- the former full-green narrative pulse is retired in Command Center scopes;
- long driver bullets become structured driver rows with impact bars;
- operator copy is shorter and more scannable;
- period cards become selector-like rather than dominant summary cards;
- KPI cards remain but are visually secondary to interpretation;
- shadows are reduced;
- spacing and typography use a calmer operational hierarchy.

Compare keeps its destination-specific information architecture and does not inherit the Command Center Intelligence Brief.

## Typography

Primary font remains Inter.

The milestone changes hierarchy rather than font family:

- Intelligence headline: approximately 22–26px;
- primary metrics: approximately 24–32px depending on context;
- operator supporting copy: generally 10.5–12.5px;
- structured driver rows replace paragraph-heavy explanations;
- tabular numerals remain preferred for metrics.

## Contract

`config/ui_v2_presentation_contract.json` is at **1.6** for this milestone.

Hard presentation concepts include:

- Command Center is intelligence-first;
- interpretation precedes detailed metric inspection;
- structured drivers are preferred over long narrative bullets;
- Smart Issue / review-option evidence boundaries must remain visible in meaning;
- insufficient evidence produces explicit no-action / no-priority copy;
- modernization may reduce visual noise but may not relax safety or evidence boundaries.

## Semantic safety QA

The final batch deliberately replaces brittle copy-marker QA with state-based validation.

Native acceptance now checks embedded machine state including:

- `mode = PREPRODUCTION_OBSERVE_ONLY`;
- `platformMutationAllowed = false`;
- `productionWritesEnabled = false`;
- `actionRecommendationsEnabled = false`;
- `automaticAlertsEnabled = false`;
- `operationalDiagnosisEnabled = false`;
- `causalClaimsEnabled = false`.

It also rejects forbidden execution directives such as bid, budget, price, promotion, campaign-pause, listing-publish or automatic-customer-contact mutations.

This allows operator-facing language to remain natural Vietnamese without weakening the actual safety gate.

## Final lineage

Validated Native patch:

`native-production-shadow-mode-v32`

Compatibility patch:

`v2-production-shadow-mode-v17`

Final GitHub Actions validation:

- workflow: **Multi-Shop Core CI & Staging QA**;
- run: **#418**;
- run id: `36217309491`;
- commit: `697ce458e022a3c7c1bc99a512fecf8c74f87cea`;
- core-tests: **PASS**;
- full staging: **PASS**;
- Native QA failed checks: **0**.

Final fingerprints:

- semantic: `c25b7cfe67c6d8d477e6e8cd65a466eb3c74ca4f97a3c500b0e9320f1223b321`;
- payload: `b932e231bde32417500ffd6b28ffd18918630598d67f17c9b44dd4f3c70715fa`;
- Native: `996701f4d3aa54175cfb47308991e1b5edce46d05f5aa260723649a7ceaa9088`;
- Native HTML SHA256: `f4b7cdcea9df5dffa5f8cf5156af2a580ea969b69556d1afc0f904590953567e`.

## Human visual validation

Run #418 was rendered and reviewed with real September payload state for:

- Portfolio / Toàn hệ thống;
- SYT+;
- Mall;
- Compare;
- dark mode;
- period selectors and KPI population.

Human review result: **PASS — no blocking layout, hierarchy, clipping or operator-copy defect found in the reviewed desktop states.**

The Intelligence Brief correctly updates by scope while Compare remains on its own destination architecture.

## Production safety

This milestone:

- modifies only Native PREPRODUCTION output;
- keeps `automation/command_center_v2_template.html` read-only;
- does not write the production Data Mart;
- does not modify production `index.html`;
- does not deploy production;
- does not enable automatic alerts;
- does not enable automatic actions;
- does not authorize production cutover.

Run #418 manifest explicitly records:

- `productionCutoverAuthorized=false`;
- `productionDataMartWritten=false`;
- `productionDeploymentPerformed=false`;
- `productionIndexModified=false`;
- `productionV2TemplateModified=false`.

## Acceptance criteria — final result

- canonical repository tests: **PASS**;
- full staging: **PASS**;
- Native artifact QA: **PASS**;
- `Tóm tắt vận hành` in Portfolio and Shop scopes: **PASS**;
- Compare excluded from Command Center-only Intelligence Brief: **PASS**;
- period switching / metric population: **PASS**;
- evidence-bound Smart Issue / review state: **PASS**;
- semantic no-mutation safety QA: **PASS**;
- forbidden automatic directives absent: **PASS**;
- production safety flags false: **PASS**;
- light/dark desktop human visual review: **PASS**.

## Rollout rule

This milestone validates the pattern for Command Center. It does **not** mean Product / Ads / Customer pages should copy this exact layout.

Future destinations should inherit the same principle — **interpretation before inspection** — while adapting their intelligence surfaces to the domain-specific questions operators need answered.

## Next boundary

The Intelligence-first visual batch is complete.

The next project decision should return to the production-readiness roadmap. Production activation remains a separate explicit human decision and must not be inferred from this visual milestone.
