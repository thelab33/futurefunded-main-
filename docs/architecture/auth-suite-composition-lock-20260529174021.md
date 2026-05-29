# Auth Suite Composition Lock

Date: 2026-05-29T17:41:00-05:00

Commit under patch:
9ac8c7e (HEAD -> main, tag: safety-before-auth-suite-composition-lock-20260529173456, tag: auth-suite-enterprise-polish-visual-ok-20260529172751) Elevate auth suite enterprise polish

Patch:
- apps/web/app/static/css/auth.css

Marker:
- hoi-auth-suite-composition-lock-v1

Intent:
- Fix desktop auth-suite clipping and over-tall panel composition after enterprise polish.
- Preserve the premium SaaS auth direction while preventing header wash/content overlap.
- Repair browser-gate selector argument handling.

Proof:
- CSS brace sanity passed.
- Route proof passed for login, auth suite, platform, onboarding, dashboard, and campaign.
- Browser composition gate passed across mobile/tablet/desktop for all six auth pages.
- Gate checks include overflow, submit sizing, header/form/root hooks, and hero/card clipping.

Reports:
- audit_outputs/auth-suite-composition-lock/20260529174021/reports/css-sanity.txt
- audit_outputs/auth-suite-composition-lock/20260529174021/reports/route-proof.txt
- audit_outputs/auth-suite-composition-lock/20260529174021/reports/auth-suite-composition-gate.md

Screenshots:
- audit_outputs/auth-suite-composition-lock/20260529174021/screenshots
