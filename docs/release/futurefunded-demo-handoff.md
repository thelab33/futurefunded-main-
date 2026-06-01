# FutureFunded Demo Handoff

FutureFunded is now organized around locked, proof-backed launch surfaces.

## Locked launch surfaces

| Surface | Route | Purpose |
|---|---|---|
| Platform homepage | `/platform/` | Product story, trust, campaign funnel, sponsor and donor positioning |
| Campaign page | `/c/connect-atx-elite` | Public giving surface for donors, families, and sponsors |
| Launch onboarding | `/platform/onboarding` | Private setup workspace for campaign creation and sponsor packages |
| Operator login | `/platform/login` | Secure organizer access |
| Operator dashboard | `/platform/dashboard` | Private command center after login |

## Local demo flow

1. Open `/platform/`.
2. Walk through the FutureFunded product story.
3. Open the live Connect ATX Elite fundraiser.
4. Show the secure campaign checkout flow.
5. Open `/platform/onboarding` to show setup readiness.
6. Open `/platform/login`.
7. Sign in with the local demo operator account.
8. Open `/platform/dashboard` to show the operator command center.

## Local demo operator login

Local-only demo credentials are generated in the local dev database.

- URL: `/platform/login`
- Email: `operator@getfuturefunded.local`
- Password: `FutureFunded!2026`

Do not use this credential in production.

## Proof commands

Run the main proof:

    bash scripts/demo/ff-fast-proof-strict.sh

Run the all-surface board:

    FF_SURFACE_BOARD_STRICT=1 node scripts/release/ff_surface_lock_board.mjs

Run the dashboard board:

    FF_DASHBOARD_BOARD_STRICT=1 node scripts/release/ff_dashboard_screenshot_board.mjs

Serve the all-surface board:

    python3 -m http.server 8767 --directory audit_outputs/surface-lock-board/latest

Open:

    http://127.0.0.1:8767/index.html

Serve the dashboard board:

    python3 -m http.server 8770 --directory audit_outputs/dashboard-screenshot-board/latest

Open:

    http://127.0.0.1:8770/index.html

## Founder demo script

Start with the homepage:

- “FutureFunded gives teams and nonprofits a polished fundraising page, sponsor packages, and a private operator dashboard without needing to stitch together scattered tools.”

Move to the campaign page:

- “This is the public page families, donors, sponsors, and local businesses see. It is built to feel trustworthy, mobile-first, and easy to give from.”

Move to onboarding:

- “This is the private launch workspace where an organizer prepares the campaign before sharing it publicly.”

Move to login and dashboard:

- “This is the private operator command center for launch readiness, giving records, sponsor interest, offline support, and exports.”

Close with proof:

- “Every locked surface is backed by mobile, tablet, and desktop screenshot boards plus strict proof checks before we ship.”
