(() => {
  const root = document.querySelector("[data-ff-onboard-root]");
  const form = document.querySelector("[data-ff-onboard-form]");
  if (!root || !form) return;

  const panels = Array.from(document.querySelectorAll("[data-ff-step-panel]"));
  const steps = Array.from(document.querySelectorAll("[data-step-index]"));
  const nextBtn = document.querySelector("[data-ff-next-step]");
  const prevBtn = document.querySelector("[data-ff-prev-step]");
  const saveBtn = document.querySelector("[data-ff-save-onboarding]");
  const progressBar = document.querySelector("[data-ff-progress-bar]");
  const progressLabels = Array.from(document.querySelectorAll("[data-ff-progress-label]"));\n  const progressRing = document.querySelector("[data-ff-progress-ring]");
  const saveNote = document.querySelector("[data-ff-save-note]");
  const previewSources = Array.from(document.querySelectorAll("[data-ff-preview-source]"));

  let current = 0;

  function clampStep(value) {
    return Math.max(0, Math.min(panels.length - 1, value));
  }

  function setStep(index) {
    current = clampStep(index);

    panels.forEach((panel, i) => {
      panel.classList.toggle("is-active", i === current);
    });

    steps.forEach((step, i) => {
      if (i === current) step.setAttribute("aria-current", "step");
      else step.removeAttribute("aria-current");
    });

    const pct = Math.round(((current + 1) / panels.length) * 100);
    if (progressBar) progressBar.style.width = `${pct}%`;
    progressLabels.forEach((label) => { label.textContent = `${pct}%`; });\n    if (progressRing) {\n      progressRing.style.setProperty("--ff-progress-deg", `${Math.round((pct / 100) * 360)}deg`);\n      progressRing.setAttribute("aria-label", `${pct}% complete`);\n    }

    if (prevBtn) prevBtn.disabled = current === 0;
    if (nextBtn) nextBtn.textContent = current === panels.length - 1 ? "Review complete" : "Continue";
  }

  function updatePreviewValue(key, value) {
    document.querySelectorAll(`[data-ff-preview-target="${key}"]`).forEach((target) => {
      target.textContent = value || target.textContent;
    });
  }

  function syncPreview() {
    previewSources.forEach((source) => {
      const key = source.getAttribute("data-ff-preview-source");
      updatePreviewValue(key, source.value);
    });
  }

  nextBtn?.addEventListener("click", () => setStep(current + 1));
  prevBtn?.addEventListener("click", () => setStep(current - 1));

  steps.forEach((step) => {
    step.addEventListener("click", () => {
      const index = Number(step.getAttribute("data-step-index"));
      if (Number.isFinite(index)) setStep(index);
    });
  });

  previewSources.forEach((source) => {
    source.addEventListener("input", syncPreview);
    source.addEventListener("change", syncPreview);
  });

  saveBtn?.addEventListener("click", () => {
    const payload = Object.fromEntries(new FormData(form).entries());

    try {
      localStorage.setItem("ff:onboarding:draft", JSON.stringify({
        savedAt: new Date().toISOString(),
        payload,
      }));
    } catch (_) {}

    if (saveNote) {
      saveNote.textContent = "Setup saved locally. Ready for preview or handoff.";
      saveNote.dataset.tone = "success";
    }

    const idle = saveBtn.getAttribute("data-ff-idle-text") || "Save setup";
    saveBtn.textContent = "Saved";
    setTimeout(() => {
      saveBtn.textContent = idle;
    }, 1600);
  });

  try {
    const saved = JSON.parse(localStorage.getItem("ff:onboarding:draft") || "null");
    if (saved?.payload) {
      Object.entries(saved.payload).forEach(([name, value]) => {
        const field = form.elements.namedItem(name);
        if (field && typeof field.value !== "undefined") field.value = value;
      });
    }
  } catch (_) {}

  syncPreview();
  setStep(0);
})();
