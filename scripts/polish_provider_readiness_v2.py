#!/usr/bin/env python3
"""
FutureFunded Provider Readiness v2

Goal:
- Make provider readiness feel like a polished launch-control panel.
- PayPal missing => optional / not enabled, not scary.
- Mail missing => receipts and sponsor follow-up disabled until configured.
- Stripe/Public URL stay launch-critical.
- Keep this internal/operator-facing only.
- Preserve existing provider readiness audit contract while adding v2 checks.
"""

from __future__ import annotations

import shutil
import time
from pathlib import Path

ROOT = Path.cwd()

PARTIAL = ROOT / "apps/web/app/templates/platform/_provider_readiness_panel.html"
CSS = ROOT / "apps/web/app/static/css/ff.css"
AUDIT = ROOT / "scripts/final_provider_readiness_v2_audit.py"
OLD_AUDIT = ROOT / "scripts/final_provider_readiness_polish_audit.py"

CSS_MARKER = "FutureFunded Provider Readiness v2"

PARTIAL_TEXT = r'''{# FutureFunded Provider Readiness v2
   Internal/operator-facing launch control panel.
   Never render on public campaign pages.
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

{% set _launch_ready_count = 0 %}
{% if _stripe_ready %}{% set _launch_ready_count = _launch_ready_count + 1 %}{% endif %}
{% if _public_ready %}{% set _launch_ready_count = _launch_ready_count + 1 %}{% endif %}
{% set _ops_ready_count = _launch_ready_count %}
{% if _mail_ready %}{% set _ops_ready_count = _ops_ready_count + 1 %}{% endif %}
{% if _paypal_ready %}{% set _ops_ready_count = _ops_ready_count + 1 %}{% endif %}

<section class="ff-providerReadiness ff-providerReadiness--v2 ff-platformCard"
         data-ff-provider-readiness
         data-ff-provider-readiness-v2
         aria-labelledby="provider-readiness-title">
  <div class="ff-providerReadiness__head ff-providerReadinessV2__head">
    <div>
      <p class="ff-platformKicker">Launch controls</p>
      <h2 id="provider-readiness-title">Provider setup for a sellable fundraising OS.</h2>
      <p>
        Keep checkout, receipts, sponsor follow-up, and public links ready before campaigns go live.
        Optional providers stay clearly marked so operators know what is blocking launch and what is not.
      </p>
    </div>

    <div class="ff-providerReadiness__score ff-providerReadinessV2__score"
         aria-label="{{ _launch_ready_count }} of 2 launch-critical providers ready">
      <strong>{{ _launch_ready_count }}/2</strong>
      <span>launch-critical ready</span>
    </div>
  </div>

  <div class="ff-providerReadinessV2__summary" aria-label="Provider readiness summary">
    <article data-provider-summary-state="{{ 'ready' if _stripe_ready and _public_ready else 'needs_setup' }}">
      <strong>{{ 'Launch-ready' if _stripe_ready and _public_ready else 'Launch needs setup' }}</strong>
      <span>Stripe + public URL are the critical launch gate.</span>
    </article>

    <article data-provider-summary-state="{{ 'ready' if _mail_ready else 'optional' }}">
      <strong>{{ 'Receipts enabled' if _mail_ready else 'Receipts disabled' }}</strong>
      <span>{{ 'Email is configured for confirmations and follow-up.' if _mail_ready else 'Configure SMTP before relying on email receipts.' }}</span>
    </article>

    <article data-provider-summary-state="{{ 'ready' if _paypal_ready else 'optional' }}">
      <strong>{{ 'PayPal enabled' if _paypal_ready else 'PayPal optional' }}</strong>
      <span>{{ 'Alternative payment rail is configured.' if _paypal_ready else 'Not enabled until client credentials are added.' }}</span>
    </article>
  </div>

  <div class="ff-providerReadiness__grid ff-providerReadinessV2__grid" aria-label="Provider readiness checklist">
    <article class="ff-providerReadiness__item ff-providerReadinessV2__item"
             data-provider="stripe"
             data-provider-state="{{ 'ready' if _stripe_ready else 'needs_setup' }}">
      <span aria-hidden="true">{{ '✓' if _stripe_ready else '!' }}</span>
      <div>
        <strong>Stripe</strong>
        <p>{{ 'Donation checkout is ready. Keep webhook signing secret current.' if _stripe_ready else 'Required for card checkout. Add publishable key, secret key, and webhook secret.' }}</p>
        <small>{{ 'Next: verify webhook endpoint after deploy.' if _stripe_ready else 'Launch blocker until configured.' }}</small>
      </div>
    </article>

    <article class="ff-providerReadiness__item ff-providerReadinessV2__item"
             data-provider="paypal"
             data-provider-state="{{ 'ready' if _paypal_ready else 'optional' }}">
      <span aria-hidden="true">{{ '✓' if _paypal_ready else '○' }}</span>
      <div>
        <strong>PayPal</strong>
        <p>{{ 'PayPal is enabled as an additional payment option.' if _paypal_ready else 'Optional / not enabled. Stripe can carry launch without PayPal.' }}</p>
        <small>{{ 'Next: test order create + capture.' if _paypal_ready else 'Add PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET when ready.' }}</small>
      </div>
    </article>

    <article class="ff-providerReadiness__item ff-providerReadinessV2__item"
             data-provider="mail"
             data-provider-state="{{ 'ready' if _mail_ready else 'disabled' }}">
      <span aria-hidden="true">{{ '✓' if _mail_ready else '!' }}</span>
      <div>
        <strong>Email</strong>
        <p>{{ 'Receipts and sponsor follow-up are configured.' if _mail_ready else 'Receipts disabled until SMTP is configured.' }}</p>
        <small>{{ 'Next: send a test receipt before launch.' if _mail_ready else 'Add SMTP host, username, password, and default sender.' }}</small>
      </div>
    </article>

    <article class="ff-providerReadiness__item ff-providerReadinessV2__item"
             data-provider="public-url"
             data-provider-state="{{ 'ready' if _public_ready else 'needs_setup' }}">
      <span aria-hidden="true">{{ '✓' if _public_ready else '!' }}</span>
      <div>
        <strong>Public URL</strong>
        <p>{{ 'Production links and callbacks have a base URL.' if _public_ready else 'Required for share links, callbacks, and receipt URLs.' }}</p>
        <small>{{ 'Next: confirm canonical domain after deploy.' if _public_ready else 'Set PUBLIC_BASE_URL or FF_PUBLIC_BASE_URL.' }}</small>
      </div>
    </article>
  </div>

  <div class="ff-providerReadinessV2__actions" aria-label="Provider setup guidance">
    <article>
      <strong>Launch gate</strong>
      <p>Stripe and Public URL should be green before taking live campaign traffic.</p>
    </article>

    <article>
      <strong>Operator follow-up</strong>
      <p>Email can be configured after visual demo, but before relying on receipts or sponsor notifications.</p>
    </article>

    <article>
      <strong>Optional rails</strong>
      <p>PayPal is additive. Keep it disabled until credentials and capture flow are verified.</p>
    </article>
  </div>

  <div class="ff-providerReadiness__foot ff-providerReadinessV2__foot">
    <p>
      Operator-only launch controls. Public campaign pages stay donor-first and free of setup noise.
    </p>
  </div>
</section>
'''

