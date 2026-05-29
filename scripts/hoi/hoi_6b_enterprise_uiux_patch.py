#!/usr/bin/env python3
from __future__ import annotations

import re
import time
from pathlib import Path

ROOT = Path.cwd()

FILES = {
    "ff_css": ROOT / "apps/web/app/static/css/ff.css",
    "campaign_css": ROOT / "apps/web/app/static/css/campaign.css",
}

MARKERS = {
    "ff_css": "hoi-6b-enterprise-typography-authority-v1",
    "campaign_css": "hoi-6b-campaign-mobile-cta-authority-v1",
}

FF_CSS_BLOCK = r'''

/* ==========================================================================
   FutureFunded HOI 6B — Enterprise Typography + Surface Authority
   Marker: hoi-6b-enterprise-typography-authority-v1

   Purpose:
   - unify premium type rhythm across public, campaign, auth, onboarding, operator
   - create calmer enterprise-grade density
   - improve mobile readability without changing contracts or app logic
========================================================================== */

@layer base, components, platform, campaign, utilities;

@layer base {
  :root {
    --ff-type-display: clamp(2.35rem, 8vw, 5.35rem);
    --ff-type-hero: clamp(2.05rem, 6.5vw, 4.65rem);
    --ff-type-title: clamp(1.78rem, 4.5vw, 3.25rem);
    --ff-type-section: clamp(1.42rem, 3.15vw, 2.35rem);
    --ff-type-card: clamp(1.08rem, 1.4vw, 1.28rem);
    --ff-type-body: clamp(1rem, 0.38vw + 0.93rem, 1.125rem);
    --ff-type-small: clamp(0.875rem, 0.25vw + 0.82rem, 0.96rem);

    --ff-leading-tight: 0.94;
    --ff-leading-title: 1.02;
    --ff-leading-body: 1.58;
    --ff-leading-small: 1.48;

    --ff-tracking-display: -0.065em;
    --ff-tracking-title: -0.045em;
    --ff-tracking-body: -0.011em;

    --ff-ui-radius-xl: 28px;
    --ff-ui-radius-2xl: 34px;
    --ff-ui-shadow-soft: 0 22px 70px rgba(15, 23, 42, 0.12);
    --ff-ui-shadow-lift: 0 30px 90px rgba(15, 23, 42, 0.16);
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
  ) {
    text-rendering: geometricPrecision;
    -webkit-font-smoothing: antialiased;
    font-feature-settings: "kern" 1, "liga" 1, "calt" 1;
    letter-spacing: var(--ff-tracking-body);
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
  ) :is(h1, .ff-h1, .ff-heroTitle, .ff-campaignHero__title) {
    max-width: 12.5ch;
    font-size: var(--ff-type-hero);
    line-height: var(--ff-leading-tight);
    letter-spacing: var(--ff-tracking-display);
    text-wrap: balance;
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
  ) :is(h2, .ff-h2, .ff-sectionTitle) {
    max-width: 15ch;
    font-size: var(--ff-type-section);
    line-height: var(--ff-leading-title);
    letter-spacing: var(--ff-tracking-title);
    text-wrap: balance;
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
    font-size: var(--ff-type-body);
    line-height: var(--ff-leading-body);
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
  ) :is(.ff-eyebrow, .ff-kicker, .ff-badge, small) {
    font-size: var(--ff-type-small);
    line-height: var(--ff-leading-small);
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
    ) :is(h1, .ff-h1, .ff-heroTitle, .ff-campaignHero__title) {
      max-width: 11ch;
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
      max-width: 62ch;
    }
  }
}

@layer components {
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
    border-radius: var(--ff-ui-radius-xl);
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
    min-height: 44px;
    letter-spacing: -0.012em;
  }

  :where(
    [data-ff-operator-locked],
    [data-ff-dashboard-locked],
    [data-ff-protected-root],
    .ff-dashboardLocked,
    .ff-lockedState,
    .ff-errorPage,
    .ff-errorShell
  ) {
    min-height: min(760px, calc(100svh - 24px));
    display: grid;
    place-items: center;
    padding: clamp(1.25rem, 4vw, 3rem);
    background:
      radial-gradient(circle at 18% 10%, rgba(245, 158, 11, 0.16), transparent 34rem),
      radial-gradient(circle at 84% 0%, rgba(59, 130, 246, 0.12), transparent 32rem),
      linear-gradient(180deg, rgba(255, 255, 255, 0.92), rgba(248, 250, 252, 0.96));
  }

  :where(
    [data-ff-operator-locked],
    [data-ff-dashboard-locked],
    [data-ff-protected-root],
    .ff-dashboardLocked,
    .ff-lockedState,
    .ff-errorPage,
    .ff-errorShell
  ) :is(.ff-card, .ff-panel, .ff-authCard, .ff-lockCard, .card) {
    max-width: 680px;
    border: 1px solid rgba(148, 163, 184, 0.28);
    border-radius: var(--ff-ui-radius-2xl);
    box-shadow: var(--ff-ui-shadow-soft);
  }
}
'''

