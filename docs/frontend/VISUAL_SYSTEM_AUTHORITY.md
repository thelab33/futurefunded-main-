# FutureFunded Visual System Authority

FutureFunded’s public product surfaces should feel like one premium fundraising SaaS:
warm, mobile-first, donor-safe, sponsor-ready, institutionally credible, and white-label ready.

## CSS Authority

| File                                                | Role                                                                                      |
| --------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| `apps/web/app/static/css/ff.css`                    | Shared tokens, type rhythm, layout primitives, cards, buttons, forms, trust components    |
| `apps/web/app/static/css/ff.homepage-flagship.css`  | Platform homepage composition and marketing sections                                      |
| `apps/web/app/static/css/ff.ui-micropolish.css`     | Public campaign page composition, donation/sponsor storytelling, campaign-specific polish |
| `apps/web/app/static/css/ff.operator-dashboard.css` | Login, dashboard, onboarding, operator surfaces                                           |

## Rules

1. Do not add one-off global polish files.
2. Do not load an extra final handoff CSS file unless all page audits are updated and screenshots approve it.
3. Shared visual decisions belong in `ff.css`.
4. Homepage-only layout belongs in `ff.homepage-flagship.css`.
5. Campaign-only layout belongs in `ff.ui-micropolish.css`.
6. Operator/internal layout belongs in `ff.operator-dashboard.css`.
7. Public campaign and homepage should share:
   - warm background language
   - restrained orange/accent use
   - same card radius system
   - same button behavior
   - same typography rhythm
   - same mobile-first spacing scale
   - same trust/sponsor-safe tone

## Current Clean Runtime CSS Stacks

Homepage:

- `ff.css`
- `ff.homepage-flagship.css`

Campaign:

- `ff.css`
- `ff.ui-micropolish.css`

Login/Dashboard/Onboarding:

- `ff.css`
- `ff.operator-dashboard.css`
