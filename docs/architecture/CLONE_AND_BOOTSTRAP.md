# Clone & Bootstrap Architecture

Goal: make Unipalm reusable without copying hidden assumptions from the current shops or legacy production stack.

This is an architecture guide, not yet a production clone command.

## 1. What should be reusable core

A cloned instance should normally reuse:
- Shop Registry engine and validation;
- Source Schema Guard framework;
- Staging / Processed / Semantic engines;
- atomic persistence patterns;
- Historical / Context framework;
- Product and Ads Intelligence framework;
- Diagnosis / Persistence / Smart Issue lifecycle framework;
- Operator review mechanism;
- canonical UI Payload pattern;
- shared Native V2 design/language foundation;
- architecture validation and tests.

These are `CORE` or `CORE_PLUS_*` roles in `config/system_module_registry.json`.

## 2. What is instance-specific

A new seller/brand must supply its own:
- enabled shops and platform-native IDs;
- RAW roots/source locations;
- storage namespace IDs;
- credentials/secrets;
- lifecycle metadata;
- reviewed source-schema fingerprints where exports differ;
- Business Context evidence appropriate to its platform/market;
- approved branding/presentation variables where the shared design contract permits them.

Current SYT+/Mall identities are examples of instance config, not reusable code assumptions.

## 3. What must NOT be cloned

Do not clone as the future architecture:
- the legacy single-shop production Apps Script/process stack;
- legacy Control Center state shape;
- current production Sheet IDs;
- current Vercel/environment secrets;
- historical run IDs/fingerprints;
- recovery tools designed only for the legacy mart;
- current operator review events.

Legacy production components have `DO_NOT_CLONE` replication roles.

## 4. Target bootstrap flow

For a future standardized instance:

```text
Unipalm Core
   + instance shop registry
   + source/storage registry
   + secret injection
   + reviewed schema/context configuration
          |
          v
Architecture validation
          |
          v
Synthetic N-shop tests
          |
          v
Read-only staging
          |
          v
Processed/Semantic PREPRODUCTION
          |
          v
Intelligence + UI PREPRODUCTION
          |
          v
Human review / production cutover plan
```

## 5. Resource/secrets rule

Secrets must remain external to the repository. Documentation may state the required environment variable name and expected shape, but never commit credentials.

Storage/resource identifiers may remain in an instance registry where they are not secrets, but reusable core code must not own them.

A future standard clone template should eventually provide example/schema files rather than copying current resource IDs.

## 6. Shop onboarding standard

A new shop should primarily require:
1. add Shop Registry entry;
2. supply valid RAW root(s);
3. validate source schema against registry;
4. run staging in isolation;
5. pass Processed/Semantic all-shop rules;
6. validate lifecycle/history boundaries;
7. verify Product/Ads Intelligence capability states;
8. validate UI payload/Native V2;
9. explicitly approve production inclusion.

Adding a third/fourth shop must not require editing generic business algorithms simply to enumerate the shop.

## 7. Current cloneability gaps to close before project 100%

- active production workflow still contains current-instance resource IDs;
- legacy production/control state is still single-shop oriented;
- final production deployment architecture has not cut over to N-shop core;
- mutable operational state migration is still being standardized;
- UI composition still has some exact-string patch coupling;
- branch/ruleset protection is not currently enforcing CI before direct pushes.

These are explicit roadmap items, not hidden assumptions.

## 8. Clone readiness definition

Unipalm is clone-ready when a new maintainer can provision a new non-production instance by replacing only documented instance configuration/secrets/evidence, without forking core algorithms or editing legacy single-shop code.
