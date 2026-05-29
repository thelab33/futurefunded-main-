#!/usr/bin/env python3
"""
FutureFunded FAQ Trust Center Refinement

Goal:
- Replace the current FAQ block with a premium, compact Trust Center.
- De-dupe repeated secure/receipt/sponsor-review copy.
- Remove extra Donate/Sponsor CTAs from FAQ.
- Keep #faq anchor and Help nav contract intact.
- Add an audit to prevent FAQ clutter from coming back.
"""

from __future__ import annotations

import re
import shutil
import time
from pathlib import Path

ROOT = Path.cwd()

TEMPLATES = [
    ROOT / "apps/web/app/templates/campaign_premium.html",
    ROOT / "apps/web/app/templates/campaign/index.html",
]

CSS = ROOT / "apps/web/app/static/css/ff.css"
AUDIT = ROOT / "scripts/final_faq_trust_center_audit.py"

CSS_MARKER = "FutureFunded FAQ Trust Center v1"

FAQ_SECTION = r'''
      <section class="ff-campaignSection ff-section--faqClean ff-section--faqLive"
               id="faq"
               aria-labelledby="faq-title"
               data-ff-faq-live>
        <div class="ff-campaignFunnelShell">
          <div class="ff-faqLive ff-trustPanel ff-homeCard ff-premiumSectionCard" data-ff-reveal>
            <div class="ff-faqLive__head">
              <div>
                <p class="ff-homeKicker">Trust center</p>
                <h2 id="faq-title">Give with clarity.</h2>
              </div>

              <p>
                The essentials donors, parents, and sponsors need before backing {{ _team_name }} —
                clear use of funds, secure checkout, receipts, and reviewed sponsor placement.
              </p>
            </div>

            <div class="ff-faqLive__statusGrid" aria-label="Campaign trust signals">
              <article class="ff-faqLiveStatus">
                <span aria-hidden="true">✓</span>
                <strong>Secure checkout</strong>
                <p>Payments run through trusted checkout. FutureFunded does not store card numbers.</p>
              </article>

              <article class="ff-faqLiveStatus">
                <span aria-hidden="true">↗</span>
                <strong>Receipt-ready</strong>
                <p>Supporters receive confirmation after a completed contribution.</p>
              </article>

              <article class="ff-faqLiveStatus">
                <span aria-hidden="true">★</span>
                <strong>Reviewed sponsors</strong>
                <p>Sponsor recognition is reviewed before appearing on the public campaign.</p>
              </article>
            </div>

            <div class="ff-faqLive__body">
              <div class="ff-faqLive__answers" aria-label="Frequently asked questions">
                <details class="ff-faqLiveItem" open>
                  <summary>
                    <span>Where does the money go?</span>
                  </summary>
                  <p>
                    Contributions help cover practical season costs: tournament fees, travel, meals,
                    hydration, uniforms, gym time, gear, and player essentials.
                  </p>
                </details>

                <details class="ff-faqLiveItem">
                  <summary>
                    <span>Is checkout secure?</span>
                  </summary>
                  <p>
                    Yes. Payments are completed through secure checkout providers. FutureFunded keeps
                    the campaign experience simple and does not store donor card numbers.
                  </p>
                </details>

                <details class="ff-faqLiveItem">
                  <summary>
                    <span>Are sponsor placements reviewed?</span>
                  </summary>
                  <p>
                    Yes. Sponsor packages can be selected from the campaign, but public recognition is
                    reviewed so the page stays clean, family-safe, and appropriate for the program.
                  </p>
                </details>

                <details class="ff-faqLiveItem">
                  <summary>
                    <span>Can I share this with someone else?</span>
                  </summary>
                  <p>
                    Absolutely. Share the campaign with parents, alumni, local businesses, and supporters
                    who want a clear way to help the season.
                  </p>
                </details>
              </div>

              <aside class="ff-faqLiveDecision" aria-label="Share or contact">
                <p class="ff-homeKicker">Still deciding?</p>
                <h3>Send the campaign to someone who can help.</h3>
                <p>
                  Share it with a parent, sponsor, alumni supporter, or local business. Every warm intro
                  can move the season forward.
                </p>

                <div class="ff-faqLiveDecision__actions">
                  <button class="ff-button ff-button--primary"
                          type="button"
                          data-ff-share-trigger
                          data-ff-qr-trigger
                          data-ff-action="open-qr-modal">
                    Share campaign
                  </button>

                  <a class="ff-button ff-button--ghost"
                     href="mailto:sponsor@futurefunded.com?subject={{ _team_name|urlencode }} campaign question">
                    Contact
                  </a>
                </div>
              </aside>
            </div>
          </div>
        </div>
      </section>
'''

