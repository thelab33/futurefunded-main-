#!/usr/bin/env python3
"""
FutureFunded Campaign Momentum Visual Polish

Upgrades the Campaign Momentum / Live Campaign Signal strip into a more premium
status-console style module while preserving:
- data-ff-momentum
- data-ff-momentum-rail
- ff.momentum.js
- sponsor package contract
- no duplicate Donate/Sponsor CTA buttons

Also refreshes the retired public sponsor recognition partial so the OS audit
does not confuse the retired stub with an old sponsor wall.
"""

from __future__ import annotations

import shutil
import time
from pathlib import Path

ROOT = Path.cwd()

PARTIAL = ROOT / "apps/web/app/templates/campaign/_campaign_momentum_bar.html"
PUBLIC_SPONSOR_PARTIAL = ROOT / "apps/web/app/templates/campaign/_public_sponsor_recognition.html"
CSS = ROOT / "apps/web/app/static/css/ff.css"
VISUAL_AUDIT = ROOT / "scripts/final_campaign_momentum_visual_audit.py"

CSS_MARKER = "FutureFunded Campaign Momentum Visual Console v3"

PARTIAL_TEXT = r'''{# FutureFunded Campaign Momentum Visual Console v3
   Premium OS-style status strip. No duplicate CTAs. No explanatory baggage.
#}

{% set _ff_platform = ff_platform|default({}, true) %}
{% set _ff_profile = ff_campaign_profile|default(campaign_profile|default({}, true), true) %}
{% set _ff_packages = _ff_profile.sponsor_packages|default(sponsor_packages|default(_sponsor_tiers|default([], true), true), true) %}
{% set _ff_supporters = _ff_profile.supporters|default(_ff_profile.supporter_count|default(_supporters|default(148, true), true), true) %}
{% set _ff_supporters_display = "{:,}".format(_ff_supporters|int) if _ff_supporters else '148' %}
{% set _ff_package_count = _ff_packages|length if _ff_packages else 3 %}

<section class="ff-campaignSection ff-section--momentum"
         id="campaign-momentum"
         aria-labelledby="campaign-momentum-title"
         data-ff-campaign-momentum-section>
  <div class="ff-campaignFunnelShell">
    <aside class="ff-momentum ff-momentum--signal ff-momentum--visualConsole ff-homeCard"
           data-ff-momentum
           data-ff-momentum-paused="false"
           aria-label="Campaign momentum signal">
      <div class="ff-momentumConsole">
        <div class="ff-momentumConsole__identity">
          <p class="ff-momentumSignal__kicker">
            <span aria-hidden="true"></span>
            Live campaign signal
          </p>

          <h2 id="campaign-momentum-title">Momentum is building.</h2>
        </div>

        <div class="ff-momentum__rail ff-momentumSignal__rail ff-momentumConsole__rail"
             data-ff-momentum-rail
             tabindex="0"
             aria-label="Campaign momentum highlights. Hover or focus to pause.">
          {% for repeat in [1, 2] %}
            <div class="ff-momentum__track" aria-hidden="{{ 'false' if repeat == 1 else 'true' }}">
              <span class="ff-momentum__item">
                <span class="ff-momentum__dot" aria-hidden="true"></span>
                <strong>{{ _ff_supporters_display }} supporters</strong>
                backing the season
              </span>

              <span class="ff-momentum__item">
                <span class="ff-momentum__dot" aria-hidden="true"></span>
                <strong>Sponsor-ready</strong>
                reviewed recognition
              </span>

              <span class="ff-momentum__item">
                <span class="ff-momentum__dot" aria-hidden="true"></span>
                <strong>Family-safe</strong>
                sponsor placement
              </span>

              <span class="ff-momentum__item">
                <span class="ff-momentum__dot" aria-hidden="true"></span>
                <strong>Season costs</strong>
                travel, meals, gear
              </span>

              <span class="ff-momentum__item">
                <span class="ff-momentum__dot" aria-hidden="true"></span>
                <strong>Secure giving</strong>
                checkout-ready
              </span>

              <span class="ff-momentum__item">
                <span class="ff-momentum__dot" aria-hidden="true"></span>
                <strong>{{ _ff_package_count }} sponsor tiers</strong>
                open for partners
              </span>
            </div>
          {% endfor %}
        </div>

        <div class="ff-momentumSignal__metrics ff-momentumConsole__metrics" aria-label="Campaign signal metrics">
          <article>
            <strong>{{ _ff_supporters_display }}</strong>
            <span>backers</span>
          </article>
          <article>
            <strong>{{ _ff_package_count }}</strong>
            <span>sponsor tiers</span>
          </article>
          <article>
            <strong>Secure</strong>
            <span>checkout-ready</span>
          </article>
        </div>
      </div>
    </aside>
  </div>
</section>
'''

