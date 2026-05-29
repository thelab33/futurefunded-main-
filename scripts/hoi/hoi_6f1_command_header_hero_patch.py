#!/usr/bin/env python3
from __future__ import annotations

import time
from pathlib import Path

ROOT = Path.cwd()

FF_CSS = ROOT / "apps/web/app/static/css/ff.css"
CAMPAIGN_CSS = ROOT / "apps/web/app/static/css/campaign.css"

FF_MARKER = "hoi-6f1-command-header-hero-governor-v1"
CAMPAIGN_MARKER = "hoi-6f1-campaign-header-hero-governor-v1"

FF_BLOCK = r'''

/* ==========================================================================
   FutureFunded HOI 6F.1 — Command Center Header + Hero Governor
   Marker: hoi-6f1-command-header-hero-governor-v1

   Intent:
   - keep pages premium and bold without poster-scale type
   - reduce cramped mobile header truncation
   - make platform/login/onboarding/dashboard feel like one SaaS system
========================================================================== */

@layer components, platform, utilities {
  :where(
    [data-ff-header],
    .ff-siteHeader,
    .ff-header,
    .ff-topbar,
    .ff-navBar,
    .ff-shellHeader
  ) {
    min-width: 0;
  }

  :where(
    [data-ff-header],
    .ff-siteHeader,
    .ff-header,
    .ff-topbar,
    .ff-navBar,
    .ff-shellHeader
  ) :is(
    .ff-brand,
    .ff-siteBrand,
    .ff-headerBrand,
    .ff-logoLockup,
    .ff-brandLockup
  ) {
    min-width: 0;
    max-width: min(42vw, 22rem);
  }

  :where(
    [data-ff-header],
    .ff-siteHeader,
    .ff-header,
    .ff-topbar,
    .ff-navBar,
    .ff-shellHeader
  ) :is(
    .ff-brandText,
    .ff-brandName,
    .ff-siteBrand__name,
    .ff-headerBrand__name,
    .ff-logoText,
    .ff-wordmark
  ) {
    min-width: 0;
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  :where(
    .ff-platformPage,
    [data-ff-home-root],
    [data-ff-login-root],
    [data-ff-onboard-root],
    [data-ff-operator-root],
    [data-ff-dashboard-root],
    [data-ff-operator-locked],
    [data-ff-dashboard-locked],
    [data-ff-protected-root]
  ) :is(h1, .ff-h1, .ff-heroTitle) {
    font-size: clamp(2rem, 4.4vw, 3.58rem);
    line-height: 1;
    letter-spacing: -0.048em;
    max-width: 13.75ch;
  }

  :where(
    [data-ff-operator-root],
    [data-ff-dashboard-root],
    [data-ff-operator-locked],
    [data-ff-dashboard-locked],
    [data-ff-protected-root],
    .ff-dashboardLocked,
    .ff-lockedState,
    .ff-errorPage,
    .ff-errorShell
  ) :is(h1, .ff-h1, .ff-heroTitle) {
    font-size: clamp(2rem, 3.55vw, 3.28rem);
    max-width: 13ch;
    line-height: 1;
    letter-spacing: -0.047em;
  }

  :where(
    .ff-platformPage,
    [data-ff-home-root],
    [data-ff-login-root],
    [data-ff-onboard-root],
    [data-ff-operator-root],
    [data-ff-dashboard-root],
    [data-ff-operator-locked],
    [data-ff-dashboard-locked],
    [data-ff-protected-root]
  ) :is(.ff-lede, .ff-heroLead, .ff-sectionLead, .ff-subtitle, .ff-mutedLead) {
    font-size: clamp(0.98rem, 0.5vw + 0.92rem, 1.12rem);
    line-height: 1.52;
    max-width: 56ch;
  }

  @media (max-width: 720px) {
    :where(
      [data-ff-header],
      .ff-siteHeader,
      .ff-header,
      .ff-topbar,
      .ff-navBar,
      .ff-shellHeader
    ) {
      gap: 0.55rem;
    }

    :where(
      [data-ff-header],
      .ff-siteHeader,
      .ff-header,
      .ff-topbar,
      .ff-navBar,
      .ff-shellHeader
    ) :is(
      .ff-brand,
      .ff-siteBrand,
      .ff-headerBrand,
      .ff-logoLockup,
      .ff-brandLockup
    ) {
      max-width: min(46vw, 13.5rem);
    }

    :where(
      [data-ff-header],
      .ff-siteHeader,
      .ff-header,
      .ff-topbar,
      .ff-navBar,
      .ff-shellHeader
    ) :is(
      .ff-brandMeta,
      .ff-brandKicker,
      .ff-brandSubtitle,
      .ff-siteBrand__eyebrow,
      .ff-headerBrand__meta
    ) {
      display: none;
    }

    :where(
      .ff-platformPage,
      [data-ff-home-root],
      [data-ff-login-root],
      [data-ff-onboard-root],
      [data-ff-operator-root],
      [data-ff-dashboard-root],
      [data-ff-operator-locked],
      [data-ff-dashboard-locked],
      [data-ff-protected-root]
    ) :is(h1, .ff-h1, .ff-heroTitle) {
      font-size: clamp(1.96rem, 9.6vw, 2.92rem);
      line-height: 0.99;
      letter-spacing: -0.052em;
      max-width: 11.6ch;
    }

    :where(
      .ff-platformPage,
      [data-ff-home-root],
      [data-ff-login-root],
      [data-ff-onboard-root],
      [data-ff-operator-root],
      [data-ff-dashboard-root],
      [data-ff-operator-locked],
      [data-ff-dashboard-locked],
      [data-ff-protected-root]
    ) :is(.ff-lede, .ff-heroLead, .ff-sectionLead, .ff-subtitle, .ff-mutedLead) {
      font-size: clamp(0.96rem, 3.25vw, 1.04rem);
      line-height: 1.48;
    }
  }
}
'''

