#!/usr/bin/env python3
from __future__ import annotations

import re
import time
from pathlib import Path

ROOT = Path.cwd()

FILES = {
    "platform": ROOT / "apps/web/app/templates/platform/index.html",
    "campaign": ROOT / "apps/web/app/templates/campaign/index.html",
    "login": ROOT / "apps/web/app/templates/platform/login.html",
    "onboarding": ROOT / "apps/web/app/templates/platform/onboarding.html",
    "dashboard": ROOT / "apps/web/app/templates/platform/dashboard.html",
    "ff_css": ROOT / "apps/web/app/static/css/ff.css",
    "campaign_css": ROOT / "apps/web/app/static/css/campaign.css",
}

MARKER = "hoi-6j-unified-brand-shell-v1"

FF_CSS_BLOCK = r'''

/* ==========================================================================
   FutureFunded HOI 6J — Unified Brand Shell + Header/Nav Authority
   Marker: hoi-6j-unified-brand-shell-v1

   Intent:
   - one premium header rhythm across platform, campaign, login, onboarding, dashboard
   - preserve page-specific nav modes: marketing, campaign, operator
   - unify FF mark sizing, brand lockup, pill shell, nav spacing, and mobile behavior
   - avoid risky macro/template rewrites while the product is launch-ready
========================================================================== */

@layer components, platform, utilities {
  :root {
    --ff-6j-header-max: 1180px;
    --ff-6j-header-h: 58px;
    --ff-6j-header-pad: 0.48rem;
    --ff-6j-header-gap: clamp(0.55rem, 1.4vw, 1rem);
    --ff-6j-header-radius: 999px;
    --ff-6j-logo-size: 40px;
    --ff-6j-logo-radius: 14px;
    --ff-6j-header-bg: rgba(255, 255, 255, 0.76);
    --ff-6j-header-border: rgba(148, 163, 184, 0.22);
    --ff-6j-header-shadow: 0 18px 58px rgba(15, 23, 42, 0.09);
    --ff-6j-header-ink: #211712;
    --ff-6j-header-muted: rgba(33, 23, 18, 0.58);
  }

  /* Shell targets:
     - platform/campaign use .ff-siteHeader > .ff-siteHeader__shell
     - login/onboarding/dashboard use custom topbar classes
  */
  :where(.ff-siteHeader[data-ff-header]) > :where(.ff-siteHeader__shell),
  :where(.ff-loginAuthority__topbar[data-ff-header]),
  :where(.ffOnboardV2__topbar[data-ff-header]),
  :where(.ff-dashboardModern__topbar[data-ff-header]) {
    width: min(var(--ff-6j-header-max), calc(100% - 2rem));
    min-height: var(--ff-6j-header-h);
    margin-inline: auto;
    padding: var(--ff-6j-header-pad);
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--ff-6j-header-gap);
    border: 1px solid var(--ff-6j-header-border);
    border-radius: var(--ff-6j-header-radius);
    background:
      linear-gradient(180deg, rgba(255,255,255,0.88), var(--ff-6j-header-bg));
    color: var(--ff-6j-header-ink);
    box-shadow: var(--ff-6j-header-shadow);
    backdrop-filter: blur(18px) saturate(1.18);
    -webkit-backdrop-filter: blur(18px) saturate(1.18);
  }

  :where(.ff-siteHeader[data-ff-header]) {
    width: 100%;
  }

  :where(
    .ff-siteHeader__brand,
    .ff-loginAuthority__brand,
    .ffOnboardV2__brand,
    .ff-dashboardModern__brand
  ) {
    min-width: 0;
    display: inline-flex;
    align-items: center;
    gap: 0.72rem;
    color: inherit;
    text-decoration: none;
  }

  :where(
    .ff-brandMark__symbol,
    .ff-brandMark__logo,
    .ff-loginAuthority__brandMark,
    .ffOnboardV2__logo,
    .ff-dashboardModern__brandMark
  ) {
    width: var(--ff-6j-logo-size);
    height: var(--ff-6j-logo-size);
    flex: 0 0 var(--ff-6j-logo-size);
    display: grid;
    place-items: center;
    overflow: hidden;
    border-radius: var(--ff-6j-logo-radius);
    background:
      radial-gradient(circle at 30% 20%, rgba(255,255,255,0.24), transparent 32%),
      linear-gradient(135deg, #3d261b, #160d08);
    color: #fff;
    font-size: 0.84rem;
    font-weight: 950;
    letter-spacing: -0.035em;
    box-shadow:
      inset 0 1px 0 rgba(255,255,255,0.22),
      0 10px 26px rgba(15,23,42,0.12);
  }

  :where(.ff-brandMark__logo) {
    object-fit: cover;
    background: #fff;
  }

  :where(
    .ff-brandMark__copy,
    .ff-loginAuthority__brandCopy,
    .ff-dashboardModern__brandCopy
  ),
  :where(.ffOnboardV2__brand > span:last-child) {
    min-width: 0;
    display: grid;
    gap: 0.12rem;
  }

  :where(
    .ff-brandMark__copy,
    .ff-loginAuthority__brandCopy,
    .ff-dashboardModern__brandCopy
  ) strong,
  :where(.ffOnboardV2__brand > span:last-child strong) {
    max-width: 18rem;
    overflow: hidden;
    color: var(--ff-6j-header-ink);
    font-size: clamp(0.92rem, 1vw, 1.02rem);
    font-weight: 950;
    line-height: 1;
    letter-spacing: -0.04em;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  :where(
    .ff-brandMark__copy,
    .ff-loginAuthority__brandCopy,
    .ff-dashboardModern__brandCopy
  ) small,
  :where(.ffOnboardV2__brand > span:last-child small) {
    max-width: 18rem;
    overflow: hidden;
    color: var(--ff-6j-header-muted);
    font-size: clamp(0.64rem, 0.7vw, 0.72rem);
    font-weight: 950;
    line-height: 1;
    letter-spacing: 0.17em;
    text-overflow: ellipsis;
    text-transform: uppercase;
    white-space: nowrap;
  }

  :where(
    .ff-siteHeader__nav,
    .ff-loginAuthority__nav,
    .ffOnboardV2__nav,
    .ff-dashboardModern__nav
  ) {
    min-width: 0;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 0.18rem;
  }

  :where(
    .ff-siteHeader__nav,
    .ff-loginAuthority__nav,
    .ffOnboardV2__nav,
    .ff-dashboardModern__nav
  ) a {
    min-height: 38px;
    padding: 0.64rem 0.82rem;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 999px;
    color: rgba(33, 23, 18, 0.72);
    font-size: clamp(0.78rem, 0.72vw, 0.88rem);
    font-weight: 900;
    line-height: 1;
    letter-spacing: -0.015em;
    text-decoration: none;
    white-space: nowrap;
  }

  :where(
    .ff-siteHeader__nav,
    .ff-loginAuthority__nav,
    .ffOnboardV2__nav,
    .ff-dashboardModern__nav
  ) a:hover,
  :where(
    .ff-siteHeader__nav,
    .ff-loginAuthority__nav,
    .ffOnboardV2__nav,
    .ff-dashboardModern__nav
  ) a:focus-visible {
    color: #160f0b;
    background: rgba(255, 255, 255, 0.82);
  }

  :where(
    .ff-siteHeader__actions,
    .ff-campaignHeader__actions,
    .ff-dashboardModern__heroActions
  ) {
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
  }

  :where(.ff-siteHeader__actions) :where(.ff-button),
  :where(.ff-campaignHeader__actions) :where(.ff-button) {
    min-height: 40px;
    padding-inline: 0.95rem;
  }

  /* Page mode nuance without changing the underlying HTML. */
  :where([data-ff-header-mode="marketing"]) :where(.ff-siteHeader__nav) {
    flex: 1 1 auto;
  }

  :where([data-ff-header-mode="operator"]) :where(
    .ff-loginAuthority__nav,
    .ffOnboardV2__nav,
    .ff-dashboardModern__nav
  ) a {
    font-weight: 920;
  }

  :where([data-ff-header-mode="campaign"]) :where(.ff-siteHeader__brand) {
    max-width: min(38vw, 21rem);
  }

  @media (max-width: 860px) {
    :where(.ff-siteHeader[data-ff-header]) > :where(.ff-siteHeader__shell),
    :where(.ff-loginAuthority__topbar[data-ff-header]),
    :where(.ffOnboardV2__topbar[data-ff-header]),
    :where(.ff-dashboardModern__topbar[data-ff-header]) {
      width: min(100% - 1rem, var(--ff-6j-header-max));
      min-height: 56px;
      gap: 0.45rem;
      border-radius: 24px;
    }

    :where(
      .ff-brandMark__symbol,
      .ff-brandMark__logo,
      .ff-loginAuthority__brandMark,
      .ffOnboardV2__logo,
      .ff-dashboardModern__brandMark
    ) {
      --ff-6j-logo-size: 36px;
      --ff-6j-logo-radius: 12px;
    }

    :where(
      .ff-brandMark__copy,
      .ff-loginAuthority__brandCopy,
      .ff-dashboardModern__brandCopy
    ) strong,
    :where(.ffOnboardV2__brand > span:last-child strong) {
      max-width: 10.5rem;
    }

    :where(
      .ff-brandMark__copy,
      .ff-loginAuthority__brandCopy,
      .ff-dashboardModern__brandCopy
    ) small,
    :where(.ffOnboardV2__brand > span:last-child small) {
      max-width: 10.5rem;
      font-size: 0.58rem;
      letter-spacing: 0.12em;
    }

    :where(
      .ff-siteHeader__nav,
      .ff-loginAuthority__nav,
      .ffOnboardV2__nav,
      .ff-dashboardModern__nav
    ) {
      justify-content: flex-end;
      overflow-x: auto;
      scrollbar-width: none;
    }

    :where(
      .ff-siteHeader__nav,
      .ff-loginAuthority__nav,
      .ffOnboardV2__nav,
      .ff-dashboardModern__nav
    )::-webkit-scrollbar {
      display: none;
    }

    :where(
      .ff-siteHeader__nav,
      .ff-loginAuthority__nav,
      .ffOnboardV2__nav,
      .ff-dashboardModern__nav
    ) a {
      min-height: 34px;
      padding: 0.52rem 0.62rem;
      font-size: 0.75rem;
    }
  }

  @media (max-width: 560px) {
    :where(.ff-siteHeader[data-ff-header]) > :where(.ff-siteHeader__shell),
    :where(.ff-loginAuthority__topbar[data-ff-header]),
    :where(.ffOnboardV2__topbar[data-ff-header]),
    :where(.ff-dashboardModern__topbar[data-ff-header]) {
      align-items: center;
      border-radius: 22px;
    }

    :where(
      .ff-siteHeader__brand,
      .ff-loginAuthority__brand,
      .ffOnboardV2__brand,
      .ff-dashboardModern__brand
    ) {
      flex: 0 1 auto;
      max-width: 48vw;
    }

    :where(
      .ff-brandMark__copy,
      .ff-loginAuthority__brandCopy,
      .ff-dashboardModern__brandCopy
    ) small,
    :where(.ffOnboardV2__brand > span:last-child small) {
      display: none;
    }

    :where(
      .ff-brandMark__copy,
      .ff-loginAuthority__brandCopy,
      .ff-dashboardModern__brandCopy
    ) strong,
    :where(.ffOnboardV2__brand > span:last-child strong) {
      max-width: 7.8rem;
    }

    :where(.ff-siteHeader__actions) :where(.ff-button--ghost),
    :where(.ff-campaignHeader__actions) :where(.ff-button--ghost) {
      display: none;
    }

    :where(.ff-siteHeader__actions) :where(.ff-button),
    :where(.ff-campaignHeader__actions) :where(.ff-button) {
      min-height: 36px;
      padding-inline: 0.78rem;
      font-size: 0.76rem;
    }
  }
}
'''