PUBLIC_SPONSOR_STUB = '''{# Retired by FutureFunded Campaign Momentum Visual Console v3.
   The old Community Sponsors / public sponsor wall no longer renders on the
   public campaign surface.

   Replacement surface:
   - Campaign Momentum
   - Live campaign signal
   - campaign/_campaign_momentum_bar.html

   Keep this file as a compatibility stub for older includes and audits.
#}
'''

CSS_PATCH = r'''
/* ==========================================================================
   FutureFunded Campaign Momentum Visual Console v3
   Premium status-console treatment for the campaign signal strip.
   ========================================================================== */

.ff-momentum--visualConsole {
  position: relative;
  isolation: isolate;
  overflow: hidden;
  padding: clamp(10px, 1.8vw, 14px);
  border-radius: clamp(21px, 3vw, 30px);
  border: 1px solid rgba(72, 44, 25, 0.10);
  background:
    linear-gradient(90deg, rgba(255, 122, 26, 0.12), transparent 17%),
    radial-gradient(circle at 6% 0%, rgba(255, 122, 26, 0.16), transparent 18rem),
    radial-gradient(circle at 92% 10%, rgba(18, 124, 111, 0.115), transparent 20rem),
    linear-gradient(135deg, rgba(255, 255, 255, 0.96), rgba(255, 250, 242, 0.80));
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.92) inset,
    0 18px 50px rgba(55, 36, 20, 0.082);
}

.ff-momentum--visualConsole::before {
  content: "";
  position: absolute;
  inset: 0;
  z-index: -1;
  pointer-events: none;
  background:
    linear-gradient(90deg, rgba(243, 95, 22, 0.18), transparent 22%, transparent 78%, rgba(18, 124, 111, 0.10)),
    linear-gradient(rgba(72, 44, 25, 0.025) 1px, transparent 1px),
    linear-gradient(90deg, rgba(72, 44, 25, 0.022) 1px, transparent 1px);
  background-size: auto, 28px 28px, 28px 28px;
  opacity: 0.9;
}

.ff-momentum--visualConsole::after {
  content: "";
  position: absolute;
  inset: 0 auto 0 0;
  width: 4px;
  border-radius: 999px;
  background: linear-gradient(180deg, var(--ff-brand, #f35f16), rgba(18, 124, 111, 0.70));
  box-shadow: 0 0 24px rgba(243, 95, 22, 0.28);
}

.ff-momentumConsole {
  display: grid;
  grid-template-columns: minmax(170px, 0.72fr) minmax(240px, 1.5fr) minmax(245px, 0.9fr);
  align-items: center;
  gap: clamp(10px, 1.8vw, 16px);
}

.ff-momentumConsole__identity {
  min-width: 0;
  padding-left: 4px;
}

.ff-momentumConsole__identity h2 {
  margin-top: 5px;
  color: var(--ff-ink-strong, #130d08);
  font-size: clamp(1.13rem, 1.65vw, 1.58rem);
  letter-spacing: -0.052em;
  line-height: 0.98;
}

.ff-momentum--visualConsole .ff-momentumSignal__kicker {
  gap: 7px;
  color: #9a3d0f;
  font-size: 0.62rem;
  letter-spacing: 0.145em;
}

.ff-momentum--visualConsole .ff-momentumSignal__kicker span {
  inline-size: 7px;
  block-size: 7px;
  background: var(--ff-brand, #f35f16);
  box-shadow:
    0 0 0 4px rgba(243, 95, 22, 0.12),
    0 0 18px rgba(243, 95, 22, 0.42);
}

.ff-momentumConsole__rail {
  min-width: 0;
}

.ff-momentum--visualConsole .ff-momentumSignal__rail {
  min-height: 42px;
  border-radius: 999px;
  border-color: rgba(72, 44, 25, 0.085);
  background:
    linear-gradient(90deg, rgba(255, 255, 255, 0.88), rgba(255, 250, 242, 0.78)),
    rgba(255, 255, 255, 0.62);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.86),
    inset 0 -1px 0 rgba(72, 44, 25, 0.025),
    0 8px 24px rgba(55, 36, 20, 0.05);
}

.ff-momentum--visualConsole .ff-momentumSignal__rail::before {
  background: linear-gradient(90deg, rgba(255, 250, 242, 1), rgba(255, 250, 242, 0));
}

.ff-momentum--visualConsole .ff-momentumSignal__rail::after {
  background: linear-gradient(270deg, rgba(255, 250, 242, 1), rgba(255, 250, 242, 0));
}

.ff-momentum--visualConsole .ff-momentum__track {
  animation-duration: 54s;
}

.ff-momentum--visualConsole .ff-momentum__item {
  min-height: 30px;
  border-color: rgba(72, 44, 25, 0.072);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.82), rgba(255, 250, 242, 0.66));
  color: rgba(56, 42, 31, 0.76);
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.72) inset,
    0 5px 14px rgba(55, 36, 20, 0.032);
  font-size: 0.735rem;
  font-weight: 820;
  padding-inline: 10px;
}

.ff-momentum--visualConsole .ff-momentum__item strong {
  color: var(--ff-ink-strong, #130d08);
  font-weight: 950;
}

.ff-momentum--visualConsole .ff-momentum__dot {
  inline-size: 5px;
  block-size: 5px;
  background: var(--ff-brand, #f35f16);
  box-shadow:
    0 0 0 3px rgba(243, 95, 22, 0.10),
    0 0 14px rgba(243, 95, 22, 0.28);
}

.ff-momentumConsole__metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 7px;
}

.ff-momentum--visualConsole .ff-momentumConsole__metrics article {
  position: relative;
  overflow: hidden;
  border: 1px solid rgba(72, 44, 25, 0.072);
  border-radius: 15px;
  background:
    radial-gradient(circle at 100% 0%, rgba(255, 122, 26, 0.095), transparent 4.5rem),
    linear-gradient(180deg, rgba(255, 255, 255, 0.86), rgba(255, 250, 242, 0.68));
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.82) inset,
    0 8px 20px rgba(55, 36, 20, 0.043);
  padding: 8px 9px;
}

.ff-momentum--visualConsole .ff-momentumConsole__metrics article::before {
  content: "";
  position: absolute;
  inset: auto 9px 0;
  height: 2px;
  border-radius: 999px 999px 0 0;
  background: rgba(243, 95, 22, 0.42);
}

.ff-momentum--visualConsole .ff-momentumConsole__metrics strong {
  color: var(--ff-ink-strong, #130d08);
  font-size: clamp(0.86rem, 1.05vw, 0.98rem);
  font-weight: 950;
  letter-spacing: -0.035em;
  line-height: 1;
}

.ff-momentum--visualConsole .ff-momentumConsole__metrics span {
  margin-top: 4px;
  color: var(--ff-ink-subtle, rgba(74, 55, 39, 0.60));
  font-size: 0.59rem;
  font-weight: 900;
  letter-spacing: 0.015em;
  text-transform: uppercase;
}

@media (max-width: 980px) {
  .ff-momentumConsole {
    grid-template-columns: 1fr;
    align-items: stretch;
  }

  .ff-momentumConsole__identity {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 12px;
    padding-left: 0;
  }

  .ff-momentumConsole__identity h2 {
    margin-top: 0;
    text-align: right;
  }

  .ff-momentumConsole__metrics {
    order: 2;
  }

  .ff-momentumConsole__rail {
    order: 3;
  }
}

@media (max-width: 560px) {
  .ff-section--momentum {
    padding-block: 12px 16px;
  }

  .ff-momentum--visualConsole {
    padding: 12px;
    border-radius: 22px;
  }

  .ff-momentum--visualConsole::after {
    width: 3px;
  }

  .ff-momentumConsole__identity {
    display: grid;
    justify-content: stretch;
    gap: 5px;
  }

  .ff-momentumConsole__identity h2 {
    text-align: left;
    font-size: clamp(1.2rem, 6vw, 1.55rem);
  }

  .ff-momentumConsole__metrics {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .ff-momentum--visualConsole .ff-momentumConsole__metrics article {
    padding: 8px 7px;
    border-radius: 13px;
  }

  .ff-momentum--visualConsole .ff-momentumConsole__metrics span {
    font-size: 0.54rem;
  }

  .ff-momentum--visualConsole .ff-momentumSignal__rail {
    min-height: 40px;
    border-radius: 18px;
  }

  .ff-momentum--visualConsole .ff-momentum__item {
    min-height: 29px;
    font-size: 0.69rem;
  }
}

@media (prefers-reduced-motion: reduce) {
  .ff-momentum--visualConsole .ff-momentumSignal__rail {
    border-radius: 18px;
  }
}

:root[data-theme="dark"] .ff-momentum--visualConsole,
[data-theme="dark"] .ff-momentum--visualConsole {
  border-color: rgba(255,255,255,0.12);
  background:
    linear-gradient(90deg, rgba(255, 122, 26, 0.16), transparent 20%),
    radial-gradient(circle at 5% 0%, rgba(255, 122, 26, 0.16), transparent 18rem),
    radial-gradient(circle at 92% 0%, rgba(37, 99, 235, 0.15), transparent 18rem),
    rgba(15, 23, 42, 0.78);
}
'''

