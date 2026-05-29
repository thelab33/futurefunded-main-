#!/usr/bin/env python3
"""
FutureFunded Bare-Minimal FAQ Refinement

Goal:
- Replace the large FAQ Trust Center with a compact FAQ checkpoint.
- Remove status cards, side CTA, Share campaign, Contact button, and duplicated trust copy.
- Preserve #faq anchor and Help nav target.
- Keep details/summary accessibility.
- Update the FAQ audit contract to the new bare-minimal version.
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
MINI_AUDIT = ROOT / "scripts/final_faq_minimal_audit.py"

CSS_MARKER = "FutureFunded Minimal FAQ v2"

FAQ_SECTION = r'''
      <section class="ff-campaignSection ff-section--faqClean ff-section--faqMini"
               id="faq"
               aria-labelledby="faq-title"
               data-ff-faq-mini>
        <div class="ff-campaignFunnelShell">
          <div class="ff-faqMini ff-homeCard ff-premiumSectionCard" data-ff-reveal>
            <div class="ff-faqMini__head">
              <div>
                <p class="ff-homeKicker">Quick answers</p>
                <h2 id="faq-title">The essentials before you give.</h2>
              </div>
              <p>Simple answers for donors, parents, and sponsors.</p>
            </div>

            <div class="ff-faqMini__list" aria-label="Frequently asked questions">
              <details class="ff-faqMiniItem">
                <summary>
                  <span>Where does the money go?</span>
                </summary>
                <p>
                  Contributions help cover tournament fees, travel, meals, hydration, uniforms,
                  gym time, gear, and player essentials.
                </p>
              </details>

              <details class="ff-faqMiniItem">
                <summary>
                  <span>Is checkout secure?</span>
                </summary>
                <p>
                  Yes. Payments are completed through secure checkout providers.
                  FutureFunded does not store donor card numbers.
                </p>
              </details>

              <details class="ff-faqMiniItem">
                <summary>
                  <span>How do sponsors work?</span>
                </summary>
                <p>
                  Sponsors choose a package, then recognition is reviewed before appearing
                  publicly so the campaign stays clean and family-safe.
                </p>
              </details>
            </div>
          </div>
        </div>
      </section>
'''

CSS_PATCH = r'''
/* ==========================================================================
   FutureFunded Minimal FAQ v2
   Bare-minimum donor confidence checkpoint. No side card. No CTA clutter.
   ========================================================================== */

.ff-section--faqMini {
  padding-block: clamp(22px, 3.2vw, 38px);
  scroll-margin-top: calc(var(--ff-header-h, 72px) + 22px);
}

.ff-faqMini {
  position: relative;
  isolation: isolate;
  display: grid;
  gap: clamp(12px, 1.8vw, 18px);
  overflow: hidden;
  padding: clamp(16px, 2.4vw, 24px);
  border-radius: clamp(22px, 3vw, 30px);
}

.ff-faqMini::before {
  content: "";
  position: absolute;
  inset: 0;
  z-index: -1;
  pointer-events: none;
  background:
    radial-gradient(circle at 0% 0%, rgba(18, 124, 111, 0.09), transparent 18rem),
    radial-gradient(circle at 100% 0%, rgba(255, 122, 26, 0.075), transparent 18rem),
    linear-gradient(135deg, rgba(255, 255, 255, 0.95), rgba(255, 250, 242, 0.78));
}

.ff-faqMini__head {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: end;
  gap: clamp(10px, 2vw, 20px);
}

.ff-faqMini__head h2 {
  margin-top: 6px;
  font-size: clamp(1.45rem, 2.8vw, 2.45rem);
  letter-spacing: -0.058em;
  line-height: 0.98;
}

.ff-faqMini__head > p {
  max-width: 34ch;
  color: var(--ff-ink-muted, rgba(56, 42, 31, 0.72));
  font-size: 0.9rem;
  font-weight: 720;
  line-height: 1.45;
  text-align: right;
}

.ff-faqMini__list {
  display: grid;
  gap: 8px;
}

.ff-faqMiniItem {
  overflow: hidden;
  border: 1px solid rgba(72, 44, 25, 0.08);
  border-radius: 16px;
  background:
    linear-gradient(180deg, rgba(255,255,255,0.86), rgba(255,250,242,0.68));
  box-shadow:
    0 1px 0 rgba(255,255,255,0.78) inset,
    0 8px 20px rgba(55,36,20,0.038);
}

.ff-faqMiniItem summary {
  display: flex;
  min-height: 46px;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  cursor: pointer;
  list-style: none;
  color: var(--ff-ink-strong, #130d08);
  font-size: 0.92rem;
  font-weight: 920;
  letter-spacing: -0.024em;
  padding: 12px 14px;
}

.ff-faqMiniItem summary::-webkit-details-marker {
  display: none;
}

.ff-faqMiniItem summary::after {
  content: "+";
  display: inline-flex;
  inline-size: 24px;
  block-size: 24px;
  flex: 0 0 auto;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(72, 44, 25, 0.09);
  border-radius: 999px;
  background: rgba(255, 250, 242, 0.86);
  color: #a84310;
  font-size: 0.94rem;
  font-weight: 950;
  line-height: 1;
}

.ff-faqMiniItem[open] summary::after {
  content: "–";
}

.ff-faqMiniItem p {
  max-width: 78ch;
  margin: -2px 14px 14px;
  color: var(--ff-ink-muted, rgba(56, 42, 31, 0.74));
  font-size: 0.86rem;
  line-height: 1.55;
}

@media (max-width: 740px) {
  .ff-faqMini {
    padding: 15px;
    border-radius: 22px;
  }

  .ff-faqMini__head {
    grid-template-columns: 1fr;
    align-items: start;
  }

  .ff-faqMini__head > p {
    max-width: none;
    text-align: left;
  }

  .ff-faqMini__head h2 {
    font-size: clamp(1.35rem, 6.5vw, 1.95rem);
  }

  .ff-faqMiniItem summary {
    min-height: 44px;
    padding: 12px;
  }

  .ff-faqMiniItem p {
    margin-inline: 12px;
  }
}

:root[data-theme="dark"] .ff-faqMini::before,
[data-theme="dark"] .ff-faqMini::before {
  background:
    radial-gradient(circle at 0% 0%, rgba(18, 124, 111, 0.16), transparent 18rem),
    radial-gradient(circle at 100% 0%, rgba(255, 122, 26, 0.13), transparent 18rem),
    rgba(15, 23, 42, 0.76);
}

:root[data-theme="dark"] .ff-faqMiniItem,
[data-theme="dark"] .ff-faqMiniItem {
  border-color: rgba(255,255,255,0.12);
  background: rgba(15, 23, 42, 0.70);
}
'''

AUDIT_TEXT = r'''#!/usr/bin/env python3
"""Audit: FAQ renders as a bare-minimal donor confidence checkpoint."""

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
    print("\nFutureFunded minimal FAQ audit")
    print("=" * 72)

    css = read(ROOT / "apps/web/app/static/css/ff.css")

    for term in [
        "FutureFunded Minimal FAQ v2",
        ".ff-faqMini",
        ".ff-faqMini__list",
        ".ff-faqMiniItem",
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
        "Quick answers",
        "The essentials before you give.",
        "Simple answers for donors, parents, and sponsors.",
        "ff-faqMini",
        "Where does the money go?",
        "Is checkout secure?",
        "How do sponsors work?",
    ]

    for term in required:
        ok(f"minimal FAQ contains {term}") if term in faq else fail(f"minimal FAQ missing {term}")

    banned_in_faq = [
        "Trust center",
        "Give with clarity.",
        "ff-faqLive",
        "ff-faqLive__statusGrid",
        "ff-faqLiveDecision",
        "Secure checkout</strong>",
        "Receipt-ready",
        "Reviewed sponsors",
        "Still deciding?",
        "Share campaign",
        "Contact",
        "Can I share this with someone else?",
        "Donate now",
        "Sponsor next",
        "Become a sponsor",
        "data-ff-open-checkout",
        "data-ff-open-sponsor",
        "data-ff-donate-trigger",
        "data-ff-sponsor-trigger",
        "sponsor@futurefunded.com",
    ]

    for term in banned_in_faq:
        ok(f"minimal FAQ removed clutter: {term}") if term not in faq else fail(f"minimal FAQ still contains clutter: {term}")

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

    print("\n✅ MINIMAL FAQ AUDIT PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def backup(path: Path) -> None:
    if not path.exists():
        return
    stamp = time.strftime("%Y%m%d-%H%M%S")
    dst = path.with_suffix(path.suffix + f".bak-faq-mini-{stamp}")
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
        print("Minimal FAQ CSS already present.")
        return

    write(CSS, css.rstrip() + "\n\n" + CSS_PATCH.strip() + "\n")


def write_audits() -> None:
    write(AUDIT, AUDIT_TEXT)
    write(MINI_AUDIT, AUDIT_TEXT)
    AUDIT.chmod(0o755)
    MINI_AUDIT.chmod(0o755)


def main() -> int:
    print("\nFutureFunded refactor FAQ to bare minimum")
    print("=" * 72)

    for path in TEMPLATES:
        patch_template(path)

    patch_css()
    write_audits()

    print("\n✅ Bare-minimal FAQ refinement complete.")
    print("\nNext run:")
    print("  python scripts/final_faq_minimal_audit.py")
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
