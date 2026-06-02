# FutureFunded Incident Response Lite

## Severity 1

Examples:

- Wrong payment amount
- Donation not recorded
- Receipt sent to wrong recipient
- Live secret exposed
- Dashboard shows incorrect totals

Actions:

1. Disable payments immediately.
2. Preserve logs and audit outputs.
3. Stop public launch/demo if donor trust is impacted.
4. Rotate affected secrets.
5. Re-run money ops gate.
6. Write a short incident note.

## Severity 2

Examples:

- Email provider failure
- CSV export issue
- Dashboard board failure
- Non-critical route error

Actions:

1. Keep payments disabled if money ops is affected.
2. Fix surgically.
3. Re-run boards/gates.
4. Commit/tag the fix.

## Payment kill switch

Local/test safety:

- `FF_FORBID_LIVE_KEYS=1`
- `FF_STRIPE_ENFORCE_LIVE_KEYS=0`
- `FF_EMAIL_DRY_RUN=1`

Production kill switch should be implemented through hosting env/secrets and documented before live donations.
