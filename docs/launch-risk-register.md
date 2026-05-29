# FutureFunded Launch Risk Register

## Status

- Blockers: 0
- High risks: 0
- Medium risks remaining: 11
- Low risks remaining: 1

As of Wave 12A, the focused launch contract audit reports no blocker or high issues. The active fundraising loop, sponsor flow, Stripe checkout, lifecycle dispatch, and dashboard review queue have passing proof artifacts.

## Remaining medium/low findings

### Lifecycle messaging markers

Files flagged:

- `apps/api/app/services/email_service.py`
- `apps/web/app/services/operator_notifications.py`

Decision:

These should be treated as legacy or secondary service-edge risks unless confirmed active in the live Flask web flow. The verified production email path currently runs through the FutureFunded web lifecycle dispatch and transactional email services.

Follow-up:

- Confirm whether these files are imported by the live web app.
- If inactive, mark as legacy/service-edge and avoid using them in launch demo materials.
- If active, replace stub/outbox language with provider-backed implementation notes.

### CSS rescue/version markers

File flagged:

- `apps/web/app/static/css/ff.css`

Decision:

These are not rendered UX blockers. They are internal provenance markers from the rebuild waves.

Follow-up:

- Leave in place until after demo if removing them risks CSS regressions.
- Consolidate into a clean stylesheet authority pass after stakeholder demo.

### Old campaign momentum scripts

Files flagged:

- `scripts/final_campaign_momentum_visual_audit.py`
- `scripts/polish_campaign_momentum_signal_visual.py`

Decision:

These appear to be patch/audit utilities, not runtime application files.

Follow-up:

- Move to `scripts/archive/` or document as historical patch tooling after launch.
- Do not include in stakeholder materials.

### Test TODO marker

File flagged:

- `tests/qa/ux/ff_public_templates_ux_gates.spec.ts`

Decision:

Low risk. QA TODO marker does not block launch if current smoke/scout proof remains green.

Follow-up:

- Replace TODO with an explicit backlog comment after launch.

## Launch decision

FutureFunded is demo-ready from a launch-contract perspective because no blocker or high risks remain. Remaining medium/low findings are cleanup/documentation items, not current rendered-funnel blockers.

