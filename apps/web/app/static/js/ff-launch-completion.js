/*
  FutureFunded Launch Completion Runtime
  File: apps/web/app/static/js/ff-launch-completion.js
  Version: onboarding-runtime-authority-v1

  Owns:
  - onboarding copy buttons
  - launch setup save feedback
  - readiness meter hydration
  - local draft persistence
  - dashboard launch assistant copy support
*/

(() => {
  "use strict";

  const VERSION = "onboarding-runtime-authority-v1";
  const ROOT_SELECTOR =
    "[data-ff-onboard-root], [data-ff-dashboard-launch-assistant='p0-launch-completion']";

  const roots = Array.from(document.querySelectorAll(ROOT_SELECTOR));

  if (!roots.length) return;

  const storageKey = "futurefunded.launchSetupDraft.v1";

  const clamp = (value, min = 0, max = 100) => {
    const number = Number.parseFloat(value);
    if (!Number.isFinite(number)) return min;
    return Math.min(max, Math.max(min, number));
  };

  const textOf = (node) => {
    if (!node) return "";
    if ("value" in node) return String(node.value || "").trim();
    return String(node.textContent || "").trim();
  };

  const setStatus = (root, message, tone = "neutral") => {
    const status = root.querySelector("[data-ff-save-status]");
    if (!status) return;

    status.textContent = message;
    status.dataset.ffTone = tone;
  };

  const setButtonCopied = (button) => {
    const old = button.textContent;
    button.textContent = "Copied";
    button.dataset.ffCopied = "true";

    window.setTimeout(() => {
      button.textContent = old;
      delete button.dataset.ffCopied;
    }, 1800);
  };


  const fieldValue = (scope, name) =>
    String(scope?.querySelector(`[name="${name}"]`)?.value || "").trim();

  const composeTextDonateMessage = (scope) => {
    if (!scope) return "";

    const keyword = fieldValue(scope, "text_to_donate_keyword") || "ATX";
    const number = fieldValue(scope, "text_to_donate_number") || "+1 512 000 0000";
    const url =
      fieldValue(scope, "text_to_donate_fallback_url") ||
      "https://getfuturefunded.com/c/connect-atx-elite";

    return `Text ${keyword} to ${number} to support the campaign, or give online: ${url}`;
  };

  const updateTextDonatePreview = (root) => {
    root.querySelectorAll("[data-ff-text-donate-setup]").forEach((scope) => {
      const preview = scope.querySelector("[data-ff-text-donate-preview]");
      if (preview) preview.textContent = composeTextDonateMessage(scope);
    });
  };

  const copyText = async (text) => {
    const value = String(text || "").trim();
    if (!value) return false;

    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(value);
      return true;
    }

    const textarea = document.createElement("textarea");
    textarea.value = value;
    textarea.setAttribute("readonly", "");
    textarea.className = "ff-copyBuffer";
    document.body.appendChild(textarea);
    textarea.select();

    try {
      return document.execCommand("copy");
    } finally {
      textarea.remove();
    }
  };

  const wireCopyButtons = (root) => {
    root.addEventListener("click", async (event) => {
      const button = event.target.closest("[data-ff-copy-button]");
      if (!button || !root.contains(button)) return;

      const scope =
        button.closest("[data-ff-text-donate-setup], [data-ff-onboarding-text-to-donate], article, section") ||
        root;

      const explicit =
        button.getAttribute("data-ff-copy-value") ||
        button.dataset.ffCopyValue ||
        "";

      const source =
        scope.querySelector("[data-ff-copy-source]") ||
        button.closest("article")?.querySelector("[data-ff-copy-source]") ||
        root.querySelector("[data-ff-copy-source]");

      const text = button.matches("[data-ff-copy-text-donate]")
        ? composeTextDonateMessage(scope)
        : explicit || textOf(source);

      if (!text) {
        setStatus(root, "Nothing to copy yet.", "warning");
        return;
      }

      try {
        await copyText(text);
        setButtonCopied(button);
        setStatus(root, "Copied to clipboard.", "success");
      } catch {
        if (source && "focus" in source) source.focus();
        if (source && "select" in source) source.select();
        setStatus(root, "Copy failed. Select the text and copy manually.", "warning");
      }
    });
  };

  const formToObject = (form) => {
    const data = new FormData(form);
    const payload = {};

    for (const [key, value] of data.entries()) {
      if (payload[key]) {
        payload[key] = Array.isArray(payload[key])
          ? [...payload[key], value]
          : [payload[key], value];
      } else {
        payload[key] = value;
      }
    }

    return payload;
  };

  const scoreForm = (form) => {
    const fields = Array.from(form.querySelectorAll("input, select, textarea")).filter((field) => {
      if (field.type === "hidden" || field.disabled) return false;
      if (field.type === "checkbox") return true;
      return true;
    });

    if (!fields.length) return 68;

    let completed = 0;

    for (const field of fields) {
      if (field.type === "checkbox") {
        if (field.checked) completed += 1;
        continue;
      }

      if (String(field.value || "").trim()) completed += 1;
    }

    return Math.round((completed / fields.length) * 100);
  };

  const updateReadiness = (root) => {
    const form = root.querySelector("[data-ff-form='launch-setup']");
    const score = form ? scoreForm(form) : 68;
    const safeScore = clamp(score, 0, 100);

    root.style.setProperty("--ff-onboard-progress", `${safeScore}%`);

    root.querySelectorAll("[data-ff-progress-value], [data-ff-progress-bucket]").forEach((meter) => {
      meter.dataset.ffProgressValue = String(safeScore);
      meter.dataset.ffProgressBucket = String(safeScore);
      meter.style.setProperty("--ff-onboard-progress", `${safeScore}%`);
    });

    root.querySelectorAll("[data-ff-readiness-score]").forEach((node) => {
      node.textContent = `${safeScore}%`;
    });
  };

  const saveDraft = (root, form) => {
    const payload = {
      savedAt: new Date().toISOString(),
      version: VERSION,
      form: formToObject(form),
    };

    try {
      window.localStorage.setItem(storageKey, JSON.stringify(payload));
    } catch {
      // localStorage may be disabled; the UI still confirms local in-page save.
    }

    root.dataset.ffLaunchSaved = "true";
    setStatus(root, "Launch setup saved locally for this browser.", "success");

    window.dispatchEvent(
      new CustomEvent("futurefunded:launch-setup-saved", {
        detail: payload,
      }),
    );
  };

  const restoreDraft = (root, form) => {
    let payload = null;

    try {
      payload = JSON.parse(window.localStorage.getItem(storageKey) || "null");
    } catch {
      payload = null;
    }

    if (!payload?.form) return;

    for (const [key, value] of Object.entries(payload.form)) {
      const fields = Array.from(form.querySelectorAll(`[name="${CSS.escape(key)}"]`));
      if (!fields.length) continue;

      for (const field of fields) {
        if (field.type === "checkbox") {
          field.checked = value === "on" || value === true;
        } else if (Array.isArray(value)) {
          field.value = value[0] || "";
        } else {
          field.value = value;
        }
      }
    }

    root.dataset.ffLaunchRestored = "true";
    setStatus(root, "Recovered your last local launch draft.", "success");
  };

  const wireForm = (root) => {
    const form = root.querySelector("[data-ff-form='launch-setup']");
    if (!form) return;

    restoreDraft(root, form);
    updateReadiness(root);

    form.addEventListener("input", () => {
      root.dataset.ffLaunchDirty = "true";
      setStatus(root, "Unsaved local changes.", "neutral");
      updateReadiness(root);
    });

    form.addEventListener("change", () => {
      root.dataset.ffLaunchDirty = "true";
      updateReadiness(root);
    });

    root.addEventListener("click", (event) => {
      const button = event.target.closest("[data-ff-action='save-launch-setup']");
      if (!button || !root.contains(button)) return;

      event.preventDefault();

      button.setAttribute("aria-busy", "true");
      const old = button.textContent;
      button.textContent = "Saved";

      saveDraft(root, form);
      updateReadiness(root);

      window.setTimeout(() => {
        button.removeAttribute("aria-busy");
        button.textContent = old;
      }, 1400);
    });
  };

  const wireSmoothAnchors = (root) => {
    root.addEventListener("click", (event) => {
      const link = event.target.closest("a[href^='#']");
      if (!link || !root.contains(link)) return;

      const target = document.querySelector(link.getAttribute("href"));
      if (!target) return;

      event.preventDefault();
      target.scrollIntoView({ behavior: "smooth", block: "start" });
      target.setAttribute("tabindex", "-1");
      target.focus({ preventScroll: true });
    });
  };

  const boot = (root) => {
    if (root.dataset.ffLaunchCompletionRuntime === VERSION) return;

    root.dataset.ffLaunchCompletionRuntime = VERSION;
    document.documentElement.dataset.ffLaunchCompletionRuntime = VERSION;

    wireCopyButtons(root);
    wireForm(root);
    wireSmoothAnchors(root);
    updateTextDonatePreview(root);
    root.addEventListener("input", () => updateTextDonatePreview(root));
    updateReadiness(root);
  };

  roots.forEach(boot);

  window.FutureFundedLaunchCompletion = {
    version: VERSION,
    roots,
    updateReadiness: () => roots.forEach(updateReadiness),
  };

  console.info("[FutureFunded] Launch completion runtime ready.", VERSION);
})();
