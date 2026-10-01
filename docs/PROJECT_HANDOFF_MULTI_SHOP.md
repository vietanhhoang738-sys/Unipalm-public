# PROJECT HANDOFF — Unipalm Multi-Shop Command Center

Last updated: 2026-09-26  
Repository: `vietanhhoang738-sys/Unipalm`  
Development branch: `multi-shop-catalog-resolver`


Current canonical PREPRODUCTION UI V2 baseline:
- GitHub Actions run `35988078609` (#216) — PASS
- native patch: `native-sidebar-rail-v13`
- native fingerprint: `bd53638b958c5fb2abc216ee1c39a8dd9c9d158341049c0bd5e17512cab70a4d`
- UI Payload fingerprint: `c2e8bf92ea1ef69a222a78f03de51e52d9b7a80f6f57b4217fe13434ddca6f68`
- Semantic fingerprint: `3a77d886b5350dda2ea842367e53b6727ecc1073dce0b33f25df0c4f6ed5c62c`
- reviewed Drive baseline: `ui_native_v2_baseline_2026_09_run_216.zip`
- Language System + Product Naming System are permanent hard contracts; see Section 27 and `docs/ui-v2-language-product-naming-system.md`.
- Shared Design Language + destination architecture are also a hard contract; see `docs/ui-v2-destination-architecture.md`.
- production V2/Data Mart/index/deployment remain untouched.


Latest validated cleanup/data-chain checkpoint:
- GitHub Actions run `35992225052` (#244) — PASS
- Semantic contract: `1.2`
- Semantic fingerprint: `fb862a21b281d3b33611e35c060d5dfbbe19a3bdbb455fc9f9c034b755a3c162`
- UI Payload contract: `1.2`
- UI Payload fingerprint: `58f054911b139278ee2cf0350e76746bb77dc3e8f22c4a578721b0ca03af4f78`
- Native fingerprint: `53c3ebae2160567f6ba6c4d9a3983eb7b8d4ef49127fb08698e3d122ccaeb44c`
- Native QA: 30/30 PASS
- semantic partition: 8 marts + manifest + QA; redundant monthly marts are no longer persisted
- cleanup audit: `docs/system-cleanup-audit-2026-09.md`
- #216 remains the accepted human-reviewed visual/interaction baseline; #244 is the latest technical cleanup checkpoint.

Latest validated Portfolio + Shop semantic checkpoint:
- GitHub Actions run `36088664004` (#252) — **PASS**
- branch commit: `7cc6bd0473a480a7f6d5920d19fcb7843bcc9aac`
- UI Payload contract: `1.4`
- UI Payload fingerprint: `76c8aacccf2a90a527a0e4e909b848780b54ad59d791a17eab1a72db1241c2a3`
- Semantic fingerprint: `fb862a21b281d3b33611e35c060d5dfbbe19a3bdbb455fc9f9c034b755a3c162`
- Native patch: `native-shop-semantic-v15`
- V2 compatibility patch: `v2-shop-semantic-v5`
- Native fingerprint: `f3ff94404198cb8abb65e615ce41b7f52a4d4e7cc5889d2242f987ace807684b`
- source production V2 SHA256: `9540f23b4d9537441e3bd4cdeafd15747ab4280a87a0130d223984009d99c952`
- Portfolio semantic audit: `docs/ui-v2-portfolio-semantic-audit.md`
- Shop semantic audit: `docs/ui-v2-shop-semantic-audit.md`
- #216 remains the human-reviewed visual/interaction baseline. #252 is the latest semantic/data-binding validation checkpoint; it does not supersede the approved visual design.
- production V2/Data Mart/index/deployment remain untouched.

Latest validated Historical Intelligence Foundation checkpoint:
- GitHub Actions run `36090296993` (#259) — **PASS**
- branch runtime checkpoint: `2687b2d4298f97e09718aa7d98b97b75fc6c475d`
- Historical Intelligence contract: `1.0`
- Historical fingerprint: `fc6418b091497ae7c5a9560d4ea9348b50c3f13a481b7520950082455e92a171`
- trusted Semantic months: `2026-09` only
- Processed v2 READY months: `2026-09` only for both current shops
- Portfolio history status: `INSUFFICIENT_HISTORY`
- Shop history status: `INSUFFICIENT_HISTORY` for both current shops
- six-month intelligence / historical alerts / diagnosis: **disabled**
- history artifact: `multi-shop-history-2026-09`, artifact ID `10845416876`
- history artifact digest: `sha256:f3ef6091f095ce744078cc32cc2ed269cc0e9d1ca92a1f3460e93cdcc83c7e5a`
- #216 remains the accepted human-reviewed visual/interaction baseline; #259 is the historical-intelligence foundation checkpoint.
- production V2/Data Mart/index/deployment remain untouched.

Latest validated Historical Backfill v1 checkpoint:
- GitHub Actions run `36098551468` (#276) — **PASS**
- runtime branch checkpoint: `d5d80a532c99e9884352a8df53ce43e7e42b4d82`
- trusted Semantic months: `2026-07, 2026-08, 2026-09`
- Processed READY months: `2026-07, 2026-08, 2026-09` for both current shops
- Historical fingerprint: `12f6667a045535ea7b17616f45acfc12b0157fa572d4ee0c14f662ab25ea66fa`
- July Semantic fingerprint: `70ddd954833cb413b8127cbe51b4ce801c1a6766ffe8d20ac34d0ca15c2f3571`
- August Semantic fingerprint: `39bd92c7aa44794a2f823511e67a58e26e09a679c38d5bc0412ddf75c8951351`
- September Semantic fingerprint: `c25b7cfe67c6d8d477e6e8cd65a466eb3c74ca4f97a3c500b0e9320f1223b321`
- current September UI Payload fingerprint: `4438f3026f0bd0e8a3b61800262d5222b1ee6b0590f002778ebdc2d3cfd3a68d`
- current September Native fingerprint: `3e701fa64252e3b9c8d440580387e18fcd11e33bc59fce1baa43b01494e9870e`
- August idempotency run `36098360904` (#275): Processed **NOOP** both shops + Semantic **NOOP**
- Portfolio history: 55 trusted days (`2026-07-20..2026-09-17`), 0 complete months
- Portfolio / both Shop history status: `INSUFFICIENT_HISTORY`
- READY factual comparators: Previous Day, Previous 7D, previous-month matched MTD, Same Weekday
- Same Day-of-Month: still `INSUFFICIENT_HISTORY`
- 6M intelligence / historical alerts / diagnosis: **disabled**
- audit: `docs/historical-backfill-v1.md`
- #216 remains the accepted human-reviewed visual/interaction baseline; #276 is the trusted-history backfill checkpoint.
- production V2/Data Mart/index/deployment remain untouched.

Latest validated Historical Comparator Binding checkpoint:
- GitHub Actions run `36111013628` (#291) — **PASS**
- runtime branch checkpoint: `7973cdd0d383a85f9a5cb8a54cf5253a12d7331d`
- Historical Intelligence contract: `1.1`
- Historical fingerprint: `8c61ea948f5c175f9dcaf9cbcd630b536b5f68b71bf2a2e74ce45d46373163da`
- UI Payload contract: `1.5`
- UI Payload fingerprint: `0f168586b6e4a136e6914c5e9c7760f8d03137a270d546a9682a70964d59aca5`
- Native patch: `native-historical-comparator-v16`
- V2 compatibility patch: `v2-historical-comparator-v6`
- Native fingerprint: `52a881b192bd51f5d2da849b5534b7c0c612e788fb339e3b3b2c6715ab97bcb7`
- Semantic fingerprint remains `c25b7cfe67c6d8d477e6e8cd65a466eb3c74ca4f97a3c500b0e9320f1223b321`
- Processed and Semantic Drive writes were **NOOP**, proving no business-fact rewrite.
- Mall history origin: `SHOP_LAUNCH`; observed trusted lifecycle boundary `2026-07-20`; dates before that are **not missing data**.
- Portfolio history origin: `ALL_ENABLED_SHOPS_ACTIVE`; Portfolio begins when all enabled shops are active.
- Portfolio/Mall `INSUFFICIENT_HISTORY` now means **history depth is still short**, not that pre-launch data is missing.
- READY factual comparators bound into Command Center: Previous Day, Previous 7D, previous-month matched MTD, Same Weekday.
- historical anomaly / alerts / diagnosis remain **disabled**.
- audit: `docs/historical-comparator-binding-v1.md`
- #216 remains the accepted human-reviewed visual/interaction baseline; #291 is the Historical Comparator Binding checkpoint.
- production V2/Data Mart/index/deployment remain untouched.

Latest validated Business Context Calendar Foundation checkpoint:
- GitHub Actions run `36113962295` (#313) — **PASS**
- runtime checkpoint: `a9c981d010465cd67d41c6df9e5d13fdca951a5c`
- Business Context contract: `1.1`
- Calendar version: `2026.09.25`
- Context fingerprint: `d4fef77fe3f18d2e9b91ea611dbcd755372fff1e9fc5e29739fb851b9a0a8cd0`
- reviewed sources: 12
- selected events: 17
- context-day rows: 157
- exact-date matching-eligible events: 15
- Historical Intelligence contract: `1.2`
- Historical fingerprint: `6e700e748b00991625e77abb440188854e1675033038697e89b7f74a3d3e0cd4`
- UI Payload contract: `1.6`
- UI Payload fingerprint: `e56dbc7dcb442418007e042c42c1e1465dffe382deb4f11bfab0daafbf84ed25`
- Native fingerprint: `d40893b865ad63fdaa0f850c98a662f89e837e18e657a1933abd0b3985965c2f`
- Processed both shops: **NOOP**
- Semantic: **NOOP**
- Context source hierarchy: Platform Seller Official → Platform Consumer Official → Government Official → Industry Analytics.
- Exact campaign matching is allowed only from official platform/government tiers; Metric is market-season context only.
- search snippets are forbidden as canonical source evidence.
- image-only official calendars remain reference-only until dates are readable/verified.
- monthly freshness guard blocks a future-month run until calendar sources are reviewed for that month.
- Context is platform/scope aware: TikTok events do not contaminate current Shopee-only shop scopes.
- `contextMatchedBaseline=false`; historical alerts/diagnosis remain disabled.
- audit: `docs/business-context-calendar-foundation-v1.md`
- #216 remains the accepted human-reviewed visual/interaction baseline; #313 is the Business Context Calendar Foundation checkpoint.
- production V2/Data Mart/index/deployment remain untouched.

Latest validated Context-Aware Comparator Qualification checkpoint:
- GitHub Actions run `36115233375` (#324) — **PASS**
- runtime checkpoint: `9b0b34aee7fbef0b8db91e50fdec8f9bd722d53c`
- Historical Intelligence contract: `1.3`
- Historical fingerprint: `4e1aa6008022518566811aea96318ccf033cdcff4aa03765986e04473c4a385d`
- UI Payload contract: `1.7`
- UI Payload fingerprint: `725e39867e7525d9c9f978a0a2aeb3e5b3e19ebbbbb674c56083c5e4b7d6d262`
- Native patch: `native-context-qualified-v17`
- V2 compatibility patch: `v2-context-qualified-v7`
- Native fingerprint: `916151c505b792b5ac54871d53a49be055a178c0ef4de0e1d4294bd3cd3ad3fb`
- Business Context fingerprint unchanged: `d4fef77fe3f18d2e9b91ea611dbcd755372fff1e9fc5e29739fb851b9a0a8cd0`
- Semantic fingerprint unchanged: `c25b7cfe67c6d8d477e6e8cd65a466eb3c74ca4f97a3c500b0e9320f1223b321`
- Processed both shops: **NOOP**
- Semantic: **NOOP**
- allowed qualification statuses: `CONTEXT_COMPATIBLE / CONTEXT_DIFFERENT / CONTEXT_UNKNOWN`
- qualification uses only exact `matching_eligible=true` official context; Metric/broad seasonal context cannot decide compatibility.
- Portfolio/SYT+ Previous Day: `CONTEXT_COMPATIBLE`
- Portfolio/SYT+ Previous 7D and matched MTD: `CONTEXT_DIFFERENT`
- Mall Previous Day: `CONTEXT_UNKNOWN`
- context-matched baseline filtering remains **OFF**
- causal claims / anomaly / alerts / diagnosis remain **OFF**
- audit: `docs/context-aware-comparator-qualification-v1.md`
- #216 remains the accepted human-reviewed visual/interaction baseline; #324 is the Context-Aware Comparator Qualification checkpoint.
- production V2/Data Mart/index/deployment remain untouched.

Latest validated Context-Matched Historical Baseline checkpoint:
- GitHub Actions run `36116620804` (#334) — **PASS**
- runtime checkpoint: `e2229c602ee134187c34bb6e7f84664d2ae242d8`
- Historical Intelligence contract: `1.4`
- Historical fingerprint: `915074583bde8db6482596b6c85dc9ab6417c58e10935bff1c099e160b191e4a`
- UI Payload contract: `1.8`
- UI Payload fingerprint: `dfcd2d7509b8cdf044da86913ef7919c69d930b03a916f810d9bf5daa9c42439`
- Native patch: `native-context-matched-baseline-v18`
- V2 compatibility patch: `v2-context-matched-baseline-v8`
- Native fingerprint: `7edcf9d683e2a03ae0a9f8cb2dd1312703ff8972e66844a6e527ec1dcf3aa6f9`
- Business Context fingerprint unchanged: `d4fef77fe3f18d2e9b91ea611dbcd755372fff1e9fc5e29739fb851b9a0a8cd0`
- Semantic fingerprint unchanged: `c25b7cfe67c6d8d477e6e8cd65a466eb3c74ca4f97a3c500b0e9320f1223b321`
- Processed both shops: **NOOP**
- Semantic: **NOOP**
- original all-history Same Weekday baseline remains preserved.
- new `contextMatchedBaseline` uses only `CONTEXT_COMPATIBLE` samples.
- current real result: Portfolio/SYT+/Mall all have `INSUFFICIENT_CONTEXT_MATCHED_HISTORY` for Same Weekday because compatible sample count is 0/4.
- no matched statistics are emitted while insufficient; silent fallback is forbidden.
- global `contextMatchedBaseline=false` correctly reflects that no current scope has a READY matched baseline.
- anomaly / alerts / diagnosis / causal claims remain **OFF**.
- audit: `docs/context-matched-historical-baseline-v1.md`
- #216 remains the accepted human-reviewed visual/interaction baseline; #334 is the Context-Matched Historical Baseline checkpoint.
- production V2/Data Mart/index/deployment remain untouched.

Latest validated Anomaly Eligibility Guardrails checkpoint:
- GitHub Actions run `36118612445` (#349) — **PASS**
- runtime checkpoint: `48f10f4c089625368750625c38fc2d56d815ec24`
- Historical Intelligence contract: `1.5`
- Historical fingerprint: `2393eb36a7d7c31589aca8385d36b7931e8c996cb857a87016a8dbd70526c4dd`
- UI Payload contract: `1.9`
- UI Payload fingerprint: `976bb49da517cf3d8fffde2813394ea073d2e38154dc5d42f5da8cda4d1b3a0d`
- Native patch: `native-anomaly-eligibility-v19`
- V2 compatibility patch: `v2-anomaly-eligibility-v9`
- Native fingerprint: `230462a060cc99740f0a24081d46531e1ff51fa606c99eedbfa9d764898c1a92`
- Business Context fingerprint unchanged: `d4fef77fe3f18d2e9b91ea611dbcd755372fff1e9fc5e29739fb851b9a0a8cd0`
- Semantic fingerprint unchanged: `c25b7cfe67c6d8d477e6e8cd65a466eb3c74ca4f97a3c500b0e9320f1223b321`
- Processed both shops: **NOOP**
- Semantic: **NOOP**
- `anomalyEligibilityGuardrails=true`
- `anomalyDetection=false`
- current real result: Portfolio, SYT+ and Mall all `ANOMALY_BLOCKED`; 0 eligible comparators and 0 eligible KPI checks.
- lifecycle-specific block reasons are preserved:
  - Portfolio: `PORTFOLIO_LIFECYCLE_HISTORY_TOO_SHORT`
  - SYT+: `INSUFFICIENT_HISTORY_DEPTH`
  - Mall: `SHOP_LIFECYCLE_HISTORY_TOO_SHORT`
- sample-based anomaly evaluation additionally requires a READY context-matched baseline; current Same Weekday matched samples remain 0/4.
- window comparators remain factual-only and carry `NO_STATISTICAL_BASELINE_METHOD`.
- anomaly severity / alerts / diagnosis / causal claims remain **OFF**.
- audit: `docs/anomaly-eligibility-guardrails-v1.md`
- #216 remains the accepted human-reviewed visual/interaction baseline; #349 is the Anomaly Eligibility Guardrails checkpoint.
- production V2/Data Mart/index/deployment remain untouched.

Latest validated Anomaly Detection Foundation checkpoint:
- GitHub Actions run `36120626467` (#360) — **PASS**
- runtime checkpoint: `83b6f3761f5fb4acb937b05a8f65a2314a93bce8`
- Historical Intelligence contract: `1.6`
- Historical fingerprint: `e384f879a271bfdef205b68d5be7f131f937e311f6331370a6ed4586cea1adb2`
- UI Payload contract: `1.10`
- UI Payload fingerprint: `3c813f82d87dd53214a7d311b9f639db6ce378893f4423f5ac7ac68a2dd12f85`
- Native patch: `native-anomaly-detection-foundation-v20`
- V2 compatibility patch: `v2-anomaly-detection-foundation-v10`
- Native fingerprint: `2cf8c07762c0c0b1b89ca422de17eae302292705a82e794b09f8778e636d2c4b`
- Business Context fingerprint unchanged: `d4fef77fe3f18d2e9b91ea611dbcd755372fff1e9fc5e29739fb851b9a0a8cd0`
- Semantic fingerprint unchanged: `c25b7cfe67c6d8d477e6e8cd65a466eb3c74ca4f97a3c500b0e9320f1223b321`
- Processed both shops: **NOOP**
- Semantic: **NOOP**
- detector method: `MODIFIED_Z_SCORE_MAD`
- absolute modified-Z threshold: `3.5`
- detector states: `NORMAL / DEVIATION_CANDIDATE / NOT_EVALUATED`
- detector also requires KPI-specific minimum effect size and directionality.
- synthetic tests prove NORMAL, DEVIATION_CANDIDATE and blocked/no-score paths.
- current real result: Portfolio, SYT+ and Mall all `NOT_EVALUATED`; 0 evaluated KPI checks and 0 deviation candidates because eligibility is currently blocked.
- blocked metrics publish no score.
- `anomalyDetectionFoundation=true` but operational `anomalyDetection=false`.
- severity / alerts / diagnosis / causal claims remain **OFF**.
- audit: `docs/anomaly-detection-foundation-v1.md`
- **Intelligence Foundation is now complete.**
- #216 remains the accepted human-reviewed visual/interaction baseline; #360 is the Intelligence Foundation checkpoint.
- production V2/Data Mart/index/deployment remain untouched.

Latest validated Anomaly Severity & Confidence checkpoint:
- GitHub Actions run `36122612645` (#371) — **PASS**
- runtime checkpoint: `f656f9c73eddc54aa4c890d8a2e89c0ee45cac40`
- Historical Intelligence contract: `1.7`
- Historical fingerprint: `4b910bb2a6b3453e28aa1b4b59afe622661acd2ad7c50ffc7cd02127cddd8c76`
- UI Payload contract: `1.11`
- UI Payload fingerprint: `07ed7e8999baf61154a2eb1239c95d6ff128347fc770589976ccfedc82f1086a`
- Native patch: `native-anomaly-severity-confidence-v21`
- V2 compatibility patch: `v2-anomaly-severity-confidence-v11`
- Native fingerprint: `1294f3832054dd6e36f3e6a5c18455fcc75740e172be1be4c64f8273a30d8697`
- Business Context fingerprint unchanged: `d4fef77fe3f18d2e9b91ea611dbcd755372fff1e9fc5e29739fb851b9a0a8cd0`
- Semantic fingerprint unchanged: `c25b7cfe67c6d8d477e6e8cd65a466eb3c74ca4f97a3c500b0e9320f1223b321`
- Processed both shops: **NOOP**
- Semantic: **NOOP**
- candidate-only severity/confidence evidence is now available in PREPRODUCTION.
- severity measures statistical + relative signal magnitude, **not business impact**.
- confidence measures matched-sample depth + exact context lineage + history readiness + robust-scale validity.
- synthetic candidate path validates HIGH severity + HIGH confidence.
- NORMAL / NOT_EVALUATED paths remain `NOT_ASSESSED` with no score leak.
- current real result: Portfolio, SYT+ and Mall all `NOT_ASSESSED`; 0 assessed candidates, 60 not-assessed KPI checks per scope.
- `anomalySeverityConfidence=true` while operational `anomalySeverity=false`.
- alerts / diagnosis / causal claims remain **OFF**.
- audit: `docs/anomaly-severity-confidence-v1.md`
- #216 remains the accepted human-reviewed visual/interaction baseline; #371 is the Anomaly Severity & Confidence checkpoint.
- production V2/Data Mart/index/deployment remain untouched.

Latest validated Diagnosis / Driver Attribution Foundation checkpoint:
- GitHub Actions run `36124417830` (#381) — **PASS**
- runtime checkpoint: `c46734268ab85983e4e1bd28958df045414295e8`
- Historical Intelligence contract: `1.8`
- Historical fingerprint: `8dd1ff703235ed18767bf9ff669c717c994e66b91f862fee312eef0ff4cd1e41`
- UI Payload contract: `1.12`
- UI Payload fingerprint: `67cfd56615654c02b1410be2ddf5f64058df6cf2d8bee7d155e4d2af48be985d`
- Native patch: `native-driver-attribution-foundation-v22`
- V2 compatibility patch: `v2-driver-attribution-foundation-v12`
- Native fingerprint: `a9bb0395baf99c0c4e82241b72c3d1bcfc7a0513fabd51ccc58dbcafbe46d851`
- Business Context fingerprint unchanged: `d4fef77fe3f18d2e9b91ea611dbcd755372fff1e9fc5e29739fb851b9a0a8cd0`
- Semantic fingerprint unchanged: `c25b7cfe67c6d8d477e6e8cd65a466eb3c74ca4f97a3c500b0e9320f1223b321`
- Processed both shops: **NOOP**
- Semantic: **NOOP**
- attribution states: `ATTRIBUTED / ASSOCIATION_ONLY / NOT_DIAGNOSED`
- attribution runs only on sufficiently confident `DEVIATION_CANDIDATE` evidence.
- exact business identities use `EXACT_SHAPLEY_ON_BUSINESS_IDENTITY`.
- supported identity targets: GMV, Orders, ROAS, Net Sales After Cancel, Total Platform Cost Ratio.
- unsupported candidate identities remain `ASSOCIATION_ONLY`; no contribution is fabricated.
- identity contributions and co-moving associations explicitly keep causal claim = false.
- baseline identity alignment guard blocks attribution when independent medians do not align safely.
- synthetic GMV case proves AOV can be the top factual identity contributor while AOV itself remains association-only.
- current real result: Portfolio, SYT+ and Mall all `NOT_DIAGNOSED`; 0 attributed / 0 association-only / 60 not-diagnosed KPI checks per scope.
- `driverAttributionFoundation=true` while operational `diagnosis=false`.
- alerts / causal claims remain **OFF**.
- audit: `docs/diagnosis-driver-attribution-foundation-v1.md`
- #216 remains the accepted human-reviewed visual/interaction baseline; #381 is the Diagnosis / Driver Attribution checkpoint.
- production V2/Data Mart/index/deployment remain untouched.

Latest validated Smart Issues Foundation checkpoint:
- GitHub Actions run `36126435907` (#395) — **PASS**
- runtime checkpoint: `d9beda8c7158d03b5f8af6f3eb67ec91f442b064`
- Historical Intelligence contract: `1.9`
- Historical fingerprint: `ffec9afddff8af536aecb8ef5cd890ab22830d50f2a502e095aba729ed5b5f8c`
- UI Payload contract: `1.13`
- UI Payload fingerprint: `dfcceccf489224e2129512ecdec380b5ece58d794ea3edd9bb26d648871fa9b5`
- Native patch: `native-smart-issues-foundation-v23`
- V2 compatibility patch: `v2-smart-issues-foundation-v13`
- Native fingerprint: `dadfbf83b835f7b3fd21ba85ee5a49b35845d52b01e081a73db19d5df47aef45`
- Business Context fingerprint unchanged: `d4fef77fe3f18d2e9b91ea611dbcd755372fff1e9fc5e29739fb851b9a0a8cd0`
- Semantic fingerprint unchanged: `c25b7cfe67c6d8d477e6e8cd65a466eb3c74ca4f97a3c500b0e9320f1223b321`
- Processed both shops: **NOOP**
- Semantic: **NOOP**
- Smart Issue states: `ISSUE_READY / NO_ISSUE`.
- issue creation requires `DEVIATION_CANDIDATE`, severity >= MEDIUM, confidence >= MEDIUM, and attribution boundary in `ATTRIBUTED / ASSOCIATION_ONLY`.
- scope issues are deduped by affected KPI, one issue max per comparator and five max per scope.
- issue ranking uses attribution status → business KPI priority → severity → confidence → absolute effect.
- Smart Issues surface only on the latest trusted observation; the actual statistical source comparator remains attached for audit.
- every issue keeps unresolved uncertainty and `alert/action/diagnosis/causal=false`.
- synthetic tests validate attributed issue, association-only issue, and NO_ISSUE paths.
- current real result: Portfolio, SYT+ and Mall all `NO_ISSUE`; 0 issue on every scope.
- `smartIssuesFoundation=true` while operational `smartIssues=false`.
- audit: `docs/smart-issues-foundation-v1.md`
- #216 remains the accepted human-reviewed visual/interaction baseline; #395 is the Smart Issues Foundation checkpoint.
- production V2/Data Mart/index/deployment remain untouched.

Latest validated Operator Action Policy Foundation checkpoint:
- GitHub Actions run `36128842184` (#405) — **PASS**
- runtime checkpoint: `31ddeef18ba0fd881c7560541bf384edf897084c`
- Historical Intelligence contract: `2.0`
- Historical fingerprint: `9deab0fa9a5ce8261ea28d617e374de8f1e094bfd68c750b2a7f00a011f64f31`
- UI Payload contract: `1.14`
- UI Payload fingerprint: `3fd323cfe6ff1c4943353909b1b83d6c012f3c98c22307e8690cbe8a66f2ceff`
- Native patch: `native-operator-action-policy-v24`
- V2 compatibility patch: `v2-operator-action-policy-v14`
- Native fingerprint: `19fbed9f4b631e3c21ea1a9e629f8f910051efe7aae08b3106626871dbd9e7c6`
- Business Context fingerprint unchanged: `d4fef77fe3f18d2e9b91ea611dbcd755372fff1e9fc5e29739fb851b9a0a8cd0`
- Semantic fingerprint unchanged: `c25b7cfe67c6d8d477e6e8cd65a466eb3c74ca4f97a3c500b0e9320f1223b321`
- Processed both shops: **NOOP**
- Semantic: **NOOP**
- action-policy states: `ACTION_OPTIONS_READY / NO_ACTION_OPTIONS`
- every option is `REVIEW_OPTION` + `HUMAN_REVIEW_ONLY`.
- every ISSUE_READY gets an Evidence Validation option.
- targeted driver review is allowed only for an `ATTRIBUTED` Smart Issue with a supported quantified top driver.
- `ASSOCIATION_ONLY` never gets a targeted driver action.
- every option carries prerequisites, monitor KPIs, verification checks and stop/reversal checks.
- `platformMutationAllowed=false`, `automaticExecutionEligible=false`, `automaticAlertEligible=false`, `prescriptiveRecommendation=false`, `causalClaimEligible=false`.
- Smart Issue uncertainty has advanced from `ACTION_POLICY_NOT_DEFINED` to `HUMAN_REVIEW_REQUIRED` + `PLATFORM_MUTATION_DISABLED`.
- current real result: Portfolio, SYT+ and Mall all `NO_ACTION_OPTIONS`; 0 review options because current real Smart Issues remain `NO_ISSUE`.
- `operatorActionPolicyFoundation=true` while operational `operatorActions=false`.
- audit: `docs/operator-action-policy-foundation-v1.md`
- #216 remains the accepted human-reviewed visual/interaction baseline; #405 is the latest completed operator-intelligence policy checkpoint.
- production V2/Data Mart/index/deployment remain untouched.

Latest Production Cutover Readiness / Shadow Mode v1 implementation checkpoint:
- implementation date: `2026-09-25`
- latest canonical GitHub validation: run `36165107810` (#408) — **PASS**
- runtime branch checkpoint: `36a3e16317be068c5362d25fd2e602b3979a278f`
- Historical Intelligence contract: `2.1`
- Historical fingerprint: `e8872de70b6568c8ea865eca23de34fecb3c8fe1db48b4a69558de94393065a7`
- UI Payload contract: `1.15`
- UI Payload fingerprint: `43ec276ff68eb063d91ea798c5b09a2855e5f13c991e4dfd8133d1a68fc89d5a`
- Native patch: `native-production-shadow-mode-v25`
- V2 compatibility patch: `v2-production-shadow-mode-v15`
- Native fingerprint: `0b20678448d9ff2da75166624d125556aaf518950e5479b1303f0d3d0a9ab57f`
- runtime mode: `PREPRODUCTION_OBSERVE_ONLY`
- shadow status: `SHADOW_OBSERVING`
- refresh evidence: observation `2/3`; refresh ID `36165107810-1`; safe `2/3`; stable `2/3`
- previous refresh: `36163777627-1`; lineage status: `CONSISTENT`; all non-count readiness gates PASS; `failedGates=[]`
- status model: `SHADOW_OBSERVING / READY_FOR_HUMAN_CUTOVER_REVIEW / CUTOVER_BLOCKED`
- minimum readiness evidence: 3 distinct consecutive safe refreshes + 3 distinct consecutive stable refreshes
- repeated refresh IDs are idempotent and cannot manufacture readiness.
- issue/action transitions are tracked as appeared, persisted and disappeared with source-issue lineage validation.
- production activation, automatic cutover, production writes, automatic alerts and platform mutation remain **false**.
- local QA: **133/133 PASS**, compileall PASS, production V2 template validation PASS.
- canonical observations 1 and 2 are safe/stable; neither authorizes cutover.
- audit: `docs/production-cutover-shadow-mode-v1.md`
- #216 remains the accepted human-reviewed visual/interaction baseline; #408 is the latest canonical observe-only checkpoint.
- production V2/Data Mart/index/deployment remain untouched.

## UI V2 destination architecture — current rule

UI V2 now has one shared Design Language with separate destinations:
- **Command Center** — monitoring surface; Portfolio/Tổng quan and one-Shop scopes reuse the existing production V2 renderer.
- **So sánh Shop** — dedicated analysis destination; may use a different information architecture but must reuse the V2 visual foundation and presentation contracts.

Do not treat Portfolio / Shop / Compare as three interchangeable scopes of one renderer.
Do not create separate fonts, palettes, dark modes, or independent card systems per destination.

Real validation run #216 confirms:
- separate sidebar destinations are present;
- Compare is no longer a third Command Center scope tab;
- Inter and V2 foundation palette are enforced by QA;
- legacy parallel Compare visual shell remains removed;
- production V2/Data Mart/index/deployment remain untouched.

## UI V2 interaction baseline — sidebar + Compare identity

Run #216 is the accepted PREPRODUCTION interaction baseline.

Accepted behaviors:
- pinned Sidebar is rendered in a true fixed viewport rail outside the scaled V2 app, so long-page scrolling does not cause visual jump/bounce;
- unpin keeps the rail at the current viewport position and slides it off-canvas instead of returning it to the document top;
- left-edge hover reveals the unpinned Sidebar at the current scroll position;
- Compare shop-type badges are registry-driven and appear only at useful identity anchors (shop selector, table headers and shop-specific product panels), without repeated explanatory legends;
- Compare tables use improved row rhythm/readability while preserving the shared V2 Design Language;
- production V2/Data Mart/index/deployment remain untouched.

Run #216 native QA: 28 checks PASS, 0 failures.
Drive baseline file ID: `1VJmWRqdSmpwV4q6p7ZQCJovYgm5izbVK`.

## 1. Architecture rule

The system is **N-shop**, not a two-shop system.

Adding a third, fourth, or later shop must be a configuration/data-onboarding task, not a source-code fork.

Concrete shop identities live in `config/shop_registry.json`. Generic runtime code must not embed a particular shop ID/name or assume a fixed shop count.

Every business-grain row carries `shop_id`.

Key grains:
- Orders: `shop_id + order_id`
- Order Items: `shop_id + order_id + item grain`
- Product Performance: `shop_id + period + product_id`
- Product Ads: `shop_id + data_date + product_id`
- Listing snapshot: `shop_id + snapshot_at + product_id/variation_id`

A Product ID from one shop must never be joined directly to a Product ID from another shop.

## 2. Currently registered shops

The registry currently contains:

- SYT+ — internal `SHP_VN_1000000001`
- Mall — internal `SHP_VN_1000000002`

These are current registry entries, **not architectural roles**. There is no permanent "reference" shop or "peer" shop.

Future shops are added through the same registry contract.

## 3. Raw architecture

Required steady state:

```
01_raw_data/
  <shop-root-A>/
    orders/
    ads/
    product_performance/
    business_insights/
    returns_refunds/
    listing_catalog/
  <shop-root-B>/
    ...
  <shop-root-N>/
    ...
```

Current state:
- Mall already uses `01_raw_data/unipalm_mall`.
- SYT+ domains are still directly under `01_raw_data`.
- Registry has a high-priority target `unipalm_syt_plus` plus the current legacy root as fallback.

The staging runner selects the highest-priority raw root that contains all core domains, so SYT+ can migrate without staging downtime.

Do not physically move all SYT+ domains until remaining legacy Apps Script dependencies are verified.

## 4. Listing metadata authority

Shopee Seller Center `mass_update_sales_info` export is the preferred authority for observed listing metadata:

- Product ID/name
- Variation ID/name
- Parent SKU
- Variation SKU
- current price
- seller stock
- GTIN when present

Priority:
1. Seller Center listing snapshot
2. Product Performance fallback
3. Catalog Resolver / SKU Master for canonical family or missing metadata

Historical listing snapshots are immutable. A later export supersedes current state without rewriting earlier observations.

Current Drive snapshots:
- SYT+: `mass_update_sales_info_1000000001_20260923101028.xlsx`
- Mall: `mass_update_sales_info_1000000002_20260923104414.xlsx`

The latest Mall snapshot confirms product `50562805590` Cặp Đôi Yêu Kiều now uses Parent SKU `CB019` and Variation SKUs `CB019-*`.

## 5. N-shop Catalog Resolver

Files:
- `automation/modules/catalog_resolver.py`
- `docs/multi-shop-catalog-resolver.md`

Rules:
- observed Seller Center Parent SKU is preserved;
- never infer Parent SKU by SKU-prefix slicing;
- exact SKU Master evidence can establish canonical family;
- every other enabled shop may contribute cross-shop evidence;
- same-shop listings are excluded from cross-shop reference evidence;
- multiple shops supporting the same Parent SKU do not penalize confidence;
- competing different Parent SKUs remain a conflict;
- resolver writes staging evidence only.

There is no fixed target↔reference shop pair.

## 6. Registry-driven ingestion & staging

Core files:
- `config/shop_registry.json`
- `automation/modules/shop_registry.py`
- `automation/modules/multi_shop_staging.py`
- `automation/multi_shop_staging_runner.py`
- `automation/modules/ads_product_mart.py`

The runner can stage:
- all enabled shops;
- one specified shop;
- multiple specified shops.

Each shop:
- resolves its own raw root;
- normalizes independently;
- gets its own staging artifact namespace;
- gets independent QA;
- may use catalog evidence from all other enabled shops.

No production Data Mart or UI writer exists in this staging path.

## 7. Staging QA gate

Blocking checks include:
- shop isolation;
- duplicate business keys;
- Placed/Confirmed/Paid BI coverage;
- Orders coverage;
- Ads coverage;
- Ads source-day uniqueness;
- cancelled fee invariant;
- product/variation referential QA;
- all-campaign Product Ads aggregation;
- placed Orders/GMV reconciliation;
- Catalog Resolver observability.

Product Ads canonical grain is:
`shop_id + data_date + product_id`.

Ratios must be recomputed from additive numerators/denominators across shops.

Production promotion remains forbidden until intended production shops pass staging QA.

Current September 2026 gate status:
- SYT+ staging QA: PASS
- Mall staging QA: PASS
- Schema Drift Guard: PASS for both shops
- shop-scoped processed/control candidate: PASS for both shops
- production Data Mart/UI remain untouched.

## 8. Production legacy quarantine

The current production UI/Data Mart path is intentionally **not** treated as multi-shop yet.

### `automation/source_processor.py`

Status: shop-agnostic, single-shop-per-run legacy adapter.

It:
- contains no concrete current Shop ID default;
- requires `shop_id` on source rows;
- fails if a run contains zero/multiple shops.

### `automation/run_pipeline.py`

Status: guarded legacy single-shop publisher.

It:
- may publish any one shop;
- fails if its mart input contains multiple shops;
- carries `shopId` in payload records for future compatibility.

Do not remove this guard until real multi-shop semantic marts/payload are built after staging acceptance.

### Product Ads maintenance

`automation/backfill_product_ads.py` remains a legacy recovery tool only. It is single-shop fail-closed and must be retired after multi-shop mart promotion.

## 9. Remaining external technical debt

Legacy upstream Apps Script, especially Orders, still contains explicit original-shop context in historical/current source.

Do not clone that Apps Script stack for every new shop.

Preferred migration:
1. keep legacy Apps Script for current production continuity;
2. prove Python registry-driven RAW ingestion equivalence;
3. cut domains over one by one;
4. retire Apps Script upstream.

The production Control Center also needs a future shop-scoped readiness key such as:

`shop_id + source_domain + period + run/status`.

## 10. Cleanup already completed

Removed redundant/obsolete development workflows:
- `multi-shop-catalog-ci.yml`
- `data-v2-integration-dry-run.yml`
- `data-v2-module-ci.yml`
- `ui-v2-production-adapter-canary.yml`
- obsolete `build_ui_v2_canary.py`

Retained deliberately:
- production pipeline;
- current V2 template;
- frozen V1 fallback;
- generated production state file;
- legacy Product Ads recovery workflow.

See `docs/multi-shop-architecture-audit-2026-09.md` for the full cleanup classification.

## 11. CI guard

`.github/workflows/multi-shop-staging.yml` is the consolidated **Multi-Shop Core CI & Staging QA**.

It:
- compiles multi-shop core and guarded legacy adapters;
- runs the complete unit-test suite;
- includes synthetic 3-shop tests;
- rejects concrete current Shop IDs in generic runtime code;
- rejects a staging workflow tied to one named shop.

Latest consolidated core CI after the architecture refactor: PASS.

## 12. Current migration boundary

The multi-shop pre-production data path is now validated through durable semantic persistence:

`RAW -> Staging/Schema Guard -> Processed v2 -> Durable Processed -> Semantic v2 -> Durable Semantic`

Production UI and the legacy production Data Mart remain unchanged.

The **pre-production payload/data contract is now validated**. Next work is a pre-production UI preview/adapter that consumes UI Payload v1 without modifying the production deployment.

Start future chats by reading:
- this file;
- `docs/multi-shop-architecture-audit-2026-09.md`;
- `docs/multi-shop-ingestion-staging-v1.md`;
- `docs/multi-shop-catalog-resolver.md`;
- `config/shop_registry.json`.


## 13. Processed/control-plane finding

Drive audit on 2026-09-23 confirmed:
- current processed fact rows already contain `shop_id`;
- current processed storage remains flat by domain/year/month;
- current filenames are not shop-namespaced;
- `orders_pipeline_control`, `returns_pipeline_control` and `shopee_data_control_center` are not keyed by `shop_id`.

Therefore the current `03_processed_data` + Control Center is a **legacy single-shop production boundary**.

Do not onboard additional shops into that flat namespace.

New contract:
- `automation/modules/pipeline_state.py`
- unique readiness key = `shop_id + source_domain + period`
- readiness/failure is independent per shop
- synthetic 3-shop behavior is covered by tests

See `docs/multi-shop-processed-control-plane.md`.

The legacy processed/control folders were intentionally not moved or renamed because they are still production dependencies.


## 14. SYT+ raw migration dependency status

A dedicated migration root now exists:

- `01_raw_data/unipalm_syt_plus`
- Drive folder ID `PUBLIC_RESOURCE_SHOP_01`

It is intentionally empty. Shop Registry now points to this folder ID as the high-priority candidate and keeps the current flat `01_raw_data` root as fallback.

Physical migration is **atomic across all core RAW domains**, because staging selects one complete root rather than mixing domains across roots.

Verified dependency state:
- Orders: `VERIFIED_FOLDER_ID` — legacy Apps Script config explicitly uses the raw Orders folder ID.
- Ads: `UNVERIFIED_LEGACY_CONFIG`
- Product Performance: `UNVERIFIED_LEGACY_CONFIG`
- Business Insights: `UNVERIFIED_LEGACY_CONFIG`
- Returns & Refunds: `UNVERIFIED_LEGACY_CONFIG`
- Listing Catalog: `REGISTRY_DRIVEN_ONLY`

Therefore no SYT+ raw domain has been moved yet.

Machine-readable inventory:
- `config/legacy_pipeline_dependencies.json`

Audit:
- `docs/legacy-upstream-dependency-audit.md`

The stale `orders_pipeline_controller` documentation spreadsheet was archived; current `orders_pipeline_control` remains active.


## 15. Active production state classification

`unipalm_pipeline_state_v1` is actively updated and must remain in place during migration. It is not a duplicate to clean up yet.

It stores current legacy production scheduler/source-manifest/QA/publish history. Inventory status:
`ACTIVE_LEGACY_PRODUCTION_STATE`.

The future N-shop control-plane contract in `automation/modules/pipeline_state.py` is a replacement design, not a signal to delete this production sheet before cutover.

`04_reports` is currently empty and has no active artifact dependency.


## 16. Mixed-locale Ads validation

Mall September 2026 was intentionally tested with mixed Shopee Ads export languages in the **same shop and same month**:

- 2026-09-01 through 2026-09-18: English export headers/metadata.
- 2026-09-19 through 2026-09-20: Vietnamese export headers/metadata.

Full Mall staging run:
- GitHub Actions run: `35819762057`
- result: **PASS**
- `production_write_allowed=true`
- Ads coverage: 20/20 contiguous days, 2026-09-01 through 2026-09-20
- Ads source files: 20 / unique days: 20
- normalized Ads rows: 375
- product Ads candidate rows: 339
- duplicate Ads keys: 0
- Product Ads aggregation QA: PASS
- Shop ID isolation: PASS

This validates the intended contract: language is a property of each export file, not a property of the shop. Files in different supported locales may coexist within one month and are normalized into the same canonical schema.

Operational recommendation remains: export future files in Vietnamese for consistency, while retaining EN+VI parser support and immutable historical RAW.


## 17. Source Schema Drift Guard

Implemented on 2026-09-23 before multi-shop processed-layer promotion.

Core files:
- `config/source_schema_registry.json`
- `automation/modules/schema_registry.py`
- `docs/source-schema-drift-guard.md`

Guarded contracts:
- Listing Catalog machine fields
- Product Performance
- Business Insights daily
- Business Insights traffic
- Orders
- Ads metadata
- Ads rows

Rules:
- exact approved aliases -> canonical fields;
- no fuzzy semantic matching;
- added unknown columns -> WARN + fingerprint drift;
- missing/unknown required field -> FAIL and staging block;
- column reordering does not change fingerprint;
- exact capitalization is respected first because Shopee Orders contains two distinct payment fields differing only by capitalization;
- case-insensitive fallback is used only when unambiguous.

Reviewed September baseline fingerprints now include the observed EN/VI export structures from both currently enabled shops.

Validation after baselining:
- SYT+: 48/48 source-schema audits PASS
- Mall: 52/52 source-schema audits PASS
- no unknown columns
- no new fingerprints
- both shops full staging QA PASS
- production Data Mart/UI still untouched

Successful staging now writes `schema_drift_report.json`. Blocking schema errors preserve their audit in `staging_error.json`.

A future label such as `Doanh thu` replacing Ads `GMV/Doanh số` must not be auto-mapped. Verify the metric definition first, then explicitly approve the alias and new fingerprint.


## 18. Shop-scoped processed/control v1

Implemented and validated on 2026-09-23.

Core files:
- `config/processed_layer_contract.json`
- `config/storage_registry.json`
- `automation/modules/processed_layer.py`
- `automation/multi_shop_processed_runner.py`
- `automation/modules/pipeline_state.py`

Pipeline sequence is now:

`RAW -> staging/schema QA -> processed/control candidate -> STOP`

The workflow still does not write the production Data Mart or UI.

### Partition identity

Local/CI candidate namespace:

`<shop_key>/<YYYY-MM>/<domain>/...`

Every business row is checked for the expected `shop_id` before promotion.

Required READY domains:
- orders
- ads
- product_performance
- business_insights

Additional shop-scoped domains:
- catalog_resolution
- listing_catalog

Each shop/period produces:
- normalized domain JSONL files;
- `manifest.json`;
- `processed_qa_report.json`;
- `control/pipeline_state.jsonl`.

Control-state grain is:
`shop_id + source_domain + period`.

### Deterministic rebuild

Volatile ingestion metadata such as Orders `loaded_at` is deliberately removed from processed business facts and retained only through run/manifest lineage.

Two consecutive real rebuilds against the same September RAW proved stable fingerprints:

- SYT+: `9039024ab292278d1f8486fd836736fbbb930c7cdd3c83847493bfad6712566b`
- Mall: `e5374fabf4ba581b9d206ee1c77ab690df921737647b9f13bd18774a7f9a32da`

GitHub runs:
- pass 1: `35833427497`
- pass 2: `35833611018`

Both runs PASSed staging and processed/control QA.

A rebuild of one shop/month is isolated from every other shop/month; this is covered by unit tests.

### Pre-production Drive namespace

A new sibling storage root now exists:

`03_processed_data_v2`

Drive folder ID:
`PUBLIC_RESOURCE_011`

It is explicitly PREPRODUCTION and separate from legacy `03_processed_data`.

Current structure:
- dynamic shop roots for currently registered shops;
- `_control/baselines` for reviewed immutable evidence.

The validated all-shop September baseline from run `35833611018` is stored in Drive as:
`processed_v2_baseline_all_2026_09_run_72.zip`.

The storage contract remains shop-neutral: future shops must be created dynamically from Shop Registry, not added as hard-coded storage config.

### Safety

Current v2 processed layer:
- does not write legacy `03_processed_data`;
- does not update legacy Control Center;
- does not write production Data Mart;
- does not modify UI;
- sets `production_updated=false` in every v2 pipeline state.

Automated processed Drive persistence and the multi-shop semantic layer are now implemented and validated. See sections 20–21 and `docs/multi-shop-semantic-mart-v1.md`.


## 19. Drive writer OAuth gate

Atomic processed-v2 Drive writer is implemented.

Core files:
- `automation/modules/drive_partition_writer.py`
- `automation/modules/drive_auth.py`
- `automation/multi_shop_drive_writer.py`
- `automation/bootstrap_drive_oauth.py`
- `docs/processed-v2-drive-oauth-setup.md`

Writer guarantees:
- preflight all selected shop/month partitions before mutation;
- only targets PREPRODUCTION `03_processed_data_v2`;
- legacy processed and production Data Mart root IDs are forbidden;
- upload is verified by MD5 + byte size;
- publish is atomic by temporary partition + swap;
- previous partition remains until the new partition is READY;
- unmanaged existing partition causes FAIL;
- identical `build_fingerprint` causes NOOP;
- run evidence is written under `_control/runs/<run_id>`.

Live validation discovered a Google infrastructure restriction:
- service account can see/create folders in shared My Drive folders;
- service account file upload fails with `403 storageQuotaExceeded` because service accounts have no My Drive storage quota.

The v2 root has already been shared with the automation service account, but this does not solve quota.

Current storage writer auth policy is therefore:
`auth_mode = user_oauth`.

Required GitHub secret:
`GOOGLE_DRIVE_OAUTH_JSON`.

The secret does not exist yet and must be created once by the user with:
`automation/bootstrap_drive_oauth.py`.

Full instructions:
`docs/processed-v2-drive-oauth-setup.md`.

Until that secret exists:
- staging remains valid;
- processed candidate remains valid;
- durable Drive partition publishing is blocked;
- production Data Mart/UI remain untouched.

The empty failed service-account audit run folder was retained and renamed:
`35835999951_FAILED_SERVICE_ACCOUNT_QUOTA`.

OAuth auth/core CI latest status: PASS.


## 20. Durable processed v2 persistence validated

OAuth-backed My Drive persistence is now fully validated.

Validation runs:
- first durable publish: GitHub run `PUBLIC_SNAPSHOT_NOT_CONFIGURED` — PASS
- immediate identical rebuild: GitHub run `PUBLIC_SNAPSHOT_NOT_CONFIGURED` — PASS

Run `PUBLIC_SNAPSHOT_NOT_CONFIGURED`:
- SYT+: `PUBLISHED`, 15 files uploaded
- Mall: `PUBLISHED`, 15 files uploaded
- auth mode: `user_oauth`
- control audit stored under `03_processed_data_v2/_control/runs/PUBLIC_SNAPSHOT_NOT_CONFIGURED`

Run `PUBLIC_SNAPSHOT_NOT_CONFIGURED` against unchanged business facts:
- SYT+: `NOOP`, 0 files uploaded
- Mall: `NOOP`, 0 files uploaded
- reason: `same_build_fingerprint`
- control audit stored under `03_processed_data_v2/_control/runs/PUBLIC_SNAPSHOT_NOT_CONFIGURED`

Current durable partitions:
- `03_processed_data_v2/syt_plus/2026-09`
- `03_processed_data_v2/mall/2026-09`

Direct Drive inspection confirmed:
- one active `2026-09` partition per shop;
- no leftover temp/backup partition;
- each partition contains Ads, Orders, Business Insights, Product Performance, Catalog Resolution, Listing Catalog, control state, manifest and processed QA report.

Current fingerprints:
- SYT+: `9039024ab292278d1f8486fd836736fbbb930c7cdd3c83847493bfad6712566b`
- Mall: `e838d96b4988931927e867e36f75b5f99d6253586e2fedb3d446e39b3f81ba18`

Mall fingerprint differs from an earlier baseline because its September Ads RAW was subsequently extended with the newer mixed-locale daily files. This is expected business-data change, not an idempotency failure.

The durable processed/control layer milestone is therefore complete.

Safety remains:
- legacy `03_processed_data` untouched;
- legacy Control Center untouched;
- production Data Mart untouched;
- UI untouched.

`03_processed_data_v2` remains PREPRODUCTION until the new multi-shop semantic Data Mart is designed and validated.


## 21. Durable semantic v2 milestone

Implemented and validated on 2026-09-23.

Core files:
- `config/semantic_mart_contract.json`
- `automation/modules/semantic_mart.py`
- `automation/multi_shop_semantic_runner.py`
- `automation/modules/semantic_drive_writer.py`
- `automation/multi_shop_semantic_drive_writer.py`
- `docs/multi-shop-semantic-mart-v1.md`

Drive namespace:
- `04_semantic_data_v2`
- root ID `PUBLIC_RESOURCE_012`
- canonical namespace `<YYYY-MM>/...`

The previously empty `04_reports` folder was renamed to `05_reports` so layer numbering remains coherent. Its Drive ID did not change.

Current September 2026 semantic fingerprint:
`PUBLIC_SNAPSHOT_NOT_CONFIGURED`

Durable validation:
- run `PUBLIC_SNAPSHOT_NOT_CONFIGURED`: semantic portfolio `PUBLISHED`, 13 files
- run `PUBLIC_SNAPSHOT_NOT_CONFIGURED`: identical rebuild `NOOP`, 0 files

Direct Drive inspection confirms one active `2026-09` partition, no leftover temp/backup folders, and audit records for both runs.

Semantic mart rows:
- dim_shop: 2
- dm_shop_daily: 38
- dm_shop_monthly: 2
- dm_commercial_stage_daily: 114
- dm_ads_daily: 40
- dm_ads_product_daily: 895
- dm_product_monthly: 71
- dm_traffic_source_daily: 3408
- dm_traffic_source_monthly: 180
- dm_order_quality_daily: 38

KPI aggregation recomputes ratios from additive facts. Daily Visitors/Buyers are not summed into false monthly unique metrics.

Canonical semantic persistence requires **all enabled shops**; partial shop runs cannot overwrite the portfolio partition.

Production Data Mart, legacy Control Center and production UI remain untouched.

Next milestone:
pre-production semantic payload contract / shop selector data adapter.


## 22. Traffic grain + historical deleted product correction

Validated end-to-end on 2026-09-23.

### Business Insights Traffic Source

Semantic QA exposed a real upstream normalization defect: the previous BI traffic parser flattened multiple Shopee traffic sections/sources into `Product Card`, creating duplicate semantic grains.

The normalizer now preserves:
- `channel_group`
- canonical `traffic_source`
- `traffic_source_raw`
- `exposure_metric`

Supported channel sections include:
- Product Card
- Seller Live
- Seller Video
- Shopee Affiliate

Shopee Ads traffic section remains excluded from BI traffic mart because Ads has its own authoritative source.

Staging QA now blocks duplicate keys at:
- `shop_id + data_date + order_stage + channel_group + traffic_source`
- `shop_id + data_month + order_stage + channel_group + traffic_source`

Real semantic QA after the fix:
- `dm_traffic_source_daily`: 3,408 rows, 0 duplicate grain keys
- `dm_traffic_source_monthly`: 180 rows, 0 duplicate grain keys

### Historical deleted products

SYT+ Product Performance contains historical deleted product `50805387004`, which is no longer present in the current Listing Catalog.

This is valid source history, not a Catalog Resolver failure.

Semantic product join states are now explicit:
- `MATCHED_CURRENT_CATALOG`
- `HISTORICAL_DELETED_NO_CURRENT_LISTING`
- `MISSING_CURRENT_CATALOG` (blocking)

The deleted historical product is preserved with:
- `catalog_join_status = HISTORICAL_DELETED_NO_CURRENT_LISTING`
- `catalog_status = NOT_IN_CURRENT_CATALOG`
- no invented Parent SKU/canonical identity

### Validation

Run `PUBLIC_SNAPSHOT_NOT_CONFIGURED`:
- full Staging: PASS
- Processed v2: PASS
- Processed Drive: NOOP against already published corrected facts
- Semantic QA: PASS
- Semantic Drive: PUBLISHED, 13 files
- semantic fingerprint: `PUBLIC_SNAPSHOT_NOT_CONFIGURED`

Run `PUBLIC_SNAPSHOT_NOT_CONFIGURED`:
- same source/business facts
- Processed Drive: NOOP for both shops
- Semantic Drive: NOOP
- identical semantic fingerprint

Reviewed baseline artifact:
`04_semantic_data_v2/_control/baselines/semantic_v2_baseline_2026_09_run_119.zip`

Production Data Mart/UI remain untouched.


## 23. Multi-shop UI Payload v1

Implemented and validated on 2026-09-23.

Core files:
- `config/ui_payload_contract.json`
- `automation/modules/semantic_payload.py`
- `automation/multi_shop_payload_runner.py`
- `automation/tests/test_semantic_payload.py`
- `docs/multi-shop-ui-payload-contract-v1.md`

Canonical chain is now:

`RAW -> Staging/Schema Guard -> Processed v2 -> Durable Processed -> Semantic v2 -> Durable Semantic -> UI Payload v1.x -> Native V2 PREPRODUCTION`

### Scope model

UI Payload v1 supports:
- `portfolio`
- `shop`
- `compare`

Portfolio uses the intersection of every enabled shop's common reliable window.

September 2026:
- SYT+ common reliable end: `2026-09-17`
- Mall common reliable end: `2026-09-21`
- Portfolio aligned window: `2026-09-01..2026-09-17`

Compare is pairwise, alignment-safe and N-shop:
- each pair receives its own common reliable intersection;
- no shop ranking/winner is emitted;
- N shops produce `N*(N-1)/2` pairs.

Synthetic 3-shop tests PASS.

### KPI policy

The UI does not average ratios.

Payload recomputes:
- AOV = total placed GMV / total placed Orders
- CVR = total placed Orders / total Product Clicks
- ROAS = total attributed Ads sales / total Ads spend
- platform cost ratio = (Order Fees + Ads Spend) / Net Sales After Cancel

Cross-shop non-additive unique metrics such as Visits/Buyers are not exposed as Portfolio totals.

### Product scope

Product ID remains scoped by:
`shop_id + product_id`.

Shop Product view is supported.

Portfolio Product aggregation is intentionally disabled until an exact Product Performance cutoff/cross-shop identity contract exists.

### Selector order

Shop selector preserves Shop Registry order through `dim_shop`; runtime code does not sort or hard-code current shop identities.

Current order:
1. SYT+
2. Mall

### Real validation

Run `PUBLIC_SNAPSHOT_NOT_CONFIGURED` (#129): PASS.

UI payload fingerprint:
`PUBLIC_SNAPSHOT_NOT_CONFIGURED`

Source semantic fingerprint:
`PUBLIC_SNAPSHOT_NOT_CONFIGURED`

Payload QA:
- selector scope: PASS
- all shop scopes present: PASS
- Portfolio GMV reconciliation: PASS
- Portfolio Orders reconciliation: PASS
- AOV/CVR/ROAS recomputation: PASS
- Compare pair count: PASS
- Compare IDs unique: PASS
- Product identity shop-scoped: PASS

Reviewed baseline artifact:
`04_semantic_data_v2/_control/baselines/ui_payload_v1/ui_payload_v1_baseline_2026_09_run_129.zip`

### Capability flags

Enabled:
- multi-shop selector
- Portfolio scope
- pairwise Compare
- shop Product view

Disabled until later milestones:
- cross-shop Product aggregation
- Customer Lifetime
- historical 6M Intelligence
- matched-hour Today
- production UI binding

Production Data Mart and production UI remain untouched.


## 24. Legacy iframe preview — removed

The earlier iframe-based multi-shop preview was a temporary bridge used before
the native V2 destination architecture was accepted. It has been removed from
runtime, CI and documentation to avoid maintaining two PREPRODUCTION UI paths.

Removed:
- `automation/modules/ui_preview.py`
- `automation/multi_shop_preview_runner.py`
- `automation/multi_shop_preview_template.html`
- `docs/multi-shop-ui-preview-v2.md`

Reusable V2 adaptation logic now lives in
`automation/modules/ui_v2_compat.py`.

Do not restore the iframe preview path unless a new requirement explicitly
needs a second renderer.

## 25–27. Superseded UI milestones — historical summary

Earlier PREPRODUCTION milestones established the native V2 path, completed human visual QA, and expanded Compare with the Language System / Product Naming System.

Historical accepted runs included #156, #176 and #187. They are retained only as provenance; **none is the current baseline**.

The current authoritative contracts are:
- `docs/ui-v2-destination-architecture.md`
- `docs/ui-v2-language-product-naming-system.md`
- `config/ui_v2_presentation_contract.json`
- `config/ui_payload_contract.json`

The current canonical baseline is always the baseline declared at the top of this handoff. Do not restore superseded UI layouts, iframe preview paths, old Compare aliases or superseded baseline assumptions from historical runs.

## 28. Portfolio + Shop semantic hardening

Validated on 2026-09-25.

### Portfolio

Portfolio semantics are now explicit and machine-readable:
- all enabled shops use the intersection of their common reliable windows;
- every Portfolio day must include every enabled shop;
- Visits/Buyers/New Buyers/Existing Buyers/Potential Buyers and unique impression/click metrics are not exposed as cross-shop totals;
- AOV, CVR, ROAS and total platform cost ratio are recomputed from additive components;
- the latest trusted day is displayed as **Ngày gần nhất**, not assumed to be wall-clock yesterday;
- current/previous comparisons are emitted only when both windows are complete.

See:
- `docs/ui-v2-portfolio-semantic-audit.md`

### Shop

Shop semantics are now explicit and machine-readable:
- scope is exactly one registry-backed `shop_id`;
- Visits, Buyers, New Buyers, Existing Buyers and Potential Buyers are daily-unique signals and are not summed into 7D/MTD unique totals;
- Shop headline omits those daily-unique fields;
- period CVR remains `Placed Orders / Product Clicks`;
- Visits → Product Clicks is permitted only as a one-day supporting bridge;
- Shop daily AOV/CVR/ROAS/platform-cost ratio are recomputed from additive facts rather than trusting upstream ratio fields;
- Traffic Source multi-day aggregation emits additive facts only and recomputes ratios;
- Business Product Performance remains source-MTD and shop-scoped; no Day/7D derivation is allowed;
- incomplete 7D/MTD windows are visibly labeled by observed coverage rather than presented as complete periods.

See:
- `docs/ui-v2-shop-semantic-audit.md`

### Validation

Run `36088497894` (#251) correctly failed in core tests because the first Shop QA version exposed an existing adapter weakness: Shop daily ratios were copied from upstream semantic ratio fields.

The adapter was corrected to recompute Shop daily ratios from additive facts.

Run `36088664004` (#252) then passed end-to-end:
- core tests: PASS;
- read-only staging/schema QA: PASS for both enabled shops;
- Processed v2 candidate: PASS;
- Processed Drive: NOOP for both shops;
- Semantic v2: PASS;
- Semantic Drive: NOOP;
- UI Payload v1.4: PASS;
- Native V2 PREPRODUCTION: PASS.

Current run #252 lineage:
- SYT+ Processed fingerprint: `31844799e80764aedbe253b832321bd88e4c6d3477d9e3acd74577c7f64d9f3a`
- Mall Processed fingerprint: `c67a79da38380bde5384a4249205b4172dead93e28f1b4e2e361679deb197b1a`
- Semantic fingerprint: `fb862a21b281d3b33611e35c060d5dfbbe19a3bdbb455fc9f9c034b755a3c162`
- UI Payload fingerprint: `76c8aacccf2a90a527a0e4e909b848780b54ad59d791a17eab1a72db1241c2a3`
- Native fingerprint: `f3ff94404198cb8abb65e615ce41b7f52a4d4e7cc5889d2242f987ace807684b`

Freshness observed in #252:
- SYT+: common reliable window `2026-09-01..2026-09-17`
- Mall: common reliable window `2026-09-01..2026-09-23`
- Portfolio: `2026-09-01..2026-09-17`

### Next milestone

**Historical Intelligence foundation** is now the next batch.

Do not build alerting/diagnosis heuristics first. Establish the historical data contract and history persistence/query path before enabling Business Pulse historical claims.

The next batch should define and validate:
1. multi-month history coverage by shop and source;
2. authoritative comparison windows: previous period, same weekday and same day-of-month where appropriate;
3. minimum sample sizes and explicit insufficient-history states;
4. campaign/calendar context fields that may invalidate naive comparisons;
5. historical baseline outputs consumed by Business Pulse / Smart Issues;
6. deterministic QA and PREPRODUCTION persistence without changing production UI/Data Mart.

## 29. Historical Intelligence Foundation

Implemented and validated on 2026-09-25.

Core files:
- `config/historical_intelligence_contract.json`
- `automation/modules/historical_intelligence.py`
- `automation/multi_shop_history_runner.py`
- `automation/tests/test_historical_intelligence.py`
- `docs/historical-intelligence-foundation-v1.md`

The foundation is deliberately **history-first, alert-later**.

### Trust boundary

History is classified into three levels:

1. RAW source presence = `BACKFILL_CANDIDATE_ONLY`
2. Processed v2 READY = normalized historical partition available
3. Published Semantic QA PASS = trusted business history eligible for historical baselines

RAW source presence is never treated as trusted historical business data.

The Historical runner is now part of the all-shop PREPRODUCTION CI chain:

`Semantic Drive PASS -> Historical Inventory/Baseline PASS -> UI Payload -> Native V2`

### Comparator contract

Defined but non-alerting:
- previous day;
- previous 7D;
- previous-month matched MTD;
- same weekday, minimum 4 real prior samples;
- same day-of-month, minimum 3 real prior samples.

Ratios are always recomputed from additive components.

Overall history requires:
- 3 complete months for general historical readiness;
- 6 complete months for 6M intelligence.

Context-matched claims require a future explicit campaign/calendar context dataset. Until then the context status is `CONTEXT_UNAVAILABLE`.

Historical alerts and diagnosis remain disabled.

### Real Drive inventory

Run `36090296993` (#259) validated source presence through September 2026.

SYT+ RAW core + Product Performance backfill candidates:
- `2025-11`
- `2025-12`
- `2026-01` through `2026-09`

Mall RAW core + Product Performance backfill candidates:
- `2026-07`
- `2026-08`
- `2026-09`

These are source-presence candidates only and have not yet been promoted to trusted history.

Current Processed v2 READY:
- SYT+: `2026-09`
- Mall: `2026-09`

Current trusted Semantic history:
- `2026-09` only

Therefore current Historical Intelligence correctly returns:
- Portfolio: `INSUFFICIENT_HISTORY`
- SYT+: `INSUFFICIENT_HISTORY`
- Mall: `INSUFFICIENT_HISTORY`
- 6M intelligence: false
- historical alerts: false
- diagnosis: false

### Orders historical compatibility

Older Orders partitions use `final/`, while newer months use immutable `snapshot_YYYY-MM-DD`.

Orders source selection now follows:

`latest snapshot -> legacy final -> month root`

This preserves current snapshot behavior and makes old RAW months backfillable without migration.

### Determinism and validation

Run #257 first validated the full foundation and produced historical fingerprint:
`fc6418b091497ae7c5a9560d4ea9348b50c3f13a481b7520950082455e92a171`

A deterministic fingerprint unit test was then added.

Final run #259:
- core tests: PASS
- Staging/Schema QA: PASS
- Processed v2: PASS
- Processed Drive: NOOP
- Semantic v2: PASS
- Semantic Drive: NOOP
- Historical Intelligence Foundation: PASS
- UI Payload v1.4: PASS
- Native V2: PASS
- historical fingerprint remained exactly `fc6418b091497ae7c5a9560d4ea9348b50c3f13a481b7520950082455e92a171`

Current downstream fingerprints remain:
- Semantic: `fb862a21b281d3b33611e35c060d5dfbbe19a3bdbb455fc9f9c034b755a3c162`
- UI Payload: `76c8aacccf2a90a527a0e4e909b848780b54ad59d791a17eab1a72db1241c2a3`
- Native V2: `f3ff94404198cb8abb65e615ce41b7f52a4d4e7cc5889d2242f987ace807684b`

### Next milestone — Historical Backfill v1

The next batch should backfill the **common multi-shop history first**:

- `2026-07`
- `2026-08`

September 2026 is already trusted.

Target flow:

`historical RAW -> Schema Guard -> Staging QA -> Processed v2 history -> durable Processed -> Semantic history -> historical baseline refresh`

Do not immediately backfill SYT+-only `2025-11..2026-06` into the current portfolio Semantic namespace. The current durable Semantic contract requires all enabled shops. Older shop-only history needs an explicit shop-scoped historical persistence design so Portfolio/Compare semantics cannot be contaminated.

After July + August become trusted alongside September, the system should have the first 3-month common multi-shop history window. Only then reevaluate whether general historical readiness can become `READY`. Six-month intelligence must remain disabled until its six-complete-month threshold is actually met.

## 30. Historical Backfill v1

Validated on 2026-09-25.

Authoritative audit:
- `docs/historical-backfill-v1.md`

### July root cause and fix

Initial July run #260 correctly blocked promotion at Staging QA.

The historical Orders export contained a Shopee-funded subsidy field that had previously been ignored:

`Được Shopee trợ giá -> shopee_subsidy`

Business Insights Gross Sales includes this platform-funded subsidy, so historical Orders reconciliation now restores it:

`sum(item_buyer_payment + shopee_subsidy) - shop_voucher`

For cancelled orders where item-level payment semantics are not equivalent, the QA may use observed `order_total_value` for that cancelled order as a reconciliation fallback.

This is a QA proxy only; BI remains authoritative for placed GMV.

July evidence after the fix:
- SYT+: 1,896 BI orders = 1,896 Orders rows; BI GMV `396,832,609`; Shopee subsidy `142,734,500`; selected proxy `398,104,323`; difference `+0.320466%`; PASS under the existing 0.5% QA threshold.
- Mall: 4 BI orders = 4 Orders rows; BI GMV `960,000`; one cancelled-order fallback; selected proxy `960,000`; exact 0% difference.

SYT+ historical Ads also exposed one legitimate repeated schema fingerprint:
`6fecc7a5e5f8ad040b87e299f2368389c4c38e660fee69cdecd397fac60899e4`

It had no unknown columns or missing required fields and was reviewed/baselined rather than being bypassed.

### July publish

Run `36095755224` (#265): PASS end-to-end.

Processed fingerprints:
- SYT+: `beed58ac13e7e74a6267660ce9c44e1f9df3febe4df9fb12abe483f207dbe561`
- Mall: `d7aa440e99dec8981fc7f27449c1fcb0b11ade12aeadf6a899e019ffa8c63310`

Semantic fingerprint:
`70ddd954833cb413b8127cbe51b4ce801c1a6766ffe8d20ac34d0ca15c2f3571`

July common reliable windows:
- SYT+: `2026-07-01..2026-07-31`
- Mall: `2026-07-20..2026-07-30`
- Portfolio: `2026-07-20..2026-07-30`

### August publish and idempotency

August Staging/Processed QA passed without semantic exceptions.

Processed fingerprints:
- SYT+: `a0f11f399d183343b994e3c04ec5381d0d3721382f69b4e7e66e4244a104ab0a`
- Mall: `3ff37c4aba69efe731b48cfff947b3e11b263dcde8a20b3f0f4cebd3d42677be`

Transient Drive read timeouts during early attempts were handled by hardening the atomic writers with bounded retries for idempotent operations. QA thresholds and business facts were not relaxed.

Run `36098115309` (#274): PASS
- Processed: NOOP both shops
- Semantic: PUBLISHED
- Semantic fingerprint: `39bd92c7aa44794a2f823511e67a58e26e09a679c38d5bc0412ddf75c8951351`

Run `36098360904` (#275): PASS
- Processed: NOOP both shops
- Semantic: NOOP
- proves August Processed + Semantic `PUBLISHED -> NOOP` idempotency

August common reliable windows:
- SYT+: `2026-08-01..2026-08-27`
- Mall: `2026-08-01..2026-08-31`
- Portfolio: `2026-08-01..2026-08-27`

### September canonical refresh

Run `36098551468` (#276): PASS end-to-end.

September was refreshed under the current historical Orders semantics.

Processed fingerprints:
- SYT+: `7d4fd9288c154e59903525c019d455ee14a807f1f25b7b5c74ed5303641b03aa`
- Mall: `5cbaff93bdae6d87d6784169e5692698742beed39425536a5a8283b9e9439847`

Semantic fingerprint:
`c25b7cfe67c6d8d477e6e8cd65a466eb3c74ca4f97a3c500b0e9320f1223b321`

Current September downstream:
- UI Payload: `4438f3026f0bd0e8a3b61800262d5222b1ee6b0590f002778ebdc2d3cfd3a68d`
- Native V2: `3e701fa64252e3b9c8d440580387e18fcd11e33bc59fce1baa43b01494e9870e`

### Trusted historical state after backfill

Trusted Semantic months:
- `2026-07`
- `2026-08`
- `2026-09`

Historical fingerprint:
`12f6667a045535ea7b17616f45acfc12b0157fa572d4ee0c14f662ab25ea66fa`

Coverage:
- Portfolio: 55 trusted days, `2026-07-20..2026-09-17`, **0 complete months**
- SYT+: 75 trusted days, `2026-07-01..2026-09-17`, complete month = July only
- Mall: 65 trusted days, `2026-07-20..2026-09-23`, complete month = August only

Therefore three available calendar months are not three complete historical months.

Overall status correctly remains:
- Portfolio: `INSUFFICIENT_HISTORY`
- SYT+: `INSUFFICIENT_HISTORY`
- Mall: `INSUFFICIENT_HISTORY`
- 6M Intelligence: false
- historical alerts: false
- diagnosis: false

Comparator readiness is more granular:
- Previous Day: READY
- Previous 7D: READY
- previous-month matched MTD: READY
- Same Weekday: READY with 8 real prior samples
- Same Day-of-Month: insufficient

A comparator being READY permits factual comparison only. It does not authorize anomaly/alert/diagnosis language.

### Historical Comparator Binding v1 — completed

Historical Comparator Binding v1 was completed in run #291. See Section 31 and:
- `docs/historical-comparator-binding-v1.md`

The next milestone is **Business Context Calendar Foundation v1**.

## 31. Historical Comparator Binding v1

Validated on 2026-09-25.

Authoritative audit:
- `docs/historical-comparator-binding-v1.md`

### Lifecycle correction

Mall began operating only in late July 2026. Its historical record is therefore not missing a pre-July period.

Registry-backed lifecycle policy:
- SYT+: `PREEXISTING_BEFORE_TRUSTED_WINDOW`
- Mall: `SHOP_LAUNCH`
- Portfolio: `ALL_ENABLED_SHOPS_ACTIVE`

Mall uses `FIRST_TRUSTED_SEMANTIC_DATE` as the observable lifecycle boundary. The current trusted boundary is `2026-07-20`.

This date is a data-derived first trusted Semantic date, not an independently asserted exact storefront opening timestamp.

Historical coverage now explicitly separates:
- lifecycle origin;
- calendar completeness;
- trusted-history depth;
- actual data gaps.

For Mall and Portfolio:
- `preStartDatesAreMissing=false`
- `historyDepthReason=HISTORY_LENGTH_NOT_DATA_GAP`

Therefore `INSUFFICIENT_HISTORY` means the shop/Portfolio is still young from a historical-statistics perspective, not that the pipeline lost pre-launch data.

### Historical Intelligence 1.1

Run #291 Historical fingerprint:
`8c61ea948f5c175f9dcaf9cbcd630b536b5f68b71bf2a2e74ce45d46373163da`

Trusted Semantic months remain:
- `2026-07`
- `2026-08`
- `2026-09`

Observed lifecycle-aware coverage:
- Portfolio: `2026-07-20..2026-09-17`, 55 trusted days, origin `ALL_ENABLED_SHOPS_ACTIVE`
- SYT+: `2026-07-01..2026-09-17`, 75 trusted days, origin `PREEXISTING_BEFORE_TRUSTED_WINDOW`
- Mall: `2026-07-20..2026-09-23`, 65 trusted days, origin `SHOP_LAUNCH`

READY factual comparators:
- Previous Day
- Previous 7D
- Previous-month matched MTD
- Same Weekday

Same Day-of-Month remains insufficient.

### Canonical UI Payload 1.5

Historical Intelligence is now part of the canonical payload lineage.

UI Payload fingerprint:
`0f168586b6e4a136e6914c5e9c7760f8d03137a270d546a9682a70964d59aca5`

Source Historical fingerprint:
`8c61ea948f5c175f9dcaf9cbcd630b536b5f68b71bf2a2e74ce45d46373163da`

Each Portfolio/Shop scope receives `historicalContext` with:
- lifecycle-aware coverage;
- history-depth status;
- comparator states/windows;
- same-weekday factual baseline samples;
- fail-closed alert/diagnosis flags.

Payload QA enforces:
- history lineage on all bound scopes;
- alerts/diagnosis false;
- comparator binding factual-only.

### Native V2 Business Pulse

Native patch:
`native-historical-comparator-v16`

Compatibility patch:
`v2-historical-comparator-v6`

Native fingerprint:
`52a881b192bd51f5d2da849b5534b7c0c612e788fb339e3b3b2c6715ab97bcb7`

Current facts continue to come from the current Semantic/UI Payload. Historical Intelligence contributes only the comparison/reference side.

This is important because historical binding must never replace current Shop signals such as one-day Visits.

Visible Business Pulse behavior can now state factual comparisons such as:
- current day vs previous day;
- current 7D vs prior 7D;
- MTD vs matched MTD previous month;
- same-weekday historical median/sample context.

The UI explicitly labels these as factual historical comparisons, not anomaly/alert/diagnosis claims.

### Run #291 validation

GitHub Actions run `36111013628` (#291): PASS end-to-end.

Stable upstream facts:
- SYT+ Processed `7d4fd9288c154e59903525c019d455ee14a807f1f25b7b5c74ed5303641b03aa` — NOOP
- Mall Processed `5cbaff93bdae6d87d6784169e5692698742beed39425536a5a8283b9e9439847` — NOOP
- Semantic `c25b7cfe67c6d8d477e6e8cd65a466eb3c74ca4f97a3c500b0e9320f1223b321` — NOOP

This proves the batch changed historical interpretation/UI binding without rewriting canonical business facts.

Artifacts:
- staging `10852827952`
- processed `10853362132`
- semantic `10852952796`
- history `10853082511`
- UI Payload `10852728561`
- Native V2 `10852952803`

Production safety remains unchanged:
- no production Data Mart write;
- no production V2 modification;
- no production index modification;
- no deployment;
- no historical alerts;
- no diagnosis.

### Next milestone — Business Context Calendar Foundation v1

Historical comparison is now usable. The next blocker to responsible intelligence is explicit business context.

The next batch should define a canonical context-day layer for:
- Shopee campaign / mega-sale windows;
- payday windows;
- public-holiday or special-event periods where operationally relevant;
- seller promotion windows;
- observed price-change context only when backed by a reliable source.

Rules:
- explicit sources only;
- never infer campaign labels from metric movements;
- context may qualify a comparison but must not manufacture an alert;
- Mall launch lifecycle must remain part of historical context;
- historical alerts/diagnosis remain off until later evidence thresholds are explicitly approved.

Older SYT+-only `2025-11..2026-06` remains useful for future Shop-specific deep history, but must not be injected into Portfolio history where Mall did not yet exist.

## 32. Business Context Calendar Foundation v1

Validated on 2026-09-25.

Authoritative audit:
- `docs/business-context-calendar-foundation-v1.md`

### Source authority

Exact platform campaign dates must come from reviewed official sources.

Priority:
1. Platform seller official — Shopee seller/Ads, TikTok Shop Seller Center/Academy
2. Platform consumer official — official landing/blog pages
3. Government official — public holiday context
4. Industry analytics — Metric.vn for broad market seasonality only

Hard rules:
- no exact campaign dates from Metric/industry analytics;
- no canonical evidence from search snippets;
- no auto-transcription of unreadable image-only campaign calendars;
- no campaign inference from GMV/Orders/Ads/ROAS movements;
- if a source confirms only a peak day, encode only the peak day.

### Seeded real context

The reviewed Jul–Sep 2026 calendar includes:
- Shopee 7.7 window;
- Shopee August official 1.8 / 8.8 / Member Day / 15.8 / Member Day / 25.8 windows;
- Shopee 9.9 window;
- Shopee 15.9;
- Shopee Siêu Hội Trăng Rằm;
- Shopee 25.9 peak day;
- TikTok Shop 8.8 / 9.9 named peak days;
- TikTok Shop LIVE Marathon;
- Vietnam National Day holiday context;
- Metric July summer and Aug–Sep Back-to-School market season context.

TikTok monthly official campaign-calendar image is retained as `reference_only` where exact unread dates cannot be verified.

### Canonical implementation

Files:
- `config/business_context_contract.json`
- `config/business_context_calendar.json`
- `automation/modules/business_context_calendar.py`
- `automation/multi_shop_context_runner.py`
- `automation/tests/test_business_context_calendar.py`

Context-day grain:
`data_date + context_id`

The output preserves:
- scope: PLATFORM / MARKET / SHOP;
- platform;
- context type/family;
- event window and peak dates;
- source ID/tier;
- verification state;
- exact-date verification;
- matching eligibility.

### Monthly freshness guard

Context contract 1.1 requires a monthly calendar review.

If `calendar.checked_at[:7] < as_of_period`, Context QA fails and downstream Historical/Payload/Native promotion is blocked.

This is intentional. A future month must not inherit stale campaign assumptions from the previous month.

### Run #313

Run `36113962295` (#313): PASS end-to-end.

Context:
- fingerprint `d4fef77fe3f18d2e9b91ea611dbcd755372fff1e9fc5e29739fb851b9a0a8cd0`
- 12 sources
- 17 events
- 157 context-day rows
- 15 matching-eligible exact-date events
- 0 QA failures

Historical:
- contract 1.2
- fingerprint `6e700e748b00991625e77abb440188854e1675033038697e89b7f74a3d3e0cd4`
- Context fingerprint bound on Portfolio + both Shop scopes
- comparator context QA PASS

UI Payload:
- contract 1.6
- fingerprint `e56dbc7dcb442418007e042c42c1e1465dffe382deb4f11bfab0daafbf84ed25`
- `businessContextCalendar=true`
- `contextMatchedBaseline=false`
- business-context lineage QA PASS

Native:
- fingerprint `d40893b865ad63fdaa0f850c98a662f89e837e18e657a1933abd0b3985965c2f`
- production V2 source unchanged

Upstream:
- SYT+ Processed: NOOP
- Mall Processed: NOOP
- Semantic: NOOP

Safety:
- alerts OFF
- diagnosis OFF
- context matching not evaluated yet
- production Data Mart/UI/index/deployment untouched

### Next milestone — Context-Aware Comparator Qualification v1

The next batch should compare the **context signature** of current vs reference windows and classify only factual comparability:

- `CONTEXT_COMPATIBLE`
- `CONTEXT_DIFFERENT`
- `CONTEXT_UNKNOWN`

Examples:
- 9.9 period should not be treated as fully comparable with a normal non-sale week;
- a same-weekday reference with different mega-sale context should be qualified;
- broad Metric seasonal context can be displayed but cannot make exact campaign matching decisions.

Still forbidden in the next batch:
- causal statements such as “GMV rose because of 9.9”;
- anomaly severity;
- automatic alerts;
- diagnosis.

Those require later evidence and explicit thresholds.

## 33. Context-Aware Comparator Qualification v1

Validated on 2026-09-25.

Authoritative audit:
- `docs/context-aware-comparator-qualification-v1.md`

### Qualification rule

Historical comparisons now carry one factual context-qualification status:
- `CONTEXT_COMPATIBLE`
- `CONTEXT_DIFFERENT`
- `CONTEXT_UNKNOWN`

Only exact `matching_eligible=true` context from reviewed official platform/government evidence can decide compatibility.

Broad market season context from Metric remains visible context only and cannot turn an unknown pair into a compatible pair.

### Matching identity

Exact context profiles are normalized by:
`scope_type + platform + context_family + day_count + peak_day_count`

Event IDs are not used as identity, allowing recurring campaign families to be compared without pretending that 8.8 and 9.9 are the same literal event.

Rules:
- comparator not READY -> unknown;
- unequal/empty windows -> unknown;
- no exact event on either side -> unknown;
- exact event on one side only -> different;
- equal exact profiles -> compatible;
- different exact profiles -> different.

Same-weekday and same-day-of-month samples are qualified individually. The existing baseline is not filtered yet.

### Run #324 real results

Portfolio latest trusted date: `2026-09-17`
- Previous Day: `CONTEXT_COMPATIBLE`
- Previous 7D: `CONTEXT_DIFFERENT`
- matched previous-month MTD: `CONTEXT_DIFFERENT`
- Same Weekday: `CONTEXT_DIFFERENT`, 0 compatible / 8 different

SYT+:
- same qualification pattern as Portfolio on the main three comparators.

Mall latest trusted date: `2026-09-23`
- Previous Day: `CONTEXT_UNKNOWN`
- Previous 7D: `CONTEXT_DIFFERENT`
- matched previous-month MTD: `CONTEXT_DIFFERENT`
- Same Weekday: `CONTEXT_UNKNOWN`, 0 compatible / 5 different / 3 unknown

Mall Previous Day remains unknown even though both dates are inside Back-to-School market season. This is intentional because Metric-derived season context is not exact campaign-match evidence.

### UI behavior

Business Pulse can now show:
- `Bối cảnh tương thích`
- `Khác bối cảnh`
- `Chưa rõ bối cảnh`

Visible support text explicitly states:
`chỉ đánh giá khả năng so sánh, không kết luận nguyên nhân`

No causal wording is permitted.

### Contracts and fingerprints

Historical Intelligence:
- contract `1.3`
- fingerprint `4e1aa6008022518566811aea96318ccf033cdcff4aa03765986e04473c4a385d`

UI Payload:
- contract `1.7`
- fingerprint `725e39867e7525d9c9f978a0a2aeb3e5b3e19ebbbbb674c56083c5e4b7d6d262`

Native:
- patch `native-context-qualified-v17`
- compatibility patch `v2-context-qualified-v7`
- fingerprint `916151c505b792b5ac54871d53a49be055a178c0ef4de0e1d4294bd3cd3ad3fb`

Upstream:
- both Processed partitions NOOP
- Semantic NOOP

Safety remains:
- context-matched baseline OFF
- causal claims OFF
- historical alerts OFF
- diagnosis OFF
- production Data Mart/UI/index/deployment untouched

### Next milestone — Context-Matched Historical Baseline v1

Build a separate context-matched baseline using only `CONTEXT_COMPATIBLE` samples.

Rules:
- preserve the existing all-history factual baseline;
- do not silently substitute unmatched history;
- require the same explicit minimum sample count;
- if insufficient, return `INSUFFICIENT_CONTEXT_MATCHED_HISTORY`;
- keep anomaly/alerts/diagnosis/causal claims disabled.

The expected outcome for several current scopes is legitimately “not enough compatible historical samples yet”.

## 34. Context-Matched Historical Baseline v1

Validated on 2026-09-25.

Authoritative audit:
- `docs/context-matched-historical-baseline-v1.md`

### Baseline contract

The existing all-history factual baseline remains unchanged.

For sample-based comparators:
- Same Weekday
- Same Day-of-Month

Historical Intelligence now emits a separate:
`contextMatchedBaseline`

Only samples qualified as `CONTEXT_COMPATIBLE` may enter that baseline.

Minimum sample requirements are unchanged:
- Same Weekday: 4
- Same Day-of-Month: 3

If the requirement is not met:
- status = `INSUFFICIENT_CONTEXT_MATCHED_HISTORY`
- compatible sample count/dates remain visible
- matched statistics are not published
- `silentFallbackUsed=false`

If the requirement is met:
- status = `READY`
- statistics are calculated only from compatible samples.

### Run #334 real result

Portfolio:
- Same Weekday all-history: READY, 8 samples
- Same Weekday matched: 0/4, `INSUFFICIENT_CONTEXT_MATCHED_HISTORY`
- Same Day-of-Month matched: 0/3, insufficient

SYT+:
- Same Weekday all-history: READY, 8 samples
- matched: 0/4, insufficient

Mall:
- Same Weekday all-history: READY, 8 samples
- matched: 0/4, insufficient

Therefore:
- all-history factual baselines remain usable as factual references;
- there is currently no context-matched baseline with enough history;
- UI Payload capability `contextMatchedBaseline=false` is correct, not a system failure.

### Contracts and lineage

Historical:
- contract `1.4`
- fingerprint `915074583bde8db6482596b6c85dc9ab6417c58e10935bff1c099e160b191e4a`

UI Payload:
- contract `1.8`
- fingerprint `dfcd2d7509b8cdf044da86913ef7919c69d930b03a916f810d9bf5daa9c42439`

Native:
- patch `native-context-matched-baseline-v18`
- compatibility `v2-context-matched-baseline-v8`
- fingerprint `7edcf9d683e2a03ae0a9f8cb2dd1312703ff8972e66844a6e527ec1dcf3aa6f9`

Upstream:
- SYT+ Processed: NOOP
- Mall Processed: NOOP
- Semantic: NOOP

### UI behavior

The existing factual Same Weekday baseline remains visible.

A separate operator note now states:
- `Baseline cùng bối cảnh: chưa đủ mẫu`
- `không fallback sang mẫu khác bối cảnh`

This prevents an operator from mistaking general historical samples for truly context-matched history.

### Safety

Still disabled:
- anomaly classification
- anomaly severity
- alerts
- diagnosis
- causal claims
- production Data Mart/UI/index/deployment changes

### Next milestone — Anomaly Eligibility Guardrails v1

Define the conditions required before any observation may even be evaluated as a historical anomaly.

The gate should consider:
- comparator readiness;
- context qualification;
- context-matched baseline readiness;
- trusted history depth;
- lifecycle state;
- source/data completeness.

The next milestone should remain fail-closed and should not yet emit automatic operator alerts.

## 35. Anomaly Eligibility Guardrails v1

Validated on 2026-09-25.

Authoritative audit:
- `docs/anomaly-eligibility-guardrails-v1.md`

### Purpose

The system can now decide whether a historical observation is eligible for anomaly evaluation.

Allowed status:
- `ANOMALY_ELIGIBLE`
- `ANOMALY_BLOCKED`

Eligibility is emitted at:
- scope;
- comparator;
- KPI.

This is a readiness gate only. It does not detect anomalies.

### Guardrails

The gate considers:
- comparator readiness;
- current/reference completeness;
- trusted-history depth;
- lifecycle state;
- Business Context lineage;
- context qualification;
- context-matched baseline readiness;
- metric-level baseline availability.

Window comparators remain factual-only:
- Previous Day
- Previous 7D
- matched MTD

They are blocked from statistical anomaly evaluation by:
`NO_STATISTICAL_BASELINE_METHOD`

Sample-based comparators:
- Same Weekday
- Same Day-of-Month

may become eligible only when their context-matched baseline is READY and all other gates pass.

### Run #349 real result

Portfolio:
- scope = `ANOMALY_BLOCKED`
- 0/5 comparators eligible
- 0/60 KPI checks eligible
- primary lifecycle reason: `PORTFOLIO_LIFECYCLE_HISTORY_TOO_SHORT`

SYT+:
- scope = `ANOMALY_BLOCKED`
- 0/5 comparators eligible
- 0/60 KPI checks eligible
- primary history reason: `INSUFFICIENT_HISTORY_DEPTH`

Mall:
- scope = `ANOMALY_BLOCKED`
- 0/5 comparators eligible
- 0/60 KPI checks eligible
- primary lifecycle reason: `SHOP_LIFECYCLE_HISTORY_TOO_SHORT`

Same Weekday for all three scopes additionally remains blocked because:
- context-matched baseline = `INSUFFICIENT_CONTEXT_MATCHED_HISTORY`
- compatible sample count = 0/4.

Mall Same Weekday also retains `CONTEXT_UNKNOWN`; Portfolio/SYT+ retain `CONTEXT_DIFFERENT`.

### Contracts and lineage

Historical:
- contract `1.5`
- fingerprint `2393eb36a7d7c31589aca8385d36b7931e8c996cb857a87016a8dbd70526c4dd`

UI Payload:
- contract `1.9`
- fingerprint `976bb49da517cf3d8fffde2813394ea073d2e38154dc5d42f5da8cda4d1b3a0d`

Native:
- patch `native-anomaly-eligibility-v19`
- compatibility `v2-anomaly-eligibility-v9`
- fingerprint `230462a060cc99740f0a24081d46531e1ff51fa606c99eedbfa9d764898c1a92`

Upstream:
- SYT+ Processed: NOOP
- Mall Processed: NOOP
- Semantic: NOOP

### UI behavior

Business Pulse keeps factual comparison visible, but can separately say:
- `Chưa đủ điều kiện đánh giá anomaly`

Reason codes are translated to operator wording instead of exposing backend labels.

Examples:
- lịch sử Portfolio từ khi đủ shop còn ngắn;
- lịch sử từ lúc shop mở bán còn ngắn;
- chưa đủ mẫu lịch sử cùng bối cảnh;
- chưa có baseline thống kê phù hợp.

### Safety

Still disabled:
- anomaly detection
- anomaly severity
- automatic alerts
- diagnosis
- causal claims
- production Data Mart/UI/index/deployment changes

### Next milestone — Anomaly Detection Foundation v1

The next layer should define a statistical anomaly score only for observations whose eligibility gate is READY.

Initial PREPRODUCTION work should define:
- robust score/threshold methodology;
- minimum effect size;
- KPI-specific directionality;
- no-score/no-alert behavior while eligibility is blocked.

No automatic operator alerts should be enabled in the first anomaly-detection batch.

## 36. Anomaly Detection Foundation v1

Validated on 2026-09-25.

Authoritative audit:
- `docs/anomaly-detection-foundation-v1.md`

### Purpose

This completes the Intelligence Foundation.

The detector only evaluates a KPI after Anomaly Eligibility Guardrails return `ANOMALY_ELIGIBLE`.

Allowed evidence states:
- `NORMAL`
- `DEVIATION_CANDIDATE`
- `NOT_EVALUATED`

`DEVIATION_CANDIDATE` is not an alert or diagnosis.

### Robust detector

Method:
`MODIFIED_Z_SCORE_MAD`

The context-matched baseline now includes MAD.

An eligible KPI becomes a deviation candidate only when:
- robust score is available;
- `abs(modified Z) >= 3.5`;
- KPI-specific minimum effect-size passes;
- KPI directionality gate passes.

Minimum relative effects are KPI-specific, ranging from 10% to 25%.

Directionality is also KPI-specific:
- commercial outcome KPIs such as GMV/CVR/ROAS are lower-only;
- cancellation/cost-ratio KPIs are higher-only;
- Ads Spend and Order Fees are two-sided deviation signals.

If MAD is zero, baseline median is zero, statistics are missing or eligibility is blocked:
- detector returns `NOT_EVALUATED`;
- no modified Z-score is published.

### Run #360 real result

Portfolio:
- current observation: `2026-09-17`
- detector status: `NOT_EVALUATED`
- evaluated metrics: 0
- deviation candidates: 0
- not evaluated checks: 60

SYT+:
- current observation: `2026-09-17`
- detector status: `NOT_EVALUATED`
- evaluated metrics: 0
- deviation candidates: 0
- not evaluated checks: 60

Mall:
- current observation: `2026-09-23`
- detector status: `NOT_EVALUATED`
- evaluated metrics: 0
- deviation candidates: 0
- not evaluated checks: 60

This is expected because eligibility remains blocked by history/lifecycle/context-matched-baseline depth.

There is no score leakage: blocked metrics carry `scorePublished=false` and no `modifiedZScore`.

### Contracts and lineage

Historical:
- contract `1.6`
- fingerprint `e384f879a271bfdef205b68d5be7f131f937e311f6331370a6ed4586cea1adb2`

UI Payload:
- contract `1.10`
- fingerprint `3c813f82d87dd53214a7d311b9f639db6ce378893f4423f5ac7ac68a2dd12f85`

Native:
- patch `native-anomaly-detection-foundation-v20`
- compatibility `v2-anomaly-detection-foundation-v10`
- fingerprint `2cf8c07762c0c0b1b89ca422de17eae302292705a82e794b09f8778e636d2c4b`

Upstream:
- SYT+ Processed: NOOP
- Mall Processed: NOOP
- Semantic: NOOP

### Runtime capability boundary

Enabled:
- `anomalyEligibilityGuardrails=true`
- `anomalyDetectionFoundation=true`

Still disabled:
- `anomalyDetection=false`
- anomaly severity
- alerts
- diagnosis
- causal claims
- production Data Mart/UI/index/deployment changes

### Intelligence Foundation — complete

The foundation now consists of:

1. trusted multi-month historical facts;
2. lifecycle-aware history;
3. factual historical comparators;
4. explicit Business Context Calendar;
5. context qualification;
6. context-matched historical baselines;
7. anomaly eligibility guardrails;
8. robust anomaly detection foundation.

The next work is no longer foundation plumbing. It moves into operator intelligence quality.

### Next milestone — Anomaly Severity & Confidence v1

Severity/confidence should only be computed from `DEVIATION_CANDIDATE` evidence.

The next layer should combine:
- statistical strength;
- business effect size;
- baseline sample depth;
- context confidence;
- data freshness/completeness.

No severity should be emitted for `NORMAL` or `NOT_EVALUATED`, and automatic alerts should remain disabled until diagnosis is also validated.

## 37. Anomaly Severity & Confidence v1

Validated on 2026-09-25.

Authoritative audit:
- `docs/anomaly-severity-confidence-v1.md`

### Purpose

Only `DEVIATION_CANDIDATE` metrics may receive severity/confidence evidence.

`NORMAL` and `NOT_EVALUATED` always return:
`NOT_ASSESSED`

with no severity/confidence score.

### Severity

Severity is explicitly:
`STATISTICAL_AND_RELATIVE_MAGNITUDE_ONLY_NOT_BUSINESS_IMPACT`

It combines:
- modified-Z strength;
- relative effect-size strength.

Levels:
- LOW
- MEDIUM
- HIGH

This is signal magnitude, not a conclusion about business damage.

### Confidence

Confidence combines:
- context-matched sample depth;
- exact Context lineage;
- history readiness;
- valid robust scale / MAD.

Levels:
- LOW
- MEDIUM
- HIGH

### Run #371 real result

Portfolio:
- detector = `NOT_EVALUATED`
- severity/confidence = `NOT_ASSESSED`
- assessed candidates = 0
- not assessed KPI checks = 60

SYT+:
- detector = `NOT_EVALUATED`
- severity/confidence = `NOT_ASSESSED`
- assessed candidates = 0
- not assessed KPI checks = 60

Mall:
- detector = `NOT_EVALUATED`
- severity/confidence = `NOT_ASSESSED`
- assessed candidates = 0
- not assessed KPI checks = 60

No severity/confidence score is published on real current data.

### Contracts and lineage

Historical:
- contract `1.7`
- fingerprint `4b910bb2a6b3453e28aa1b4b59afe622661acd2ad7c50ffc7cd02127cddd8c76`

UI Payload:
- contract `1.11`
- fingerprint `07ed7e8999baf61154a2eb1239c95d6ff128347fc770589976ccfedc82f1086a`

Native:
- patch `native-anomaly-severity-confidence-v21`
- compatibility `v2-anomaly-severity-confidence-v11`
- fingerprint `1294f3832054dd6e36f3e6a5c18455fcc75740e172be1be4c64f8273a30d8697`

Upstream:
- SYT+ Processed: NOOP
- Mall Processed: NOOP
- Semantic: NOOP

### Runtime boundary

Enabled evidence machinery:
- `anomalyEligibilityGuardrails=true`
- `anomalyDetectionFoundation=true`
- `anomalySeverityConfidence=true`

Still disabled operationally:
- `anomalyDetection=false`
- `anomalySeverity=false`
- automatic alerts
- diagnosis
- causal claims
- production Data Mart/UI/index/deployment

### Next milestone — Diagnosis / Driver Attribution Foundation v1

The next layer should use sufficiently confident deviation candidates to identify factual contributors and supported hypotheses.

It must separate:
- measured contribution;
- association;
- diagnostic hypothesis;
- causal claim.

Causal claims and automatic alerts remain disabled.

## 38. Diagnosis / Driver Attribution Foundation v1

Validated on 2026-09-25.

Authoritative audit:
- `docs/diagnosis-driver-attribution-foundation-v1.md`

### Purpose

The system can now separate:
- exact identity contribution;
- co-moving association;
- unsupported diagnosis.

Allowed states:
- `ATTRIBUTED`
- `ASSOCIATION_ONLY`
- `NOT_DIAGNOSED`

Operational diagnosis remains disabled.

### Gates

Attribution requires:
- `DEVIATION_CANDIDATE`;
- Severity/Confidence = `ASSESSED`;
- confidence >= MEDIUM.

Anything else is `NOT_DIAGNOSED`.

### Exact business identities

Supported attribution targets:

1. `GMV = Product Clicks × CVR × AOV`
2. `Orders = Product Clicks × CVR`
3. `ROAS = Ads Attributed Sales / Ads Spend`
4. `Net Sales = Placed GMV - Cancelled Sales`
5. `Platform Cost Ratio = (Order Fees + Ads Spend) / Net Sales After Cancel`

Method:
`EXACT_SHAPLEY_ON_BUSINESS_IDENTITY`

Reference:
`CONTEXT_MATCHED_BASELINE_MEDIANS`

### Safety guards

A baseline-alignment residual > 25% blocks exact attribution and falls back to `ASSOCIATION_ONLY`.

Association source:
`CO_MOVING_DEVIATION_CANDIDATES_ONLY`

Association does not imply contribution or cause.

Every contribution and association explicitly carries causal claim = false.

### Synthetic validation

Controlled GMV decline:
- detector = DEVIATION_CANDIDATE;
- evidence confidence = HIGH;
- Product Clicks unchanged;
- CVR unchanged;
- AOV materially lower.

Result:
- GMV = `ATTRIBUTED`
- top driver = `placedAov`
- Shapley contributions close to the modeled identity difference
- causal claim = false.

The AOV candidate itself has no supported independent identity:
- AOV = `ASSOCIATION_ONLY`
- no fabricated contribution.

### Run #381 real result

Portfolio:
- `NOT_DIAGNOSED`
- attributed = 0
- association-only = 0
- not diagnosed = 60

SYT+:
- `NOT_DIAGNOSED`
- attributed = 0
- association-only = 0
- not diagnosed = 60

Mall:
- `NOT_DIAGNOSED`
- attributed = 0
- association-only = 0
- not diagnosed = 60

This is expected because current real data is still blocked before detector/diagnosis readiness.

### Contracts and lineage

Historical:
- contract `1.8`
- fingerprint `8dd1ff703235ed18767bf9ff669c717c994e66b91f862fee312eef0ff4cd1e41`

UI Payload:
- contract `1.12`
- fingerprint `67cfd56615654c02b1410be2ddf5f64058df6cf2d8bee7d155e4d2af48be985d`

Native:
- patch `native-driver-attribution-foundation-v22`
- compatibility `v2-driver-attribution-foundation-v12`
- fingerprint `a9bb0395baf99c0c4e82241b72c3d1bcfc7a0513fabd51ccc58dbcafbe46d851`

Upstream:
- SYT+ Processed: NOOP
- Mall Processed: NOOP
- Semantic: NOOP

### Runtime boundary

Enabled evidence machinery:
- `anomalyEligibilityGuardrails=true`
- `anomalyDetectionFoundation=true`
- `anomalySeverityConfidence=true`
- `driverAttributionFoundation=true`

Still operationally disabled:
- anomaly detection
- anomaly severity
- diagnosis
- automatic alerts
- causal claims
- production Data Mart/UI/index/deployment changes

### Next milestone — Smart Issues Foundation v1

The next layer should synthesize the validated evidence chain into a durable operator-facing issue object.

A Smart Issue should bind:
- affected KPI;
- anomaly evidence;
- severity/confidence;
- factual attribution or association boundary;
- context;
- lifecycle/data-quality constraints;
- unresolved uncertainty.

It must not yet send automatic alerts or prescribe actions without an explicit action-policy contract.

## 39. Smart Issues Foundation v1

Validated on 2026-09-25.

Authoritative audit:
- `docs/smart-issues-foundation-v1.md`

### Purpose

Smart Issues package the validated evidence chain into an operator-facing issue object.

Allowed states:
- `ISSUE_READY`
- `NO_ISSUE`

An issue is evidence synthesis only; it is not an alert, diagnosis, causal claim or autonomous recommendation.

### Issue gates

A Smart Issue requires:
- detector = `DEVIATION_CANDIDATE`;
- severity >= MEDIUM;
- confidence >= MEDIUM;
- attribution boundary = `ATTRIBUTED` or `ASSOCIATION_ONLY`.

Anything below those gates produces no issue.

### Issue evidence

Each issue carries:
- deterministic issue ID;
- affected KPI;
- latest trusted observation date;
- source comparator;
- current value / context-matched baseline / effect / modified Z;
- severity and confidence;
- attribution or association boundary;
- top identity contributor when available;
- Business Context and matched-sample evidence;
- lifecycle/history constraints;
- unresolved uncertainty.

Required uncertainty at the original #395 checkpoint included:
- `CAUSALITY_NOT_ESTABLISHED`;
- `AUTOMATIC_ALERTS_DISABLED`;
- `ACTION_POLICY_NOT_DEFINED`.

After Operator Action Policy v1 (#405), `ACTION_POLICY_NOT_DEFINED` is superseded by:
- `HUMAN_REVIEW_REQUIRED`;
- `PLATFORM_MUTATION_DISABLED`.

See Section 40.

### Deduplication and ranking

- max one issue per comparator;
- dedupe by affected KPI at scope level;
- max five issues per scope.

Ranking:
1. attribution status;
2. business KPI priority;
3. severity;
4. confidence;
5. absolute effect.

Primary business KPI priority prevents a derived ratio from displacing a more important GMV/Orders issue purely because its statistical score is larger.

### UI surface

Smart Issues belong to:
`LATEST_TRUSTED_OBSERVATION`

Native V2 maps them to **Ngày gần nhất** only.

The statistical source comparator such as `sameWeekday` remains inside the issue evidence and is not confused with the UI tab.

Foundation issue action copy:
- `Bằng chứng đã tổng hợp`

Operational diagnosis drawer remains disabled.

### Run #395 real result

Portfolio:
- `NO_ISSUE`
- issue count = 0

SYT+:
- `NO_ISSUE`
- issue count = 0

Mall:
- `NO_ISSUE`
- issue count = 0

This is expected because real current data does not yet contain a qualified deviation candidate.

### Contracts and lineage

Historical:
- contract `1.9`
- fingerprint `ffec9afddff8af536aecb8ef5cd890ab22830d50f2a502e095aba729ed5b5f8c`

UI Payload:
- contract `1.13`
- fingerprint `dfcceccf489224e2129512ecdec380b5ece58d794ea3edd9bb26d648871fa9b5`

Native:
- patch `native-smart-issues-foundation-v23`
- compatibility `v2-smart-issues-foundation-v13`
- fingerprint `dadfbf83b835f7b3fd21ba85ee5a49b35845d52b01e081a73db19d5df47aef45`

Upstream:
- SYT+ Processed: NOOP
- Mall Processed: NOOP
- Semantic: NOOP

### Runtime boundary

Enabled evidence machinery:
- anomaly eligibility guardrails;
- anomaly detection foundation;
- severity/confidence;
- driver attribution foundation;
- `smartIssuesFoundation=true`.

Still operationally disabled:
- anomaly detection;
- anomaly severity;
- diagnosis;
- `smartIssues=false`;
- automatic alerts;
- action recommendations;
- causal claims;
- production Data Mart/UI/index/deployment.

### Next milestone — Operator Action Policy Foundation v1

The next layer should convert `ISSUE_READY` evidence into reviewable action options.

Each action option must preserve:
- evidence lineage;
- why the action is relevant;
- prerequisites;
- KPI to monitor;
- verification/reversal checks;
- unresolved uncertainty.

No platform mutation or automatic business action should be permitted in the foundation version.

## 40. Operator Action Policy Foundation v1

Validated on 2026-09-25.

Authoritative audit:
- `docs/operator-action-policy-foundation-v1.md`

### Purpose

Convert a qualified `ISSUE_READY` Smart Issue into bounded review options without enabling autonomous business actions.

Allowed scope states:
- `ACTION_OPTIONS_READY`
- `NO_ACTION_OPTIONS`

Every option:
- `status=REVIEW_OPTION`
- `executionMode=HUMAN_REVIEW_ONLY`

### Review-option policy

Every Smart Issue may receive:
1. `VALIDATE_EVIDENCE_BEFORE_CHANGE`
2. one targeted driver-review option when exact attribution supports it.

Targeted review is only allowed for:
- `ATTRIBUTED`;
- supported quantified top driver.

`ASSOCIATION_ONLY` receives evidence validation only.

Current targeted review rules cover:
- Product Clicks;
- CVR;
- AOV;
- Ads Spend;
- Ads Attributed Sales;
- Cancelled Sales;
- Order Fees;
- Net Sales After Cancel.

These are investigation/review options, not instructions to change the business.

### Required action evidence

Each option includes:
- source issue ID;
- scope and observation date;
- affected KPI;
- source comparator;
- severity/confidence/attribution lineage;
- why the option is relevant;
- prerequisites;
- monitor KPIs;
- verification checks;
- stop/reversal checks;
- unresolved uncertainty.

### Hard safety boundary

Every option keeps:
- `requiresHumanReview=true`
- `prescriptiveRecommendation=false`
- `platformMutationAllowed=false`
- `automaticExecutionEligible=false`
- `automaticAlertEligible=false`
- `causalClaimEligible=false`

Explicitly forbidden directives include:
- changing bid/budget;
- changing price/promotion;
- pausing campaign;
- publishing listing changes;
- automatic customer contact.

### Smart Issue uncertainty advancement

Because an Action Policy now exists, current Smart Issues no longer claim:
`ACTION_POLICY_NOT_DEFINED`

Current uncertainty instead preserves:
- `CAUSALITY_NOT_ESTABLISHED`
- `AUTOMATIC_ALERTS_DISABLED`
- `HUMAN_REVIEW_REQUIRED`
- `PLATFORM_MUTATION_DISABLED`

### Synthetic validation

Attributed GMV/AOV case:
- Smart Issue = ISSUE_READY
- action policy = ACTION_OPTIONS_READY
- 2 options:
  - evidence validation;
  - AOV/price/promotion-mix review.
- no mutation/execution.

Association-only case:
- Smart Issue = ISSUE_READY
- only generic evidence validation;
- no targeted driver action.

NO_ISSUE case:
- `NO_ACTION_OPTIONS`
- 0 options.

### Run #405 real result

Portfolio:
- Smart Issue = `NO_ISSUE`
- Action Policy = `NO_ACTION_OPTIONS`
- option count = 0

SYT+:
- Smart Issue = `NO_ISSUE`
- Action Policy = `NO_ACTION_OPTIONS`
- option count = 0

Mall:
- Smart Issue = `NO_ISSUE`
- Action Policy = `NO_ACTION_OPTIONS`
- option count = 0

This is expected while current history/context readiness remains insufficient for real anomaly candidates.

### Contracts and lineage

Historical:
- contract `2.0`
- fingerprint `9deab0fa9a5ce8261ea28d617e374de8f1e094bfd68c750b2a7f00a011f64f31`

UI Payload:
- contract `1.14`
- fingerprint `3fd323cfe6ff1c4943353909b1b83d6c012f3c98c22307e8690cbe8a66f2ceff`

Native:
- patch `native-operator-action-policy-v24`
- compatibility `v2-operator-action-policy-v14`
- fingerprint `19fbed9f4b631e3c21ea1a9e629f8f910051efe7aae08b3106626871dbd9e7c6`

Upstream:
- SYT+ Processed: NOOP
- Mall Processed: NOOP
- Semantic: NOOP

### Runtime boundary

Enabled foundation machinery:
- anomaly eligibility;
- anomaly detection foundation;
- severity/confidence;
- driver attribution;
- Smart Issues;
- `operatorActionPolicyFoundation=true`.

Still operationally disabled:
- anomaly detection/severity;
- diagnosis;
- Smart Issues actions;
- `operatorActions=false`;
- automatic alerts;
- automatic execution;
- platform mutation;
- causal claims;
- production Data Mart/UI/index/deployment.

### Next milestone — Production Cutover Readiness / Shadow Mode v1

The intelligence and operator-policy stack is now structurally complete.

The next milestone should validate it across real refresh cycles in shadow mode and define:
- readiness gates;
- stability rules;
- issue/action appearance and disappearance semantics;
- rollback controls;
- activation controls;
- production cutover checklist.

No production cutover should occur automatically.

## 41. Production Cutover Readiness / Shadow Mode v1

Implementation date: 2026-09-25  
Latest canonical GitHub validation: run `36166448309` (#409) — **PASS**  
Production cutover: **not authorized**

This batch adds a durable, observe-only shadow layer around the completed intelligence and Operator Action Policy stack. It measures readiness over distinct real refreshes without activating production behavior.

### Contract advancement

- Historical Intelligence contract: `2.1`
- UI Payload contract: `1.15`
- Native patch: `native-production-shadow-mode-v25`
- V2 compatibility patch: `v2-production-shadow-mode-v15`
- mode: `PREPRODUCTION_OBSERVE_ONLY`

The supported shadow statuses are:

- `SHADOW_OBSERVING`
- `READY_FOR_HUMAN_CUTOVER_REVIEW`
- `CUTOVER_BLOCKED`

`READY_FOR_HUMAN_CUTOVER_REVIEW` is readiness evidence only. It never authorizes cutover.

### Durable refresh evidence

Each staging run supplies a refresh ID built from `github.run_id + github.run_attempt`. The history artifact now persists `shadow_mode_state.json`, and the next same-month run restores the latest successful non-expired state before building new history.

The rules are fail-closed:

- only a distinct refresh ID advances counters;
- retrying the same ID is idempotent;
- missing prior state starts a new observation sequence;
- source-period or trusted-month regression blocks readiness;
- only the configured recent refresh window is retained.

### Lineage and transition model

Every shadow snapshot records:

- as-of period;
- trusted Semantic months and fingerprints;
- Business Context fingerprint;
- deterministic source snapshot key;
- all enabled Portfolio and Shop scopes.

Deterministic Smart Issue and Action Option IDs are classified on each distinct refresh as:

- appeared;
- persisted;
- disappeared.

Every current Action Option must reference a current Smart Issue. An action cannot persist after its source issue disappears. A change in issue/action state resets the consecutive stability counter.

### Readiness gates

All eight gates must pass:

1. `TRUSTED_LINEAGE_COMPLETE`
2. `LINEAGE_CONTINUITY`
3. `ALL_ENABLED_SCOPES_PRESENT`
4. `FAIL_CLOSED_SAFETY`
5. `ISSUE_ACTION_TRANSITIONS_VALID`
6. `MINIMUM_SAFE_REFRESHES`
7. `MINIMUM_STABLE_REFRESHES`
8. `HUMAN_VISUAL_BASELINE_RETAINED`

The minimum evidence is 3 consecutive safe refreshes and 3 consecutive stable refreshes. The accepted visual baseline remains run `#216`.

### Activation and rollback boundary

Always false in this milestone:

- production activation;
- automatic cutover;
- cutover authorization;
- production writes;
- automatic alerts;
- platform mutation.

Explicit human approval remains mandatory after all gates pass. The legacy production path is retained as the rollback target; rollback preparation is required before any future activation, and automatic rollback is not introduced here.

### Propagation and UI boundary

Shadow evidence flows through:

`Historical Intelligence → canonical UI Payload → Native V2 bundle`

The bundle exposes evidence for audit but adds no activation control and makes no visual change to the approved production V2 foundation.

### Local validation

- repository test suite: **133/133 PASS**;
- repeated-refresh idempotency: PASS;
- three-refresh readiness progression: PASS;
- issue/action disappearance semantics: PASS;
- lineage-regression blocking: PASS;
- cutover remains false after gates pass: PASS;
- JSON contracts: parse PASS;
- Python compileall: PASS;
- production V2 template validation: PASS;
- configuration validation reached only the expected local missing-secret guard.

### Canonical observation 1

Run `36163777627` (#407), commit `f3ece03c7e52d829139481e09b2a11539ce254bb`, completed successfully on 2026-09-25:

- `core-tests`: PASS;
- full all-shop September `staging`: PASS;
- refresh ID: `36163777627-1`;
- shadow status: `SHADOW_OBSERVING`;
- sequence / consecutive safe / consecutive stable: `1 / 1 / 1`;
- lineage: `INITIALIZED`, valid and complete;
- failed gates: none;
- pending gates: `MINIMUM_SAFE_REFRESHES`, `MINIMUM_STABLE_REFRESHES`;
- Historical fingerprint: `f7e4bccea88a06614279d43e6dfcde2235e73b32c1d7e00b1c404fb3135172f9`;
- UI Payload fingerprint: `ee828633b42fec15a759d11ff9fa7bc8b909f6d3b6cbfa29720f953d5d50b5ef`;
- Native fingerprint: `1706c59f67b1d8db6fe25a29c0532ec0c9c8f4c33c7129d828574623a408d801`;
- production activation/cutover/writes/deployment, automatic alerts and platform mutation remain false.

Observation 1 is valid readiness evidence, but at least two more distinct successful refreshes are still required before a human Cutover Readiness Review.

### Canonical observation 2

Run `36165107810` (#408), commit `36a3e16317be068c5362d25fd2e602b3979a278f`, completed successfully on 2026-09-26:

- `core-tests`: PASS;
- full all-shop September `staging`: PASS;
- refresh ID: `36165107810-1`;
- previous refresh ID: `36163777627-1`;
- shadow status: `SHADOW_OBSERVING`;
- sequence / consecutive safe / consecutive stable: `2 / 2 / 2`;
- lineage: `CONSISTENT`, valid and complete;
- source snapshot key remained `4165d021b6faf0b8f9e9255a4845c7a3f109e1fc9aca99597c25df4889ac2b10`;
- failed gates: none;
- pending gates: `MINIMUM_SAFE_REFRESHES`, `MINIMUM_STABLE_REFRESHES`;
- Historical fingerprint: `e8872de70b6568c8ea865eca23de34fecb3c8fe1db48b4a69558de94393065a7`;
- UI Payload fingerprint: `43ec276ff68eb063d91ea798c5b09a2855e5f13c991e4dfd8133d1a68fc89d5a`;
- Native fingerprint: `0b20678448d9ff2da75166624d125556aaf518950e5479b1303f0d3d0a9ab57f`;
- history artifact ID: `10877686004`, digest `sha256:826f7d3ed2f909a2aed49df1b5f30e0e5eb1a4085af8b6b80fd006406a4abbd5`;
- production activation/cutover/writes/deployment, automatic alerts and platform mutation remain false.

Observation 2 proves durable same-month state restoration and lineage continuity. One more distinct successful refresh is still required before a human Cutover Readiness Review.

### Canonical observation 3

Run `36166448309` (#409), commit `32e486e9ee009079c3ffc00d8eb0d1358ca19336`, completed successfully on 2026-09-26:

- `core-tests`: PASS;
- full all-shop September `staging`: PASS;
- refresh ID: `36166448309-1`;
- previous refresh ID: `36165107810-1`;
- shadow status: `READY_FOR_HUMAN_CUTOVER_REVIEW`;
- sequence / consecutive safe / consecutive stable: `3 / 3 / 3`;
- lineage: `CONSISTENT`, valid and complete;
- source snapshot key remained `4165d021b6faf0b8f9e9255a4845c7a3f109e1fc9aca99597c25df4889ac2b10` across observations 1–3;
- all eight readiness gates: PASS;
- failed gates: none;
- pending gates: none;
- Historical QA: `17/17 PASS`;
- Historical fingerprint: `633d754808b8650bb357646bbbc9127a1cf5fe21c98d2680ed3a01af5241ea1e`;
- UI Payload fingerprint: `97b83b7d491b7ec47a4803a62f652fcc53dd8d0ce604a2d917b87eea3df6d75c`;
- Native QA: `33/33 PASS`;
- Native fingerprint: `0f712159ee14398936e3667b68966b65f403fc452cd28025ddd3cedf46dbd223`;
- source production V2 SHA256 remained `9540f23b4d9537441e3bd4cdeafd15747ab4280a87a0130d223984009d99c952`;
- history artifact ID: `10877828363`, digest `sha256:9caffa79a10ff5fdf54fa2a310acd879c63e77e8900f39f4d058bed7dc4cd885`;
- Native V2 artifact ID: `10877143917`, digest `sha256:403bd90dff0c760430eb17cfc748b07d9b7e9f306b56e9f695f6d5d5d4504a7e`;
- production activation/cutover/writes/deployment, automatic alerts and platform mutation remain false.

Observation 3 completes the automated shadow-readiness evidence. It makes the batch eligible for a human review; it does not authorize cutover.

### UI canary smoke checkpoint

The exact Native V2 HTML from run #409 was opened as a local read-only canary and passed an operator browser smoke check:

- Command Center Portfolio rendered;
- Shop scope and SYT+/Mall switching rendered and updated bound data;
- the separate Compare destination rendered its business-analysis sections;
- dark mode worked;
- the document had meaningful content, no framework error overlay and no browser console errors;
- `PREPRODUCTION` remained visible and all production safety flags remained false.

This smoke check does not replace explicit human visual acceptance. Run #216 remains the accepted visual/interaction baseline until the #409 canary is reviewed and approved.

Audit: `docs/production-cutover-shadow-mode-v1.md`

### Next milestone — Human Cutover Readiness Review

Review and approve the #409 UI canary, confirm rollback preparedness, and conduct the human Cutover Readiness Review. Production activation remains a separate explicitly approved action.
