/* ==========================================================================
   FutureFunded — Onboarding Workspace JS v5
   File: apps/web/app/static/js/ff-onboarding.js
   Marker: FF_ONBOARDING_JS_FOCUSED_V5

   Scope:
   - /platform/onboarding only
   - Stable template contract: ffOnboardV2__*
   - No framework dependency
========================================================================== */

(() => {
  const root =
    document.querySelector('[data-ff-onboarding-root]') ||
    document.querySelector('[data-ff-onboard-root]') ||
    document.querySelector('[data-ff-page-root]');

  if (!root) return;

  const storageKey = 'futurefunded.platformOnboarding.v5';

  const $ = (selector, scope = root) => scope.querySelector(selector);
  const $$ = (selector, scope = root) => Array.from(scope.querySelectorAll(selector));

  const fields = $$('input[name], textarea[name], select[name]');
  const saveButtons = $$('[data-ff-save-onboarding]');
  const saveNote = $('[data-ff-save-note]');
  const themePreview = $('[data-ff-theme-preview]');
  const presetButtons = $$('[data-ff-theme-preset]');

  const colorFields = {
    primary: $('[data-ff-color-primary]'),
    accent: $('[data-ff-color-accent]'),
    soft: $('[data-ff-color-soft]')
  };

  const previewSources = $$('[data-ff-preview-source]');
  const previewTargets = $$('[data-ff-preview-target]');

  const presets = {
    elite: { primary: '#ff5a1f', accent: '#0f766e', soft: '#fff3e7', label: 'Elite orange' },
    school: { primary: '#2563eb', accent: '#f59e0b', soft: '#eff6ff', label: 'School blue' },
    club: { primary: '#12845f', accent: '#ff5a1f', soft: '#effaf4', label: 'Club green' },
    nonprofit: { primary: '#6d4aff', accent: '#0f766e', soft: '#f5f1ff', label: 'Nonprofit violet' }
  };

  function setStatus(message, tone = 'neutral') {
    if (!saveNote) return;
    saveNote.textContent = message;
    saveNote.dataset.tone = tone;
  }

  function collectDraft() {
    return fields.reduce((draft, field) => {
      draft[field.name] = field.type === 'checkbox' ? field.checked : field.value;
      return draft;
    }, { updatedAt: new Date().toISOString() });
  }

  function applyDraft(draft) {
    if (!draft || typeof draft !== 'object') return;
    fields.forEach((field) => {
      if (!(field.name in draft)) return;
      if (field.type === 'checkbox') field.checked = Boolean(draft[field.name]);
      else field.value = draft[field.name];
    });
  }

  function saveDraft({ quiet = false } = {}) {
    try {
      localStorage.setItem(storageKey, JSON.stringify(collectDraft()));
      if (!quiet) setStatus('Saved privately in this browser. Public campaign content was not changed.', 'success');
    } catch {
      if (!quiet) setStatus('Could not save locally. Your browser may be blocking storage.', 'warning');
    }
  }

  function loadDraft() {
    try {
      const raw = localStorage.getItem(storageKey);
      if (!raw) return;
      applyDraft(JSON.parse(raw));
      setStatus('Loaded your private draft from this browser.', 'success');
    } catch {
      setStatus('Saved draft could not be loaded. Template defaults were kept.', 'warning');
    }
  }

  function applyPreviewColors() {
    const primary = colorFields.primary?.value || presets.elite.primary;
    const accent = colorFields.accent?.value || presets.elite.accent;
    const soft = colorFields.soft?.value || presets.elite.soft;

    const targets = [document.documentElement, document.body, themePreview].filter(Boolean);

    targets.forEach((target) => {
      target.style.setProperty('--onb-orange', primary);
      target.style.setProperty('--onb-orange-2', primary);
      target.style.setProperty('--onb-teal', accent);
      target.style.setProperty('--onb-cream', soft);
    });
  }

  function updatePreviewText() {
    const values = previewSources.reduce((acc, field) => {
      acc[field.dataset.ffPreviewSource] = String(field.value || '').trim();
      return acc;
    }, {});

    previewTargets.forEach((target) => {
      const key = target.dataset.ffPreviewTarget;
      const value = values[key];
      if (!value) return;

      if (key === 'campaignName') {
        target.textContent = value.replace(/\s+(Season Fund|Fundraiser)$/i, '') || value;
      }

      if (key === 'summary') {
        target.textContent = value;
      }
    });
  }

  function setPreset(name) {
    const preset = presets[name];
    if (!preset) return;

    if (colorFields.primary) colorFields.primary.value = preset.primary;
    if (colorFields.accent) colorFields.accent.value = preset.accent;
    if (colorFields.soft) colorFields.soft.value = preset.soft;

    presetButtons.forEach((button) => {
      button.setAttribute('aria-pressed', String(button.dataset.preset === name));
    });

    applyPreviewColors();
    updatePreviewText();
    saveDraft({ quiet: true });
    setStatus(`${preset.label} theme applied privately.`, 'success');
  }

  function markDirty() {
    applyPreviewColors();
    updatePreviewText();
    saveDraft({ quiet: true });
    setStatus('Private draft updated in this browser.', 'neutral');
  }

  loadDraft();
  applyPreviewColors();
  updatePreviewText();

  fields.forEach((field) => {
    field.addEventListener('input', markDirty);
    field.addEventListener('change', markDirty);
  });

  presetButtons.forEach((button) => {
    button.addEventListener('click', () => setPreset(button.dataset.preset));
  });

  saveButtons.forEach((button) => {
    const idleText = button.dataset.ffIdleText || button.textContent.trim() || 'Save setup';

    button.addEventListener('click', () => {
      saveDraft();
      button.textContent = 'Saved';
      button.setAttribute('aria-live', 'polite');

      window.setTimeout(() => {
        button.textContent = idleText;
      }, 1300);
    });
  });

  root.dataset.ffOnboardingJsReady = 'true';
})();
