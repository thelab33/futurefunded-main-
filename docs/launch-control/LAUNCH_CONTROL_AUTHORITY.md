# FutureFunded Launch Control Authority

## Clean root

Use this repo as the new source of truth:

    ~/futurefunded-main

The old repo remains an archive/source reference only:

    ~/futurefunded-product-spine

## CSS authority

- apps/web/app/static/css/ff.css is global foundation CSS.
- apps/web/app/static/css/campaign.css is campaign-only CSS.
- apps/web/app/static/css/onboarding.css is onboarding-only CSS.
- apps/web/app/static/css/auth.css is auth/login-only CSS.

## Patch rule

No append-only CSS patches.

Every future CSS change must:

1. create a backup outside app source,
2. remove/replace the older concern block,
3. pass lint or brace checks,
4. show exact diff stat,
5. not touch unrelated surfaces.

## Proof authority

- Demo start: bash scripts/demo/ff-demo-start.sh
- Campaign money proof: node scripts/campaign-payment-smoke.mjs
- Fast proof: bash scripts/demo/ff-fast-proof-strict.sh
- Product doctor: npm run doctor

## Generated artifact policy

Generated/local artifacts stay ignored:

- audit_outputs/
- downloads/
- .rollback/
- node_modules/
- .venv/
- *.bak-*
- *.tmp
- *.log