CAMPAIGN_CSS_BLOCK = r'''

/* ==========================================================================
   FutureFunded HOI 6J — Campaign Header Brand Shell Tuning
   Marker: hoi-6j-unified-brand-shell-v1
========================================================================== */

@layer campaign {
  .ff-campaignHeader[data-ff-header] > .ff-siteHeader__shell {
    max-width: min(1180px, calc(100% - 1rem));
  }

  @media (max-width: 560px) {
    .ff-campaignHeader[data-ff-header] .ff-siteHeader__brand {
      max-width: 46vw;
    }

    .ff-campaignHeader[data-ff-header] .ff-brandMark__copy strong {
      max-width: 7.2rem;
    }

    .ff-campaignHeader[data-ff-header] .ff-siteHeader__nav {
      display: none;
    }
  }
}
'''

def backup(path: Path) -> None:
    if path.exists():
        stamp = time.strftime("%Y%m%d%H%M%S")
        backup_path = path.with_suffix(path.suffix + f".bak-hoi6j-{stamp}")
        backup_path.write_text(path.read_text(errors="ignore"))
        print(f"Backup: {backup_path}")

def write_if_changed(path: Path, text: str) -> None:
    old = path.read_text(errors="ignore") if path.exists() else ""
    if old == text:
        print(f"No change: {path}")
        return
    backup(path)
    path.write_text(text)
    print(f"Patched: {path}")

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

