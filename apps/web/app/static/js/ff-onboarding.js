/* ==========================================================================
   FutureFunded HOI 6H.1 — CSP-safe onboarding Brand Kit
   Marker: hoi-6h1-onboarding-csp-layer-fix-v1
========================================================================== */
(() => {
  "use strict";

  const root = document.querySelector("[data-ff-onboard-root]");
  if (!root) return;

  const save = document.querySelector("[data-ff-save-onboarding]");
  const note = document.querySelector("[data-ff-save-note]");
  const presetButtons = [...document.querySelectorAll("[data-ff-theme-preset]")];

  const setPreset = (preset) => {
    if (!preset) return;
    root.setAttribute("data-ff-brand-preset", preset);
  };

  presetButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const preset = button.getAttribute("data-preset") || "elite";
      setPreset(preset);

      try {
        window.localStorage.setItem("futurefunded:onboarding-brand-preset", preset);
      } catch (_) {}

      presetButtons.forEach((item) => {
        item.setAttribute("aria-pressed", item === button ? "true" : "false");
      });
    });
  });

  try {
    const savedPreset = window.localStorage.getItem("futurefunded:onboarding-brand-preset");
    if (savedPreset) {
      setPreset(savedPreset);
      presetButtons.forEach((item) => {
        item.setAttribute("aria-pressed", item.getAttribute("data-preset") === savedPreset ? "true" : "false");
      });
    }
  } catch (_) {}

  if (save) {
    save.addEventListener("click", () => {
      const payload = {
        preset: root.getAttribute("data-ff-brand-preset") || "elite",
        savedAt: new Date().toISOString(),
      };

      try {
        window.localStorage.setItem("futurefunded:onboarding-brand-kit", JSON.stringify(payload));
      } catch (_) {}

      if (note) {
        note.textContent = "Launch setup saved locally. Review the campaign before sharing.";
      }
    });
  }
})();
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
