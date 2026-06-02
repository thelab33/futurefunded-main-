# FutureFunded Private Config Handoff

FutureFunded is demo-safe and proof-backed. Private provider values must stay outside git.

## Never commit

- `.env`
- `.env.*`
- `.env.email.local`
- `audit_outputs/`
- `.ff_backups/`
- Stripe secrets
- SMTP/API tokens
- production database URLs
- admin/operator bootstrap secrets

## Configure privately before live users

### Stripe

Use test mode first:

- `STRIPE_PUBLIC_KEY`
- `STRIPE_PUBLISHABLE_KEY`
- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `FF_STRIPE_WEBHOOK_SECRET`
- `STRIPE_WEBHOOK_SIGNING_SECRET`

Before final live mode:

- rotate exposed test secrets
- configure live webhook endpoint in Stripe
- run test-mode proof again
- run final live-payment gate only after all test gates pass

### Email

Configure SMTP/provider credentials privately:

- `FF_EMAIL_TEST_TO`
- `FF_OPERATOR_NOTIFY_EMAIL`
- `FF_EMAIL_FROM`
- `FF_EMAIL_REPLY_TO`
- `FF_SMTP_HOST`
- `FF_SMTP_PORT`
- `FF_SMTP_USERNAME`
- `FF_SMTP_PASSWORD`
- `FF_SMTP_USE_TLS`
- `FF_SMTP_USE_SSL`

Controlled real-send switch:

- `FF_EMAIL_REAL_SEND_CONFIRM=SEND_TEST_EMAIL`

This must send only two proof emails before any donor/family/sponsor email is enabled.

### Database

Local SQLite is acceptable for demo/dev. Live users require a managed production database and provider-managed backups.

## Proof commands

- `FF_BASE_URL="http://127.0.0.1:5000" bash scripts/release/ff_platform_live_readiness_gate.sh`
- `FF_BASE_URL="http://127.0.0.1:5000" bash scripts/release/ff_money_ops_current_gate.sh`
- `bash scripts/release/ff_production_ops_gate.sh`
