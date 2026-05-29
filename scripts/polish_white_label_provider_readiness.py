#!/usr/bin/env python3
"""
FutureFunded White-Label + Provider Readiness Polish

Phase 1:
- Adds a premium internal Provider Readiness panel for platform operators.
- Wires the panel into onboarding/dashboard when those templates exist.
- Adds launch/provider ENV documentation.
- Adds audits for provider readiness surface + active white-label risk.
- Keeps public campaign page clean.

This is intentionally operator-facing, not public donor-facing.
"""

from __future__ import annotations

import os
import re
import shutil
import sys
import time
from pathlib import Path

ROOT = Path.cwd()

PARTIAL = ROOT / "apps/web/app/templates/platform/_provider_readiness_panel.html"
CSS = ROOT / "apps/web/app/static/css/ff.css"
ENV_EXAMPLE = ROOT / ".env.example"

TEMPLATES = [
    ROOT / "apps/web/app/templates/platform/dashboard.html",
    ROOT / "apps/web/app/templates/platform/onboarding.html",
]

PROVIDER_AUDIT = ROOT / "scripts/final_provider_readiness_polish_audit.py"
WHITE_LABEL_AUDIT = ROOT / "scripts/final_white_label_active_surface_audit.py"

CSS_MARKER = "FutureFunded Provider Readiness OS v1"
INCLUDE = '{% include "platform/_provider_readiness_panel.html" ignore missing %}'

PARTIAL_TEXT = r'''{# FutureFunded Provider Readiness OS v1
   Internal/operator-facing launch readiness panel.
   Do not render this on public campaign pages.
#}

{% set _stripe_ready =
  (config.get('STRIPE_PUBLISHABLE_KEY') or config.get('STRIPE_PUBLIC_KEY'))
  and config.get('STRIPE_SECRET_KEY')
  and config.get('STRIPE_WEBHOOK_SECRET')
%}
{% set _paypal_ready = config.get('PAYPAL_CLIENT_ID') and config.get('PAYPAL_CLIENT_SECRET') %}
{% set _mail_ready =
  (config.get('MAIL_SERVER') or config.get('SMTP_HOST'))
  and (config.get('MAIL_USERNAME') or config.get('SMTP_USERNAME'))
  and (config.get('MAIL_PASSWORD') or config.get('SMTP_PASSWORD'))
  and (config.get('MAIL_DEFAULT_SENDER') or config.get('DEFAULT_FROM_EMAIL') or config.get('MAIL_FROM'))
%}
{% set _public_ready =
  config.get('PUBLIC_BASE_URL')
  or config.get('FF_PUBLIC_BASE_URL')
  or config.get('APP_BASE_URL')
  or config.get('SERVER_NAME')
%}

{% set _ready_count = 0 %}
{% if _stripe_ready %}{% set _ready_count = _ready_count + 1 %}{% endif %}
{% if _paypal_ready %}{% set _ready_count = _ready_count + 1 %}{% endif %}
{% if _mail_ready %}{% set _ready_count = _ready_count + 1 %}{% endif %}
{% if _public_ready %}{% set _ready_count = _ready_count + 1 %}{% endif %}

<section class="ff-providerReadiness ff-platformCard"
         data-ff-provider-readiness
         aria-labelledby="provider-readiness-title">
  <div class="ff-providerReadiness__head">
    <div>
      <p class="ff-platformKicker">Launch readiness</p>
      <h2 id="provider-readiness-title">Provider setup for a sellable fundraising OS.</h2>
      <p>
        Keep payments, sponsor follow-up, email receipts, and public URLs ready before campaigns go live.
      </p>
    </div>

    <div class="ff-providerReadiness__score"
         aria-label="{{ _ready_count }} of 4 launch providers ready">
      <strong>{{ _ready_count }}/4</strong>
      <span>ready</span>
    </div>
  </div>

  <div class="ff-providerReadiness__grid" aria-label="Provider readiness checklist">
    <article class="ff-providerReadiness__item"
             data-provider="stripe"
             data-provider-state="{{ 'ready' if _stripe_ready else 'needs_setup' }}">
      <span aria-hidden="true">{{ '✓' if _stripe_ready else '!' }}</span>
      <div>
        <strong>Stripe</strong>
        <p>{{ 'Checkout keys and webhook secret configured.' if _stripe_ready else 'Add publishable key, secret key, and webhook secret.' }}</p>
      </div>
    </article>

    <article class="ff-providerReadiness__item"
             data-provider="paypal"
             data-provider-state="{{ 'ready' if _paypal_ready else 'needs_setup' }}">
      <span aria-hidden="true">{{ '✓' if _paypal_ready else '!' }}</span>
      <div>
        <strong>PayPal</strong>
        <p>{{ 'PayPal client credentials are configured.' if _paypal_ready else 'Add PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET before enabling PayPal.' }}</p>
      </div>
    </article>

    <article class="ff-providerReadiness__item"
             data-provider="mail"
             data-provider-state="{{ 'ready' if _mail_ready else 'needs_setup' }}">
      <span aria-hidden="true">{{ '✓' if _mail_ready else '!' }}</span>
      <div>
        <strong>Email</strong>
        <p>{{ 'SMTP sender is ready for receipts and sponsor follow-up.' if _mail_ready else 'Add SMTP host, username, password, and default sender.' }}</p>
      </div>
    </article>

    <article class="ff-providerReadiness__item"
             data-provider="public-url"
             data-provider-state="{{ 'ready' if _public_ready else 'needs_setup' }}">
      <span aria-hidden="true">{{ '✓' if _public_ready else '!' }}</span>
      <div>
        <strong>Public URL</strong>
        <p>{{ 'Public base URL is configured for links and callbacks.' if _public_ready else 'Set PUBLIC_BASE_URL or FF_PUBLIC_BASE_URL for production links.' }}</p>
      </div>
    </article>
  </div>

  <div class="ff-providerReadiness__foot">
    <p>
      Operator-only readiness layer. Public campaign pages stay donor-first and free of setup noise.
    </p>
  </div>
</section>
'''

