# FutureFunded launch closeout surface map — local-pm2

- Generated: `2026-05-15T20:01:42+00:00`
- Base: `http://127.0.0.1:5000`
- Surfaces checked: `12`

## Executive launch call

**No P0/P1 issues found by static crawl. Visual/payment smoke still required.**

## Surface table

| Priority | Status | Surface | Title | Flags |
|---|---:|---|---|---|
| P2 | 200 | `http://127.0.0.1:5000/c/connect-atx-elite?css_v=sister-final-20260515150135` | Connect ATX Elite • Fundraiser | legacy-checkout-css-present-review-later, legacy-embedded-checkout-js-present-review-later |
| P2 | 200 | `http://127.0.0.1:5000/platform/dashboard?operator_token=REDACTED&css_v=sister-final-20260515150135` | FutureFunded Dashboard · Spring Fundraiser | authenticated-page-contains-tokenized-next-values-review-later |
| OK | 403 | `http://127.0.0.1:5000/platform/dashboard?css_v=sister-final-20260515150135` | Operator access required · FutureFunded | expected-locked-dashboard |
| OK | 200 | `http://127.0.0.1:5000/platform/onboarding?css_v=sister-final-20260515150135` | Launch workspace · FutureFunded | clean |
| OK | 200 | `http://127.0.0.1:5000/contact?css_v=sister-final-20260515150135` | Contact FutureFunded | clean |
| OK | 200 | `http://127.0.0.1:5000/privacy?css_v=sister-final-20260515150135` | Privacy • FutureFunded | clean |
| OK | 200 | `http://127.0.0.1:5000/terms?css_v=sister-final-20260515150135` | Terms • FutureFunded | clean |
| OK | 200 | `http://127.0.0.1:5000/platform?css_v=sister-final-20260515150135` | FutureFunded Platform | clean |
| OK | 200 | `http://127.0.0.1:5000/platform/onboarding?operator_token=REDACTED&css_v=sister-final-20260515150135` | Launch workspace · FutureFunded | clean |
| OK | 200 | `http://127.0.0.1:5000/sponsors?css_v=sister-final-20260515150135` | Linked page | clean |
| OK | 200 | `http://127.0.0.1:5000/platform/login?css_v=sister-final-20260515150135` | FutureFunded Organizer Login | clean |
| OK | 200 | `http://127.0.0.1:5000/platform/?css_v=sister-final-20260515150135` | FutureFunded Platform | clean |

## Today-only closeout roadmap

### P0 — must fix before sister/demo handoff
- No P0 route/status blockers found by this crawl.

### P1 — polish only if it affects trust or money flow
- No P1 structural/accessibility flags found by this crawl.

### P2 — do not chase today unless visually obvious
- Legacy checkout CSS/JS references can be consolidated later if payment smoke remains green.
- Static demo values on dashboard should eventually wire to ledger data, but do not block today if checkout and ledger work.
- Cosmetic micro-polish should stop once visual board + money loop pass.

## Recommended final command sequence

```bash
node scripts/audit/ff_visual_surface_board.mjs
bash scripts/release/verify-stripe-network.sh
git status --short
```

