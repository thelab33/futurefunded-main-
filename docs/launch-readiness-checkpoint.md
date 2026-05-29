# FutureFunded Launch Readiness Checkpoint

## Status

FutureFunded is at a stable MVP launch checkpoint.

## Closed Waves

- Wave 0 — Launch audit
- Wave 1 — Button/function sweep
- Wave 2A — Lifecycle messaging
- Wave 2B — CTA hierarchy
- Wave 2C — Public source cleanup
- Wave 2D — Lifecycle provider readiness
- Wave 2E — CSS authority
- Wave 2F — JS selector contract
- Wave 3 — Operator/onboarding polish
- Wave 4 — Final funnel smoke

## Current launch truth

- Blockers: 0
- High issues: 0
- Local platform: 200
- Local onboarding: 200
- Local campaign: 200
- Live platform: 200
- Live campaign: 200
- Dashboard: protected with intentional operator locked state
- Donation contract: present
- Sponsor contract: present
- Share contract: present
- Embedded checkout shell: present
- Lifecycle messages: preview-spooled and idempotency-protected
- SMTP: pending provider credentials

## Canonical CSS

- apps/web/app/static/css/ff.css
- apps/web/app/static/css/ff.checkout.css
- apps/web/app/static/css/platform-home.css

## Remaining known non-blockers

- SMTP delivery is not configured yet; lifecycle messages currently preview-spool.
- Remaining stale/demo markers are internal/tooling only.
- Production is running under PM2 + Cloudflare tunnel.

## Next product phase

1. Visual review of onboarding/dashboard as operator workflow.
2. Real Stripe test donation and sponsor checkout smoke.
3. SMTP provider setup.
4. Mobile viewport QA.
5. Final copy/brand pass before broader demo.