CSS_PATCH = r'''
/* ==========================================================================
   FutureFunded Provider Readiness OS v1
   Operator-facing launch readiness panel for platform dashboard/onboarding.
   ========================================================================== */

.ff-providerReadiness {
  position: relative;
  isolation: isolate;
  display: grid;
  gap: clamp(14px, 2vw, 22px);
  overflow: hidden;
  margin-block: clamp(18px, 3vw, 34px);
  padding: clamp(18px, 2.6vw, 28px);
  border: 1px solid rgba(72, 44, 25, 0.10);
  border-radius: clamp(22px, 3vw, 32px);
  background:
    radial-gradient(circle at 0% 0%, rgba(255, 122, 26, 0.14), transparent 22rem),
    radial-gradient(circle at 100% 0%, rgba(18, 124, 111, 0.11), transparent 24rem),
    linear-gradient(135deg, rgba(255, 255, 255, 0.94), rgba(255, 250, 242, 0.76));
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.86) inset,
    0 20px 54px rgba(55, 36, 20, 0.08);
}

.ff-providerReadiness::before {
  content: "";
  position: absolute;
  inset: 0;
  z-index: -1;
  pointer-events: none;
  background:
    linear-gradient(rgba(72, 44, 25, 0.025) 1px, transparent 1px),
    linear-gradient(90deg, rgba(72, 44, 25, 0.022) 1px, transparent 1px);
  background-size: 28px 28px;
  opacity: 0.82;
}

.ff-providerReadiness__head {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: end;
  gap: clamp(14px, 2vw, 22px);
}

.ff-providerReadiness__head h2 {
  max-width: 760px;
  margin-top: 7px;
  color: var(--ff-ink-strong, #130d08);
  font-size: clamp(1.5rem, 2.8vw, 2.55rem);
  letter-spacing: -0.058em;
  line-height: 0.98;
}

.ff-providerReadiness__head p:not(.ff-platformKicker) {
  max-width: 72ch;
  margin-top: 9px;
  color: var(--ff-ink-muted, rgba(56, 42, 31, 0.74));
  font-size: 0.94rem;
  line-height: 1.58;
}

.ff-providerReadiness__score {
  display: grid;
  min-width: 104px;
  place-items: center;
  border: 1px solid rgba(72, 44, 25, 0.09);
  border-radius: 22px;
  background:
    radial-gradient(circle at 100% 0%, rgba(255, 122, 26, 0.16), transparent 7rem),
    rgba(255, 255, 255, 0.76);
  box-shadow:
    0 1px 0 rgba(255,255,255,0.76) inset,
    0 12px 28px rgba(55,36,20,0.06);
  padding: 14px;
}

.ff-providerReadiness__score strong {
  color: var(--ff-ink-strong, #130d08);
  font-size: clamp(1.35rem, 2.5vw, 2rem);
  font-weight: 950;
  letter-spacing: -0.055em;
  line-height: 1;
}

.ff-providerReadiness__score span {
  margin-top: 5px;
  color: var(--ff-ink-subtle, rgba(74, 55, 39, 0.62));
  font-size: 0.7rem;
  font-weight: 900;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.ff-providerReadiness__grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: clamp(10px, 1.6vw, 14px);
}

.ff-providerReadiness__item {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 11px;
  min-width: 0;
  border: 1px solid rgba(72, 44, 25, 0.08);
  border-radius: 18px;
  background:
    linear-gradient(180deg, rgba(255,255,255,0.86), rgba(255,250,242,0.66));
  box-shadow:
    0 1px 0 rgba(255,255,255,0.82) inset,
    0 10px 24px rgba(55,36,20,0.045);
  padding: 13px;
}

.ff-providerReadiness__item > span {
  display: inline-flex;
  inline-size: 27px;
  block-size: 27px;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  font-size: 0.82rem;
  font-weight: 950;
  line-height: 1;
}

.ff-providerReadiness__item[data-provider-state="ready"] > span {
  background: rgba(18, 124, 111, 0.11);
  color: #127c6f;
}

.ff-providerReadiness__item[data-provider-state="needs_setup"] > span {
  background: rgba(255, 122, 26, 0.13);
  color: #a84310;
}

.ff-providerReadiness__item strong {
  display: block;
  color: var(--ff-ink-strong, #130d08);
  font-size: 0.95rem;
  font-weight: 950;
  letter-spacing: -0.025em;
  line-height: 1.05;
}

.ff-providerReadiness__item p {
  margin-top: 5px;
  color: var(--ff-ink-muted, rgba(56, 42, 31, 0.72));
  font-size: 0.78rem;
  line-height: 1.45;
}

.ff-providerReadiness__foot {
  border-top: 1px solid rgba(72, 44, 25, 0.08);
  padding-top: 12px;
}

.ff-providerReadiness__foot p {
  color: var(--ff-ink-subtle, rgba(74, 55, 39, 0.60));
  font-size: 0.78rem;
  font-weight: 780;
}

@media (max-width: 1080px) {
  .ff-providerReadiness__grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .ff-providerReadiness {
    padding: 16px;
    border-radius: 24px;
  }

  .ff-providerReadiness__head {
    grid-template-columns: 1fr;
    align-items: start;
  }

  .ff-providerReadiness__score {
    width: 100%;
    min-width: 0;
    justify-items: start;
  }

  .ff-providerReadiness__grid {
    grid-template-columns: 1fr;
  }
}

:root[data-theme="dark"] .ff-providerReadiness,
[data-theme="dark"] .ff-providerReadiness {
  border-color: rgba(255,255,255,0.12);
  background:
    radial-gradient(circle at 0% 0%, rgba(255, 122, 26, 0.16), transparent 22rem),
    radial-gradient(circle at 100% 0%, rgba(37, 99, 235, 0.15), transparent 24rem),
    rgba(15, 23, 42, 0.76);
}

:root[data-theme="dark"] .ff-providerReadiness__item,
:root[data-theme="dark"] .ff-providerReadiness__score,
[data-theme="dark"] .ff-providerReadiness__item,
[data-theme="dark"] .ff-providerReadiness__score {
  border-color: rgba(255,255,255,0.12);
  background: rgba(15, 23, 42, 0.70);
}
'''

