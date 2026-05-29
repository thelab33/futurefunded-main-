# FutureFunded Repo Authority

Generated: `2026-05-19T21:04:16.810905+00:00`

## Production rule

No new public pages should be added until this registry is intentionally updated. Future patches should target the canonical files below unless a migration plan says otherwise.

## Canonical active surfaces

### Platform homepage
- **Route:** `/platform/`
- **Purpose:** Primary SaaS sales surface for FutureFunded.
- **Templates:**
  - ✅ `apps/web/app/templates/platform/index.html`
- **Css:**
  - ✅ `apps/web/app/static/css/platform-home.css`
  - ✅ `apps/web/app/static/css/ff.css`
- **Js:**
  - None
- **Audits:**
  - ✅ `scripts/audit/ff_visual_surface_board.mjs`

### Campaign demo
- **Route:** `/c/connect-atx-elite`
- **Purpose:** Flagship public donor/sponsor campaign surface.
- **Templates:**
  - ✅ `apps/web/app/templates/campaign/index.html`
  - ✅ `apps/web/app/templates/campaign_premium.html`
- **Css:**
  - ✅ `apps/web/app/static/css/ff.css`
- **Js:**
  - ✅ `apps/web/app/static/js/ff-campaign.js`
- **Audits:**
  - ✅ `scripts/audit/ff_visual_surface_board.mjs`

### Launch workspace / onboarding
- **Route:** `/platform/onboarding`
- **Purpose:** Launch setup workflow for team/campaign operators.
- **Templates:**
  - ✅ `apps/web/app/templates/platform/onboarding.html`
- **Css:**
  - ✅ `apps/web/app/static/css/ff.css`
- **Js:**
  - ✅ `apps/web/app/static/js/islands/onboarding.js`
- **Audits:**
  - ✅ `scripts/audit/ff_visual_surface_board.mjs`

### Operator login
- **Route:** `/platform/login`
- **Purpose:** Protected operator sign-in handoff.
- **Templates:**
  - ✅ `apps/web/app/templates/platform/login.html`
- **Css:**
  - ✅ `apps/web/app/static/css/login.css`
  - ♻️ `apps/web/app/static/css/ff-login-calm.css` — retired from live login/locked routes; shadow-merged into `login.css`
- **Js:**
  - ✅ `apps/web/app/static/js/ff-login.js`
- **Audits:**
  - ✅ `scripts/audit/ff_visual_surface_board.mjs`

### Protected dashboard
- **Route:** `/platform/dashboard`
- **Purpose:** Private operator command center.
- **Templates:**
  - ✅ `apps/web/app/templates/platform/dashboard.html`
  - ✅ `apps/web/app/templates/platform/dashboard_locked.html`
  - ✅ `apps/web/app/templates/_partials/ff_dashboard_launch_assistant.html`
- **Css:**
  - ✅ `apps/web/app/static/css/dashboard-modern.css`
  - ♻️ `apps/web/app/static/css/ff-dashboard-final.css` — retired from live dashboard route; shadow-merged into `dashboard-modern.css`
  - ♻️ `apps/web/app/static/css/ff-dashboard-protected-exec.css` — retired from live dashboard route; shadow-merged into `dashboard-modern.css`
  - ✅ `apps/web/app/static/css/ff-fortune500-final.css`
  - ✅ `apps/web/app/static/css/ff-launch-completion.css`
- **Js:**
  - ✅ `apps/web/app/static/js/ff-dashboard-protected-exec.js`
  - ✅ `apps/web/app/static/js/ff-launch-completion.js`
- **Audits:**
  - ✅ `scripts/audit/ff_dashboard_protected_exec_audit.mjs`
  - ✅ `scripts/audit/ff_dashboard_final_polish_audit.mjs`
  - ✅ `scripts/audit/ff_visual_surface_board.mjs`

### Shared shell/components
- **Route:** `shared`
- **Purpose:** Shared layout and reusable UI fragments.
- **Templates:**
  - ✅ `apps/web/app/templates/_base/site_base.html`
  - ✅ `apps/web/app/templates/_partials/ff_site_header.html`
  - ✅ `apps/web/app/templates/shared/_button.html`
  - ✅ `apps/web/app/templates/shared/_faq_item.html`
  - ✅ `apps/web/app/templates/shared/_pill.html`
  - ✅ `apps/web/app/templates/shared/_section_intro.html`
  - ✅ `apps/web/app/templates/shared/_stat_card.html`
