# FutureFunded Live Launch Runbook

## Phase 1 — Demo-safe

Required:

- Surface board green
- Dashboard board green
- Campaign payment smoke green
- Money ops current gate green
- Live Stripe blocked
- Email dry-run enabled

## Phase 2 — Test-payment-safe

Required:

- Stripe test keys configured privately
- Stripe test webhook secret configured privately
- Signed webhook proof green
- Ledger/export/dashboard proof green
- Donor receipt preview generated
- Operator alert preview generated

## Phase 3 — Real-email-safe

Required:

- SMTP/provider credentials configured privately
- Controlled real-send switch enabled
- Exactly two proof emails sent
- Donor receipt arrives in controlled inbox
- Operator alert arrives in controlled inbox
- No family/donor/sponsor blast

## Phase 4 — Production-ready

Required:

- Managed DB provisioned
- Production secrets in hosting secret manager
- Live Stripe keys rotated and configured
- Stripe live webhook endpoint configured
- Live kill switch documented
- Backup/restore documented
- Rollback command documented
- Final board/gate run green

## Commands

- `FF_BASE_URL="https://YOUR_DOMAIN" bash scripts/release/ff_platform_live_readiness_gate.sh`
- `FF_BASE_URL="https://YOUR_DOMAIN" bash scripts/release/ff_money_ops_current_gate.sh`
- `scripts/release/ff_email_real_send_controlled.sh`
- `bash scripts/release/ff_production_ops_gate.sh`

## Stop conditions

Stop launch if:

- Any payment webhook proof fails.
- Dashboard ledger/export fails.
- Email delivery sends to the wrong recipient.
- Live keys appear in git.
- Production DB is local SQLite.
- Screenshot board fails.
