# FutureFunded Production Handoff Checklist

Use this before giving the platform to a real operator.

## Access

- [ ] Operator account created
- [ ] Operator can log in at `/platform/login`
- [ ] Dashboard opens after login
- [ ] Dashboard is not publicly accessible without valid login/token
- [ ] Password saved securely outside the repo

## Campaign setup

- [ ] Onboarding page opens
- [ ] Onboarding can save setup records
- [ ] Dashboard displays saved setup records
- [ ] Dashboard "Open" links load exact setup records
- [ ] Workflow statuses update correctly:
  - Draft
  - Review needed
  - Launch-ready
  - Launched
  - Archived

## Public campaign

- [ ] Campaign page returns 200
- [ ] Hero/donation card renders correctly
- [ ] Mobile layout has no horizontal overflow
- [ ] Donation CTA opens checkout shell
- [ ] Sponsor CTA is visible
- [ ] FAQ/trust sections are visible

## Payments

- [ ] Stripe test session can verify successfully
- [ ] Payment success banner renders
- [ ] Ledger summary responds
- [ ] Recent donations render on dashboard
- [ ] Offline donation form works
- [ ] Export CSV works

## Sponsor workflow

- [ ] Sponsor packages are visible on public campaign page
- [ ] Sponsor orders appear in dashboard when available
- [ ] Sponsor fulfillment notes are reviewed before public placement

## Data / database

- [ ] `DATABASE_URL` points to the intended production database
- [ ] SQLite is not accidentally used for production unless intentionally configured
- [ ] Migrations are applied
- [ ] Backups are configured
- [ ] Setup records can be recovered/exported
- [ ] Donation ledger records can be exported

## Audits

Run locally or against production:

    FF_OPERATOR_TOKEN="..." node scripts/audit/platform-ops-hardening.mjs

    FF_SESSION_ID="..." node scripts/audit/demo-hardening.mjs

Expected:

    Platform ops: 0 failed
    Demo hardening: 0 failed

## Final handoff

- [ ] Give operator the login URL
- [ ] Give operator email/password through a secure channel
- [ ] Give operator the Sister Demo Runbook
- [ ] Confirm operator can:
  - open dashboard
  - open onboarding
  - change workflow status
  - add offline support
  - export CSV
