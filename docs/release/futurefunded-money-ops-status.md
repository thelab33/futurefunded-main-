# FutureFunded Money Ops Status

Generated: `20260601015645`

## Current status

FutureFunded has a locked frontend/demo baseline. The campaign page, checkout opener, visual boards, login, onboarding, and dashboard surfaces are green.

The real-money operations layer is not fully production-ready until database, webhook, email delivery, and completed donation storage are proved end-to-end.

## What exists

- Campaign checkout session route exists.
- Campaign checkout session status route exists.
- Campaign ledger summary route exists.
- Campaign ledger events route exists.
- Campaign CSV export route exists.
- Offline donation route exists.
- Stripe webhook route exists.
- PayPal order and capture routes exist.
- Email lifecycle code exists.
- Email doctor can spool donor receipt, sponsor confirmation, operator donation alert, and operator sponsor alert previews.

## Current blockers

| Area | Blocker |
|---|---|
| Database | Active money DB is not confirmed for current repo/runtime |
| Stripe | Local secret/publishable/webhook env is missing |
| Webhook | Route exists, but signed event processing needs test proof |
| PayPal | Sandbox credentials missing |
| Email | SMTP/provider config missing; currently preview spool only |
| Receipts | No completed donation record found |
| Dashboard ledger | Needs proof from real stored donation records |
| CSV export | Needs proof from real stored donation records |
| Old gates | Some old release gates reference removed/renamed audit files |

## Safe next target

Money Ops Pass 1 should prove this in test mode:

1. Active database path is inside current repo or production database.
2. Stripe test keys are loaded.
3. Stripe webhook secret is loaded.
4. A test checkout session is created.
5. A completed/simulated paid event writes to ledger.
6. Donor receipt is generated.
7. Operator alert is generated.
8. Dashboard ledger reads the stored record.
9. CSV export includes the stored record.

## Live-money rule

Do not enable live Stripe/PayPal until test-mode money loop is green and webhook/receipt/storage/export are proved.

## Environment example

Use `docs/release/futurefunded-money-env.example` as the safe example file. Do not commit real `.env` files or real secrets.
