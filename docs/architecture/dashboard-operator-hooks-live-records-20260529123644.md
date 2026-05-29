# Dashboard Operator Hooks + Live Records

Date: 2026-05-29T12:37:05-05:00

Patch:
- apps/web/app/templates/platform/dashboard.html
- apps/web/app/static/css/ff.css

Markers:
- hoi-phase5d-dashboard-operator-live-record-hooks-v1

Result:
- Added stable dashboard offline URL contract.
- Added ledger refresh button.
- Added donation table hydration target.
- Added sponsor order hydration target.
- Added offline donation form and status target.
- Preserved existing operator root, ledger, events, export, shared header, and dashboard JS contracts.

Verification:
- audit_outputs/dashboard-operator-hooks/20260529123644/reports/hook-proof.txt
- audit_outputs/dashboard-operator-hooks/20260529123644/reports/dashboard-inspect-rerun.txt

Safety tag:
- safety-before-dashboard-operator-hooks-20260529123644
