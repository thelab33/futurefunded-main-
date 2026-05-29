#!/usr/bin/env python3
from __future__ import annotations

import time
from pathlib import Path

ROOT = Path.cwd()

ONBOARD_JS = ROOT / "apps/web/app/static/js/ff-onboarding.js"
CAMPAIGN_JS = ROOT / "apps/web/app/static/js/ff-campaign.js"
FF_CSS = ROOT / "apps/web/app/static/css/ff.css"
CAMPAIGN_CSS = ROOT / "apps/web/app/static/css/campaign.css"

MARKER = "hoi-6i-brand-kit-contract-v1"

ONBOARD_APPEND = r'''

/* ==========================================================================
   FutureFunded HOI 6I — Brand Kit Persistence Contract
   Marker: hoi-6i-brand-kit-contract-v1

   Contract:
   - Onboarding owns setup intent.
   - Brand Kit saves a stable frontend contract to localStorage.
   - Campaign can preview the selected preset without inline styles.
   - Backend can later persist this exact contract to campaign settings.
========================================================================== */
(() => {
  "use strict";

  const CONTRACT_KEY = "futurefunded:brand-kit-contract:v1";
  const LEGACY_PRESET_KEY = "futurefunded:onboarding-brand-preset";
  const LEGACY_KIT_KEY = "futurefunded:onboarding-brand-kit";

  const ALLOWED_PRESETS = new Set(["elite", "school", "club", "nonprofit"]);

  const root = document.querySelector("[data-ff-onboard-root]");
  if (!root) return;

  const presetButtons = [...document.querySelectorAll("[data-ff-theme-preset]")];
  const saveButton = document.querySelector("[data-ff-save-onboarding]");
  const note = document.querySelector("[data-ff-save-note]");

  const fields = {
    primary: document.querySelector("[data-ff-color-primary]"),
    accent: document.querySelector("[data-ff-color-accent]"),
    soft: document.querySelector("[data-ff-color-soft]"),
  };

  function cleanPreset(value) {
    const preset = String(value || "").trim().toLowerCase();
    return ALLOWED_PRESETS.has(preset) ? preset : "elite";
  }

  function activePreset() {
    const pressed = presetButtons.find((button) => button.getAttribute("aria-pressed") === "true");
    return cleanPreset(
      root.getAttribute("data-ff-brand-preset") ||
      pressed?.getAttribute("data-preset") ||
      "elite"
    );
  }

  function buildContract() {
    return {
      version: 1,
      preset: activePreset(),
      primary: fields.primary?.value || "",
      accent: fields.accent?.value || "",
      soft: fields.soft?.value || "",
      source: "platform/onboarding",
      scope: "campaign-preview",
      updatedAt: new Date().toISOString(),
    };
  }

  function applyPreset(preset) {
    const safePreset = cleanPreset(preset);
    root.setAttribute("data-ff-brand-preset", safePreset);

    presetButtons.forEach((button) => {
      button.setAttribute(
        "aria-pressed",
        button.getAttribute("data-preset") === safePreset ? "true" : "false"
      );
    });

    return safePreset;
  }

  function saveContract(reason = "manual") {
    const contract = buildContract();
    contract.reason = reason;

    try {
      window.localStorage.setItem(CONTRACT_KEY, JSON.stringify(contract));
      window.localStorage.setItem(LEGACY_PRESET_KEY, contract.preset);
      window.localStorage.setItem(LEGACY_KIT_KEY, JSON.stringify(contract));
    } catch (_) {}

    root.setAttribute("data-ff-brand-contract-saved", "true");

    if (note) {
      note.textContent =
        reason === "preset"
          ? "Brand preset saved. Preview the campaign to see the theme contract."
          : "Brand kit saved locally. Preview the campaign to see the selected theme.";
    }

    return contract;
  }

  function restoreContract() {
    try {
      const raw = window.localStorage.getItem(CONTRACT_KEY);
      if (!raw) {
        const legacyPreset = window.localStorage.getItem(LEGACY_PRESET_KEY);
        if (legacyPreset) applyPreset(legacyPreset);
        return;
      }

      const contract = JSON.parse(raw);
      applyPreset(contract.preset);

      if (fields.primary && contract.primary) fields.primary.value = contract.primary;
      if (fields.accent && contract.accent) fields.accent.value = contract.accent;
      if (fields.soft && contract.soft) fields.soft.value = contract.soft;

      root.setAttribute("data-ff-brand-contract-saved", "true");
    } catch (_) {}
  }

  presetButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const preset = applyPreset(button.getAttribute("data-preset"));
      saveContract("preset");

      root.dispatchEvent(
        new CustomEvent("ff:brand-kit:preset", {
          bubbles: true,
          detail: { preset },
        })
      );
    });
  });

  Object.values(fields).forEach((field) => {
    if (!field) return;
    field.addEventListener("change", () => {
      saveContract("field");
    });
  });

  if (saveButton) {
    saveButton.addEventListener("click", () => {
      saveContract("manual");
    });
  }

  restoreContract();
})();
'''

