#!/usr/bin/env python3
from __future__ import annotations

import time
from pathlib import Path

ROOT = Path.cwd()

FF_CSS = ROOT / "apps/web/app/static/css/ff.css"
CAMPAIGN_CSS = ROOT / "apps/web/app/static/css/campaign.css"

FF_MARKER = "hoi-6e-saas-command-typography-governor-v1"
CAMPAIGN_MARKER = "hoi-6e-campaign-command-hero-governor-v1"

FF_BLOCK = r'''

/* ==========================================================================
   FutureFunded HOI 6E — SaaS Command Typography Governor
   Marker: hoi-6e-saas-command-typography-governor-v1

   Intent:
   - keep the bold premium FutureFunded voice
   - reduce poster-sized hero typography on protected/operator surfaces
   - make every page feel like a polished SaaS command center
   - preserve all routes, hooks, buttons, and payment behavior
========================================================================== */

@layer base, components, platform, utilities {
  :root {
    --ff-6e-hero-public: clamp(2.05rem, 5.4vw, 4.05rem);
    --ff-6e-hero-operator: clamp(2.05rem, 4.6vw, 3.55rem);
    --ff-6e-title: clamp(1.55rem, 3.25vw, 2.55rem);
    --ff-6e-card-title: clamp(1.02rem, 1.05vw, 1.22rem);
    --ff-6e-lede: clamp(1rem, 0.62vw + 0.9rem, 1.18rem);
    --ff-6e-tight-tracking: -0.047em;
    --ff-6e-hero-measure: 13.6ch;
    --ff-6e-operator-measure: 12.4ch;
  }

  :where(
    .ff-platformPage,
    [data-ff-home-root],
    [data-ff-login-root],
    [data-ff-onboard-root]
  ) :is(h1, .ff-h1, .ff-heroTitle) {
    max-width: var(--ff-6e-hero-measure);
    font-size: var(--ff-6e-hero-public);
    line-height: 0.98;
    letter-spacing: var(--ff-6e-tight-tracking);
    text-wrap: balance;
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
    .ff-errorShell,
    .ff-dashboardPage,
    .ff-operatorPage
  ) :is(h1, .ff-h1, .ff-heroTitle) {
    max-width: var(--ff-6e-operator-measure);
    font-size: var(--ff-6e-hero-operator);
    line-height: 1;
    letter-spacing: -0.052em;
    text-wrap: balance;
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
  ) :is(h2, .ff-h2, .ff-sectionTitle) {
    max-width: 16ch;
    font-size: var(--ff-6e-title);
    line-height: 1.04;
    letter-spacing: -0.038em;
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
    max-width: 58ch;
    font-size: var(--ff-6e-lede);
    line-height: 1.5;
    letter-spacing: -0.014em;
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
  ) :is(.ff-cardTitle, .ff-panelTitle, .ff-stepTitle, .ff-metricTitle, h3) {
    font-size: var(--ff-6e-card-title);
    line-height: 1.1;
    letter-spacing: -0.026em;
    text-wrap: balance;
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
  ) :is(.ff-card, .ff-panel, .ff-surface, .ff-authCard, .ff-lockCard, .card) {
    max-width: min(100%, 920px);
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
  ) :is(.ff-eyebrow, .ff-kicker, .ff-badge) {
    letter-spacing: 0.12em;
  }

  @media (min-width: 1024px) {
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
    ) {
      --ff-6e-hero-operator: clamp(2.35rem, 4vw, 3.72rem);
    }
  }

  @media (max-width: 720px) {
    :root {
      --ff-6e-hero-public: clamp(2rem, 11vw, 3.2rem);
      --ff-6e-hero-operator: clamp(2rem, 10vw, 3rem);
      --ff-6e-hero-measure: 11.8ch;
      --ff-6e-operator-measure: 11.2ch;
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
      line-height: 0.98;
      letter-spacing: -0.054em;
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
      font-size: clamp(0.98rem, 3.4vw, 1.08rem);
      line-height: 1.48;
    }
  }
}
'''

CAMPAIGN_BLOCK = r'''

/* ==========================================================================
   FutureFunded HOI 6E — Campaign Command Hero Governor
   Marker: hoi-6e-campaign-command-hero-governor-v1

   Intent:
   - keep campaign emotionally bold
   - prevent hero typography from feeling oversized or shouty
   - keep mobile fold donor-first and scannable
========================================================================== */

@layer campaign {
  [data-ff-page-root] :is(
    .ff-campaignHero__title,
    .ff-heroTitle,
    h1
  ) {
    max-width: 12.4ch;
    font-size: clamp(2.05rem, 5.2vw, 3.9rem);
    line-height: 0.98;
    letter-spacing: -0.052em;
    text-wrap: balance;
  }

  [data-ff-page-root] :is(
    .ff-campaignHero__lede,
    .ff-heroLead,
    .ff-campaignHero p,
    .ff-hero p
  ) {
    max-width: 56ch;
    font-size: clamp(1rem, 0.55vw + 0.92rem, 1.14rem);
    line-height: 1.5;
  }

  [data-ff-page-root] :is(
    .ff-donatePanel h2,
    .ff-donationPanel h2,
    .ff-givePanel h2,
    .ff-checkoutPanel h2,
    [data-ff-donation-panel] h2
  ) {
    font-size: clamp(1.32rem, 2.7vw, 2.12rem);
    line-height: 1.04;
    letter-spacing: -0.038em;
  }

  @media (max-width: 720px) {
    [data-ff-page-root] :is(
      .ff-campaignHero__title,
      .ff-heroTitle,
      h1
    ) {
      max-width: 11ch;
      font-size: clamp(2.02rem, 10.2vw, 3.1rem);
      line-height: 0.98;
      letter-spacing: -0.055em;
    }

    [data-ff-page-root] :is(
      .ff-campaignHero__lede,
      .ff-heroLead,
      .ff-campaignHero p,
      .ff-hero p
    ) {
      max-width: 34rem;
      font-size: clamp(0.98rem, 3.4vw, 1.06rem);
      line-height: 1.48;
    }
  }
}
'''

def backup(path: Path) -> None:
    stamp = time.strftime("%Y%m%d%H%M%S")
    backup_path = path.with_suffix(path.suffix + f".bak-hoi6e-{stamp}")
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

print("HOI 6E SaaS command typography governor complete.")