def add_attrs_to_opening_tag(text: str, pattern: str, attrs: str) -> str:
    match = re.search(pattern, text)
    if not match:
      return text

    tag = match.group(0)

    changed = tag
    for attr in attrs.split():
        # split only attr names from attr="value"
        name = attr.split("=")[0]
        if re.search(rf"\b{name}\b", changed):
            continue
        changed = changed[:-1] + f" {attr}>"

    return text[:match.start()] + changed + text[match.end():]

# Platform header: already good; add explicit mode/context.
p = FILES["platform"]
if p.exists():
    text = p.read_text(errors="ignore")
    text = text.replace(
        '<header class="ff-siteHeader ff-siteHeader--platform" data-ff-header data-ff-home-header role="banner">',
        '<header class="ff-siteHeader ff-siteHeader--platform" data-ff-header data-ff-header-mode="marketing" data-ff-brand-context="fundraising-platform" data-ff-home-header role="banner">'
    )
    write_if_changed(p, text)

# Campaign header: already good; add explicit mode/context while preserving campaign hooks.
p = FILES["campaign"]
if p.exists():
    text = p.read_text(errors="ignore")
    text = text.replace(
        '<header class="ff-siteHeader ff-campaignHeader" data-ff-campaign-header="true" data-ff-header="campaign" data-ff-header-surface="unified" data-ff-header-variant="campaign" role="banner">',
        '<header class="ff-siteHeader ff-campaignHeader" data-ff-campaign-header="true" data-ff-header="campaign" data-ff-header-mode="campaign" data-ff-brand-context="live-season-fund" data-ff-header-surface="unified" data-ff-header-variant="campaign" role="banner">'
    )
    write_if_changed(p, text)

