# FutureFunded Release Map

Generated: `2026-05-19T21:04:16.815973+00:00`

## Release surfaces

| Surface | Route | Status | Required audits |
|---|---:|---|---|
| Platform homepage | `/platform/` | Active | visual surface board |
| Campaign demo | `/c/connect-atx-elite` | Active | visual surface board, payment smoke where needed |
| Launch workspace | `/platform/onboarding` | Active | visual surface board |
| Operator login | `/platform/login` | Active | visual surface board |
| Protected dashboard | `/platform/dashboard` | Active/private | protected exec, final polish, visual surface board |
| Locked dashboard | `/platform/dashboard` without token | Active/403 | protected exec, visual surface board |

## Current release gate command set

```bash
FF_BASE_URL="https://getfuturefunded.com" node scripts/audit/ff_dashboard_protected_exec_audit.mjs
FF_BASE_URL="https://getfuturefunded.com" node scripts/audit/ff_dashboard_final_polish_audit.mjs
FF_BASE_URL="https://getfuturefunded.com" node scripts/audit/ff_visual_surface_board.mjs
```

## Freeze rule

Do not add new pages, duplicate CSS authorities, or duplicate JS authorities until the registry is updated and the release gate remains green.

## Current live asset map

| Surface | Route | CSS | JS | Status |
|---|---:|---:|---:|---|
| Platform homepage | `/platform/` | 6 | 2 | Active |
| Campaign demo | `/c/connect-atx-elite` | 9 | 9 | Active |
| Launch workspace | `/platform/onboarding` | 6 | 1 | Active |
| Operator login | `/platform/login` | 5 | 1 | Active |
| Protected dashboard | `/platform/dashboard` with token | 6 | 2 | Active/private |
| Locked dashboard | `/platform/dashboard` without token | 3 | 0 | Active/403 |

