# FutureFunded Homepage + Login Premium Authority v8.1

Status: Approved visual baseline for public platform homepage and organizer login.

Locked surfaces:
- `/platform/`
- `/platform/login`

Core files:
- `apps/web/app/templates/platform/index.html`
- `apps/web/app/templates/platform/login.html`
- `apps/web/app/static/css/platform-home.css`
- `apps/web/app/static/css/login.css`
- `apps/web/app/static/js/login.js`
- `scripts/audit/ff_public_ux_money_smoke.py`

Proof:
- Public UX + money smoke gate passed.
- Visual surface board passed 12/12.
- Overflow flags: 0.
- Payment config endpoint reachable.
- Campaign checkout/sponsor/share hooks preserved.
- Homepage now uses `homepage-authority-v8` plus final polish v8.1.
- Login now uses `login-public-official-v2` plus final polish v8.1.

Decision:
Do not continue broad homepage/login redesign before launch. Future changes should be micro-polish only.