ENV_BLOCK = r'''

# -----------------------------------------------------------------------------
# FutureFunded launch provider readiness
# -----------------------------------------------------------------------------
# Stripe
STRIPE_PUBLISHABLE_KEY=
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=

# PayPal
PAYPAL_CLIENT_ID=
PAYPAL_CLIENT_SECRET=

# Mail / SMTP
MAIL_SERVER=
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=
MAIL_PASSWORD=
MAIL_DEFAULT_SENDER=

# Public URL / callbacks
PUBLIC_BASE_URL=
FF_PUBLIC_BASE_URL=

# White-label defaults
FF_DEFAULT_BRAND_NAME=FutureFunded
FF_DEFAULT_TEAM_NAME=
FF_DEFAULT_CAMPAIGN_SLUG=
FF_DEFAULT_LOCATION=
FF_SPONSOR_CONTACT_EMAIL=
'''

PROVIDER_AUDIT_TEXT = r'''#!/usr/bin/env python3
"""Audit: provider readiness panel renders on internal platform surfaces only."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PASS: list[str] = []
FAIL: list[str] = []


def ok(message: str) -> None:
    PASS.append(message)
    print(f"✅ {message}")


def fail(message: str) -> None:
    FAIL.append(message)
    print(f"❌ {message}")


def token() -> str:
    env_token = os.environ.get("FF_OPERATOR_ACCESS_TOKEN", "").strip()
    if env_token:
        return env_token
    token_file = Path("/tmp/ff_operator_token")
    return token_file.read_text(encoding="utf-8").strip() if token_file.exists() else ""


def main() -> int:
    print("\nFutureFunded provider readiness polish audit")
    print("=" * 72)

    try:
        from apps.web.app import create_app
    except Exception as exc:
        fail(f"could not import create_app: {exc}")
        return 1

    app = create_app()
    client = app.test_client()

    onboarding = client.get("/platform/onboarding", follow_redirects=False)
    onboarding_html = onboarding.get_data(as_text=True)

    ok("/platform/onboarding loads") if onboarding.status_code == 200 else fail(f"/platform/onboarding HTTP {onboarding.status_code}")

    for term in [
        "data-ff-provider-readiness",
        "Launch readiness",
        "Provider setup for a sellable fundraising OS.",
        "Stripe",
        "PayPal",
        "Email",
        "Public URL",
    ]:
        ok(f"onboarding provider panel contains {term}") if term in onboarding_html else fail(f"onboarding missing {term}")

    op_token = token()
    if op_token:
        dashboard = client.get(f"/platform/dashboard?token={op_token}", follow_redirects=False)
        dashboard_html = dashboard.get_data(as_text=True)
        ok("/platform/dashboard token access loads") if dashboard.status_code == 200 else fail(f"/platform/dashboard HTTP {dashboard.status_code}")

        for term in [
            "data-ff-provider-readiness",
            "Launch readiness",
            "Stripe",
            "PayPal",
            "Email",
            "Public URL",
        ]:
            ok(f"dashboard provider panel contains {term}") if term in dashboard_html else fail(f"dashboard missing {term}")
    else:
        ok("operator token not available; dashboard panel check skipped")

    campaign = client.get("/c/connect-atx-elite", follow_redirects=False)
    campaign_html = campaign.get_data(as_text=True)

    ok("/c/connect-atx-elite loads") if campaign.status_code == 200 else fail(f"/c/connect-atx-elite HTTP {campaign.status_code}")
    ok("public campaign does not render provider readiness panel") if "data-ff-provider-readiness" not in campaign_html else fail("public campaign renders provider readiness panel")

    print("\n" + "=" * 72)
    print(f"PASS: {len(PASS)}  FAIL: {len(FAIL)}")

    if FAIL:
        print("\nFailures:")
        for item in FAIL:
            print(f"❌ {item}")
        return 1

    print("\n✅ PROVIDER READINESS POLISH AUDIT PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

WHITE_LABEL_AUDIT_TEXT = r'''#!/usr/bin/env python3
"""Scoped white-label risk audit for active FutureFunded surfaces.

This audit separates true active-surface risks from deprecated/demo seed files.
It does not fail on known demo defaults yet; it gives a focused report for the
next white-label extraction pass.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TERMS = [
    "Connect ATX Elite",
    "connect-atx-elite",
    "Austin, TX",
    "sponsor@futurefunded.com",
]

SKIP_PARTS = {
    ".git",
    ".venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "deprecated",
    "bak",
}

ACTIVE_PREFIXES = (
    "apps/web/app/templates/",
    "apps/web/app/blueprints/",
    "apps/web/app/services/",
    "apps/web/app/config/",
)

PASS: list[str] = []
WARN: list[str] = []
FAIL: list[str] = []


def ok(message: str) -> None:
    PASS.append(message)
    print(f"✅ {message}")


def warn(message: str) -> None:
    WARN.append(message)
    print(f"⚠️  {message}")


def fail(message: str) -> None:
    FAIL.append(message)
    print(f"❌ {message}")


def should_scan(path: Path) -> bool:
    rel = path.relative_to(ROOT).as_posix()

    if any(part in SKIP_PARTS or part.startswith(".bak") for part in path.parts):
        return False

    if not rel.startswith(ACTIVE_PREFIXES):
        return False

    if path.suffix not in {".py", ".html", ".jinja", ".j2"}:
        return False

    return True


def main() -> int:
    print("\nFutureFunded active white-label surface audit")
    print("=" * 72)

    matches: dict[str, list[str]] = {term: [] for term in TERMS}

    for path in ROOT.rglob("*"):
        if not path.is_file() or not should_scan(path):
            continue

        text = path.read_text(encoding="utf-8", errors="ignore")
        rel = path.relative_to(ROOT).as_posix()

        for term in TERMS:
            if term in text:
                matches[term].append(rel)

    for term, files in matches.items():
        if files:
            warn(f"active white-label term still present: {term} ({len(files)} file(s))")
            for rel in files[:16]:
                print(f"   • {rel}")
        else:
            ok(f"active white-label term clear: {term}")

    print("\nRecommended next extraction:")
    print("  1. Move demo team defaults into config/team_campaigns.py or DB seed only.")
    print("  2. Replace active template fallbacks with profile-driven values.")
    print("  3. Keep deprecated templates excluded from launch readiness gates.")
    print("  4. Keep public campaign free of provider-readiness/operator copy.")

    print("\n" + "=" * 72)
    print(f"PASS: {len(PASS)}  WARN: {len(WARN)}  FAIL: {len(FAIL)}")

    if FAIL:
        return 1

    print("\n✅ ACTIVE WHITE-LABEL AUDIT COMPLETED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def backup(path: Path) -> None:
    if not path.exists():
        return
    stamp = time.strftime("%Y%m%d-%H%M%S")
    dst = path.with_suffix(path.suffix + f".bak-provider-readiness-{stamp}")
    shutil.copy2(path, dst)
    print(f"Backup: {dst}")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""


def write(path: Path, text: str) -> None:
    old = read(path)
    if old == text:
        print(f"No change: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    backup(path)
    path.write_text(text, encoding="utf-8")
    print(f"Updated: {path}")


def append_once(path: Path, marker: str, text: str) -> None:
    old = read(path)
    if marker in old:
        print(f"Already present: {marker} in {path}")
        return
    write(path, old.rstrip() + "\n\n" + text.strip() + "\n")


def insert_include(template: Path) -> None:
    if not template.exists():
        print(f"Skipped missing template: {template}")
        return

    text = read(template)
    original = text

    if INCLUDE in text or "_provider_readiness_panel.html" in text:
        print(f"Provider readiness include already present: {template}")
        return

    insertion = "\n\n" + INCLUDE + "\n"

    # Prefer placing after readiness/action blocks if visible.
    anchors = [
        "Next best actions",
        "Readiness",
        "Campaign performance",
        "Preview campaign",
        "</main>",
    ]

    for anchor in anchors:
        idx = text.find(anchor)
        if idx == -1:
            continue

        if anchor == "</main>":
            text = text[:idx] + insertion + text[idx:]
            break

        # Insert after the nearest following closing section/div boundary.
        boundary_candidates = [
            text.find("</section>", idx),
            text.find("</div>", idx),
        ]
        boundary_candidates = [x for x in boundary_candidates if x != -1]

        if boundary_candidates:
            pos = min(boundary_candidates)
            closing = "</section>" if text.startswith("</section>", pos) else "</div>"
            pos += len(closing)
            text = text[:pos] + insertion + text[pos:]
            break

    if text == original:
        text = text.rstrip() + insertion + "\n"

    write(template, text)


def patch_env_example() -> None:
    if ENV_EXAMPLE.exists():
        append_once(ENV_EXAMPLE, "FutureFunded launch provider readiness", ENV_BLOCK)
    else:
        write(ENV_EXAMPLE, ENV_BLOCK.strip() + "\n")


def main() -> int:
    print("\nFutureFunded white-label + provider readiness polish")
    print("=" * 72)

    write(PARTIAL, PARTIAL_TEXT)

    append_once(CSS, CSS_MARKER, CSS_PATCH)

    for template in TEMPLATES:
        insert_include(template)

    patch_env_example()

    write(PROVIDER_AUDIT, PROVIDER_AUDIT_TEXT)
    PROVIDER_AUDIT.chmod(0o755)

    write(WHITE_LABEL_AUDIT, WHITE_LABEL_AUDIT_TEXT)
    WHITE_LABEL_AUDIT.chmod(0o755)

    print("\n✅ White-label + provider readiness polish complete.")
    print("\nNext run:")
    print("  python scripts/final_provider_readiness_polish_audit.py")
    print("  python scripts/final_white_label_active_surface_audit.py")
    print("  python scripts/final_faq_minimal_audit.py")
    print("  python scripts/final_campaign_momentum_visual_audit.py")
    print("  python scripts/final_sponsor_package_behavior_audit.py")
    print("  python scripts/final_campaign_profile_audit.py")
    print("  python scripts/final_platform_smoke.py")
    print("  python scripts/final_funnel_functional_audit.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