CSS_PATCH = r'''
/* ==========================================================================
   FutureFunded FAQ Trust Center v1
   Compact donor/sponsor confidence system. Removes duplicated FAQ clutter.
   ========================================================================== */

.ff-section--faqLive {
  padding-block: clamp(34px, 4.8vw, 58px);
}

.ff-faqLive {
  position: relative;
  isolation: isolate;
  display: grid;
  gap: clamp(16px, 2.4vw, 24px);
  padding: clamp(18px, 3vw, 30px);
  border-radius: clamp(24px, 4vw, 34px);
  overflow: hidden;
}

.ff-faqLive::before {
  content: "";
  position: absolute;
  inset: 0;
  z-index: -1;
  pointer-events: none;
  background:
    radial-gradient(circle at 0% 0%, rgba(18, 124, 111, 0.11), transparent 24rem),
    radial-gradient(circle at 100% 0%, rgba(255, 122, 26, 0.10), transparent 22rem),
    linear-gradient(135deg, rgba(255, 255, 255, 0.94), rgba(255, 250, 242, 0.78));
}

.ff-faqLive__head {
  display: grid;
  grid-template-columns: minmax(0, 0.82fr) minmax(280px, 1fr);
  align-items: end;
  gap: clamp(14px, 2.4vw, 24px);
}

.ff-faqLive__head h2 {
  margin-top: 8px;
  font-size: clamp(1.9rem, 3.7vw, 3.7rem);
  letter-spacing: -0.065em;
}

.ff-faqLive__head > p {
  max-width: 70ch;
  color: var(--ff-ink-muted, rgba(56, 42, 31, 0.74));
  font-size: clamp(0.92rem, 1.15vw, 1.02rem);
  line-height: 1.62;
}

.ff-faqLive__statusGrid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: clamp(10px, 1.6vw, 14px);
}

.ff-faqLiveStatus {
  position: relative;
  min-width: 0;
  overflow: hidden;
  border: 1px solid rgba(72, 44, 25, 0.08);
  border-radius: 18px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.86), rgba(255, 250, 242, 0.68));
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.80) inset,
    0 10px 24px rgba(55, 36, 20, 0.045);
  padding: clamp(13px, 1.8vw, 17px);
}

.ff-faqLiveStatus::after {
  content: "";
  position: absolute;
  inset: auto 12px 0;
  height: 2px;
  border-radius: 999px 999px 0 0;
  background: rgba(18, 124, 111, 0.42);
}

.ff-faqLiveStatus span {
  display: inline-flex;
  inline-size: 26px;
  block-size: 26px;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: rgba(18, 124, 111, 0.10);
  color: #127c6f;
  font-size: 0.84rem;
  font-weight: 950;
  line-height: 1;
}

.ff-faqLiveStatus strong {
  display: block;
  margin-top: 10px;
  color: var(--ff-ink-strong, #130d08);
  font-size: 0.98rem;
  font-weight: 950;
  letter-spacing: -0.03em;
  line-height: 1.05;
}

.ff-faqLiveStatus p {
  margin-top: 6px;
  color: var(--ff-ink-subtle, rgba(74, 55, 39, 0.60));
  font-size: 0.82rem;
  line-height: 1.48;
}

.ff-faqLive__body {
  display: grid;
  grid-template-columns: minmax(0, 1.38fr) minmax(260px, 0.62fr);
  gap: clamp(12px, 2vw, 18px);
  align-items: start;
}

.ff-faqLive__answers {
  display: grid;
  gap: 9px;
}

.ff-faqLiveItem {
  overflow: hidden;
  border: 1px solid rgba(72, 44, 25, 0.08);
  border-radius: 17px;
  background: rgba(255, 255, 255, 0.72);
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.76) inset,
    0 8px 20px rgba(55, 36, 20, 0.035);
}

.ff-faqLiveItem summary {
  display: flex;
  min-height: 48px;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  color: var(--ff-ink-strong, #130d08);
  cursor: pointer;
  font-size: 0.92rem;
  font-weight: 920;
  letter-spacing: -0.022em;
  list-style: none;
  padding: 14px 15px;
}

.ff-faqLiveItem summary::-webkit-details-marker {
  display: none;
}

.ff-faqLiveItem summary::after {
  content: "+";
  display: inline-flex;
  inline-size: 24px;
  block-size: 24px;
  flex: 0 0 auto;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(72, 44, 25, 0.09);
  border-radius: 999px;
  background: rgba(255, 250, 242, 0.82);
  color: #a84310;
  font-size: 0.95rem;
  font-weight: 950;
  line-height: 1;
}

.ff-faqLiveItem[open] summary::after {
  content: "–";
}

.ff-faqLiveItem p {
  margin: -4px 15px 15px;
  max-width: 72ch;
  color: var(--ff-ink-muted, rgba(56, 42, 31, 0.74));
  font-size: 0.88rem;
  line-height: 1.58;
}

.ff-faqLiveDecision {
  position: sticky;
  top: calc(var(--ff-header-h, 70px) + 18px);
  overflow: hidden;
  border: 1px solid rgba(243, 95, 22, 0.13);
  border-radius: 22px;
  background:
    radial-gradient(circle at 100% 0%, rgba(255, 122, 26, 0.15), transparent 12rem),
    linear-gradient(180deg, rgba(255, 255, 255, 0.88), rgba(255, 250, 242, 0.72));
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.80) inset,
    0 14px 34px rgba(55, 36, 20, 0.07);
  padding: clamp(16px, 2.4vw, 20px);
}

.ff-faqLiveDecision h3 {
  margin-top: 8px;
  font-size: clamp(1.15rem, 1.7vw, 1.45rem);
  letter-spacing: -0.045em;
}

.ff-faqLiveDecision > p:not(.ff-homeKicker) {
  margin-top: 8px;
  color: var(--ff-ink-muted, rgba(56, 42, 31, 0.74));
  font-size: 0.88rem;
  line-height: 1.58;
}

.ff-faqLiveDecision__actions {
  display: grid;
  grid-template-columns: 1fr;
  gap: 9px;
  margin-top: 14px;
}

.ff-faqLiveDecision__actions .ff-button {
  width: 100%;
}

@media (max-width: 900px) {
  .ff-faqLive__head,
  .ff-faqLive__body {
    grid-template-columns: 1fr;
  }

  .ff-faqLiveDecision {
    position: relative;
    top: auto;
  }
}

@media (max-width: 720px) {
  .ff-faqLive {
    padding: 16px;
    border-radius: 24px;
  }

  .ff-faqLive__statusGrid {
    grid-template-columns: 1fr;
  }

  .ff-faqLive__head h2 {
    font-size: clamp(1.75rem, 8vw, 2.7rem);
  }

  .ff-faqLiveItem summary {
    align-items: flex-start;
    min-height: 46px;
    padding: 13px;
  }

  .ff-faqLiveItem p {
    margin-inline: 13px;
  }
}

:root[data-theme="dark"] .ff-faqLive::before,
[data-theme="dark"] .ff-faqLive::before {
  background:
    radial-gradient(circle at 0% 0%, rgba(18, 124, 111, 0.16), transparent 24rem),
    radial-gradient(circle at 100% 0%, rgba(255, 122, 26, 0.15), transparent 22rem),
    rgba(15, 23, 42, 0.76);
}

:root[data-theme="dark"] :is(.ff-faqLiveStatus, .ff-faqLiveItem, .ff-faqLiveDecision),
[data-theme="dark"] :is(.ff-faqLiveStatus, .ff-faqLiveItem, .ff-faqLiveDecision) {
  border-color: rgba(255, 255, 255, 0.12);
  background: rgba(15, 23, 42, 0.70);
}
'''

