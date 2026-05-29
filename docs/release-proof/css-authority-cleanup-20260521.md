# FutureFunded CSS Authority Cleanup

Status: PASS pending final visual board confirmation.

## Active CSS authorities

- `ff.css` — global foundation
- `platform-home.css` — platform homepage source authority
- `campaign.public.css` — public campaign source authority
- `login.css` — login / locked dashboard source authority
- `onboarding.css` — onboarding source authority
- `dashboard-modern.css` — protected dashboard source authority

## Generated bundles

- `platform.bundle.css`
- `campaign.bundle.css`
- `login.bundle.css`
- `onboarding.bundle.css`
- `dashboard.bundle.css`

## Standalone safety CSS

- `ff-checkout-csp.css`

## Quarantine directory

```text
apps/web/app/static/css/_quarantine/page-css-authority-clean-20260521013826
```

## Rule

Future page-level CSS edits happen in the page source authority, then the matching bundle is rebuilt.
