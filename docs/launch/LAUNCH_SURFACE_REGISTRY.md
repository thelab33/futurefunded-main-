# FutureFunded Launch Surface Registry

## Canonical flagship launch surfaces

These are the only pages that receive flagship screenshot boards and visual polish passes.

| Surface | Canonical URL | data-ff-page | Board policy |
|---|---|---|---|
| Homepage | `/` | `platform` | Board + polish |
| Campaign | `/c/connect-atx-elite` | `campaign` | Board + polish |
| Onboarding | `/platform/onboarding` | `platform-onboarding` | Board + polish |
| Private Dashboard | `/platform/dashboard?access_token=...` | `platform-dashboard` | Tokened board + polish |

## Non-flagship governed routes

These must remain functional, but do not get flagship boards unless product strategy changes.

| Bucket | Routes | Policy |
|---|---|---|
| Homepage aliases | `/platform`, `/platform/` | Eventually canonicalize/redirect to `/` |
| Onboarding alias | `/platform/onboarding/` | Eventually canonicalize/redirect to `/platform/onboarding` |
| Auth support | `/login`, `/logout`, `/platform/login`, `/platform/logout`, `/platform/register`, `/platform/invite`, `/platform/mfa`, `/platform/forgot-password`, `/platform/reset-password` | Functional + basic polish only |
| Legal/support | `/contact`, `/privacy`, `/terms`, `/legal/privacy`, `/legal/terms` | Simple, accessible, trustworthy |
| Protected dashboard variants | `/dashboard`, `/platform/dashboard/` | 403 or safe redirect is acceptable |
| System | `/robots.txt`, `/sitemap.xml`, `/security.txt`, `/.well-known/security.txt`, `/healthz`, `/site.webmanifest` | Functional smoke only |
| Campaign dynamic/API | `/c/<slug>/...` | Functional smoke with `connect-atx-elite` |

## Production rule

Do not add a new flagship page unless it is added to this registry and receives:
1. route governance classification
2. screenshot board
3. served URL audit
4. green commit tag
