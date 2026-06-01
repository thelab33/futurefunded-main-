# FutureFunded Env Runtime Notes

FutureFunded keeps committed env files as safe examples only.

## Local dev

Use ignored `.env` for local-only dev values.

The clean local database path is:

`DATABASE_URL=sqlite:///instance/futurefunded-dev.db`

## Stripe test keys

`pk_test_REPLACE_ME`, `sk_test_REPLACE_ME`, and `whsec_REPLACE_ME` are safe placeholders only.

To prove real test checkout/session behavior, replace them in local `.env` with Stripe test-mode values. Do not paste secrets into chat or commit them.

## Email

Real email delivery remains guarded by:

`FF_EMAIL_REAL_SEND_CONFIRM=SEND_TEST_EMAIL`

Only use that switch with a controlled test inbox.

## Production

Production must use the hosting provider secret manager, not local `.env`.

Rotate any secret that has been pasted into terminals, docs, screenshots, or chat before public launch.
