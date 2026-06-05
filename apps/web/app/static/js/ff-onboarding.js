/* ==========================================================================
   FutureFunded — Onboarding V1 Runtime
   File: apps/web/app/static/js/ff-onboarding.js
   Marker: FF_ONBOARDING_V1_OWNED_HEADER_RUNTIME
   Builder: FF_ONBOARDING_BUILDER_WAVE1_RUNTIME

   Scope:
   - /platform/onboarding only
   - Owned header mobile menu
   - Local draft save
   - Live preview sync
   - Progress/checklist helpers
========================================================================== */

(() => {
  "use strict";

  const doc = document;
  const root =
    doc.querySelector("[data-ff-onboarding-root]") ||
    doc.querySelector("[data-ff-onboard-root]") ||
    doc.querySelector("[data-ff-page-root]");

  if (!root) return;

  const storageKey = "futurefunded.onboarding.v1.draft";

  const $ = (selector, scope = doc) => scope.querySelector(selector);
  const $$ = (selector, scope = doc) => Array.from(scope.querySelectorAll(selector));

  const header = $("[data-ff-onboard-header]");
  const menuToggle = $("[data-ff-onboard-menu-toggle]");
  const menu = $("[data-ff-onboard-menu]");

  const fields = $$("input[name], textarea[name], select[name]", root);
  const saveButtons = $$("[data-ff-save-onboarding], [data-ff-save-setup]", root);
  const continueButtons = $$("[data-ff-continue], [data-ff-next-step]", root);
  const backButtons = $$("[data-ff-back], [data-ff-prev-step]", root);
  const saveNote = $("[data-ff-save-note]", root);

  const previewSources = $$("[data-ff-preview-source]", root);
  const previewTargets = $$("[data-ff-preview-target]", root);
  const themePresets = $$("[data-ff-theme-preset]", root);
  const themeNameField = $("[data-ff-theme-name]", root);
  const colorPrimary = $("[data-ff-color-primary]", root);
  const colorAccent = $("[data-ff-color-accent]", root);
  const colorSoft = $("[data-ff-color-soft]", root);
  const styleTargets = $$("[data-ff-style-target]", root);
  const themeTargets = $$("[data-ff-theme-target]", root);

  const progressLabels = $$("[data-ff-progress-label]", root);
  const progressRing = $("[data-ff-progress-ring]", root);
  const progressMeter = $("[data-ff-progress-meter]", root);
  const stepPanels = $$("[data-ff-step-panel], [data-ff-onboard-step]", root);
  const stepButtons = $$("[data-ff-step-button], [data-ff-progress-step]", root);

  const announce = (message) => {
    if (!saveNote) return;
    saveNote.textContent = message;
    saveNote.setAttribute("role", "status");
  };

  const readDraft = () => {
    try {
      return JSON.parse(localStorage.getItem(storageKey) || "{}");
    } catch {
      return {};
    }
  };

  const writeDraft = (payload) => {
    try {
      localStorage.setItem(storageKey, JSON.stringify(payload));
      return true;
    } catch {
      return false;
    }
  };

  const collect = () => {
    const payload = {};

    fields.forEach((field) => {
      if (!field.name) return;

      if (field.type === "checkbox") {
        payload[field.name] = field.checked;
      } else if (field.type === "radio") {
        if (field.checked) payload[field.name] = field.value;
      } else {
        payload[field.name] = field.value;
      }
    });

    payload.updatedAt = new Date().toISOString();
    return payload;
  };

  const restore = () => {
    const payload = readDraft();

    fields.forEach((field) => {
      if (!field.name || !(field.name in payload)) return;

      if (field.type === "checkbox") {
        field.checked = Boolean(payload[field.name]);
      } else if (field.type === "radio") {
        field.checked = payload[field.name] === field.value;
      } else {
        field.value = payload[field.name];
      }
    });
  };

  const save = () => {
    const ok = writeDraft(collect());
    announce(ok ? "Saved locally — safe to keep editing." : "Could not save in this browser.");
  };

  const syncBuilderMeta = () => {
    const selectedStyle = $("input[name='campaign_style']:checked", root)?.value || "Community Team";
    const selectedTheme = themeNameField?.value || "Custom Theme";

    styleTargets.forEach((target) => {
      target.textContent = selectedStyle;
    });

    themeTargets.forEach((target) => {
      target.textContent = selectedTheme;
    });

    themePresets.forEach((button) => {
      const active = button.getAttribute("data-ff-theme-preset") === selectedTheme;
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-pressed", String(active));
    });
  };

  const applyBrandTheme = () => {
    const primary = colorPrimary?.value || "#ff5a1f";
    const accent = colorAccent?.value || "#0f766e";
    const soft = colorSoft?.value || "#fff3e7";

    root.style.setProperty("--ob-live-primary", primary);
    root.style.setProperty("--ob-live-primary-2", primary);
    root.style.setProperty("--ob-live-accent", accent);
    root.style.setProperty("--ob-live-soft", soft);
  };

  const applyThemePreset = (button) => {
    if (!(button instanceof HTMLElement)) return;

    const primary = button.getAttribute("data-primary") || "#ff5a1f";
    const secondary = button.getAttribute("data-secondary") || primary;
    const accent = button.getAttribute("data-accent") || "#0f766e";
    const soft = button.getAttribute("data-soft") || "#fff3e7";
    const name = button.getAttribute("data-ff-theme-preset") || "Custom Theme";

    if (colorPrimary) colorPrimary.value = primary;
    if (colorAccent) colorAccent.value = accent;
    if (colorSoft) colorSoft.value = soft;
    if (themeNameField) themeNameField.value = name;

    root.style.setProperty("--ob-live-primary", primary);
    root.style.setProperty("--ob-live-primary-2", secondary);
    root.style.setProperty("--ob-live-accent", accent);
    root.style.setProperty("--ob-live-soft", soft);

    syncBuilderMeta();
    syncPreview();
    syncProgress();
    save();
  };

  const syncPreview = () => {
    const values = {};

    previewSources.forEach((source) => {
      const key = source.getAttribute("data-ff-preview-source");
      if (!key) return;
      values[key] = source.value || source.textContent || "";
    });

    previewTargets.forEach((target) => {
      const key = target.getAttribute("data-ff-preview-target");
      if (!key || !(key in values)) return;
      target.textContent = values[key];
    });
  };

  const filledScore = () => {
    const explicit = Number(root.getAttribute("data-ff-progress-base") || "");
    if (Number.isFinite(explicit) && explicit > 0) {
      return Math.max(20, Math.min(96, Math.round(explicit)));
    }

    const visiblePanels = stepPanels.length ? stepPanels : [];
    const activeIndex = currentStep();
    const stepWeight = visiblePanels.length ? (activeIndex + 1) / visiblePanels.length : 0.2;

    const meaningful = fields.filter((field) => {
      if (field.disabled) return false;
      if (field.type === "hidden") return false;
      return field.hasAttribute("required") || field.closest("[data-ff-required]");
    });

    const completion = meaningful.length
      ? meaningful.filter((field) => {
          if (field.type === "checkbox") return field.checked;
          if (field.type === "radio") return field.checked;
          return String(field.value || "").trim().length > 0;
        }).length / meaningful.length
      : 0.35;

    const blended = Math.round((stepWeight * 62) + (completion * 24) + 14);
    return Math.max(20, Math.min(96, blended));
  };

  const syncProgress = () => {
    const score = filledScore();

    progressLabels.forEach((label) => {
      label.textContent = `${score}%`;
    });

    if (progressRing) {
      progressRing.style.setProperty("--progress", String(score));
      progressRing.setAttribute("aria-valuenow", String(score));
    }

    if (progressMeter) {
      progressMeter.style.width = `${score}%`;
      progressMeter.setAttribute("aria-valuenow", String(score));
    }

    root.setAttribute("data-ff-onboarding-progress", String(score));
  };

  const setActiveStep = (index) => {
    if (!stepPanels.length) return;

    const safeIndex = Math.max(0, Math.min(index, stepPanels.length - 1));

    stepPanels.forEach((panel, i) => {
      const active = i === safeIndex;
      panel.hidden = !active;
      panel.setAttribute("data-active", String(active));
    });

    stepButtons.forEach((button, i) => {
      button.setAttribute("aria-current", i === safeIndex ? "step" : "false");
      button.setAttribute("aria-pressed", String(i === safeIndex));
    });

    root.setAttribute("data-ff-active-step", String(safeIndex + 1));
  };

  const currentStep = () => {
    const raw = Number(root.getAttribute("data-ff-active-step") || "1");
    return Number.isFinite(raw) ? Math.max(0, raw - 1) : 0;
  };

  if (header && menuToggle && menu) {
    menuToggle.addEventListener("click", () => {
      const open = menuToggle.getAttribute("aria-expanded") === "true";
      menuToggle.setAttribute("aria-expanded", String(!open));
      header.setAttribute("data-menu-open", String(!open));
    });

    menu.addEventListener("click", (event) => {
      if (!(event.target instanceof Element)) return;
      if (!event.target.closest("a")) return;

      menuToggle.setAttribute("aria-expanded", "false");
      header.setAttribute("data-menu-open", "false");
    });
  }

  stepButtons.forEach((button, index) => {
    button.addEventListener("click", () => setActiveStep(index));
  });

  continueButtons.forEach((button) => {
    button.addEventListener("click", () => {
      setActiveStep(currentStep() + 1);
      save();
    });
  });

  backButtons.forEach((button) => {
    button.addEventListener("click", () => {
      setActiveStep(currentStep() - 1);
    });
  });

  fields.forEach((field) => {
    field.addEventListener("input", () => {
      applyBrandTheme();
      syncBuilderMeta();
      syncPreview();
      syncProgress();
    });

    field.addEventListener("change", () => {
      if (field.matches("[data-ff-color-primary], [data-ff-color-accent], [data-ff-color-soft]") && themeNameField) {
        themeNameField.value = "Custom Theme";
      }

      applyBrandTheme();
      syncBuilderMeta();
      syncPreview();
      syncProgress();
      save();
    });
  });

  themePresets.forEach((button) => {
    button.addEventListener("click", () => applyThemePreset(button));
  });

  saveButtons.forEach((button) => {
    button.addEventListener("click", save);
  });

  restore();
  applyBrandTheme();
  syncBuilderMeta();
  syncPreview();
  syncProgress();

  if (stepPanels.length) {
    setActiveStep(currentStep());
  }

  root.setAttribute("data-ff-onboarding-js", "owned-header-v1");
})();
