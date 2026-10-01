# Checkpoint — Native V2 Extension Composition v1

Date: **2026-09-30**  
State: **VALIDATED / LOCKED — 100%**  
Environment: **PREPRODUCTION**

## Completion decision

Native V2 Extension Composition v1 satisfies both **Functional DONE** and **Maintainability DONE** for its declared scope.

The canonical Native build no longer depends on recursively calling the previous nested presentation-wrapper builders. It now uses one deterministic ordered composition plan with one temporary base-Native compatibility bridge and explicit artifact lineage.

## Functional DONE evidence

- Canonical composer: `automation/modules/ui_v2_extension_composition_canonical.py`.
- Canonical runner: `automation/multi_shop_native_v2_runner.py`.
- Existing Product/Ads/Diagnosis/Persistence/Candidate/Registry artifact validators reused unchanged.
- Real payload replay run **#2 / 36703100672**: SUCCESS.
- Full PREPRODUCTION staging run **#570 / 36703196976**, head `52e9efba825642d10734e2166ac696a638e70e24`: SUCCESS end-to-end.
- Architecture & Contract Guard on the staging head: SUCCESS.
- Native V2 QA: **33 checks, 0 failures**.
- Ads Intelligence QA: PASS, top-level `failedCheckCount = 0`; all Context Qualification / Dynamic Diagnosis / Persistence / Candidate / Registry / Operator Workflow sub-gates report zero failures.

## Maintainability DONE evidence

- explicit extension order and stable IDs;
- deterministic lineage markers embedded in the final HTML;
- compatibility bridge count machine-visible and fixed at `1`;
- canonical summary asserts `legacy_nested_wrapper_build_path_used = false`;
- regression tests cover provenance, one-boundary architecture and raw-signal leakage;
- dedicated replay workflow now triggers on Native runner/module/test/template changes;
- replay uses a real validated UI Payload artifact rather than only synthetic fixtures;
- old wrapper modules remain compatibility/reference surfaces instead of being mass-deleted during the migration;
- full design/change rules documented in `docs/native-v2-extension-composition-v1.md`.

## Locked upstream fingerprints after run #570

| Layer | Fingerprint |
| --- | --- |
| September Semantic | `38e12e9552fd81571b85e37f977bfbeb8feda9a1d3b7e301663f56fa28cad7f6` |
| Business Context | `d4fef77fe3f18d2e9b91ea611dbcd755372fff1e9fc5e29739fb851b9a0a8cd0` |
| Base Ads | `a1faa4cf2e4c9403452fb47d62504a516b4a8d2eaedff7ebe78dcf5a2220f79b` |
| Context Qualification | `23cb81876a955fca122ab6d2ad55711682972a6ddc50afc20de9ec77c5157dfc` |
| Dynamic Diagnosis | `4daab89d26c877e858c39b462b6599234b14c39a18e37f5ce373b9e1aae9b4a2` |
| Diagnosis Persistence | `4b4cf0fb8fea41db6e1b7c6e470347bc0c212b554774ec6068e743359513dabd` |
| Smart Issue Candidate | `2373ef01716950719a6bc16be046e7bb456cde74d5f4b436c05cd5605a6a05e7` |
| Smart Issue Registry / final Ads | `234cfc09d01a2418384bf23ea7dabbaf641f92e26cf8d2765ac32e12f50b1448` |
| Operator Review Workflow | `314921dc35393c169454559b7378effbfb1d2f0c35b2b5b82f663bcc97c4bc9a` |
| Registry review ledger | `f294114bb005151b50bdd96f4bbd985d365edbaba01afc8d27218dc02b3739b8` |
| Operator ledger concurrency | `a5a99966fbd29c99d0264b89772e768401f9e8d0c7707c27d2e872b5d650970d` |

No locked upstream identity changed as a consequence of the presentation refactor.

## Native artifact audit

Run #570 Native summary:

- `native_extension_composition_ready = true`
- `native_extension_composition_version = native-v2-extension-composition-v1`
- 10 unique extension IDs
- `native_extension_compatibility_bridge_count = 1`
- `native_extension_lineage_ready = true`
- `legacy_nested_wrapper_build_path_used = false`
- `native_patch_version = native-ads-financial-v38`
- source Semantic fingerprint = locked September fingerprint
- Native build fingerprint = `37db07c8115cf4fa49b9ddbed62ab812b21ced953919663af8fc8d15a64d4bdc`

The final HTML contains each locked diagnosis/persistence/candidate/registry explanatory sentence exactly once. It contains the composition lineage marker and does not contain the forbidden raw Ads signal binding or automatic Smart Issue promotion copy.

## Durable storage / OAuth audit

The refreshed `GOOGLE_DRIVE_OAUTH_JSON` credential was exercised by run #570 rather than accepted on configuration alone.

Processed v2 Drive publish:

- auth mode: `user_oauth`
- storage: `PREPRODUCTION`
- SYT+: `NOOP`, same build fingerprint
- Mall: `NOOP`, same build fingerprint
- production Data Mart written: `false`

Semantic v2 Drive publish:

- auth mode: `user_oauth`
- storage: `PREPRODUCTION`
- result: `NOOP`, same Semantic fingerprint
- production Data Mart written: `false`

OAuth app Publishing status remains `Testing`; longer-term credential/domain hardening is intentionally separate operational debt.

## Safety audit

Native safety:

- `productionCutoverAuthorized = false`
- `productionDataMartWritten = false`
- `productionDeploymentPerformed = false`
- `productionIndexModified = false`
- `productionV2TemplateModified = false`

Ads/Smart Issue safety:

- automatic actions: disabled
- automatic alerts: disabled
- automatic promotion: disabled
- automatic issue transition/resolution: disabled
- platform mutation: disabled
- causal claims: disabled
- explicit human review remains required

## Failure history retained as regression evidence

The milestone was not marked complete after superficial workflow success. Validation exposed and fixed:

1. a recursion bug in the initial bundle compatibility bridge;
2. staging protocol misuse where a workflow-level success had skipped the staging job;
3. expired/revoked Drive OAuth credentials, which were refreshed rather than bypassed;
4. missing Product v36 provenance in the composed artifact, caught by the unchanged locked validator;
5. replay workflow path coverage that originally failed to trigger on composer/runner changes.

Each issue was corrected without weakening safety or artifact validators.

## Deferred by design

- remove the final one compatibility bridge by adding first-class hooks to the base Native builder;
- Google OAuth Production/domain hardening;
- Smart Issue Review Console;
- Alert Policy;
- production cutover and rollback drill;
- retirement of old wrapper/reference surfaces only after downstream migrations no longer require them.

## Next milestone

**Smart Issue Review Console / Command Center Workflow UI v1**.

It must consume the locked Registry + Operator Review Workflow surfaces through the new canonical composition boundary. Static presentation must not invent direct mutation capability; any real write interaction requires an explicit authenticated operator control plane or another auditable command path.
