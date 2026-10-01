# Command Center V2 — Production UI Rollout

## Default / fallback

Production entrypoint is a dual encrypted UI artifact.

- Default: Command Center V2
- Immediate fallback: append \`?ui=v1\` to the same production URL
- Both UI versions receive the exact same production payload
- Switching UI does not rebuild or mutate Data Mart

This means a V2 rendering bug can be isolated from data and intelligence logic immediately.

## UI contract

V2 is presentation-only.

It reads:
- \`payload.commandCenter.periods\`
- \`payload.commandCenter.productSignals\`
- \`payload.commandCenter.featureHealth\`
- \`payload.health.sources\`
- \`payload.meta\`

It does not:
- calculate canonical KPIs from raw data,
- rank products,
- aggregate Ads campaigns,
- mutate Data Mart,
- infer missing production data.

If the production payload is missing, V2 stops with a clear data-unavailable message.
Mock/demo data is not allowed in the production template.

## Optional-feature degradation

Core Command Center remains usable if an optional feature is degraded.

Examples:
- Product Ads Mart DEGRADED -> historical shop KPI modules stay usable.
- Product Intelligence DEGRADED -> Product Opportunity / Problem section is suppressed; Data Health shows the degraded module.
- No high-confidence product signal -> product signal section stays hidden by design.

## UI safeguards kept from D2

- Brand accent: #045433
- Black / white primary neutrals
- \`transform: scale(1.25)\` is preserved
- Sidebar pin / auto-hide / hover-peek behavior is preserved
- Dark mode is preserved
- Diagnostic modal stays fixed to viewport center and independent from the scaled app root
- Logo is embedded into the template, so no external asset path can break it

## Production gates

Before running source refresh / publish, production GitHub Actions now checks:
1. V2 template static contract
2. JavaScript syntax for every inline script
3. no preview/mock dependency
4. embedded logo
5. scale 1.25
6. sidebar / drawer / dark-mode hooks
7. Product Ads + Product Intelligence health hooks
8. dual UI artifact unit tests

## Canary path

Branch \`ui-v2-production-adapter\` builds a read-only canary from the current production Data Mart.

Canary does not:
- run source_processor in write mode,
- update state,
- publish production,
- modify Google Sheets.

It only reads production mart, builds the exact payload, encrypts V2 + V1 fallback, and commits branch \`index.html\` for Vercel Preview.

## Debug order for UI incidents

1. Add \`?ui=v1\`.
2. If V1 is healthy with the same payload -> issue is V2 renderer/template.
3. If both V1 and V2 are wrong -> inspect payload / Command Center data layer.
4. Check \`commandCenter.featureHealth\`.
5. Only inspect Product Ads mart when \`productAdsMart\` is DEGRADED.
6. Only inspect Product Intelligence when \`productIntelligence\` is DEGRADED.

This prevents a visual bug from being misdiagnosed as a Data Mart or pipeline failure.
