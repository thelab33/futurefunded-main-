# FutureFunded Live Closeout Checklist

## Founder demo flow

1. Open `/platform/`
2. Explain: one polished fundraising page replaces scattered links, PDFs, screenshots, and text threads.
3. Open `/c/connect-atx-elite`
4. Click the giving CTA.
5. Confirm checkout panel opens.
6. Show sponsor packages.
7. Show share/QR path.
8. Open `/platform/login`
9. Explain protected organizer access.
10. Open `/platform/onboarding`
11. Explain launch setup.
12. Open `/platform/dashboard?access_token=<token>`
13. Explain private operator command center.

## Must pass before live

- Money proof passes.
- Visual launch gate is 100/100.
- Campaign runtime marker remains `ff-campaign-safe-runtime-v1`.
- No old `ff-campaign.js` restore.
- Checkout/sponsor/share hooks remain present.
- Desktop and mobile boards reviewed.
- Stripe live mode remains disabled until final key check.
- Operator token is not committed or shown in screenshots.

## Do not touch before demo

- `apps/web/app/static/js/ff-campaign.js`
- `apps/web/app/templates/_base/campaign_base.html`
- checkout/firewall scripts
- payment route contracts
