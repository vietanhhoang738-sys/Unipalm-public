# Unipalm Operational State

`ops/` contains mutable human/operator control state that is **not** a normative business contract.

Use this directory for explicit review ledgers, staging requests, cutover requests and similar operator-controlled state.

Rules:

- business rules and schemas belong in `config/*_contract.json`;
- shop/storage/source registries belong in `config/`;
- new mutable operational state belongs in `ops/`;
- a UI or intelligence module must not write operational state directly unless an explicit governed command path authorizes it;
- operator state must be append-only or concurrency-protected where required;
- moving active legacy production state requires an explicit cutover migration and is not implied by this directory.

Current canonical files:

- `staging_request.json` — canonical PREPRODUCTION staging-request state;
- `ads_smart_issue_review_events.json` — append-only human Smart Issue review ledger and active runtime source.

## Transitional compatibility

`.github/workflows/multi-shop-staging.yml` still reads `config/staging_request.json` on `[staging]` pushes. During the maintainability migration, `config/staging_request.json` is therefore a compatibility mirror of `ops/staging_request.json` and must be kept byte-equivalent when a push-triggered staging request is changed.

This duplication is explicit migration debt, not two independent sources of truth. It should be removed when the staging workflow is decomposed/migrated in a dedicated orchestration batch; do not combine that workflow rewrite with unrelated business-rule changes.

The old `config/ads_smart_issue_review_events.json` compatibility ledger has been removed. Smart Issue review state now has one active repository source: `ops/ads_smart_issue_review_events.json`.

## Legacy exception

- `automation/pipeline_state.json` remains in place because the current production workflow actively commits it. It must be migrated only as part of an approved production cutover.
