# FutureFunded Product Spine

This is the clean, launch-focused FutureFunded application spine.

## Core launch surfaces

- `/platform/`
- `/c/connect-atx-elite`
- `/platform/login`
- `/platform/dashboard`
- `/platform/onboarding`

## CSS authority

- `apps/web/app/static/css/ff.css` — shared platform/system CSS
- `apps/web/app/static/css/campaign.css` — public campaign CSS
- `apps/web/app/static/css/onboarding.css` — onboarding CSS

## Patch rules

- No blind global CSS rewrites.
- No template edits without a route/DOM contract audit.
- Preserve `data-ff-*` hooks.
- Every UI patch needs route smoke, CSS brace check, screenshots, and rollback.
