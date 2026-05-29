#!/usr/bin/env python3
"""
FutureFunded Campaign Momentum Signal Strip

Goal:
- Make the momentum section feel like a premium OS status strip.
- Remove paragraph-heavy feel.
- Add compact proof metrics.
- Keep no duplicate Donate/Sponsor CTAs.
- Keep data-ff-momentum + ff.momentum.js contracts intact.
"""

from __future__ import annotations

import re
import shutil
import time
from pathlib import Path

ROOT = Path.cwd()

PARTIAL = ROOT / "apps/web/app/templates/campaign/_campaign_momentum_bar.html"
CSS = ROOT / "apps/web/app/static/css/ff.css"
PREMIUM_AUDIT = ROOT / "scripts/final_campaign_momentum_premium_audit.py"
SIGNAL_AUDIT = ROOT / "scripts/final_campaign_momentum_signal_strip_audit.py"

CSS_MARKER = "FutureFunded Campaign Momentum Signal Strip v2"

PARTIAL_TEXT = r'''{# FutureFunded Campaign Momentum Signal Strip v2
   Premium OS-style proof strip. No duplicate CTAs. No explanatory baggage.
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
    <aside class="ff-momentum ff-momentum--signal ff-homeCard"
           data-ff-momentum
           data-ff-momentum-paused="false"
           aria-label="Campaign momentum signal">
      <div class="ff-momentumSignal__header">
        <div class="ff-momentumSignal__title">
          <p class="ff-momentumSignal__kicker">
            <span aria-hidden="true"></span>
            Live campaign signal
          </p>
          <h2 id="campaign-momentum-title">Momentum is building.</h2>
        </div>

        <div class="ff-momentumSignal__metrics" aria-label="Campaign signal metrics">
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

      <div class="ff-momentum__rail ff-momentumSignal__rail"
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
              <strong>Family-safe</strong>
              sponsor placement
            </span>

            <span class="ff-momentum__item">
              <span class="ff-momentum__dot" aria-hidden="true"></span>
              <strong>{{ _ff_package_count }} sponsor tiers</strong>
              open for partners
            </span>
          </div>
        {% endfor %}
      </div>
    </aside>
  </div>
</section>
'''

