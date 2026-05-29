# FutureFunded Sister Demo Handoff

## Current mode

FutureFunded is configured for test-payment demo mode.

No live money should move during this demo. Stripe live keys should only be added after the campaign owner approves the experience and is ready to accept real donations.

## Demo pages

- Platform: http://127.0.0.1:5000/platform/
- Campaign: http://127.0.0.1:5000/c/connect-atx-elite
- Login: http://127.0.0.1:5000/platform/login
- Dashboard: use the private operator token URL only

## What to review

1. Campaign story and trust level
2. Give securely / checkout experience
3. Sponsor package flow
4. Share and QR flow
5. Dashboard/operator readiness
6. Copy, tone, images, and team details

## Gates passed

- Launch quality gate
- Campaign payment/sponsor/share smoke
- Visual screenshot ratchet
- Payment readiness gate
- Stripe test-payment demo mode
- Secret hygiene scan

## Live money handoff

Only after approval:

1. Campaign owner creates or confirms Stripe account
2. Add live Stripe publishable key and secret key to deployment environment
3. Set live mode flags
4. Run final live-mode launch gate
5. Send campaign link to donors and sponsors
