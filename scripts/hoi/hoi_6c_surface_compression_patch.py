#!/usr/bin/env python3
from __future__ import annotations

import time
from pathlib import Path

ROOT = Path.cwd()

FF_CSS = ROOT / "apps/web/app/static/css/ff.css"
CAMPAIGN_CSS = ROOT / "apps/web/app/static/css/campaign.css"

FF_MARKER = "hoi-6c-surface-copy-compression-v1"
CAMPAIGN_MARKER = "hoi-6c-campaign-fold-compression-v1"

FF_BLOCK = r'''

/* ==========================================================================
   FutureFunded HOI 6C — Surface Copy Compression + Premium Rhythm
   Marker: hoi-6c-surface-copy-compression-v1

   Purpose:
   - tighten fold density without making pages feel cramped
   - improve scan rhythm across home/campaign/auth/onboarding/operator
   - make protected dashboard states feel intentional and branded
========================================================================== */

@layer base, components, platform, utilities {
  :root {
    --ff-6c-section-y: clamp(3.6rem, 7vw, 6.5rem);
    --ff-6c-section-y-tight: clamp(2.4rem, 5.2vw, 4.5rem);
    --ff-6c-card-pad: clamp(1.05rem, 2.4vw, 1.7rem);
    --ff-6c-card-gap: clamp(0.85rem, 1.8vw, 1.25rem);
    --ff-6c-copy-measure: 62ch;
    --ff-6c-lede-measure: 54ch;
  }

  :where(
    .ff-platformPage,
    .ff-campaign,
    [data-ff-page-root],
    [data-ff-home-root],
    [data-ff-login-root],
    [data-ff-onboard-root],
    [data-ff-operator-root],
    [data-ff-dashboard-root]
  ) :is(section, .ff-section, .ff-band, .ff-panelBand) {
    scroll-margin-top: 96px;
  }

  :where(
    .ff-platformPage,
    .ff-campaign,
    [data-ff-page-root],
    [data-ff-home-root],
    [data-ff-login-root],
    [data-ff-onboard-root],
    [data-ff-operator-root],
    [data-ff-dashboard-root]
  ) :is(.ff-sectionHeader, .ff-copyStack, .ff-stack, .ff-card, .ff-panel) {
    gap: var(--ff-6c-card-gap);
  }

  :where(
    .ff-platformPage,
    .ff-campaign,
    [data-ff-page-root],
    [data-ff-home-root],
    [data-ff-login-root],
    [data-ff-onboard-root],
    [data-ff-operator-root],
    [data-ff-dashboard-root]
  ) :is(.ff-card, .ff-panel, .ff-surface, .ff-authCard, .ff-onboardCard, .ff-dashboardCard) {
    padding: var(--ff-6c-card-pad);
  }

  :where(
    .ff-platformPage,
    .ff-campaign,
    [data-ff-page-root],
    [data-ff-home-root],
    [data-ff-login-root],
    [data-ff-onboard-root],
    [data-ff-operator-root],
    [data-ff-dashboard-root]
  ) :is(p, li, .ff-copy, .ff-bodyText) {
    max-width: var(--ff-6c-copy-measure);
    text-wrap: pretty;
  }

  :where(
    .ff-platformPage,
    .ff-campaign,
    [data-ff-page-root],
    [data-ff-home-root],
    [data-ff-login-root],
    [data-ff-onboard-root],
    [data-ff-operator-root],
    [data-ff-dashboard-root]
  ) :is(.ff-lede, .ff-heroLead, .ff-subtitle, .ff-sectionLead, .ff-mutedLead) {
    max-width: var(--ff-6c-lede-measure);
    text-wrap: pretty;
  }

  :where(
    .ff-platformPage,
    .ff-campaign,
    [data-ff-page-root],
    [data-ff-home-root],
    [data-ff-login-root],
    [data-ff-onboard-root],
    [data-ff-operator-root],
    [data-ff-dashboard-root]
  ) :is(.ff-eyebrow, .ff-kicker, .ff-badge) {
    letter-spacing: 0.055em;
    text-transform: uppercase;
  }

  :where(
    .ff-platformPage,
    .ff-campaign,
    [data-ff-page-root],
    [data-ff-home-root],
    [data-ff-login-root],
    [data-ff-onboard-root],
    [data-ff-operator-root],
    [data-ff-dashboard-root]
  ) :is(.ff-button, .ff-btn, button, a[role="button"]) {
    text-wrap: balance;
  }

  :where(
    [data-ff-login-root],
    [data-ff-onboard-root],
    [data-ff-operator-root],
    [data-ff-dashboard-root],
    .ff-authPage,
    .ff-onboardPage,
    .ff-dashboardPage
  ) :is(h1, .ff-h1, .ff-heroTitle) {
    max-width: 13.5ch;
  }

  :where(
    [data-ff-login-root],
    [data-ff-onboard-root],
    [data-ff-operator-root],
    [data-ff-dashboard-root],
    .ff-authPage,
    .ff-onboardPage,
    .ff-dashboardPage
  ) :is(p, .ff-copy, .ff-lede, .ff-heroLead) {
    max-width: 56ch;
  }

  :where(
    [data-ff-operator-locked],
    [data-ff-dashboard-locked],
    [data-ff-protected-root],
    .ff-dashboardLocked,
    .ff-lockedState,
    .ff-errorPage,
    .ff-errorShell
  ) :is(h1, h2, .ff-h1, .ff-h2) {
    max-width: 14ch;
    text-wrap: balance;
  }

  :where(
    [data-ff-operator-locked],
    [data-ff-dashboard-locked],
    [data-ff-protected-root],
    .ff-dashboardLocked,
    .ff-lockedState,
    .ff-errorPage,
    .ff-errorShell
  ) :is(p, .ff-copy, .ff-lede) {
    max-width: 48ch;
    color: var(--ff-muted, #64748b);
  }

  @media (max-width: 720px) {
    :where(
      .ff-platformPage,
      .ff-campaign,
      [data-ff-page-root],
      [data-ff-home-root],
      [data-ff-login-root],
      [data-ff-onboard-root],
      [data-ff-operator-root],
      [data-ff-dashboard-root]
    ) :is(section, .ff-section, .ff-band, .ff-panelBand) {
      padding-block: var(--ff-6c-section-y-tight);
    }

    :where(
      .ff-platformPage,
      .ff-campaign,
      [data-ff-page-root],
      [data-ff-home-root],
      [data-ff-login-root],
      [data-ff-onboard-root],
      [data-ff-operator-root],
      [data-ff-dashboard-root]
    ) :is(.ff-card, .ff-panel, .ff-surface, .ff-authCard, .ff-onboardCard, .ff-dashboardCard) {
      border-radius: 24px;
    }
  }
}
'''

