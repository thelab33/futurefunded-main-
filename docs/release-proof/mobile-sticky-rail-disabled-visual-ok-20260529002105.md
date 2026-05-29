# Mobile Sticky Rail Disabled Visual Approval

Date: 2026-05-29T00:21:05-05:00

Patch:
- apps/web/app/static/css/campaign.css
- Marker: hoi-phase2b-mobile-sticky-rail-safe-disable-v1

Safety tag:
- safety-before-mobile-sticky-rail-disable-20260529001945

Verification:
- audit_outputs/mobile-sticky-rail-safe-disable/latest/reports/sticky-disable-proof.md

Approved result:
- Mobile sticky rail is hidden: none 0x0.
- Tablet/desktop unaffected.
- Campaign, checkout, platform, login, onboarding routes returned 200.
- CSS braces pass.
- Checkout modal still opens.
- No horizontal overflow before/after checkout.
- CSP inline-script errors are known and separate from this visual CSS fix.
