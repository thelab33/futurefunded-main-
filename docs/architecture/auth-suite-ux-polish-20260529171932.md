# Auth Suite UX Polish

Date: 2026-05-29T17:20:17-05:00

Commit under patch:
ec7c132 (HEAD -> main, tag: safety-before-auth-suite-ux-polish-20260529171932, tag: auth-suite-browser-visual-proof-20260529171443) Document auth suite browser visual proof

Patch:
- apps/web/app/static/css/auth.css

Marker:
- hoi-auth-suite-ux-polish-v1

Scope:
- /platform/forgot-password
- /platform/reset-password
- /platform/invite
- /platform/mfa
- /platform/register

Intent:
- Tighten the new auth utility pages from functional browser-pass to premium SaaS polish.
- Reduce oversized poster feeling.
- Improve desktop density, card confidence, form rhythm, proof-card treatment, and CTA affordance.
- Preserve login/auth hooks, shared shell header, auth.css loading, and route behavior.

Proof:
- CSS brace sanity passed.
- Route proof passed for auth suite, login, platform, onboarding, dashboard, and campaign.
- Browser UX gate passed across mobile/tablet/desktop for all six auth pages.

Reports:
- audit_outputs/auth-suite-ux-polish/20260529171932/reports/css-sanity.txt
- audit_outputs/auth-suite-ux-polish/20260529171932/reports/route-proof.txt
- audit_outputs/auth-suite-ux-polish/20260529171932/reports/auth-suite-ux-gate.md

Screenshots:
- audit_outputs/auth-suite-ux-polish/20260529171932/screenshots
