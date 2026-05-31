# FutureFunded Page Polish Lock Plan

## Rule

No page gets redesigned blindly anymore.

Every page moves through the same lock workflow:

1. Screenshot board
2. Template/class contract audit
3. Surgical page polish
4. Screenshot board again
5. Payment or interaction proof where applicable
6. Visual launch gate
7. Commit and tag

## Current flagship baseline

### Campaign page

Route: `/c/connect-atx-elite`

Status: locked as fundraising flagship baseline.

Proof expectations:

- Route returns 200
- Checkout opener exists
- Checkout modal opens
- Campaign payment smoke passes
- Visual launch gate passes
- No broken campaign media
- No horizontal overflow

### Platform homepage

Route: `/platform/`

Status: homepage board green, ready for second visual refinement pass.

Proof expectations:

- Route returns 200
- Homepage screenshot board passes mobile/tablet/desktop
- `data-ff-home-root` exists
- `data-ff-homepage-flagship` exists
- No broken images
- No horizontal overflow
- Visual launch gate remains 100/100

## Remaining surfaces to lock

### Launch onboarding

Route: `/platform/onboarding`

Goal:

- Make onboarding feel like a premium setup wizard, not a form dump.
- Confirm mobile flow, field hierarchy, trust cues, and completion CTA.

### Operator login

Route: `/platform/login`

Goal:

- Make login feel secure, calm, premium, and institutional.
- Avoid generic admin-login styling.

### Operator dashboard locked state

Route: `/platform/dashboard`

Goal:

- Ensure locked dashboard state is polished and intentional.
- Do not leak operator-only details.

### Operator dashboard authenticated state

Route: `/platform/dashboard?access_token=<local token>`

Goal:

- Make it feel like a real command center for campaigns, sponsors, records, readiness, and launch follow-up.
- Audit separately because it is an operator surface, not a marketing surface.

## Visual bar

Every page must feel:

- premium but restrained
- mobile-first
- sponsor-safe
- institution-ready
- readable in grayscale
- not like a spreadsheet
- not like a template
- trustworthy enough for schools, teams, nonprofits, sponsors, and families

## Lock order

1. Campaign page
2. Platform homepage
3. Onboarding
4. Login
5. Dashboard locked
6. Dashboard authenticated
7. Final release gate
