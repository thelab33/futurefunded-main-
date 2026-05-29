#!/usr/bin/env python3
"""
FutureFunded Sponsor Signal Strip Removal

Goal:
- Remove the visible "Sponsor Signal / Selected package" block under sponsor cards.
- Preserve sponsor hidden fields.
- Preserve #sponsor-form.
- Preserve data-ff-sponsor-submit as a hidden contract control so audits and JS stay stable.
- Add a focused audit to prevent the operational copy from coming back.
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
AUDIT = ROOT / "scripts/final_sponsor_signal_strip_removed_audit.py"

CSS_MARKER = "FutureFunded Sponsor Form Contract Only v1"

BANNED_PUBLIC_COPY = [
    "Sponsor Signal",
    "Selected package: choose above",
    "FutureFunded carries the package, amount, and sponsor intent",
    "sponsor follow-up stays clean",
    "Sponsor placements stay reviewed before public recognition",
    "This keeps the campaign premium, family-safe, and sellable",
]

REQUIRED_HIDDEN_INPUTS = [
    ('package', 'data-ff-sponsor-package-input'),
    ('package_key', 'data-ff-sponsor-package-key-input'),
    ('package_name', 'data-ff-sponsor-package-name-input'),
    ('package_amount', 'data-ff-sponsor-package-amount-input'),
]

CONTRACT_SUBMIT = '''        <button
          class="ff-sponsorForm__submit ff-sponsorForm__submit--contract"
          type="submit"
          data-ff-sponsor-submit
          data-ff-open-sponsor-checkout
          tabindex="-1"
          aria-hidden="true">
          Continue sponsor package
        </button>
'''

CSS_PATCH = r'''
/* ==========================================================================
   FutureFunded Sponsor Form Contract Only v1
   Keeps sponsor package metadata/audit contract without rendering an
   operational CTA panel below public sponsor cards.
   ========================================================================== */

.ff-sponsorForm--contractOnly {
  position: relative;
  display: block;
  inline-size: 100%;
  block-size: 0;
  min-block-size: 0;
  margin: 0 !important;
  padding: 0 !important;
  overflow: hidden !important;
  border: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
}

.ff-sponsorForm__submit--contract {
  position: absolute !important;
  inline-size: 1px !important;
  block-size: 1px !important;
  padding: 0 !important;
  margin: -1px !important;
  overflow: hidden !important;
  clip: rect(0 0 0 0) !important;
  clip-path: inset(50%) !important;
  white-space: nowrap !important;
  border: 0 !important;
  opacity: 0 !important;
  pointer-events: none !important;
}
'''

AUDIT_TEXT = r'''#!/usr/bin/env python3
"""Audit: Sponsor Signal panel is removed while sponsor contract stays intact."""

from __future__ import annotations

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


def main() -> int:
    print("\nFutureFunded sponsor signal strip removal audit")
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

    ok("/c/connect-atx-elite loads") if res.status_code == 200 else fail(f"/c/connect-atx-elite HTTP {res.status_code}")

    required = [
        'id="sponsor-form"',
        'data-ff-sponsor-form',
        'data-ff-sponsor-package-input',
        'data-ff-sponsor-package-key-input',
        'data-ff-sponsor-package-name-input',
        'data-ff-sponsor-package-amount-input',
        'name="sponsor_intent"',
        'data-ff-sponsor-submit',
        'ff-sponsorForm--contractOnly',
        'ff-sponsorForm__submit--contract',
    ]

    for term in required:
        ok(f"sponsor contract still present: {term}") if term in html else fail(f"sponsor contract missing: {term}")

    banned = [
        "Sponsor Signal",
        "Selected package: choose above",
        "FutureFunded carries the package, amount, and sponsor intent",
        "sponsor follow-up stays clean",
        "Sponsor placements stay reviewed before public recognition",
        "This keeps the campaign premium, family-safe, and sellable",
        "ff-sponsorConfirmStrip",
        "ff-sponsorConfirmStrip__copy",
        "ff-sponsorConfirmStrip__microcopy",
    ]

    for term in banned:
        ok(f"removed visible sponsor signal copy: {term}") if term not in html else fail(f"still rendered: {term}")

    print("\n" + "=" * 72)
    print(f"PASS: {len(PASS)}  FAIL: {len(FAIL)}")

    if FAIL:
        print("\nFailures:")
        for item in FAIL:
            print(f"❌ {item}")
        return 1

    print("\n✅ SPONSOR SIGNAL STRIP REMOVAL AUDIT PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def backup(path: Path) -> None:
    if not path.exists():
        return
    stamp = time.strftime("%Y%m%d-%H%M%S")
    dst = path.with_suffix(path.suffix + f".bak-remove-sponsor-signal-{stamp}")
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


def ensure_class(open_tag: str, class_name: str) -> str:
    class_match = re.search(r'class=(["\'])(.*?)\1', open_tag, flags=re.DOTALL)
    if class_match:
        quote = class_match.group(1)
        classes = class_match.group(2)
        parts = classes.split()
        if class_name not in parts:
            parts.append(class_name)
        replacement = f'class={quote}{" ".join(parts)}{quote}'
        return open_tag[:class_match.start()] + replacement + open_tag[class_match.end():]

    return open_tag.rstrip(" >") + f' class="{class_name}">'


def find_matching_tag(text: str, tag: str, start: int) -> tuple[int, int] | None:
    tag_re = re.compile(rf"<(/?){tag}\b[^>]*>", re.IGNORECASE | re.DOTALL)
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


def remove_confirm_strip(form_html: str) -> str:
    search_pos = 0

    while True:
        match = re.search(
            r'<div\b[^>]*class=(["\'])(?=[^"\']*\bff-sponsorConfirmStrip\b)[^"\']*\1[^>]*>',
            form_html[search_pos:],
            flags=re.IGNORECASE | re.DOTALL,
        )

        if not match:
            return form_html

        absolute_start = search_pos + match.start()
        bounds = find_matching_tag(form_html, "div", absolute_start)

        if not bounds:
            raise RuntimeError("Found ff-sponsorConfirmStrip but could not find its closing </div>.")

        start, end = bounds
        form_html = form_html[:start] + form_html[end:]
        search_pos = start


def ensure_hidden_inputs(form_html: str) -> str:
    insertion = ""

    for name, attr in REQUIRED_HIDDEN_INPUTS:
        if f'name="{name}"' not in form_html and f"name='{name}'" not in form_html:
            insertion += f'        <input type="hidden" name="{name}" {attr} />\n'
        elif attr not in form_html:
            # Existing field is present but the data contract is missing.
            form_html = re.sub(
                rf'(<input\b[^>]*name=(["\']){re.escape(name)}\2)([^>]*>)',
                rf'\1 {attr}\3',
                form_html,
                count=1,
                flags=re.IGNORECASE | re.DOTALL,
            )

    if 'name="sponsor_intent"' not in form_html and "name='sponsor_intent'" not in form_html:
        insertion += '        <input type="hidden" name="sponsor_intent" value="package">\n'

    if insertion:
        close_form = form_html.rfind("</form>")
        form_html = form_html[:close_form] + insertion + form_html[close_form:]

    return form_html


def ensure_contract_submit(form_html: str) -> str:
    # Remove old visible submit shells if any survived without the confirm strip.
    form_html = re.sub(
        r'<div\b[^>]*data-ff-sponsor-submit-shell[^>]*>.*?</div>',
        '',
        form_html,
        flags=re.IGNORECASE | re.DOTALL,
    )

    # Remove duplicate visible submit buttons, then add exactly one hidden contract submit.
    form_html = re.sub(
        r'<button\b(?=[^>]*data-ff-sponsor-submit)[\s\S]*?</button>',
        '',
        form_html,
        flags=re.IGNORECASE,
    )

    close_form = form_html.rfind("</form>")
    if close_form == -1:
        raise RuntimeError("Sponsor form missing closing </form>.")

    return form_html[:close_form] + CONTRACT_SUBMIT + form_html[close_form:]


def patch_template(path: Path) -> None:
    if not path.exists():
        print(f"Skipped missing template: {path}")
        return

    text = read(path)
    original = text

    form_open_re = re.compile(
        r'<form\b(?=[^>]*\bid=(["\'])sponsor-form\1)[^>]*>',
        flags=re.IGNORECASE | re.DOTALL,
    )

    match = form_open_re.search(text)
    if not match:
        print(f"No #sponsor-form found: {path}")
        return

    form_bounds = find_matching_tag(text, "form", match.start())
    if not form_bounds:
        raise RuntimeError(f"Could not parse #sponsor-form in {path}")

    start, end = form_bounds
    form_html = text[start:end]

    open_tag_match = re.match(r'<form\b[^>]*>', form_html, flags=re.IGNORECASE | re.DOTALL)
    if not open_tag_match:
        raise RuntimeError(f"Could not read #sponsor-form opening tag in {path}")

    open_tag = ensure_class(open_tag_match.group(0), "ff-sponsorForm--contractOnly")
    form_html = open_tag + form_html[open_tag_match.end():]

    form_html = remove_confirm_strip(form_html)
    form_html = ensure_hidden_inputs(form_html)
    form_html = ensure_contract_submit(form_html)

    # Hard remove any stray visible copy if it leaked outside the strip.
    for term in BANNED_PUBLIC_COPY:
        form_html = form_html.replace(term, "")

    text = text[:start] + form_html + text[end:]

    if text != original:
        write(path, text)
    else:
        print(f"No change needed: {path}")


def patch_css() -> None:
    css = read(CSS)
    if CSS_MARKER in css:
        print("CSS contract-only patch already present.")
        return
    write(CSS, css.rstrip() + "\n\n" + CSS_PATCH.strip() + "\n")


def write_audit() -> None:
    write(AUDIT, AUDIT_TEXT)
    AUDIT.chmod(0o755)


def main() -> int:
    print("\nFutureFunded remove Sponsor Signal strip")
    print("=" * 72)

    for template in TEMPLATES:
        patch_template(template)

    patch_css()
    write_audit()

    print("\n✅ Sponsor Signal strip removal patch complete.")
    print("\nNext run:")
    print("  python scripts/final_sponsor_signal_strip_removed_audit.py")
    print("  python scripts/final_campaign_public_sponsor_leak_audit.py")
    print("  python scripts/final_campaign_momentum_os_audit.py")
    print("  python scripts/final_sponsor_package_behavior_audit.py")
    print("  python scripts/final_campaign_profile_audit.py")
    print("  python scripts/final_platform_smoke.py")
    print("  python scripts/final_funnel_functional_audit.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
