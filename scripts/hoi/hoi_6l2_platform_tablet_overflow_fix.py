#!/usr/bin/env python3
from __future__ import annotations

import time
from pathlib import Path

ROOT = Path.cwd()
CSS = ROOT / "apps/web/app/static/css/ff.css"
MARKER = "hoi-6l2-platform-tablet-overflow-guard-v1"

PATCH = r'''

/* ==========================================================================
   FutureFunded HOI 6L.2 — Platform Tablet Overflow Guard
   Marker: hoi-6l2-platform-tablet-overflow-guard-v1

   Why:
   - Shared shell refactor passed.
   - Visual gate found exactly one overflow: platform homepage / tablet.
   - Cause is the marketing header trying to fit brand + full nav + two actions.
   - Keep desktop rich; keep mobile clean; tighten tablet only.
========================================================================== */

@layer components {
  @media (min-width: 561px) and (max-width: 1040px) {
    .ffShellHeader--marketing {
      width: min(100% - 1rem, var(--ff-shell-header-max, 1180px));
      max-width: calc(100vw - 1rem);
    }

    .ffShellHeader--marketing .ffShellHeader__shell {
      width: 100%;
      max-width: 100%;
      gap: 0.34rem;
      overflow: clip;
    }

    .ffShellHeader--marketing .ffShellHeader__brand {
      flex: 0 1 12.75rem;
      max-width: 12.75rem;
      gap: 0.58rem;
    }

    .ffShellHeader--marketing .ffShellHeader__copy strong,
    .ffShellHeader--marketing .ffShellHeader__copy small {
      max-width: 8.9rem;
    }

    .ffShellHeader--marketing .ffShellHeader__nav {
      flex: 1 1 auto;
      min-width: 0;
      justify-content: center;
      gap: 0.08rem;
      overflow: hidden;
    }

    .ffShellHeader--marketing .ffShellHeader__nav a {
      min-width: 0;
      padding-inline: 0.48rem;
      font-size: 0.72rem;
      letter-spacing: -0.02em;
    }

    .ffShellHeader--marketing .ffShellHeader__actions {
      flex: 0 0 auto;
      min-width: 0;
    }

    .ffShellHeader--marketing .ffShellHeader__action--ghost {
      display: none;
    }

    .ffShellHeader--marketing .ffShellHeader__action--primary {
      min-width: 7.15rem;
      padding-inline: 0.74rem;
    }
  }

  @supports not (overflow: clip) {
    @media (min-width: 561px) and (max-width: 1040px) {
      .ffShellHeader--marketing .ffShellHeader__shell {
        overflow: hidden;
      }
    }
  }
}

/* Last-mile viewport safety for the platform shell only. */
@media (min-width: 561px) and (max-width: 1040px) {
  .ffShellHeader--marketing,
  .ffShellHeader--marketing .ffShellHeader__shell {
    max-inline-size: calc(100vw - 1rem);
  }
}
'''

def backup(path: Path) -> None:
    stamp = time.strftime("%Y%m%d%H%M%S")
    backup_path = path.with_suffix(path.suffix + f".bak-hoi6l2-{stamp}")
    backup_path.write_text(path.read_text(errors="ignore"))
    print(f"Backup: {backup_path}")

if not CSS.exists():
    raise SystemExit(f"Missing CSS file: {CSS}")

text = CSS.read_text(errors="ignore")

if MARKER in text:
    print("Already patched.")
else:
    backup(CSS)
    CSS.write_text(text.rstrip() + "\n" + PATCH.strip() + "\n")
    print("Patched platform tablet overflow guard.")

