# FutureFunded Launch Backlog

## Launch-ready now

- Operator login
- Sister/demo bootstrap script
- One-command sister handoff runner
- Onboarding setup persistence
- Dashboard setup record review
- Setup workflow statuses
- Offline support recording
- CSV export
- Stripe test checkout readiness drill
- Operator notification outbox:
  - setup status changed
  - offline support recorded
  - paid Stripe session verified

## Deferred until after sister/demo handoff

### Sponsor lead notifications

Status: deferred.

Goal:

    Sponsor lead submitted
    → operator notification outbox
    → to arodgps@gmail.com
    → includes business name, tier, contact name/email, message

Reason deferred:

The first sponsor route patch introduced a syntax error in
`apps/web/app/blueprints/sponsors/routes.py`. The route was restored to keep
launch stability.

### Real email delivery

Status: deferred.

Current behavior:

    MAIL_ENABLED=false
    → write durable JSONL outbox records

Later behavior:

    MAIL_ENABLED=true
    → send through SMTP/provider
    → still write JSONL audit record

### Dashboard notification panel

Status: deferred.

Goal:

Show the latest operator notification outbox records directly in the dashboard.

## Production handoff checklist

Before real handoff:

- [ ] Merge/deploy branch
- [ ] Run `scripts/setup_sister_demo.py` in production environment
- [ ] Use a new private production password
- [ ] Run sister handoff drill against production
- [ ] Run payment notification drill against production
- [ ] Confirm Stripe receipt settings in Stripe Dashboard
- [ ] Send operator login securely
