# Dashboard Offline Donation URL Fix

Date: 2026-05-29T12:40:50-05:00

Patch:
- apps/web/app/templates/platform/dashboard.html

Result:
- Fixed dashboard offline donation URL from:
  - /c/<slug>/ledger/offline
- To the actual backend route:
  - /c/<slug>/ledger/offline-donation

Verification:
- Rendered dashboard data-ff-offline-url points to /ledger/offline-donation.
- Offline donation POST smoke returned 201.
- Public/platform/campaign/auth/onboarding/dashboard route smoke passed.

Reports:
- audit_outputs/dashboard-offline-url-fix/20260529124045/reports/template-proof.txt
- audit_outputs/dashboard-offline-url-fix/20260529124045/reports/rendered-offline-url.txt
- audit_outputs/dashboard-offline-url-fix/20260529124045/reports/offline-post-status.txt
- audit_outputs/dashboard-offline-url-fix/20260529124045/reports/offline-post-body.txt
- audit_outputs/dashboard-offline-url-fix/20260529124045/reports/route-proof.txt

Safety tag:
- safety-before-dashboard-offline-url-fix-20260529124045