- **Css:**
  - ✅ `apps/web/app/static/css/ff.css`
- **Js:**
  - ✅ `apps/web/app/static/js/csp-safe-init.js`
- **Audits:**
  - None

## No-touch active authority files

These files are considered production authority. Do not rename, delete, or quarantine without a deliberate migration.

- ✅ `apps/web/app/static/css/ff.css`
- ✅ `apps/web/app/static/css/platform-home.css`
- ✅ `apps/web/app/static/css/dashboard-modern.css`
- ♻️ `apps/web/app/static/css/ff-dashboard-final.css` — retired from live dashboard route; shadow-merged into `dashboard-modern.css`
- ♻️ `apps/web/app/static/css/ff-dashboard-protected-exec.css` — retired from live dashboard route; shadow-merged into `dashboard-modern.css`
- ✅ `apps/web/app/static/css/login.css`
- ♻️ `apps/web/app/static/css/ff-login-calm.css` — retired from live login/locked routes; shadow-merged into `login.css`
- ✅ `apps/web/app/static/js/ff-campaign.js`
- ✅ `apps/web/app/static/js/ff-dashboard-protected-exec.js`
- ✅ `apps/web/app/templates/platform/index.html`
- ✅ `apps/web/app/templates/campaign/index.html`
- ✅ `apps/web/app/templates/campaign_premium.html`
- ✅ `apps/web/app/templates/platform/onboarding.html`
- ✅ `apps/web/app/templates/platform/login.html`
- ✅ `apps/web/app/templates/platform/dashboard.html`
- ✅ `apps/web/app/templates/platform/dashboard_locked.html`

## Review-only files

These may be active, historical, or loaded indirectly. Do not quarantine until a reference audit confirms they are unused.

- ✅ `apps/web/app/static/css/campaign.css`
- ✅ `apps/web/app/static/css/ff-campaign-enterprise.css`
- ✅ `apps/web/app/static/css/ff-campaign-final-compression.css`
- ✅ `apps/web/app/static/css/ff.checkout.css`
- ✅ `apps/web/app/static/css/ff.cinematic.css`
- ✅ `apps/web/app/static/css/onboarding.css`
- ♻️ `apps/web/app/static/css/ff-onboarding-executive.css` — retired from live onboarding route; shadow-merged into `onboarding.css`
- ♻️ `apps/web/app/static/css/ff-homepage-executive.css` — retired from live homepage route; shadow-merged into `platform-home.css`
- ✅ `apps/web/app/static/js/ff-embedded-checkout.js`
- ✅ `apps/web/app/static/js/ff-checkout-direct.js`
- ✅ `apps/web/app/static/js/ff-campaign-enterprise.js`
- ✅ `apps/web/app/static/js/ff-campaign-final-compression.js`
- ✅ `apps/web/app/static/js/ff-homepage-executive.js`
- ✅ `apps/web/app/static/js/ff-operator-dashboard.js`
- ✅ `apps/web/app/static/js/ff-payment-provider-status.js`

## Already quarantined / deprecated areas

- ✅ `apps/web/app/templates/campaign/deprecated`
- ✅ `apps/web/app/static/css/_quarantine`

## Patch script policy

Patch scripts are allowed during active development but should be moved to a timestamped archive once their changes are committed and audited.

- `scripts/patches/*.py`
- `scripts/patch_*.py`
- `scripts/elite_patch_*.py`

## Latest inventory counts

- **active_hint_files:** `19`
- **by_suffix:** `{'.css': 23, '.html': 47, '.js': 38, '.json': 7, '.md': 30, '.mjs': 65, '.py': 117, '.txt': 2}`
- **css_files:** `23`
- **js_files:** `103`
- **suspicious_or_stale_hint_files:** `106`
- **template_files:** `47`
- **total_scanned:** `329`

## Git status when inventory was generated

- `?? scripts/audit/ff_active_repo_inventory.py`
- `?? scripts/audit/ff_repo_authority_inventory.py`