CAMPAIGN_CSS_BLOCK = r'''

/* ==========================================================================
   FutureFunded HOI 6B — Campaign Mobile CTA Authority
   Marker: hoi-6b-campaign-mobile-cta-authority-v1

   Purpose:
   - make donation the unmistakable primary action on mobile
   - keep sponsor/share visible but secondary
   - preserve all data-ff hooks and checkout behavior
========================================================================== */

@layer campaign {
  [data-ff-page-root] :is(
    [data-ff-open-checkout],
    [data-ff-donate-trigger],
    [data-ff-payment-trigger]
  ) {
    isolation: isolate;
  }

  @media (max-width: 720px) {
    [data-ff-page-root] :is(
      .ff-campaignHero__actions,
      .ff-heroActions,
      .ff-actions,
      .ff-ctaRow,
      .ff-donateActions,
      .ff-campaignActions
    ) {
      display: grid;
      grid-template-columns: 1fr;
      gap: 0.7rem;
      align-items: stretch;
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
      width: 100%;
      min-height: 54px;
      justify-content: center;
      border-radius: 999px;
      font-size: 1rem;
      font-weight: 850;
      box-shadow:
        0 18px 40px rgba(15, 23, 42, 0.16),
        0 0 0 1px rgba(255, 255, 255, 0.3) inset;
      transform: translateZ(0);
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
      width: 100%;
      min-height: 46px;
      justify-content: center;
      border-radius: 999px;
      font-size: 0.94rem;
      font-weight: 760;
      box-shadow: none;
      opacity: 0.86;
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
      min-height: 42px;
      font-size: 0.9rem;
      opacity: 0.76;
    }

    [data-ff-page-root] :is(
      .ff-donatePanel,
      .ff-donationPanel,
      .ff-givePanel,
      .ff-checkoutPanel,
      [data-ff-donation-panel]
    ) {
      border-radius: 30px;
      box-shadow:
        0 26px 80px rgba(15, 23, 42, 0.13),
        0 0 0 1px rgba(148, 163, 184, 0.2) inset;
    }

    [data-ff-page-root] :is(
      .ff-donatePanel,
      .ff-donationPanel,
      .ff-givePanel,
      .ff-checkoutPanel,
      [data-ff-donation-panel]
    ) :is(
      [data-ff-open-checkout],
      [data-ff-donate-trigger],
      [data-ff-payment-trigger],
      [data-ff-donate-submit]
    ) {
      min-height: 56px;
      width: 100%;
      border-radius: 999px;
      font-weight: 900;
      letter-spacing: -0.018em;
    }

    [data-ff-page-root] :is(
      [data-ff-amount-button],
      .ff-amountButton,
      .ff-quickAmount,
      .ff-donationAmount
    ) {
      min-height: 48px;
      border-radius: 18px;
      font-weight: 820;
      letter-spacing: -0.015em;
    }

    [data-ff-page-root] :is(
      .ff-stickyDonate,
      .ff-mobileDonateBar,
      .ff-donateRail,
      [data-ff-sticky-donate]
    ) {
      border-radius: 24px 24px 0 0;
      box-shadow:
        0 -18px 50px rgba(15, 23, 42, 0.16),
        0 -1px 0 rgba(148, 163, 184, 0.18);
      backdrop-filter: blur(18px) saturate(1.2);
      -webkit-backdrop-filter: blur(18px) saturate(1.2);
    }

    [data-ff-page-root] :is(
      .ff-stickyDonate,
      .ff-mobileDonateBar,
      .ff-donateRail,
      [data-ff-sticky-donate]
    ) :is(
      [data-ff-open-checkout],
      [data-ff-donate-trigger],
      [data-ff-payment-trigger]
    ) {
      min-height: 52px;
      border-radius: 999px;
      font-weight: 900;
    }
  }

  @media (max-width: 520px) {
    [data-ff-page-root] :is(h1, .ff-campaignHero__title, .ff-heroTitle) {
      max-width: 10.8ch;
      letter-spacing: -0.068em;
    }

    [data-ff-page-root] :is(
      .ff-campaignHero__lede,
      .ff-heroLead,
      .ff-campaignHero p,
      .ff-hero p
    ) {
      max-width: 34rem;
      font-size: clamp(1rem, 3.8vw, 1.08rem);
      line-height: 1.52;
    }
  }
}
'''

def backup(path: Path) -> None:
    if path.exists():
        stamp = time.strftime("%Y%m%d%H%M%S")
        b = path.with_suffix(path.suffix + f".bak-hoi6b-{stamp}")
        b.write_text(path.read_text(errors="ignore"))
        print(f"Backup: {b}")

def append_once(path: Path, marker: str, block: str) -> bool:
    if not path.exists():
        raise SystemExit(f"Missing required file: {path}")

    text = path.read_text(errors="ignore")
    if marker in text:
        print(f"Already patched: {path}")
        return False

    backup(path)
    path.write_text(text.rstrip() + "\n" + block.strip() + "\n")
    print(f"Patched: {path}")
    return True

def main() -> int:
    changed = False
    changed |= append_once(FILES["ff_css"], MARKERS["ff_css"], FF_CSS_BLOCK)
    changed |= append_once(FILES["campaign_css"], MARKERS["campaign_css"], CAMPAIGN_CSS_BLOCK)

    print("\nHOI 6B patch complete." if changed else "\nHOI 6B already present.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