AUDIT_TEXT = r'''#!/usr/bin/env python3
"""Audit: FAQ renders as a compact premium Trust Center."""

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


def extract_faq(html: str) -> str:
    match = re.search(
        r'<section\b[^>]*\bid=["\']faq["\'][^>]*>[\s\S]*?</section>',
        html,
        flags=re.IGNORECASE,
    )
    return match.group(0) if match else ""


def main() -> int:
    print("\nFutureFunded FAQ Trust Center audit")
    print("=" * 72)

    css = read(ROOT / "apps/web/app/static/css/ff.css")

    for term in [
        "FutureFunded FAQ Trust Center v1",
        ".ff-faqLive",
        ".ff-faqLive__statusGrid",
        ".ff-faqLiveDecision",
    ]:
        ok(f"CSS contains {term}") if term in css else fail(f"CSS missing {term}")

    try:
        from apps.web.app import create_app
    except Exception as exc:
        fail(f"could not import create_app: {exc}")
        return 1

    app = create_app()
    client = app.test_client()

    res = client.get("/c/connect-atx-elite", follow_redirects=False)
    html = res.get_data(as_text=True)
    faq = extract_faq(html)

    ok("/c/connect-atx-elite loads") if res.status_code == 200 else fail(f"/c/connect-atx-elite HTTP {res.status_code}")
    ok("#faq section renders") if faq else fail("#faq section missing")

    required = [
        "Trust center",
        "Give with clarity.",
        "ff-faqLive",
        "ff-faqLive__statusGrid",
        "Secure checkout",
        "Receipt-ready",
        "Reviewed sponsors",
        "Where does the money go?",
        "Is checkout secure?",
        "Are sponsor placements reviewed?",
        "Can I share this with someone else?",
        "Still deciding?",
        "Share campaign",
        "Contact",
    ]

    for term in required:
        ok(f"FAQ contains {term}") if term in faq else fail(f"FAQ missing {term}")

    banned_in_faq = [
        "Receipts, privacy, and answers",
        "Clear answers before you give.",
        "Donors should know exactly how checkout works",
        "No account required. Secure checkout. Simple receipts.",
        "Donate now",
        "Sponsor next",
        "Become a sponsor",
        "data-ff-open-checkout",
        "data-ff-open-sponsor",
        "data-ff-donate-trigger",
        "data-ff-sponsor-trigger",
    ]

    for term in banned_in_faq:
        ok(f"FAQ removed clutter: {term}") if term not in faq else fail(f"FAQ still contains clutter: {term}")

    global_required = [
        "id=\"sponsor-form\"",
        "data-ff-sponsor-package-key-input",
        "data-ff-sponsor-submit",
        "Live campaign signal",
        "Momentum is building.",
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

    print("\n✅ FAQ TRUST CENTER AUDIT PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def backup(path: Path) -> None:
    if not path.exists():
        return
    stamp = time.strftime("%Y%m%d-%H%M%S")
    dst = path.with_suffix(path.suffix + f".bak-faq-trust-center-{stamp}")
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


def find_balanced_section(text: str, start: int) -> tuple[int, int] | None:
    tag_re = re.compile(r"<(/?)section\b[^>]*>", re.IGNORECASE | re.DOTALL)
    first = tag_re.search(text, start)

    if not first or first.group(1):
        return None

    depth = 0

    for match in tag_re.finditer(text, first.start()):
        if match.group(1):
            depth -= 1
            if depth == 0:
                return first.start(), match.end()
        else:
            depth += 1

    return None


def patch_template(path: Path) -> None:
    if not path.exists():
        print(f"Skipped missing template: {path}")
        return

    text = read(path)
    original = text

    match = re.search(
        r"<section\b(?=[^>]*\bid=(['\"])faq\1)[^>]*>",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if not match:
        print(f"No #faq section found: {path}")
        return

    bounds = find_balanced_section(text, match.start())

    if not bounds:
        raise RuntimeError(f"Could not parse #faq section in {path}")

    start, end = bounds
    text = text[:start] + FAQ_SECTION.rstrip() + "\n" + text[end:]

    if text != original:
        write(path, text)
    else:
        print(f"No change needed: {path}")


def patch_css() -> None:
    css = read(CSS)

    if CSS_MARKER in css:
        print("FAQ Trust Center CSS already present.")
        return

    write(CSS, css.rstrip() + "\n\n" + CSS_PATCH.strip() + "\n")


def write_audit() -> None:
    write(AUDIT, AUDIT_TEXT)
    AUDIT.chmod(0o755)


def main() -> int:
    print("\nFutureFunded refine FAQ into Trust Center")
    print("=" * 72)

    for path in TEMPLATES:
        patch_template(path)

    patch_css()
    write_audit()

    print("\n✅ FAQ Trust Center refinement complete.")
    print("\nNext run:")
    print("  python scripts/final_faq_trust_center_audit.py")
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
