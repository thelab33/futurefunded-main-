#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
import time
from pathlib import Path

ROOT = Path.cwd()

PARTIAL = ROOT / "apps/web/app/templates/_partials/ff_shell_header.html"
FF_CSS = ROOT / "apps/web/app/static/css/ff.css"

MARKER = "hoi-6l-shared-shell-header-v1"

TARGETS = {
    "platform": {
        "path": ROOT / "apps/web/app/templates/platform/index.html",
        "needle": "ff-siteHeader--platform",
        "call": """{{ ff_shell_header(
  mode='marketing',
  brand_name='FutureFunded',
  context='Fundraising platform',
  brand_href='/platform/',
  nav_items=[
    {'label':'Product','href':'#product'},
    {'label':'Campaigns','href':'#campaigns'},
    {'label':'Sponsors','href':'#sponsors'},
    {'label':'Proof','href':'#proof'},
    {'label':'FAQ','href':'#faq'}
  ],
  actions=[
    {'label':'View fundraiser','href':'/c/connect-atx-elite','tone':'ghost'},
    {'label':'Start campaign','href':'/platform/onboarding','tone':'primary'}
  ]
) }}""",
    },
    "campaign": {
        "path": ROOT / "apps/web/app/templates/campaign/index.html",
        "needle": "ff-campaignHeader",
        "call": """{{ ff_shell_header(
  mode='campaign',
  brand_name=_team_name|default('Connect ATX Elite', true),
  context='Live season fund',
  brand_href='/c/connect-atx-elite',
  nav_items=[
    {'label':'Impact','href':'#impact'},
    {'label':'Sponsors','href':'#sponsors'},
    {'label':'Team','href':'#team'},
    {'label':'Help','href':'#faq'}
  ],
  actions=[
    {'label':'Share','element':'button','tone':'ghost','attrs':'type="button" data-ff-share-trigger aria-label="Share campaign"'},
    {'label':'Give securely','element':'button','tone':'primary','attrs':'type="button" data-ff-open-checkout aria-label="Give securely"'}
  ],
  extra_class='ffShellHeader--campaignPublic'
) }}""",
    },
    "login": {
        "path": ROOT / "apps/web/app/templates/platform/login.html",
        "needle": "ff-loginAuthority__topbar",
        "call": """{{ ff_shell_header(
  mode='operator',
  brand_name='FutureFunded',
  context='Organizer access',
  brand_href='/platform/',
  nav_items=[
    {'label':'Platform','href':'/platform/'},
    {'label':'Fundraiser','href':'/c/connect-atx-elite'}
  ],
  actions=[]
) }}""",
    },
    "onboarding": {
        "path": ROOT / "apps/web/app/templates/platform/onboarding.html",
        "needle": "ffOnboardV2__topbar",
        "call": """{{ ff_shell_header(
  mode='operator',
  brand_name='FutureFunded',
  context='Launch workspace',
  brand_href='/platform/',
  nav_items=[
    {'label':'Platform','href':'/platform/'},
    {'label':'Preview','href':'/c/connect-atx-elite'},
    {'label':'Dashboard','href':'/platform/dashboard'}
  ],
  actions=[]
) }}""",
    },
    "dashboard": {
        "path": ROOT / "apps/web/app/templates/platform/dashboard.html",
        "needle": "ff-dashboardModern__topbar",
        "call": """{{ ff_shell_header(
  mode='operator',
  brand_name=_brand_name|default('FutureFunded', true),
  context='Operator command center',
  brand_href='/platform/dashboard',
  nav_items=[
    {'label':'Setup','href':'/platform/onboarding'},
    {'label':'Public page','href':'/c/connect-atx-elite'},
    {'label':'Sponsors','href':'#sponsors'}
  ],
  actions=[]
) }}""",
    },
}

PARTIAL_TEXT = r'''{# ============================================================================
  FutureFunded — Shared Shell Header
  Marker: hoi-6l-shared-shell-header-v1

  One header contract for:
  - marketing pages
  - campaign donor pages
  - operator/auth/dashboard pages

  Stable contract:
  data-ff-header
  data-ff-header-mode="marketing|campaign|operator"
  data-ff-brand-context
============================================================================ #}

{% macro ff_shell_header(
  mode='marketing',
  brand_name='FutureFunded',
  context='Fundraising platform',
  brand_href='/platform/',
  nav_items=[],
  actions=[],
  extra_class=''
) -%}
  {%- set _mode = mode|default('marketing', true) -%}
  {%- set _context = context|default('Fundraising platform', true) -%}
  {%- set _context_slug = _context|string|lower|replace('&', 'and')|replace('/', '-')|replace(' ', '-') -%}

  <header
    class="ffShellHeader ffShellHeader--{{ _mode|e }} {{ extra_class|default('', true)|e }}"
    data-ff-header
    data-ff-header-mode="{{ _mode|e }}"
    data-ff-brand-context="{{ _context_slug|e }}"
    role="banner"
  >
    <div class="ffShellHeader__shell">
      <a class="ffShellHeader__brand" href="{{ brand_href|default('/platform/', true)|e }}" aria-label="{{ brand_name|default('FutureFunded', true)|e }} {{ _context|e }}">
        <span class="ffShellHeader__mark" aria-hidden="true">FF</span>
        <span class="ffShellHeader__copy">
          <strong>{{ brand_name|default('FutureFunded', true) }}</strong>
          <small>{{ _context }}</small>
        </span>
      </a>

      {% if nav_items %}
        <nav class="ffShellHeader__nav" aria-label="{{ _context|e }} navigation">
          {% for item in nav_items %}
            <a href="{{ item.href|default('#', true)|e }}">{{ item.label|default('Link', true) }}</a>
          {% endfor %}
        </nav>
      {% endif %}

      {% if actions %}
        <div class="ffShellHeader__actions" aria-label="{{ _context|e }} actions">
          {% for action in actions %}
            {% set _tone = action.tone|default('ghost', true) %}
            {% set _attrs = action.attrs|default('', true) %}
            {% if action.element|default('a', true) == 'button' %}
              <button class="ffShellHeader__action ffShellHeader__action--{{ _tone|e }}" {{ _attrs|safe }}>
                {{ action.label|default('Action', true) }}
              </button>
            {% else %}
              <a class="ffShellHeader__action ffShellHeader__action--{{ _tone|e }}" href="{{ action.href|default('#', true)|e }}" {{ _attrs|safe }}>
                {{ action.label|default('Action', true) }}
              </a>
            {% endif %}
          {% endfor %}
        </div>
      {% endif %}
    </div>
  </header>
{%- endmacro %}
'''

