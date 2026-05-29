# FutureFunded Wave 2E/2F Closeout

## Wave 2E — CSS Authority

Closed.

Canonical rendered CSS files:

- `apps/web/app/static/css/ff.css`
- `apps/web/app/static/css/ff.checkout.css`
- `apps/web/app/static/css/platform-home.css`

Unused CSS was quarantined, not deleted.

## Wave 2F — JS Contract

Closed.

Core rendered campaign interaction contracts are present:

- `data-ff-open-checkout`
- `data-ff-donate-trigger`
- `data-ff-payment-trigger`
- `data-ff-open-sponsor`
- `data-ff-sponsor-trigger`
- `data-ff-share-trigger`
- `data-ff-close-embedded-checkout`

The optional campaign intel island is scoped out of the generic launch selector audit because launch pages do not render `#ffCampaignIntel`.

## Decision

Wave 2E/2F are closed unless a rendered-page smoke test finds a real interaction failure.
