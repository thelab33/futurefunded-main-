# FutureFunded Secret Rotation Checklist

Rotate before production if any secret appeared in terminal output, screenshots, chat, docs, or logs.

## Stripe

Rotate:

- Test secret key
- Test webhook secret
- Live secret key before launch if generated early
- Live webhook secret after final endpoint setup if exposed

Never commit:

- `sk_test_*`
- `sk_live_*`
- `rk_live_*`
- `whsec_*`

## Email

Rotate or regenerate:

- SMTP password
- SendGrid API key
- Postmark server token
- Gmail app password

## App

Rotate:

- `SECRET_KEY`
- Admin PIN or setup token
- Operator bootstrap credentials

## Database

Use hosting/provider secret manager for:

- Production `DATABASE_URL`
- Backup credentials
- Restore credentials

## Verification

- `scripts/release/ff_env_sanity_check.sh .env`
- `FF_BASE_URL="http://127.0.0.1:5000" bash scripts/release/ff_money_ops_current_gate.sh`
- `bash scripts/release/ff_production_ops_gate.sh`
