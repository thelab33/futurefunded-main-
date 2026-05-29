# FutureFunded Final UI Core Blocker Cleanup

- Timestamp: `20260523024222`
- Quarantine root: `apps/web/app/_quarantine/ui-core-final-blockers-20260523024222`

## Comment references cleaned

- `apps/web/app/static/css/campaign.css`
- `apps/web/app/static/css/ff.css`

## Files quarantined

- `apps/web/app/static/css/campaign.public.css` → `apps/web/app/_quarantine/ui-core-final-blockers-20260523024222/apps/web/app/static/css/campaign.public.css` (git-mv)
- `apps/web/app/static/css/ff-checkout-csp.css` → `apps/web/app/_quarantine/ui-core-final-blockers-20260523024222/apps/web/app/static/css/ff-checkout-csp.css` (git-mv)
- `apps/web/app/templates/campaign_premium.html` → `apps/web/app/_quarantine/ui-core-final-blockers-20260523024222/apps/web/app/templates/campaign_premium.html` (git-mv)

## Active references before

```
apps/web/app/templates/campaign_premium.html:8:   campaign_premium.html cannot drift into competing page systems.
apps/web/app/static/css/campaign.public.css:5:  Active campaign bundle sources should now be: ff.css campaign.public.css
apps/web/app/static/css/campaign.css:7:  - Absorbs former campaign.public.css campaign-only rules
apps/web/app/static/css/campaign.css:8:  - Absorbs ff-checkout-csp.css runtime-safe checkout helpers
apps/web/app/static/css/campaign.css:12:/* ===== BEGIN campaign.public.css authority ===== */
apps/web/app/static/css/campaign.css:2039:/* ===== END campaign.public.css authority ===== */
apps/web/app/static/css/ff.css:7545:   Visible amount selection states for campaign_premium.html.
apps/web/app/static/css/ff.css:7598:   Final checkout shell skin for campaign_premium.html.
apps/web/app/static/css/ff.css:8245:   Drop-in support for campaign_premium.html.
apps/web/app/static/css/ff.css:9260:   Premium story + FAQ/trust section refactor for campaign_premium.html.
```

## Active references after

```
(none)
```
