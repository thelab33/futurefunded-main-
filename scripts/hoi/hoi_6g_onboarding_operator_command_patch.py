#!/usr/bin/env python3
from __future__ import annotations

import time
from pathlib import Path

ROOT = Path.cwd()
FF_CSS = ROOT / "apps/web/app/static/css/ff.css"
MARKER = "hoi-6g-onboarding-operator-command-center-v1"

BLOCK = r'''

/* ==========================================================================
   FutureFunded HOI 6G — Onboarding + Operator Dashboard Command Center
   Marker: hoi-6g-onboarding-operator-command-center-v1

   Intent:
   - give onboarding and unlocked operator dashboard the same premium treatment
   - keep typography bold but controlled
   - make dashboard feel like a real SaaS command center
   - preserve tokens, hooks, routes, and dashboard JS behavior
========================================================================== */

@layer platform, components, utilities {
  :root {
    --ff-6g-command-max: 1180px;
    --ff-6g-command-pad: clamp(1rem, 3vw, 1.75rem);
    --ff-6g-command-gap: clamp(0.85rem, 1.7vw, 1.35rem);
    --ff-6g-command-hero: clamp(2rem, 4.1vw, 3.35rem);
    --ff-6g-command-title: clamp(1.32rem, 2.4vw, 2rem);
    --ff-6g-command-card-title: clamp(1rem, 1vw, 1.18rem);
    --ff-6g-command-copy: clamp(0.96rem, 0.35vw + 0.9rem, 1.06rem);
    --ff-6g-command-radius: 26px;
    --ff-6g-command-border: rgba(148, 163, 184, 0.22);
    --ff-6g-command-shadow: 0 20px 60px rgba(15, 23, 42, 0.10);
  }

  /* -----------------------------------------------------------------------
     Onboarding: launch workspace polish
  ----------------------------------------------------------------------- */

  :where(
    [data-ff-onboard-root],
    .ff-onboardPage,
    .ff-onboardingPage,
    .ff-launchWorkspace,
    .ff-onboarding
  ) {
    text-rendering: geometricPrecision;
    -webkit-font-smoothing: antialiased;
  }

  :where(
    [data-ff-onboard-root],
    .ff-onboardPage,
    .ff-onboardingPage,
    .ff-launchWorkspace,
    .ff-onboarding
  ) :is(
    .ff-shell,
    .ff-container,
    .ff-pageShell,
    .ff-onboardShell,
    .ff-workspaceShell
  ) {
    max-width: var(--ff-6g-command-max);
  }

  :where(
    [data-ff-onboard-root],
    .ff-onboardPage,
    .ff-onboardingPage,
    .ff-launchWorkspace,
    .ff-onboarding
  ) :is(
    .ff-hero,
    .ff-onboardHero,
    .ff-launchHero,
    .ff-workspaceHero,
    header
  ) {
    border-radius: clamp(24px, 3vw, 36px);
  }

  :where(
    [data-ff-onboard-root],
    .ff-onboardPage,
    .ff-onboardingPage,
    .ff-launchWorkspace,
    .ff-onboarding
  ) :is(h1, .ff-h1, .ff-heroTitle) {
    max-width: 12.6ch;
    font-size: var(--ff-6g-command-hero);
    line-height: 1;
    letter-spacing: -0.048em;
    text-wrap: balance;
  }

  :where(
    [data-ff-onboard-root],
    .ff-onboardPage,
    .ff-onboardingPage,
    .ff-launchWorkspace,
    .ff-onboarding
  ) :is(h2, .ff-h2, .ff-sectionTitle, .ff-panelTitle) {
    max-width: 16ch;
    font-size: var(--ff-6g-command-title);
    line-height: 1.05;
    letter-spacing: -0.036em;
    text-wrap: balance;
  }

  :where(
    [data-ff-onboard-root],
    .ff-onboardPage,
    .ff-onboardingPage,
    .ff-launchWorkspace,
    .ff-onboarding
  ) :is(p, li, .ff-copy, .ff-bodyText, .ff-heroLead, .ff-sectionLead) {
    max-width: 60ch;
    font-size: var(--ff-6g-command-copy);
    line-height: 1.52;
    text-wrap: pretty;
  }

  :where(
    [data-ff-onboard-root],
    .ff-onboardPage,
    .ff-onboardingPage,
    .ff-launchWorkspace,
    .ff-onboarding
  ) :is(
    .ff-card,
    .ff-panel,
    .ff-surface,
    .ff-stepCard,
    .ff-onboardCard,
    .ff-packageCard,
    .ff-formCard,
    .ff-checklistCard,
    [data-ff-card]
  ) {
    border: 1px solid var(--ff-6g-command-border);
    border-radius: var(--ff-6g-command-radius);
    box-shadow: var(--ff-6g-command-shadow);
  }

  :where(
    [data-ff-onboard-root],
    .ff-onboardPage,
    .ff-onboardingPage,
    .ff-launchWorkspace,
    .ff-onboarding
  ) :is(
    input,
    select,
    textarea,
    .ff-input,
    .ff-select,
    .ff-textarea
  ) {
    min-height: 46px;
    border-radius: 16px;
  }

  :where(
    [data-ff-onboard-root],
    .ff-onboardPage,
    .ff-onboardingPage,
    .ff-launchWorkspace,
    .ff-onboarding
  ) :is(
    button,
    .ff-button,
    .ff-btn,
    a[role="button"],
    input[type="submit"]
  ) {
    min-height: 44px;
    border-radius: 999px;
  }

  /* -----------------------------------------------------------------------
     Operator dashboard: unlocked/token command-center polish
  ----------------------------------------------------------------------- */

  :where(
    body.ff-dashboardModernBody,
    [data-ff-operator-root],
    [data-ff-dashboard-root],
    .ff-dashboardPage,
    .ff-dashboardModern,
    .ff-operatorPage,
    .ff-operatorDashboard
  ) {
    text-rendering: geometricPrecision;
    -webkit-font-smoothing: antialiased;
  }

  :where(
    [data-ff-operator-root],
    [data-ff-dashboard-root],
    .ff-dashboardPage,
    .ff-dashboardModern,
    .ff-operatorPage,
    .ff-operatorDashboard
  ) :is(
    .ff-shell,
    .ff-container,
    .ff-pageShell,
    .ff-dashboardShell,
    .ff-operatorShell,
    main
  ) {
    max-width: var(--ff-6g-command-max);
  }

  :where(
    [data-ff-operator-root],
    [data-ff-dashboard-root],
    .ff-dashboardPage,
    .ff-dashboardModern,
    .ff-operatorPage,
    .ff-operatorDashboard
  ) :is(
    .ff-dashboardHero,
    .ff-operatorHero,
    .ff-dashboardModern__hero,
    .ff-commandHero,
    .ff-hero
  ) {
    border-radius: clamp(24px, 3vw, 36px);
  }

  :where(
    [data-ff-operator-root],
    [data-ff-dashboard-root],
    .ff-dashboardPage,
    .ff-dashboardModern,
    .ff-operatorPage,
    .ff-operatorDashboard
  ) :is(h1, .ff-h1, .ff-heroTitle, .ff-dashboardModern__title) {
    max-width: 13ch;
    font-size: clamp(2rem, 3.65vw, 3.25rem);
    line-height: 1;
    letter-spacing: -0.046em;
    text-wrap: balance;
  }

  :where(
    [data-ff-operator-root],
    [data-ff-dashboard-root],
    .ff-dashboardPage,
    .ff-dashboardModern,
    .ff-operatorPage,
    .ff-operatorDashboard
  ) :is(h2, .ff-h2, .ff-sectionTitle, .ff-dashboardModern__sectionTitle) {
    max-width: 17ch;
    font-size: var(--ff-6g-command-title);
    line-height: 1.05;
    letter-spacing: -0.034em;
  }

  :where(
    [data-ff-operator-root],
    [data-ff-dashboard-root],
    .ff-dashboardPage,
    .ff-dashboardModern,
    .ff-operatorPage,
    .ff-operatorDashboard
  ) :is(
    .ff-card,
    .ff-panel,
    .ff-surface,
    .ff-dashboardCard,
    .ff-dashboardModern__card,
    .ff-dashboardModern__metric,
    .ff-metricCard,
    .ff-ledgerCard,
    .ff-sponsorCard,
    [data-ff-card]
  ) {
    border: 1px solid var(--ff-6g-command-border);
    border-radius: var(--ff-6g-command-radius);
    box-shadow: var(--ff-6g-command-shadow);
  }

  :where(
    [data-ff-operator-root],
    [data-ff-dashboard-root],
    .ff-dashboardPage,
    .ff-dashboardModern,
    .ff-operatorPage,
    .ff-operatorDashboard
  ) :is(
    .ff-cardTitle,
    .ff-panelTitle,
    .ff-metricTitle,
    .ff-dashboardModern__metricLabel,
    h3
  ) {
    font-size: var(--ff-6g-command-card-title);
    line-height: 1.12;
    letter-spacing: -0.024em;
    text-wrap: balance;
  }

  :where(
    [data-ff-operator-root],
    [data-ff-dashboard-root],
    .ff-dashboardPage,
    .ff-dashboardModern,
    .ff-operatorPage,
    .ff-operatorDashboard
  ) :is(
    .ff-metricValue,
    .ff-dashboardModern__metricValue,
    [data-ff-metric-value]
  ) {
    font-size: clamp(1.45rem, 2.6vw, 2.25rem);
    line-height: 1;
    letter-spacing: -0.045em;
  }

  :where(
    [data-ff-operator-root],
    [data-ff-dashboard-root],
    .ff-dashboardPage,
    .ff-dashboardModern,
    .ff-operatorPage,
    .ff-operatorDashboard
  ) :is(
    table,
    .ff-table,
    .ff-ledgerTable,
    [data-ff-donations-table]
  ) {
    border-radius: 20px;
    overflow: clip;
  }

  :where(
    [data-ff-operator-root],
    [data-ff-dashboard-root],
    .ff-dashboardPage,
    .ff-dashboardModern,
    .ff-operatorPage,
    .ff-operatorDashboard
  ) :is(
    input,
    select,
    textarea,
    .ff-input,
    .ff-select,
    .ff-textarea
  ) {
    min-height: 44px;
    border-radius: 14px;
  }

  :where(
    [data-ff-operator-root],
    [data-ff-dashboard-root],
    .ff-dashboardPage,
    .ff-dashboardModern,
    .ff-operatorPage,
    .ff-operatorDashboard
  ) :is(
    button,
    .ff-button,
    .ff-btn,
    a[role="button"],
    input[type="submit"]
  ) {
    min-height: 44px;
    border-radius: 999px;
  }

  @media (max-width: 720px) {
    :where(
      [data-ff-onboard-root],
      .ff-onboardPage,
      .ff-onboardingPage,
      .ff-launchWorkspace,
      .ff-onboarding,
      [data-ff-operator-root],
      [data-ff-dashboard-root],
      .ff-dashboardPage,
      .ff-dashboardModern,
      .ff-operatorPage,
      .ff-operatorDashboard
    ) :is(h1, .ff-h1, .ff-heroTitle, .ff-dashboardModern__title) {
      max-width: 11.4ch;
      font-size: clamp(1.95rem, 9.4vw, 2.9rem);
      line-height: 0.99;
      letter-spacing: -0.052em;
    }

    :where(
      [data-ff-onboard-root],
      .ff-onboardPage,
      .ff-onboardingPage,
      .ff-launchWorkspace,
      .ff-onboarding,
      [data-ff-operator-root],
      [data-ff-dashboard-root],
      .ff-dashboardPage,
      .ff-dashboardModern,
      .ff-operatorPage,
      .ff-operatorDashboard
    ) :is(
      .ff-card,
      .ff-panel,
      .ff-surface,
      .ff-dashboardCard,
      .ff-dashboardModern__card,
      .ff-dashboardModern__metric,
      .ff-onboardCard,
      .ff-stepCard,
      .ff-packageCard
    ) {
      border-radius: 22px;
    }
  }
}
'''

def backup(path: Path) -> None:
    stamp = time.strftime("%Y%m%d%H%M%S")
    backup_path = path.with_suffix(path.suffix + f".bak-hoi6g-{stamp}")
    backup_path.write_text(path.read_text(errors="ignore"))
    print(f"Backup: {backup_path}")

if not FF_CSS.exists():
    raise SystemExit(f"Missing {FF_CSS}")

text = FF_CSS.read_text(errors="ignore")
if MARKER in text:
    print(f"Already patched: {FF_CSS}")
else:
    backup(FF_CSS)
    FF_CSS.write_text(text.rstrip() + "\n" + BLOCK.strip() + "\n")
    print(f"Patched: {FF_CSS}")

print("HOI 6G onboarding + operator command polish complete.")
