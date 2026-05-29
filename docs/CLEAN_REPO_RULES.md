# FutureFunded Clean Repo Rules

This repo was created from committed HEAD only.

## Hard rules

- Do not blindly rewrite `ff.css`.
- Do not copy old backup CSS or generated audit output into active source.
- Do not edit payment, checkout, Stripe, PayPal, sponsor, share, QR, modal, or dashboard token hooks without a contract audit.
- Preserve `data-ff-*` hooks as product contracts.
- Every UI patch must include:
  - safety tag
  - route smoke
  - CSS brace check
  - mobile/tablet/desktop screenshots
  - rollback command

## CSS ownership

- `apps/web/app/static/css/ff.css`: shared tokens/base/platform/operator authority.
- `apps/web/app/static/css/campaign.css`: public campaign authority.
- `apps/web/app/static/css/onboarding.css`: onboarding-specific authority if linked.
- Verify homepage CSS links before creating or relying on `platform-home.css`.

## Launch surfaces

- `/platform/`
- `/c/connect-atx-elite`
- `/platform/login`
- `/platform/dashboard`
- `/platform/onboarding`

Screenshots beat “tests pass.”