# Login header: add shared data contract, keep local classes.
p = FILES["login"]
if p.exists():
    text = p.read_text(errors="ignore")
    text = text.replace(
        '<header class="ff-loginAuthority__topbar" aria-label="FutureFunded organizer access">',
        '<header class="ff-loginAuthority__topbar" data-ff-header data-ff-header-mode="operator" data-ff-brand-context="organizer-access" role="banner" aria-label="FutureFunded organizer access">'
    )
    write_if_changed(p, text)

# Onboarding header: add explicit mode/context.
p = FILES["onboarding"]
if p.exists():
    text = p.read_text(errors="ignore")
    text = text.replace(
        '<header class="ffOnboardV2__topbar" data-ff-header>',
        '<header class="ffOnboardV2__topbar" data-ff-header data-ff-header-mode="operator" data-ff-brand-context="launch-workspace" role="banner">'
    )
    write_if_changed(p, text)

# Dashboard header: add shared data contract, keep local classes.
p = FILES["dashboard"]
if p.exists():
    text = p.read_text(errors="ignore")
    text = text.replace(
        '<header class="ff-dashboardModern__topbar" aria-label="Dashboard navigation">',
        '<header class="ff-dashboardModern__topbar" data-ff-header data-ff-header-mode="operator" data-ff-brand-context="operator-command-center" role="banner" aria-label="Dashboard navigation">'
    )
    write_if_changed(p, text)

append_once(FILES["ff_css"], MARKER, FF_CSS_BLOCK)
append_once(FILES["campaign_css"], MARKER, CAMPAIGN_CSS_BLOCK)

print("HOI 6J unified brand shell patch complete.")