CSS_PATCH = r'''
/* ==========================================================================
   FutureFunded Provider Readiness v2
   Launch-control polish: critical, optional, and disabled provider states.
   ========================================================================== */

.ff-providerReadiness--v2 {
  gap: clamp(14px, 2vw, 20px);
}

.ff-providerReadinessV2__head {
  align-items: center;
}

.ff-providerReadinessV2__score {
  min-width: 148px;
  text-align: center;
}

.ff-providerReadinessV2__score span {
  max-width: 12ch;
  text-align: center;
  line-height: 1.15;
}

.ff-providerReadinessV2__summary {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: clamp(9px, 1.4vw, 13px);
}

.ff-providerReadinessV2__summary article {
  position: relative;
  overflow: hidden;
  border: 1px solid rgba(72, 44, 25, 0.085);
  border-radius: 18px;
  background:
    linear-gradient(180deg, rgba(255,255,255,0.84), rgba(255,250,242,0.66));
  box-shadow:
    0 1px 0 rgba(255,255,255,0.82) inset,
    0 10px 24px rgba(55,36,20,0.045);
  padding: 13px 14px;
}

.ff-providerReadinessV2__summary article::after {
  content: "";
  position: absolute;
  inset: auto 12px 0;
  height: 2px;
  border-radius: 999px 999px 0 0;
  background: rgba(18, 124, 111, 0.44);
}

.ff-providerReadinessV2__summary article[data-provider-summary-state="needs_setup"]::after {
  background: rgba(243, 95, 22, 0.54);
}

.ff-providerReadinessV2__summary article[data-provider-summary-state="optional"]::after {
  background: rgba(99, 102, 241, 0.42);
}

.ff-providerReadinessV2__summary strong {
  display: block;
  color: var(--ff-ink-strong, #130d08);
  font-size: 0.94rem;
  font-weight: 950;
  letter-spacing: -0.025em;
}

.ff-providerReadinessV2__summary span {
  display: block;
  margin-top: 5px;
  color: var(--ff-ink-muted, rgba(56,42,31,0.72));
  font-size: 0.76rem;
  line-height: 1.45;
}

.ff-providerReadinessV2__item small {
  display: block;
  margin-top: 8px;
  color: var(--ff-ink-subtle, rgba(74,55,39,0.62));
  font-size: 0.72rem;
  font-weight: 820;
  line-height: 1.35;
}

.ff-providerReadiness__item[data-provider-state="optional"] > span {
  background: rgba(99, 102, 241, 0.12);
  color: #4f46e5;
}

.ff-providerReadiness__item[data-provider-state="disabled"] > span {
  background: rgba(243, 95, 22, 0.13);
  color: #a84310;
}

.ff-providerReadinessV2__actions {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: clamp(9px, 1.5vw, 13px);
  border-top: 1px solid rgba(72, 44, 25, 0.08);
  padding-top: clamp(12px, 1.8vw, 16px);
}

.ff-providerReadinessV2__actions article {
  border: 1px solid rgba(72, 44, 25, 0.075);
  border-radius: 16px;
  background: rgba(255,255,255,0.58);
  padding: 12px;
}

.ff-providerReadinessV2__actions strong {
  display: block;
  color: var(--ff-ink-strong, #130d08);
  font-size: 0.82rem;
  font-weight: 950;
  letter-spacing: -0.02em;
}

.ff-providerReadinessV2__actions p {
  margin-top: 5px;
  color: var(--ff-ink-muted, rgba(56,42,31,0.72));
  font-size: 0.74rem;
  line-height: 1.42;
}

@media (max-width: 960px) {
  .ff-providerReadinessV2__summary,
  .ff-providerReadinessV2__actions {
    grid-template-columns: 1fr;
  }
}

:root[data-theme="dark"] .ff-providerReadinessV2__summary article,
:root[data-theme="dark"] .ff-providerReadinessV2__actions article,
[data-theme="dark"] .ff-providerReadinessV2__summary article,
[data-theme="dark"] .ff-providerReadinessV2__actions article {
  border-color: rgba(255,255,255,0.12);
  background: rgba(15, 23, 42, 0.64);
}
'''