CAMPAIGN_APPEND = r'''

/* ==========================================================================
   FutureFunded HOI 6I — Campaign Brand Kit Theme Bridge
   Marker: hoi-6i-brand-kit-contract-v1

   Contract:
   - Reads onboarding brand kit from localStorage.
   - Applies only safe preset attributes.
   - Does not use inline styles.
   - Does not change checkout/payment/sponsor hooks.
========================================================================== */
(() => {
  "use strict";

  const CONTRACT_KEY = "futurefunded:brand-kit-contract:v1";
  const LEGACY_PRESET_KEY = "futurefunded:onboarding-brand-preset";
  const ALLOWED_PRESETS = new Set(["elite", "school", "club", "nonprofit"]);

  function cleanPreset(value) {
    const preset = String(value || "").trim().toLowerCase();
    return ALLOWED_PRESETS.has(preset) ? preset : "";
  }

  function readPreset() {
    try {
      const raw = window.localStorage.getItem(CONTRACT_KEY);
      if (raw) {
        const contract = JSON.parse(raw);
        const preset = cleanPreset(contract.preset);
        if (preset) return preset;
      }

      return cleanPreset(window.localStorage.getItem(LEGACY_PRESET_KEY));
    } catch (_) {
      return "";
    }
  }

  function campaignRoots() {
    return [
      document.querySelector("[data-ff-page-root]"),
      document.querySelector(".ff-campaign"),
      document.body,
      document.documentElement,
    ].filter(Boolean);
  }

  function applyPreset(preset) {
    const safePreset = cleanPreset(preset);
    if (!safePreset) return;

    campaignRoots().forEach((root) => {
      root.setAttribute("data-ff-brand-preset", safePreset);
      root.setAttribute("data-ff-brand-kit-source", "local-preview");
    });
  }

  function start() {
    applyPreset(readPreset());

    window.addEventListener("storage", (event) => {
      if (event.key === CONTRACT_KEY || event.key === LEGACY_PRESET_KEY) {
        applyPreset(readPreset());
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, { once: true });
  } else {
    start();
  }
})();
'''

FF_CSS_APPEND = r'''

/* ==========================================================================
   FutureFunded HOI 6I — Brand Kit Preset Tokens
   Marker: hoi-6i-brand-kit-contract-v1

   CSP-safe theming:
   - Use data attributes and static preset tokens.
   - Do not require inline style attributes.
========================================================================== */

@layer utilities {
  :where(
    [data-ff-brand-preset="elite"],
    [data-ff-brand-preset="elite"] *
  ) {
    --ff-brand-primary: #ff5a1f;
    --ff-brand-accent: #0f766e;
    --ff-brand-soft: #fff3e7;
  }

  :where(
    [data-ff-brand-preset="school"],
    [data-ff-brand-preset="school"] *
  ) {
    --ff-brand-primary: #1d4ed8;
    --ff-brand-accent: #f59e0b;
    --ff-brand-soft: #eff6ff;
  }

  :where(
    [data-ff-brand-preset="club"],
    [data-ff-brand-preset="club"] *
  ) {
    --ff-brand-primary: #047857;
    --ff-brand-accent: #111827;
    --ff-brand-soft: #ecfdf5;
  }

  :where(
    [data-ff-brand-preset="nonprofit"],
    [data-ff-brand-preset="nonprofit"] *
  ) {
    --ff-brand-primary: #7c3aed;
    --ff-brand-accent: #db2777;
    --ff-brand-soft: #f5f3ff;
  }

  :where(.ffOnboardV2)[data-ff-brand-preset] {
    --onboard-primary: var(--ff-brand-primary);
    --onboard-accent: var(--ff-brand-accent);
    --onboard-soft: var(--ff-brand-soft);
  }
}
'''

CAMPAIGN_CSS_APPEND = r'''

/* ==========================================================================
   FutureFunded HOI 6I — Campaign Theme Contract Preview
   Marker: hoi-6i-brand-kit-contract-v1

   Applies saved onboarding preset to campaign preview using static tokens.
   This is frontend preview only; backend persistence can later render the same
   data-ff-brand-preset attribute server-side.
========================================================================== */

@layer campaign {
  [data-ff-page-root][data-ff-brand-preset],
  .ff-campaign[data-ff-brand-preset],
  body[data-ff-brand-preset] {
    --ff-campaign-primary: var(--ff-brand-primary);
    --ff-campaign-accent: var(--ff-brand-accent);
    --ff-campaign-soft: var(--ff-brand-soft);
  }

  [data-ff-page-root][data-ff-brand-preset] :is(
    [data-ff-open-checkout],
    [data-ff-donate-trigger],
    [data-ff-payment-trigger],
    .ff-btn-primary,
    .ff-button--primary
  ) {
    background: linear-gradient(
      135deg,
      var(--ff-campaign-primary),
      color-mix(in srgb, var(--ff-campaign-primary) 74%, white)
    );
    border-color: color-mix(in srgb, var(--ff-campaign-primary) 82%, black);
  }

  [data-ff-page-root][data-ff-brand-preset] :is(
    .ff-progress__bar,
    .ff-meter__bar,
    .ff-campaignProgress__bar,
    [data-ff-progress-bar]
  ) {
    background: linear-gradient(90deg, var(--ff-campaign-primary), var(--ff-campaign-accent));
  }

  [data-ff-page-root][data-ff-brand-preset] :is(
    .ff-badge,
    .ff-pill,
    .ff-eyebrow,
    .ff-kicker
  ) {
    border-color: color-mix(in srgb, var(--ff-campaign-primary) 28%, transparent);
  }

  [data-ff-page-root][data-ff-brand-preset] :is(
    .ff-campaignHero,
    .ff-hero,
    .ff-donatePanel,
    .ff-donationPanel,
    .ff-sponsorCard
  ) {
    --ff-theme-wash: var(--ff-campaign-soft);
  }
}
'''

def backup(path: Path) -> None:
    if path.exists():
        stamp = time.strftime("%Y%m%d%H%M%S")
        backup_path = path.with_suffix(path.suffix + f".bak-hoi6i-{stamp}")
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

append_once(ONBOARD_JS, MARKER, ONBOARD_APPEND)
append_once(CAMPAIGN_JS, MARKER, CAMPAIGN_APPEND)
append_once(FF_CSS, MARKER, FF_CSS_APPEND)
append_once(CAMPAIGN_CSS, MARKER, CAMPAIGN_CSS_APPEND)

print("HOI 6I brand kit contract patch complete.")
