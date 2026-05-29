#!/usr/bin/env python3
from __future__ import annotations

import re
import time
from pathlib import Path

ROOT = Path.cwd()
CSS = ROOT / "apps/web/app/static/css/ff.css"
MARKER = "hoi-6l1-shared-shell-layer-fix-v1"

PATCH = r'''

/* ==========================================================================
   FutureFunded HOI 6L.1 — Shared Shell CSS Layer Repair
   Marker: hoi-6l1-shared-shell-layer-fix-v1

   Why:
   - The shared header markup is correct.
   - The proof measured the FF logo mark at 18px.
   - That means shell sizing rules were not reliably applying.
   - This adds a valid single-layer shell authority and a geometry failsafe.
========================================================================== */

@layer components {
  .ffShellHeader,
  .ffShellHeader * {
    box-sizing: border-box;
  }

  .ffShellHeader {
    --ff-shell-header-max: 1180px;
    --ff-shell-header-h: 58px;
    --ff-shell-header-bg: rgba(255, 255, 255, 0.8);
    --ff-shell-header-border: rgba(148, 163, 184, 0.22);
    --ff-shell-header-ink: #201610;
    --ff-shell-header-muted: rgba(32, 22, 16, 0.58);
    --ff-shell-header-shadow: 0 18px 58px rgba(15, 23, 42, 0.09);
    position: relative;
    z-index: 50;
    width: min(var(--ff-shell-header-max), calc(100% - 2rem));
    margin: 1rem auto 0;
    color: var(--ff-shell-header-ink);
  }

  .ffShellHeader__shell {
    min-height: var(--ff-shell-header-h);
    padding: 0.48rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: clamp(0.45rem, 1vw, 0.9rem);
    border: 1px solid var(--ff-shell-header-border);
    border-radius: 999px;
    background:
      linear-gradient(180deg, rgba(255,255,255,0.92), var(--ff-shell-header-bg));
    box-shadow: var(--ff-shell-header-shadow);
    backdrop-filter: blur(18px) saturate(1.16);
    -webkit-backdrop-filter: blur(18px) saturate(1.16);
  }

  .ffShellHeader__brand {
    min-width: 0;
    max-width: min(34vw, 22rem);
    display: inline-flex;
    align-items: center;
    gap: 0.72rem;
    color: inherit;
    text-decoration: none;
  }

  .ffShellHeader__mark {
    width: 40px;
    min-width: 40px;
    max-width: 40px;
    height: 40px;
    min-height: 40px;
    max-height: 40px;
    flex: 0 0 40px;
    display: grid;
    place-items: center;
    overflow: hidden;
    border-radius: 14px;
    color: #fff;
    background:
      radial-gradient(circle at 30% 20%, rgba(255,255,255,0.24), transparent 34%),
      linear-gradient(135deg, #3d261b, #160d08);
    font-size: 0.84rem;
    font-weight: 950;
    line-height: 1;
    letter-spacing: -0.04em;
    box-shadow:
      inset 0 1px 0 rgba(255,255,255,0.22),
      0 10px 26px rgba(15,23,42,0.12);
  }

  .ffShellHeader__copy {
    min-width: 0;
    display: grid;
    gap: 0.14rem;
  }

  .ffShellHeader__copy strong {
    max-width: 18rem;
    overflow: hidden;
    color: var(--ff-shell-header-ink);
    font-size: clamp(0.92rem, 0.95vw, 1.02rem);
    font-weight: 950;
    line-height: 1;
    letter-spacing: -0.04em;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .ffShellHeader__copy small {
    max-width: 18rem;
    overflow: hidden;
    color: var(--ff-shell-header-muted);
    font-size: clamp(0.62rem, 0.68vw, 0.72rem);
    font-weight: 950;
    line-height: 1;
    letter-spacing: 0.17em;
    text-transform: uppercase;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .ffShellHeader__nav,
  .ffShellHeader__actions {
    min-width: 0;
    display: inline-flex;
    align-items: center;
    gap: 0.22rem;
  }

  .ffShellHeader__nav {
    justify-content: center;
  }

  .ffShellHeader__nav a,
  .ffShellHeader__action {
    min-height: 38px;
    padding: 0.66rem 0.84rem;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border: 0;
    border-radius: 999px;
    color: rgba(32, 22, 16, 0.72);
    background: transparent;
    font: inherit;
    font-size: clamp(0.76rem, 0.72vw, 0.88rem);
    font-weight: 900;
    line-height: 1;
    letter-spacing: -0.015em;
    text-decoration: none;
    white-space: nowrap;
    cursor: pointer;
  }

  .ffShellHeader__nav a:hover,
  .ffShellHeader__nav a:focus-visible,
  .ffShellHeader__action--ghost:hover,
  .ffShellHeader__action--ghost:focus-visible {
    color: #160f0b;
    background: rgba(255,255,255,0.82);
  }

  .ffShellHeader__action--ghost {
    background: rgba(255,255,255,0.72);
    box-shadow: inset 0 0 0 1px rgba(148, 163, 184, 0.18);
  }

  .ffShellHeader__action--primary {
    color: #fff;
    background: linear-gradient(135deg, #ff5a1f, #ff7a35);
    box-shadow: 0 12px 30px rgba(255, 90, 31, 0.22);
  }

  .ffShellHeader--campaign .ffShellHeader__brand {
    max-width: min(38vw, 22rem);
  }

  @media (max-width: 860px) {
    .ffShellHeader {
      width: min(100% - 1rem, var(--ff-shell-header-max));
      margin-top: 0.55rem;
    }

    .ffShellHeader__shell {
      min-height: 56px;
      border-radius: 24px;
      gap: 0.42rem;
    }

    .ffShellHeader__mark {
      width: 36px;
      min-width: 36px;
      max-width: 36px;
      height: 36px;
      min-height: 36px;
      max-height: 36px;
      flex-basis: 36px;
      border-radius: 12px;
    }

    .ffShellHeader__brand {
      max-width: 48vw;
      gap: 0.58rem;
    }

    .ffShellHeader__copy strong {
      max-width: 9.5rem;
    }

    .ffShellHeader__copy small {
      max-width: 9.5rem;
      font-size: 0.58rem;
      letter-spacing: 0.12em;
    }

    .ffShellHeader__nav {
      justify-content: flex-end;
      overflow-x: auto;
      scrollbar-width: none;
    }

    .ffShellHeader__nav::-webkit-scrollbar {
      display: none;
    }

    .ffShellHeader__nav a,
    .ffShellHeader__action {
      min-height: 34px;
      padding: 0.54rem 0.64rem;
      font-size: 0.74rem;
    }
  }

  @media (max-width: 560px) {
    .ffShellHeader__shell {
      border-radius: 22px;
    }

    .ffShellHeader__copy small {
      display: none;
    }

    .ffShellHeader__copy strong {
      max-width: 7.4rem;
    }

    .ffShellHeader--marketing .ffShellHeader__nav,
    .ffShellHeader--campaign .ffShellHeader__nav {
      display: none;
    }

    .ffShellHeader__action--ghost {
      display: none;
    }

    .ffShellHeader__action--primary {
      min-width: 7.25rem;
    }
  }
}

/* Critical geometry failsafe outside layers. */
.ffShellHeader__mark {
  width: 40px;
  min-width: 40px;
  max-width: 40px;
  height: 40px;
  min-height: 40px;
  max-height: 40px;
  flex: 0 0 40px;
}

@media (max-width: 860px) {
  .ffShellHeader__mark {
    width: 36px;
    min-width: 36px;
    max-width: 36px;
    height: 36px;
    min-height: 36px;
    max-height: 36px;
    flex-basis: 36px;
  }
}
'''

def backup(path: Path) -> None:
    stamp = time.strftime("%Y%m%d%H%M%S")
    backup_path = path.with_suffix(path.suffix + f".bak-hoi6l1-{stamp}")
    backup_path.write_text(path.read_text(errors="ignore"))
    print(f"Backup: {backup_path}")

if not CSS.exists():
    raise SystemExit(f"Missing CSS file: {CSS}")

text = CSS.read_text(errors="ignore")

# Normalize invalid grouped layer blocks like:
# @layer components, platform, utilities { ... }
# into a valid single layer. Semicolon declarations are left alone.
text = re.sub(
    r"@layer\s+([A-Za-z0-9_-]+)\s*,\s*([A-Za-z0-9_,\s-]+)\s*\{",
    lambda m: f"@layer {m.group(1)} {{ /* normalized grouped layer: {m.group(1)}, {m.group(2).strip()} */",
    text,
)

if MARKER not in text:
    text = text.rstrip() + "\n" + PATCH.strip() + "\n"
else:
    print("Marker already present; only normalized grouped layers.")

backup(CSS)
CSS.write_text(text)

print("HOI 6L.1 shell header layer fix complete.")
