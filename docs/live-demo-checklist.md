# FutureFunded Live Demo Checklist

## Pre-demo checks

Run these from the repo root:

- git status --short
- pm2 status
- curl -fsS http://127.0.0.1:5000/healthz | python -m json.tool
- scripts/audit/ff_wave4_final_funnel_smoke.sh
- python scripts/audit/ff_wave5c_stripe_checkout_smoke.py
- timeout 240s node scripts/audit/ff_wave10a_sponsor_sales_scout.mjs
- python scripts/audit/ff_wave10b_sponsor_metadata_smoke.py
- python scripts/audit/ff_wave10c_dashboard_review_queue_scout.py
- timeout 240s node scripts/audit/ff_wave6_founder_demo_scout.mjs
- python scripts/audit/ff_launch_contract_audit.py

## Route checks

- https://getfuturefunded.com/platform/
- https://getfuturefunded.com/platform/onboarding
- https://getfuturefunded.com/c/connect-atx-elite
- Private dashboard URL with operator token

## Visual checks

- Platform homepage looks polished and product-led.
- Onboarding workspace is stable and not broken into a skinny rail.
- Campaign page is mobile-first and emotionally credible.
- Sponsor intake is visible and clear.
- Dashboard sponsor queue renders.

## Money-path checks

- Donate CTA opens checkout flow.
- Sponsor package CTA opens sponsor flow.
- Stripe smoke passes.
- Sponsor metadata smoke passes.
- Dashboard queue scout passes.

## Safety checks

Do not show:

- API tokens
- Stripe secrets
- Postmark credentials
- Cloudflare token
- Raw environment files
- Internal private URLs unless intentional
