# FutureFunded Production Ops Pack

FutureFunded is now managed as a proof-backed launch system, not a one-off demo.

## Production principles

- No UI/CSS changes unless a screenshot board fails.
- No live payments until a live-payment gate passes.
- No real email delivery until controlled receipt/alert proof passes.
- No production secrets in git.
- No local SQLite for live users.
- Every launch surface must have a board or a gate.

## Current locked surfaces

- Platform homepage
- Campaign page
- Launch onboarding
- Operator login
- Operator dashboard
- Campaign checkout opener/runtime
- Platform meta routes: robots, sitemap, security.txt
- Legal/trust routes
- Surface screenshot board
- Dashboard screenshot board

## Money ops already proved

- Internal/manual donation write path
- Stripe signed webhook ledger write-through
- Ledger summary/events/export
- Email receipt/alert preview spool
- Current money ops gate

## Production boundaries

1. Managed production database
2. Hosting secret manager
3. Rotated Stripe keys and webhook secret
4. Controlled SMTP/provider email delivery
5. Live-payment kill switch
6. Rollback plan
7. Backup/restore plan
8. Incident response path

## Final live rule

A campaign can be shown, sold, and demoed before live payments. Real donations require the live launch runbook to pass.
