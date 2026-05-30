# FutureFunded Founder Demo Handoff

Date: 2026-05-29T19:47:17-05:00

Commit under handoff:
ed4ca57 (HEAD -> main, tag: stripe-webhook-local-proof-20260529191646) Document Stripe webhook local proof

## What is proven

FutureFunded has proof checkpoints for:

- Full product spine launch gate
- Campaign page
- Platform homepage
- Login and full auth suite
- Onboarding
- Operator dashboard
- Payment/demo smoke
- Strict demo proof
- Stripe local webhook forwarding
- Stripe webhook payment recording and lifecycle dispatch

Latest proof tags include:

- full-product-spine-launch-proof-20260529181248
- payment-demo-handoff-proof-20260529181736
- demo-proof-token-hygiene-fixed-20260529182335
- stripe-webhook-local-proof-20260529191646

## Demo commands

Start or restart the local demo:

```bash
bash scripts/demo/ff-demo-start.sh
```

Open demo URLs:

```bash
bash scripts/demo/ff-demo-open.sh
```

Run strict founder proof:

```bash
bash scripts/demo/ff-demo-proof.sh
```

## Demo click path

1. Start on Platform homepage:
   - Show FutureFunded as the product, not just a one-off fundraiser.
   - Explain it is for youth teams, schools, nonprofits, clubs, and community programs.

2. Open Campaign page:
   - Show public fundraising story.
   - Show donation CTA, sponsor CTA, team photos, KVUE story module, and trust details.

3. Open Login/Auth:
   - Show login page and mention the full auth suite exists:
     - forgot password
     - reset password
     - invite
     - MFA
     - register

4. Open Onboarding:
   - Show the campaign setup workflow and theme controls.

5. Open Dashboard:
   - Use the local operator token URL printed by the script.
   - Show operator/admin proof, records, and campaign operations.

6. Explain payment status:
   - Stripe is in safe test/sandbox mode locally.
   - Webhook proof passed locally.
   - No live Stripe keys should be used until final production configuration.

## Important safety notes

- Do not commit Stripe API keys.
- Do not commit webhook secrets.
- If a local whsec value was pasted or exposed, rotate it by restarting `stripe listen`.
- Local demo uses:
  - STRIPE_LIVE_MODE=0
  - FF_EXPECT_TEST_PAYMENTS=1
  - FF_FORBID_LIVE_KEYS=1

## Founder positioning

Suggested one-liner:

FutureFunded is a premium fundraising operating system for youth teams, schools, nonprofits, and clubs — combining campaign pages, sponsor visibility, onboarding, payments, auth, and operator tools into one launch-ready product spine.