CAMPAIGN_BLOCK = r'''

/* ==========================================================================
   FutureFunded HOI 6C — Campaign Fold Compression + Donor Clarity
   Marker: hoi-6c-campaign-fold-compression-v1

   Purpose:
   - tighten mobile fold rhythm
   - keep donate dominant
   - calm secondary sponsor/share CTAs
   - improve donor copy scan speed without changing markup/hooks
========================================================================== */

@layer campaign {
  [data-ff-page-root] :is(
    .ff-campaignHero,
    .ff-hero,
    .ff-campaignTop,
    .ff-campaignHeader
  ) {
    text-wrap: balance;
  }

  [data-ff-page-root] :is(
    .ff-campaignHero__title,
    .ff-heroTitle,
    h1
  ) {
    text-wrap: balance;
  }

  [data-ff-page-root] :is(
    .ff-campaignHero__lede,
    .ff-heroLead,
    .ff-campaignHero p,
    .ff-hero p
  ) {
    text-wrap: pretty;
  }

  @media (max-width: 720px) {
    [data-ff-page-root] :is(
      .ff-campaignHero,
      .ff-hero,
      .ff-campaignTop,
      .ff-campaignHeader
    ) {
      padding-block-start: clamp(1.35rem, 5vw, 2.45rem);
      padding-block-end: clamp(1.55rem, 5.8vw, 2.75rem);
    }

    [data-ff-page-root] :is(
      .ff-campaignHero__title,
      .ff-heroTitle,
      h1
    ) {
      margin-block-end: 0.78rem;
      max-width: 11.25ch;
    }

    [data-ff-page-root] :is(
      .ff-campaignHero__lede,
      .ff-heroLead,
      .ff-campaignHero p,
      .ff-hero p
    ) {
      margin-block-end: 1rem;
      max-width: 33rem;
    }

    [data-ff-page-root] :is(
      .ff-campaignHero__actions,
      .ff-heroActions,
      .ff-actions,
      .ff-ctaRow,
      .ff-donateActions,
      .ff-campaignActions
    ) {
      margin-block-start: 1rem;
      max-width: 34rem;
      margin-inline: auto;
    }

    [data-ff-page-root] :is(
      .ff-campaignHero__actions,
      .ff-heroActions,
      .ff-actions,
      .ff-ctaRow,
      .ff-donateActions,
      .ff-campaignActions
    ) :is(
      [data-ff-open-checkout],
      [data-ff-donate-trigger],
      [data-ff-payment-trigger]
    ) {
      order: -2;
    }

    [data-ff-page-root] :is(
      .ff-campaignHero__actions,
      .ff-heroActions,
      .ff-actions,
      .ff-ctaRow,
      .ff-donateActions,
      .ff-campaignActions
    ) :is(
      [data-ff-open-sponsor],
      [data-ff-sponsor-trigger]
    ) {
      order: -1;
    }

    [data-ff-page-root] :is(
      .ff-campaignHero__actions,
      .ff-heroActions,
      .ff-actions,
      .ff-ctaRow,
      .ff-donateActions,
      .ff-campaignActions
    ) :is(
      [data-ff-share],
      [data-ff-share-trigger],
      [data-ff-qr-trigger]
    ) {
      order: 2;
    }

    [data-ff-page-root] :is(
      .ff-donatePanel,
      .ff-donationPanel,
      .ff-givePanel,
      .ff-checkoutPanel,
      [data-ff-donation-panel]
    ) {
      padding: clamp(1.08rem, 4.8vw, 1.45rem);
    }

    [data-ff-page-root] :is(
      .ff-donatePanel,
      .ff-donationPanel,
      .ff-givePanel,
      .ff-checkoutPanel,
      [data-ff-donation-panel]
    ) :is(h2, h3, .ff-cardTitle, .ff-panelTitle) {
      max-width: 14ch;
      text-wrap: balance;
    }

    [data-ff-page-root] :is(
      .ff-donatePanel,
      .ff-donationPanel,
      .ff-givePanel,
      .ff-checkoutPanel,
      [data-ff-donation-panel]
    ) :is(p, .ff-copy, .ff-muted, .ff-panelText) {
      max-width: 42ch;
      line-height: 1.5;
    }

    [data-ff-page-root] :is(
      .ff-amountGrid,
      .ff-quickAmounts,
      [data-ff-amount-grid]
    ) {
      gap: 0.62rem;
    }

    [data-ff-page-root] :is(
      [data-ff-amount-button],
      .ff-amountButton,
      .ff-quickAmount,
      .ff-donationAmount
    ) {
      min-height: 46px;
    }
  }

  @media (max-width: 420px) {
    [data-ff-page-root] :is(
      .ff-campaignHero__actions,
      .ff-heroActions,
      .ff-actions,
      .ff-ctaRow,
      .ff-donateActions,
      .ff-campaignActions
    ) {
      gap: 0.58rem;
    }

    [data-ff-page-root] :is(
      .ff-campaignHero__actions,
      .ff-heroActions,
      .ff-actions,
      .ff-ctaRow,
      .ff-donateActions,
      .ff-campaignActions
    ) :is(
      [data-ff-open-sponsor],
      [data-ff-sponsor-trigger],
      [data-ff-share],
      [data-ff-share-trigger],
      [data-ff-qr-trigger]
    ) {
      min-height: 42px;
    }
  }
}
'''

def backup(path: Path) -> None:
    stamp = time.strftime("%Y%m%d%H%M%S")
    path.with_suffix(path.suffix + f".bak-hoi6c-{stamp}").write_text(path.read_text(errors="ignore"))

def append_once(path: Path, marker: str, block: str) -> None:
    if not path.exists():
        raise SystemExit(f"Missing file: {path}")

    text = path.read_text(errors="ignore")
    if marker in text:
        print(f"Already patched: {path}")
        return

    backup(path)
    path.write_text(text.rstrip() + "\n" + block.strip() + "\n")
    print(f"Patched: {path}")

append_once(FF_CSS, FF_MARKER, FF_BLOCK)
append_once(CAMPAIGN_CSS, CAMPAIGN_MARKER, CAMPAIGN_BLOCK)

print("HOI 6C compression patch complete.")
