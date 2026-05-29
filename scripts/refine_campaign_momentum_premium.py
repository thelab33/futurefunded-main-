#!/usr/bin/env python3
"""
FutureFunded Campaign Momentum Premium Refinement

Goal:
- Replace the verbose momentum copy with a compact premium signal bar.
- Remove duplicate Donate now / Sponsor next buttons from the momentum section.
- Remove low-value explanatory text and package-price clutter.
- Keep Campaign Momentum, data-ff-momentum, and ff.momentum.js contracts intact.
- Keep sponsor package behavior untouched.
"""

from __future__ import annotations

import re
import shutil
import time
from pathlib import Path

ROOT = Path.cwd()

PARTIAL = ROOT / "apps/web/app/templates/campaign/_campaign_momentum_bar.html"
CSS = ROOT / "apps/web/app/static/css/ff.css"
OS_AUDIT = ROOT / "scripts/final_campaign_momentum_os_audit.py"
PREMIUM_AUDIT = ROOT / "scripts/final_campaign_momentum_premium_audit.py"

CSS_MARKER = "FutureFunded Campaign Momentum Premium Compact v1"

OLD_COPY = [
    "Support is moving. Join the next wave.",
    "A clean signal layer for donations, sponsors, shares, and season milestones",
    "built to make",
    "feel active, trusted, and sponsor-ready",
    "helps cover tournament-day support",
    "package ready for local partners",
    "Donate now",
    "Sponsor next",
]

PARTIAL_TEXT = r'''{# FutureFunded Campaign Momentum Premium Compact v1
   Quiet campaign pulse. No duplicate CTA buttons. No operational baggage.
#}

{% set _ff_platform = ff_platform|default({}, true) %}
{% set _ff_profile = ff_campaign_profile|default(campaign_profile|default({}, true), true) %}
{% set _ff_packages = _ff_profile.sponsor_packages|default(sponsor_packages|default(_sponsor_tiers|default([], true), true), true) %}
{% set _ff_team_name = _ff_platform.team_name|default(_ff_profile.team_name|default(_team_name|default('this campaign', true), true), true) %}
{% set _ff_supporters = _ff_profile.supporters|default(_ff_profile.supporter_count|default(_supporters|default(148, true), true), true) %}
{% set _ff_supporters_display = "{:,}".format(_ff_supporters|int) if _ff_supporters else '148' %}

<section class="ff-campaignSection ff-section--momentum"
         id="campaign-momentum"
         aria-labelledby="campaign-momentum-title"
         data-ff-campaign-momentum-section>
  <div class="ff-campaignFunnelShell">
    <div class="ff-momentum ff-momentum--premium ff-homeCard"
         data-ff-momentum
         data-ff-momentum-paused="false">
      <div class="ff-momentum__header ff-momentum__header--compact">
        <div class="ff-momentum__copy">
          <p class="ff-homeKicker">Campaign Momentum</p>
          <h2 id="campaign-momentum-title">Live proof, without the noise.</h2>
          <p>
            A quiet pulse of support, sponsor interest, and season progress — designed to build trust without slowing the page down.
          </p>
        </div>
      </div>

      <div class="ff-momentum__rail"
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
              <strong>Secure giving</strong>
              checkout-ready
            </span>

            <span class="ff-momentum__item">
              <span class="ff-momentum__dot" aria-hidden="true"></span>
              <strong>Sponsor packages</strong>
              open for partners
            </span>

            <span class="ff-momentum__item">
              <span class="ff-momentum__dot" aria-hidden="true"></span>
              <strong>Season costs</strong>
              travel, meals, gear
            </span>

            <span class="ff-momentum__item">
              <span class="ff-momentum__dot" aria-hidden="true"></span>
              <strong>Reviewed recognition</strong>
              family-safe placement
            </span>

            {% if _ff_packages %}
              <span class="ff-momentum__item">
                <span class="ff-momentum__dot" aria-hidden="true"></span>
                <strong>{{ _ff_packages|length }} sponsor tiers</strong>
                ready to activate
              </span>
            {% endif %}
          </div>
        {% endfor %}
      </div>
    </div>
  </div>
</section>
'''