CSS_BLOCK = r'''

/* ==========================================================================
   FutureFunded HOI 6L — Shared Shell Header
   Marker: hoi-6l-shared-shell-header-v1

   One premium shell/header system for marketing, campaign, and operator pages.
========================================================================== */

@layer components, platform, utilities {
  .ffShellHeader,
  .ffShellHeader * {
    box-sizing: border-box;
  }

  .ffShellHeader {
    --ff-shell-header-max: 1180px;
    --ff-shell-header-h: 58px;
    --ff-shell-header-bg: rgba(255, 255, 255, 0.78);
    --ff-shell-header-border: rgba(148, 163, 184, 0.22);
    --ff-shell-header-ink: #201610;
    --ff-shell-header-muted: rgba(32, 22, 16, 0.56);
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
    height: 40px;
    flex: 0 0 40px;
    display: grid;
    place-items: center;
    border-radius: 14px;
    color: #fff;
    background:
      radial-gradient(circle at 30% 20%, rgba(255,255,255,0.24), transparent 34%),
      linear-gradient(135deg, #3d261b, #160d08);
    font-size: 0.84rem;
    font-weight: 950;
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

  .ffShellHeader--operator .ffShellHeader__nav a {
    font-weight: 920;
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
      height: 36px;
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
'''

def backup(path: Path) -> None:
    if not path.exists():
        return
    stamp = time.strftime("%Y%m%d%H%M%S")
    backup_path = path.with_suffix(path.suffix + f".bak-hoi6l-{stamp}")
    backup_path.write_text(path.read_text(errors="ignore"))
    print(f"Backup: {backup_path}")

def ensure_import(text: str) -> str:
    import_line = '{% from "_partials/ff_shell_header.html" import ff_shell_header %}'
    if import_line in text:
        return text
    return import_line + "\n" + text

def replace_header_block(text: str, needle: str, replacement: str) -> tuple[str, bool]:
    pattern = re.compile(r"<header\b[^>]*>.*?</header>", re.I | re.S)
    for match in pattern.finditer(text):
        block = match.group(0)
        if needle in block:
            new_text = text[:match.start()] + replacement + text[match.end():]
            return new_text, True
    return text, False

def append_css_once(css: str) -> str:
    if MARKER in css:
        return css
    return css.rstrip() + "\n" + CSS_BLOCK.strip() + "\n"

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Apply refactor. Default is dry-run.")
    args = parser.parse_args()

    report = {
        "applied": args.apply,
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "targets": {},
    }

    if args.apply:
        PARTIAL.parent.mkdir(parents=True, exist_ok=True)
        backup(PARTIAL)
        PARTIAL.write_text(PARTIAL_TEXT)
        print(f"Wrote partial: {PARTIAL}")
    else:
        print("DRY RUN: no files will be changed.")

    for name, cfg in TARGETS.items():
        path = cfg["path"]
        result = {
            "path": str(path.relative_to(ROOT)),
            "exists": path.exists(),
            "replaced": False,
            "changed": False,
        }

        if not path.exists():
            report["targets"][name] = result
            continue

        old = path.read_text(errors="ignore")
        new = ensure_import(old)
        new, replaced = replace_header_block(new, cfg["needle"], cfg["call"])
        result["replaced"] = replaced
        result["changed"] = old != new

        if args.apply and result["changed"]:
            backup(path)
            path.write_text(new)
            print(f"Patched {name}: {path}")

        if not replaced:
            print(f"WARNING: header block not found for {name} using needle {cfg['needle']}")

        report["targets"][name] = result

    if FF_CSS.exists():
        old_css = FF_CSS.read_text(errors="ignore")
        new_css = append_css_once(old_css)
        report["css_changed"] = old_css != new_css

        if args.apply and old_css != new_css:
            backup(FF_CSS)
            FF_CSS.write_text(new_css)
            print(f"Patched CSS: {FF_CSS}")
    else:
        report["css_changed"] = False
        report["css_missing"] = True

    out_dir = ROOT / "audit_outputs" / "hoi-6l-shared-shell-refactor" / "latest"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "report.json").write_text(json.dumps(report, indent=2) + "\n")

    lines = [
        "# FutureFunded HOI 6L — Shared Shell Refactor",
        "",
        f"Applied: `{args.apply}`",
        "",
        "| Target | Exists | Header replaced | Changed |",
        "|---|---:|---:|---:|",
    ]

    for name, result in report["targets"].items():
        lines.append(
            f"| `{name}` | `{result['exists']}` | `{result['replaced']}` | `{result['changed']}` |"
        )

    lines += [
        "",
        f"CSS changed: `{report.get('css_changed')}`",
        "",
    ]

    (out_dir / "report.md").write_text("\n".join(lines))

    print("")
    print((out_dir / "report.md").read_text())

    if not args.apply:
        print("Dry run complete. Re-run with --apply to write changes.")

if __name__ == "__main__":
    main()