CSS_PATCH = r'''
/* ==========================================================================
   FutureFunded Campaign Momentum Signal Strip v2
   Premium OS signal strip: compact proof, restrained motion, no CTA baggage.
   ========================================================================== */

.ff-section--momentum {
  padding-block: clamp(14px, 2.4vw, 26px);
}

.ff-momentum--signal {
  --ff-momentum-line: rgba(72, 44, 25, 0.09);
  --ff-momentum-glass: rgba(255, 255, 255, 0.68);
  --ff-momentum-warm: rgba(255, 122, 26, 0.12);
  --ff-momentum-mint: rgba(18, 124, 111, 0.095);

  display: grid;
  gap: 12px;
  padding: clamp(12px, 2vw, 18px);
  border: 1px solid var(--ff-momentum-line);
  border-radius: clamp(20px, 3vw, 28px);
  background:
    radial-gradient(circle at 0% 0%, var(--ff-momentum-warm), transparent 18rem),
    radial-gradient(circle at 100% 0%, var(--ff-momentum-mint), transparent 18rem),
    linear-gradient(135deg, rgba(255, 255, 255, 0.93), rgba(255, 250, 242, 0.76));
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.86) inset,
    0 18px 48px rgba(55, 36, 20, 0.075);
}

.ff-momentum--signal::before {
  opacity: 0.55;
}

.ff-momentumSignal__header {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(260px, auto);
  align-items: center;
  gap: clamp(12px, 2vw, 18px);
}

.ff-momentumSignal__title {
  min-width: 0;
}

.ff-momentumSignal__kicker {
  display: inline-flex;
  width: fit-content;
  align-items: center;
  gap: 8px;
  color: #a84310;
  font-size: 0.68rem;
  font-weight: 950;
  letter-spacing: 0.15em;
  line-height: 1;
  text-transform: uppercase;
}

.ff-momentumSignal__kicker span {
  inline-size: 7px;
  block-size: 7px;
  border-radius: 999px;
  background: var(--ff-brand, #f35f16);
  box-shadow:
    0 0 0 4px rgba(243, 95, 22, 0.12),
    0 0 18px rgba(243, 95, 22, 0.38);
}

.ff-momentumSignal__title h2 {
  margin-top: 6px;
  color: var(--ff-ink-strong, #130d08);
  font-size: clamp(1.32rem, 2.35vw, 2.15rem);
  letter-spacing: -0.058em;
  line-height: 0.96;
}

.ff-momentumSignal__metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(78px, 1fr));
  gap: 8px;
}

.ff-momentumSignal__metrics article {
  min-width: 0;
  border: 1px solid rgba(72, 44, 25, 0.075);
  border-radius: 16px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.82), rgba(255, 250, 242, 0.64));
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.82) inset,
    0 8px 20px rgba(55, 36, 20, 0.045);
  padding: 9px 10px;
}

.ff-momentumSignal__metrics strong,
.ff-momentumSignal__metrics span {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ff-momentumSignal__metrics strong {
  color: var(--ff-ink-strong, #130d08);
  font-size: clamp(0.92rem, 1.35vw, 1.08rem);
  font-weight: 950;
  letter-spacing: -0.035em;
  line-height: 1;
}

.ff-momentumSignal__metrics span {
  margin-top: 4px;
  color: var(--ff-ink-subtle, rgba(74, 55, 39, 0.6));
  font-size: 0.68rem;
  font-weight: 860;
  letter-spacing: -0.01em;
}

.ff-momentum--signal .ff-momentumSignal__rail {
  min-height: 44px;
  border-radius: 999px;
  background:
    linear-gradient(90deg, rgba(255, 255, 255, 0.92), rgba(255, 250, 242, 0.76)),
    rgba(255, 255, 255, 0.7);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.82),
    0 10px 26px rgba(55, 36, 20, 0.052);
}

.ff-momentum--signal .ff-momentum__track {
  animation-duration: 50s;
}

.ff-momentum--signal .ff-momentum__item {
  min-height: 31px;
  border-color: rgba(72, 44, 25, 0.07);
  background: rgba(255, 255, 255, 0.68);
  box-shadow: 0 5px 14px rgba(55, 36, 20, 0.035);
  color: var(--ff-ink-muted, rgba(56, 42, 31, 0.74));
  font-size: 0.76rem;
  font-weight: 820;
  padding-inline: 11px;
}

.ff-momentum--signal .ff-momentum__item strong {
  color: var(--ff-ink-strong, #130d08);
  font-weight: 950;
}

.ff-momentum--signal .ff-momentum__dot {
  inline-size: 6px;
  block-size: 6px;
  box-shadow:
    0 0 0 3px rgba(243, 95, 22, 0.10),
    0 0 14px rgba(243, 95, 22, 0.26);
}

@media (max-width: 820px) {
  .ff-momentumSignal__header {
    grid-template-columns: 1fr;
    align-items: start;
  }

  .ff-momentumSignal__metrics {
    width: 100%;
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .ff-momentum--signal {
    border-radius: 22px;
    padding: 13px;
  }

  .ff-momentumSignal__title h2 {
    font-size: clamp(1.25rem, 6vw, 1.7rem);
  }

  .ff-momentumSignal__metrics article {
    border-radius: 14px;
    padding: 8px;
  }

  .ff-momentumSignal__metrics span {
    font-size: 0.62rem;
  }

  .ff-momentum--signal .ff-momentumSignal__rail {
    border-radius: 18px;
  }
}

@media (max-width: 460px) {
  .ff-momentumSignal__metrics {
    grid-template-columns: 1fr 1fr;
  }

  .ff-momentumSignal__metrics article:last-child {
    grid-column: 1 / -1;
  }
}

:root[data-theme="dark"] .ff-momentum--signal,
[data-theme="dark"] .ff-momentum--signal {
  --ff-momentum-line: rgba(255, 255, 255, 0.12);
  --ff-momentum-glass: rgba(15, 23, 42, 0.72);
  background:
    radial-gradient(circle at 0% 0%, rgba(255, 122, 26, 0.16), transparent 18rem),
    radial-gradient(circle at 100% 0%, rgba(37, 99, 235, 0.15), transparent 18rem),
    rgba(15, 23, 42, 0.74);
}
'''

