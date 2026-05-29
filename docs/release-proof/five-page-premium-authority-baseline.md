# FutureFunded Five-Page Premium Authority Baseline

Status: Approved unified product UI baseline.

Locked surfaces:
- `/platform/`
- `/c/connect-atx-elite`
- `/platform/login`
- `/platform/dashboard`
- `/platform/onboarding`

Authority files:
- `apps/web/app/static/css/ff.css`
- `apps/web/app/static/css/platform-home.css`
- `apps/web/app/static/css/campaign.css`
- `apps/web/app/static/css/login.css`
- `apps/web/app/static/css/dashboard.css`
- `apps/web/app/static/css/onboarding.css`

Approved checkpoints:
- Homepage/login authority: `homepage-login-approved-baseline-v81`
- Campaign authority: `campaign-approved-baseline-v6`
- Dashboard/onboarding authority: `operator-onboarding-premium-authority-v1`

Proof expectations:
- Public UX + money smoke gate passes.
- Visual surface board passes 12/12.
- Overflow flags: 0.
- Campaign checkout hooks preserved.
- Sponsor hooks preserved.
- Share/QR hooks preserved.
- Dashboard token/export/ledger hooks preserved.
- Onboarding launch workspace hooks preserved.

Launch decision:
Do not continue broad redesign before launch. Future work should be restricted to:
- live payment readiness
- endpoint/webhook verification
- accessibility/functional smoke tests
- tiny visual polish only when backed by screenshots