CSS_PATCH = r'''
/* ==========================================================================
   FutureFunded Campaign Momentum Premium Compact v1
   Tightens the momentum rail into a quiet OS signal instead of a CTA block.
   ========================================================================== */

.ff-momentum--premium {
  gap: clamp(12px, 1.8vw, 18px);
  padding: clamp(16px, 2.4vw, 24px);
}

.ff-momentum__header--compact {
  grid-template-columns: minmax(0, 1fr);
  align-items: start;
}

.ff-momentum__header--compact .ff-momentum__copy {
  max-width: 920px;
}

.ff-momentum__header--compact .ff-momentum__copy h2 {
  max-width: 760px;
  font-size: clamp(1.42rem, 2.55vw, 2.35rem);
}

.ff-momentum__header--compact .ff-momentum__copy p:not(.ff-homeKicker) {
  max-width: 76ch;
  font-size: clamp(0.88rem, 1.08vw, 0.98rem);
}

.ff-momentum--premium .ff-momentum__rail {
  min-height: 50px;
}

.ff-momentum--premium .ff-momentum__item {
  min-height: 34px;
  font-size: 0.8rem;
}

.ff-momentum--premium .ff-momentum__item strong {
  letter-spacing: -0.02em;
}

@media (max-width: 760px) {
  .ff-momentum--premium {
    padding: 14px;
    border-radius: 22px;
  }

  .ff-momentum__header--compact .ff-momentum__copy h2 {
    font-size: clamp(1.3rem, 6vw, 1.8rem);
  }

  .ff-momentum__header--compact .ff-momentum__copy p:not(.ff-homeKicker) {
    font-size: 0.86rem;
  }
}
'''

PREMIUM_AUDIT_TEXT = r'''#!/usr/bin/env python3
"""Audit: Campaign Momentum is compact, premium, and free of duplicate CTA baggage."""

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
    print("\nFutureFunded Campaign Momentum premium audit")
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
        "Campaign Momentum",
        "Live proof, without the noise.",
        "quiet pulse of support",
        "data-ff-momentum",
        "ff-momentum--premium",
        "Secure giving",
        "Sponsor packages",
        "Reviewed recognition",
    ]

    for term in required:
        ok(f"premium momentum contains: {term}") if term in section else fail(f"premium momentum missing: {term}")

    banned_in_section = [
        "Support is moving. Join the next wave.",
        "A clean signal layer for donations, sponsors, shares, and season milestones",
        "built to make",
        "feel active, trusted, and sponsor-ready",
        "helps cover tournament-day support",
        "package ready for local partners",
        "Donate now",
        "Sponsor next",
        "data-ff-open-checkout",
        "data-ff-open-sponsor",
    ]

    for term in banned_in_section:
        ok(f"momentum section removed baggage: {term}") if term not in section else fail(f"momentum section still contains: {term}")

    # Keep global sponsor/donate behavior elsewhere.
    global_required = [
        "Donate",
        "Sponsor",
        "id=\"sponsor-form\"",
        "data-ff-sponsor-package-key-input",
        "data-ff-sponsor-submit",
        "ff.momentum.js",
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

    print("\n✅ CAMPAIGN MOMENTUM PREMIUM AUDIT PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def backup(path: Path) -> None:
    if not path.exists():
        return

    stamp = time.strftime("%Y%m%d-%H%M%S")
    dst = path.with_suffix(path.suffix + f".bak-premium-momentum-{stamp}")
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
        print("CSS premium compact patch already present.")
        return

    write(CSS, css.rstrip() + "\n\n" + CSS_PATCH.strip() + "\n")


def patch_os_audit() -> None:
    if not OS_AUDIT.exists():
        print(f"Skipped missing OS audit: {OS_AUDIT}")
        return

    text = read(OS_AUDIT)
    original = text

    text = text.replace(
        "Support is moving. Join the next wave.",
        "Live proof, without the noise.",
    )

    # Add old momentum copy to the rendered-removal checks if not already present.
    if "helps cover tournament-day support" not in text:
        text = text.replace(
            '"ae7dbb3d",',
            '"ae7dbb3d",\n'
            '            "Support is moving. Join the next wave.",\n'
            '            "A clean signal layer for donations, sponsors, shares, and season milestones",\n'
            '            "helps cover tournament-day support",\n'
            '            "package ready for local partners",',
        )

    if text != original:
        write(OS_AUDIT, text)
    else:
        print(f"No change: {OS_AUDIT}")


def write_premium_audit() -> None:
    write(PREMIUM_AUDIT, PREMIUM_AUDIT_TEXT)
    PREMIUM_AUDIT.chmod(0o755)


def main() -> int:
    print("\nFutureFunded refine Campaign Momentum premium")
    print("=" * 72)

    patch_partial()
    patch_css()
    patch_os_audit()
    write_premium_audit()

    print("\n✅ Premium Campaign Momentum refinement complete.")
    print("\nNext run:")
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
