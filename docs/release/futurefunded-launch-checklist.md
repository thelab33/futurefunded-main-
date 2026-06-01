# FutureFunded Launch Checklist

## Locked baseline

Before demo or release, confirm:

- Platform homepage is locked.
- Campaign page is locked.
- Launch onboarding is locked.
- Operator login is locked.
- Dashboard locked/session surfaces are locked.
- Campaign payment smoke passes.
- Visual launch gate reports `100/100 PASS`.
- Strict fast proof passes.
- Surface lock board passes.
- Dashboard board passes locked/session surfaces.

## Production cautions

Before public production launch:

- Replace all local demo credentials.
- Confirm production `SECRET_KEY`.
- Confirm Stripe and PayPal live/test mode intentionally.
- Confirm webhook URLs.
- Confirm donor receipts.
- Confirm campaign media paths.
- Confirm support/contact email.
- Confirm no local `.env`, `.ff_backups`, `.rollback`, or `audit_outputs` files are staged.
- Confirm `robots`, sitemap, metadata, and Open Graph previews.
- Confirm production database and backup strategy.
- Confirm production error logging.
- Confirm HTTPS and domain routing.
- Confirm payment provider dashboard access.

## Locked product promise

FutureFunded should present as:

- Premium but restrained.
- Mobile-first.
- Sponsor-safe.
- Donor-trustworthy.
- School and nonprofit review friendly.
- Clear enough to demo without engineering explanation.
- Operationally mature enough to sell as a turnkey fundraising platform.