SIGNAL_AUDIT_TEXT = r'''#!/usr/bin/env python3
"""Audit: Campaign Momentum renders as a premium OS signal strip."""

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


def extract_momentum_section(html: str) -> str:
    match = re.search(
        r'<section\b[^>]*data-ff-campaign-momentum-section[^>]*>[\s\S]*?</section>',
        html,
        flags=re.IGNORECASE,
    )
    return match.group(0) if match else ""


def main() -> int:
    print("\nFutureFunded Campaign Momentum signal strip audit")
    print("=" * 72)

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
        "Live campaign signal",
        "Momentum is building.",
        "ff-momentum--signal",
        "ff-momentumSignal__metrics",
        "backers",
        "sponsor tiers",
        "checkout-ready",
        "Sponsor-ready",
        "Family-safe",
        "data-ff-momentum",
    ]

    for term in required:
        ok(f"signal strip contains: {term}") if term in section else fail(f"signal strip missing: {term}")

    banned = [
        "Live proof, without the noise.",
        "quiet pulse of support",
        "Support is moving. Join the next wave.",
        "A clean signal layer",
        "Donate now",
        "Sponsor next",
        "data-ff-open-checkout",
        "data-ff-open-sponsor",
        "ff-momentum__actions",
    ]

    for term in banned:
        ok(f"signal strip removed baggage: {term}") if term not in section else fail(f"signal strip still contains: {term}")

    global_required = [
        "id=\"sponsor-form\"",
        "data-ff-sponsor-package-key-input",
        "data-ff-sponsor-submit",
        "ff.momentum.js",
        "Donate",
        "Sponsor",
    ]

    for term in global_required:
        ok(f"global campaign contract still present: {term}") if term in html else fail(f"global campaign contract missing: {term}")

    print("\n" + "=" * 72)
    print(f"PASS: {len(PASS)}  FAIL: {len(FAIL)}")

    if FAIL:
        print("\nFailures:")
        for item in FAIL:
            print(f"❌ {item}")
        return 1

    print("\n✅ CAMPAIGN MOMENTUM SIGNAL STRIP AUDIT PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def backup(path: Path) -> None:
    if not path.exists():
        return

    stamp = time.strftime("%Y%m%d-%H%M%S")
    dst = path.with_suffix(path.suffix + f".bak-signal-strip-{stamp}")
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


def patch_partial() -> None:
    if not PARTIAL.exists():
        raise FileNotFoundError(f"Missing momentum partial: {PARTIAL}")
    write(PARTIAL, PARTIAL_TEXT)


def patch_css() -> None:
    css = read(CSS)
    if CSS_MARKER in css:
        print("CSS signal strip patch already present.")
        return
    write(CSS, css.rstrip() + "\n\n" + CSS_PATCH.strip() + "\n")


def patch_premium_audit() -> None:
    if not PREMIUM_AUDIT.exists():
        print(f"Skipped missing premium audit: {PREMIUM_AUDIT}")
        return

    text = read(PREMIUM_AUDIT)
    original = text

    replacements = {
        "Live proof, without the noise.": "Momentum is building.",
        "quiet pulse of support": "Live campaign signal",
        "ff-momentum--premium": "ff-momentum--signal",
        "Secure giving": "Sponsor-ready",
        "Sponsor packages": "sponsor tiers",
        "Reviewed recognition": "Family-safe",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    if "ff-momentum__actions" not in text:
        text = text.replace(
            '"data-ff-open-sponsor",',
            '"data-ff-open-sponsor",\n        "ff-momentum__actions",',
        )

    if text != original:
        write(PREMIUM_AUDIT, text)
    else:
        print(f"No change: {PREMIUM_AUDIT}")


def write_signal_audit() -> None:
    write(SIGNAL_AUDIT, SIGNAL_AUDIT_TEXT)
    SIGNAL_AUDIT.chmod(0o755)


def main() -> int:
    print("\nFutureFunded refine Campaign Momentum into signal strip")
    print("=" * 72)

    patch_partial()
    patch_css()
    patch_premium_audit()
    write_signal_audit()

    print("\n✅ Campaign Momentum signal strip refinement complete.")
    print("\nNext run:")
    print("  python scripts/final_campaign_momentum_signal_strip_audit.py")
    print("  python scripts/final_campaign_momentum_premium_audit.py")
    print("  python scripts/final_campaign_momentum_os_audit.py")
    print("  python scripts/final_sponsor_signal_strip_removed_audit.py")
    print("  python scripts/final_campaign_public_sponsor_leak_audit.py")
    print("  python scripts/final_sponsor_package_behavior_audit.py")
    print("  python scripts/final_campaign_profile_audit.py")
    print("  python scripts/final_platform_smoke.py")
    print("  python scripts/final_funnel_functional_audit.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