AUDIT_TEXT = r'''#!/usr/bin/env python3
"""Audit: Provider Readiness v2 renders actionable launch controls."""

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


def check_panel(html: str, surface: str) -> None:
    required = [
        "data-ff-provider-readiness",
        "data-ff-provider-readiness-v2",
        "Launch controls",
        "Provider setup for a sellable fundraising OS.",
        "launch-critical ready",
        "Launch gate",
        "Operator follow-up",
        "Optional rails",
        "Stripe",
        "PayPal",
        "Email",
        "Public URL",
        "Optional / not enabled",
        "Receipts disabled until SMTP is configured.",
        "Stripe can carry launch without PayPal.",
    ]

    for term in required:
        ok(f"{surface} provider v2 contains {term}") if term in html else fail(f"{surface} provider v2 missing {term}")


def main() -> int:
    print("\nFutureFunded Provider Readiness v2 audit")
    print("=" * 72)

    css = (ROOT / "apps/web/app/static/css/ff.css").read_text(encoding="utf-8", errors="ignore")
    for term in [
        "FutureFunded Provider Readiness v2",
        ".ff-providerReadiness--v2",
        ".ff-providerReadinessV2__summary",
        ".ff-providerReadinessV2__actions",
        'data-provider-state="optional"',
    ]:
        ok(f"CSS/source contains {term}") if term in css or term in (ROOT / "apps/web/app/templates/platform/_provider_readiness_panel.html").read_text(encoding="utf-8", errors="ignore") else fail(f"CSS/source missing {term}")

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
    check_panel(onboarding_html, "onboarding")

    op_token = token()
    if op_token:
        dashboard = client.get(f"/platform/dashboard?token={op_token}", follow_redirects=False)
        dashboard_html = dashboard.get_data(as_text=True)
        ok("/platform/dashboard token access loads") if dashboard.status_code == 200 else fail(f"/platform/dashboard HTTP {dashboard.status_code}")
        check_panel(dashboard_html, "dashboard")
    else:
        ok("operator token not available; dashboard provider v2 check skipped")

    campaign = client.get("/c/connect-atx-elite", follow_redirects=False)
    campaign_html = campaign.get_data(as_text=True)
    ok("/c/connect-atx-elite loads") if campaign.status_code == 200 else fail(f"/c/connect-atx-elite HTTP {campaign.status_code}")
    ok("public campaign does not render provider readiness v2") if "data-ff-provider-readiness-v2" not in campaign_html else fail("public campaign leaked provider readiness v2")

    print("\n" + "=" * 72)
    print(f"PASS: {len(PASS)}  FAIL: {len(FAIL)}")

    if FAIL:
        print("\nFailures:")
        for item in FAIL:
            print(f"❌ {item}")
        return 1

    print("\n✅ PROVIDER READINESS V2 AUDIT PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def backup(path: Path) -> None:
    if not path.exists():
        return
    stamp = time.strftime("%Y%m%d-%H%M%S")
    dst = path.with_suffix(path.suffix + f".bak-provider-v2-{stamp}")
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


def append_css() -> None:
    css = read(CSS)
    if CSS_MARKER in css:
        print("Provider Readiness v2 CSS already present.")
        return
    write(CSS, css.rstrip() + "\n\n" + CSS_PATCH.strip() + "\n")


def patch_old_audit() -> None:
    if not OLD_AUDIT.exists():
        print(f"Skipped missing old audit: {OLD_AUDIT}")
        return

    text = read(OLD_AUDIT)
    original = text

    for term in [
        "Launch controls",
        "Optional / not enabled",
        "Receipts disabled until SMTP is configured.",
        "launch-critical ready",
    ]:
        if term not in text:
            text = text.replace(
                '"Provider setup for a sellable fundraising OS.",',
                '"Provider setup for a sellable fundraising OS.",\n'
                f'        "{term}",',
                1,
            )

    if text != original:
        write(OLD_AUDIT, text)
    else:
        print(f"No old audit changes needed: {OLD_AUDIT}")


def main() -> int:
    print("\nFutureFunded polish Provider Readiness v2")
    print("=" * 72)

    write(PARTIAL, PARTIAL_TEXT)
    append_css()
    write(AUDIT, AUDIT_TEXT)
    AUDIT.chmod(0o755)
    patch_old_audit()

    print("\n✅ Provider Readiness v2 patch complete.")
    print("\nNext run:")
    print("  python scripts/final_provider_readiness_v2_audit.py")
    print("  python scripts/final_provider_readiness_polish_audit.py")
    print("  python scripts/final_white_label_identity_boundaries_audit.py")
    print("  python scripts/final_faq_minimal_audit.py")
    print("  python scripts/final_campaign_momentum_visual_audit.py")
    print("  python scripts/final_sponsor_package_behavior_audit.py")
    print("  python scripts/final_campaign_profile_audit.py")
    print("  python scripts/final_platform_smoke.py")
    print("  python scripts/final_funnel_functional_audit.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
