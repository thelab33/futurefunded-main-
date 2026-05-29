#!/usr/bin/env python3
from __future__ import annotations

import re
import time
from pathlib import Path

ROOT = Path.cwd()

TPL = ROOT / "apps/web/app/templates/platform/onboarding.html"
CSS = ROOT / "apps/web/app/static/css/ff.css"
JS = ROOT / "apps/web/app/static/js/ff-onboarding.js"

MARKER = "hoi-6h1-onboarding-csp-layer-fix-v1"

JS_CONTENT = r'''/* ==========================================================================
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
'''

CSS_APPEND = r'''

/* ==========================================================================
   FutureFunded HOI 6H.1 — Onboarding CSP + Brand Preset Polish
   Marker: hoi-6h1-onboarding-csp-layer-fix-v1
========================================================================== */

@layer utilities {
  .ffOnboardV2[data-ff-brand-preset="elite"] {
    --onboard-primary: #ff5a1f;
    --onboard-accent: #0f766e;
    --onboard-soft: #fff3e7;
  }

  .ffOnboardV2[data-ff-brand-preset="school"] {
    --onboard-primary: #1d4ed8;
    --onboard-accent: #f59e0b;
    --onboard-soft: #eff6ff;
  }

  .ffOnboardV2[data-ff-brand-preset="club"] {
    --onboard-primary: #047857;
    --onboard-accent: #111827;
    --onboard-soft: #ecfdf5;
  }

  .ffOnboardV2[data-ff-brand-preset="nonprofit"] {
    --onboard-primary: #7c3aed;
    --onboard-accent: #db2777;
    --onboard-soft: #f5f3ff;
  }

  .ffOnboardV2__themeControls [aria-pressed="true"] {
    color: #fff;
    border-color: color-mix(in srgb, var(--onboard-primary) 82%, white);
    background: linear-gradient(135deg, var(--onboard-primary), color-mix(in srgb, var(--onboard-primary) 72%, white));
  }

  .ffOnboardV2__readiness .ffOnboardV2__meter > span {
    width: 94%;
  }
}
'''

def backup(path: Path) -> None:
    if path.exists():
        stamp = time.strftime("%Y%m%d%H%M%S")
        b = path.with_suffix(path.suffix + f".bak-hoi6h1-{stamp}")
        b.write_text(path.read_text(errors="ignore"))
        print(f"Backup: {b}")

def normalize_invalid_multi_layer_blocks(css: str) -> str:
    # CSS allows `@layer a, b;` declarations, but not `@layer a, b { ... }`.
    # These invalid grouped layer blocks caused the onboarding CSS to be ignored.
    pattern = re.compile(r"@layer\s+([A-Za-z0-9_-]+(?:\s*,\s*[A-Za-z0-9_-]+)+)\s*\{")

    def repl(match: re.Match[str]) -> str:
        original = match.group(1)
        return f"@layer utilities {{ /* normalized from invalid @layer {original} */"

    return pattern.sub(repl, css)

if not TPL.exists():
    raise SystemExit(f"Missing template: {TPL}")
if not CSS.exists():
    raise SystemExit(f"Missing CSS: {CSS}")

# 1) Fix template: no inline style, no inline script, use external JS.
backup(TPL)
tpl = TPL.read_text(errors="ignore")

tpl = tpl.replace(
    '<div\n    class="ffOnboardV2"\n    data-ff-onboard-root\n    data-ff-page-root\n    data-ff-surface="onboarding"\n  >',
    '<div\n    class="ffOnboardV2"\n    data-ff-onboard-root\n    data-ff-page-root\n    data-ff-surface="onboarding"\n    data-ff-brand-preset="elite"\n  >'
)

tpl = tpl.replace('<span style="width:94%"></span>', '<span></span>')

tpl = tpl.replace(
    '<button type="button" data-ff-theme-preset data-primary="#ff5a1f" data-accent="#0f766e" data-soft="#fff3e7">',
    '<button type="button" data-ff-theme-preset data-preset="elite" aria-pressed="true">'
)
tpl = tpl.replace(
    '<button type="button" data-ff-theme-preset data-primary="#1d4ed8" data-accent="#f59e0b" data-soft="#eff6ff">',
    '<button type="button" data-ff-theme-preset data-preset="school" aria-pressed="false">'
)
tpl = tpl.replace(
    '<button type="button" data-ff-theme-preset data-primary="#047857" data-accent="#111827" data-soft="#ecfdf5">',
    '<button type="button" data-ff-theme-preset data-preset="club" aria-pressed="false">'
)
tpl = tpl.replace(
    '<button type="button" data-ff-theme-preset data-primary="#7c3aed" data-accent="#db2777" data-soft="#f5f3ff">',
    '<button type="button" data-ff-theme-preset data-preset="nonprofit" aria-pressed="false">'
)

# Color inputs stay as form fields, but are not used to mutate inline styles under CSP.
tpl = tpl.replace(' data-ff-color-primary', ' data-ff-color-primary aria-describedby="brand-kit-note"')
tpl = tpl.replace(' data-ff-color-accent', ' data-ff-color-accent aria-describedby="brand-kit-note"')
tpl = tpl.replace(' data-ff-color-soft', ' data-ff-color-soft aria-describedby="brand-kit-note"')

tpl = tpl.replace(
    '<div class="ffOnboardV2__colorGrid">',
    '<p id="brand-kit-note" class="ffOnboardV2__miniNote">Color fields are saved for campaign setup. Presets preview safely under the current CSP.</p>\n\n            <div class="ffOnboardV2__colorGrid">'
)

tpl = re.sub(
    r"\n\s*<script>\s*\(\(\) => \{.*?\}\)\(\);\s*</script>\s*",
    '\n  <script src="{{ url_for(\'static\', filename=\'js/ff-onboarding.js\') }}?v={{ asset_v|default(\'dev\', true) }}" defer></script>\n',
    tpl,
    flags=re.DOTALL,
)

if "ff-onboarding.js" not in tpl:
    tpl = tpl.replace(
        "\n</body>",
        "\n  <script src=\"{{ url_for('static', filename='js/ff-onboarding.js') }}?v={{ asset_v|default('dev', true) }}\" defer></script>\n</body>"
    )

TPL.write_text(tpl)
print(f"Patched template: {TPL}")

# 2) Normalize invalid grouped layer blocks in ff.css and append CSP-safe preset styles.
backup(CSS)
css = CSS.read_text(errors="ignore")
css = normalize_invalid_multi_layer_blocks(css)

if MARKER not in css:
    css = css.rstrip() + "\n" + CSS_APPEND.strip() + "\n"

CSS.write_text(css)
print(f"Patched CSS: {CSS}")

# 3) Create external JS.
backup(JS)
JS.write_text(JS_CONTENT)
print(f"Wrote external JS: {JS}")

print("HOI 6H.1 onboarding CSP/layer fix complete.")