VISUAL_AUDIT_TEXT = r'''#!/usr/bin/env python3
"""Audit: Campaign Momentum has premium visual console structure."""

from __future__ import annotations

import re
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


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""


def extract_momentum_section(html: str) -> str:
    match = re.search(
        r'<section\b[^>]*data-ff-campaign-momentum-section[^>]*>[\s\S]*?</section>',
        html,
        flags=re.IGNORECASE,
    )
    return match.group(0) if match else ""


def main() -> int:
    print("\nFutureFunded Campaign Momentum visual console audit")
    print("=" * 72)

    css = read(ROOT / "apps/web/app/static/css/ff.css")
    retired = read(ROOT / "apps/web/app/templates/campaign/_public_sponsor_recognition.html")

    for term in [
        "FutureFunded Campaign Momentum Visual Console v3",
        ".ff-momentum--visualConsole",
        ".ff-momentumConsole",
        ".ff-momentumConsole__metrics",
        "prefers-reduced-motion",
    ]:
        ok(f"CSS contains {term}") if term in css else fail(f"CSS missing {term}")

    if "Retired" in retired and "Campaign Momentum" in retired and "Live campaign signal" in retired:
        ok("public sponsor recognition partial is a safe retired compatibility stub")
    else:
        fail("public sponsor recognition partial is not clearly retired")

    try:
        from apps.web.app import create_app
    except Exception as exc:
        fail(f"could not import create_app: {exc}")
        return 1

    app = create_app()
    client = app.test_client()

    res = client.get("/c/connect-atx-elite", follow_redirects=False)
    html = res.get_data(as_text=True)
    section = extract_momentum_section(html)

    ok("/c/connect-atx-elite loads") if res.status_code == 200 else fail(f"/c/connect-atx-elite HTTP {res.status_code}")
    ok("momentum section renders") if section else fail("momentum section missing")

    required = [
        "ff-momentum--visualConsole",
        "ff-momentumConsole",
        "ff-momentumConsole__identity",
        "ff-momentumConsole__rail",
        "ff-momentumConsole__metrics",
        "Live campaign signal",
        "Momentum is building.",
        "data-ff-momentum",
        "data-ff-momentum-rail",
    ]

    for term in required:
        ok(f"visual console contains {term}") if term in section else fail(f"visual console missing {term}")

    banned = [
        "Donate now",
        "Sponsor next",
        "data-ff-open-checkout",
        "data-ff-open-sponsor",
        "ff-momentum__actions",
        "Support is moving. Join the next wave.",
        "A clean signal layer",
    ]

    for term in banned:
        ok(f"visual console avoids {term}") if term not in section else fail(f"visual console still contains {term}")

    print("\n" + "=" * 72)
    print(f"PASS: {len(PASS)}  FAIL: {len(FAIL)}")

    if FAIL:
        print("\nFailures:")
        for item in FAIL:
            print(f"❌ {item}")
        return 1

    print("\n✅ CAMPAIGN MOMENTUM VISUAL CONSOLE AUDIT PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def backup(path: Path) -> None:
    if not path.exists():
        return

    stamp = time.strftime("%Y%m%d-%H%M%S")
    dst = path.with_suffix(path.suffix + f".bak-momentum-visual-{stamp}")
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


def main() -> int:
    print("\nFutureFunded polish Campaign Momentum visual")
    print("=" * 72)

    if not PARTIAL.exists():
        raise FileNotFoundError(f"Missing momentum partial: {PARTIAL}")

    write(PARTIAL, PARTIAL_TEXT)
    write(PUBLIC_SPONSOR_PARTIAL, PUBLIC_SPONSOR_STUB)

    css = read(CSS)
    if CSS_MARKER in css:
        print("CSS visual console patch already present.")
    else:
        write(CSS, css.rstrip() + "\n\n" + CSS_PATCH.strip() + "\n")

    write(VISUAL_AUDIT, VISUAL_AUDIT_TEXT)
    VISUAL_AUDIT.chmod(0o755)

    print("\n✅ Campaign Momentum visual polish complete.")
    print("\nNext run:")
    print("  python scripts/final_campaign_momentum_visual_audit.py")
    print("  python scripts/final_campaign_momentum_signal_strip_audit.py")
    print("  python scripts/final_campaign_momentum_premium_audit.py")
    print("  python scripts/final_campaign_momentum_os_audit.py")
    print("  python scripts/final_campaign_public_sponsor_leak_audit.py")
    print("  python scripts/final_sponsor_signal_strip_removed_audit.py")
    print("  python scripts/final_sponsor_package_behavior_audit.py")
    print("  python scripts/final_campaign_profile_audit.py")
    print("  python scripts/final_platform_smoke.py")
    print("  python scripts/final_funnel_functional_audit.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