CAMPAIGN_BLOCK = r'''

/* ==========================================================================
   FutureFunded HOI 6F.1 — Campaign Header + Hero Command Polish
   Marker: hoi-6f1-campaign-header-hero-governor-v1

   Intent:
   - keep campaign emotionally strong
   - reduce mobile header crowding
   - keep hero premium, controlled, and donor-first
========================================================================== */

@layer campaign {
  [data-ff-page-root] :is(
    .ff-campaignHero__title,
    .ff-heroTitle,
    h1
  ) {
    font-size: clamp(2.02rem, 4.85vw, 3.65rem);
    max-width: 12.6ch;
    line-height: 0.99;
    letter-spacing: -0.05em;
  }

  [data-ff-page-root] :is(
    .ff-campaignHero__lede,
    .ff-heroLead,
    .ff-campaignHero p,
    .ff-hero p
  ) {
    font-size: clamp(0.98rem, 0.46vw + 0.92rem, 1.1rem);
    line-height: 1.5;
    max-width: 54ch;
  }

  @media (max-width: 720px) {
    [data-ff-page-root] :is(
      .ff-campaignHero__title,
      .ff-heroTitle,
      h1
    ) {
      font-size: clamp(2rem, 9.4vw, 2.94rem);
      max-width: 11.15ch;
      line-height: 0.99;
      letter-spacing: -0.052em;
    }

    [data-ff-page-root] :is(
      .ff-campaignHero__lede,
      .ff-heroLead,
      .ff-campaignHero p,
      .ff-hero p
    ) {
      font-size: clamp(0.96rem, 3.2vw, 1.04rem);
      line-height: 1.48;
      max-width: 34rem;
    }

    [data-ff-page-root] :is(
      .ff-campaignHero__actions,
      .ff-heroActions,
      .ff-actions,
      .ff-ctaRow,
      .ff-donateActions,
      .ff-campaignActions
    ) {
      gap: 0.6rem;
    }

    [data-ff-page-root] :is(
      [data-ff-open-checkout],
      [data-ff-donate-trigger],
      [data-ff-payment-trigger]
    ) {
      min-height: 52px;
    }

    [data-ff-page-root] :is(
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
    backup_path = path.with_suffix(path.suffix + f".bak-hoi6f1-{stamp}")
    backup_path.write_text(path.read_text(errors="ignore"))
    print(f"Backup: {backup_path}")

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

print("HOI 6F.1 command header + hero polish complete.")
