#!/usr/bin/env python3
from __future__ import annotations

import re
import time
from pathlib import Path

ROOT = Path.cwd()
TPL = ROOT / "apps/web/app/templates/campaign/index.html"
CSS = ROOT / "apps/web/app/static/css/campaign.css"

MARKER = "hoi-6m-campaign-cta-compression-v1"

CSS_BLOCK = r'''

/* ==========================================================================
   FutureFunded HOI 6M — Campaign CTA Compression + Premium Hierarchy
   Marker: hoi-6m-campaign-cta-compression-v1

   Goal:
   - Make Give securely unmistakably dominant.
   - Keep sponsor/share paths available but secondary.
   - Reduce repeated visible CTA clusters.
   - Improve premium section rhythm without breaking hooks.
========================================================================== */

@layer campaign {
  .ff-campaignTrustLine {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.45rem;
    margin-top: 0.9rem;
  }

  .ff-campaignTrustLine span {
    min-height: 30px;
    padding: 0.42rem 0.68rem;
    display: inline-flex;
    align-items: center;
    border: 1px solid color-mix(in srgb, var(--ff-border, #d6c7b5) 70%, transparent);
    border-radius: 999px;
    background: color-mix(in srgb, var(--ff-surface, #fffaf3) 78%, transparent);
    color: color-mix(in srgb, var(--ff-ink, #201610) 66%, transparent);
    font-size: 0.76rem;
    font-weight: 900;
    letter-spacing: -0.01em;
    white-space: nowrap;
  }

  .ff-campaignTrustLine--hero {
    margin-top: 0.85rem;
  }

  .ff-donatePanel__proof {
    margin-top: 1rem;
    padding-top: 0.85rem;
    border-top: 1px solid color-mix(in srgb, var(--ff-border, #d6c7b5) 68%, transparent);
  }

  .ff-impactChip--static {
    cursor: default;
  }

  .ff-impactChip--static:hover {
    transform: none;
  }

  .ff-impactChip--static p {
    max-width: 26ch;
  }

  .ff-heroActions {
    align-items: stretch;
  }

  .ff-heroActions .ff-button--primary,
  .ff-donateSubmit,
  .ff-mobileDonateBar .ff-button--primary,
  .ffShellHeader--campaignPublic .ffShellHeader__action--primary {
    box-shadow:
      0 18px 44px rgba(255, 90, 31, 0.26),
      inset 0 1px 0 rgba(255, 255, 255, 0.18);
  }

  .ff-heroActions .ff-button--ghost,
  .ffShellHeader--campaignPublic .ffShellHeader__action--ghost {
    background: rgba(255, 255, 255, 0.72);
  }

  .ff-teamCard__actions .ff-button {
    width: 100%;
  }

  .ff-campaignFooter__actions {
    align-items: center;
  }

  @media (max-width: 760px) {
    .ff-heroActions {
      gap: 0.55rem;
    }

    .ff-heroActions .ff-button--primary {
      min-height: 52px;
      flex: 1 1 100%;
      font-size: 0.98rem;
    }

    .ff-heroActions .ff-button--ghost {
      min-height: 44px;
      flex: 1 1 100%;
      opacity: 0.88;
    }

    .ff-campaignTrustLine {
      gap: 0.38rem;
    }

    .ff-campaignTrustLine span {
      min-height: 28px;
      padding: 0.38rem 0.58rem;
      font-size: 0.71rem;
    }

    .ff-campaignTrustLine--hero span:nth-child(n + 3) {
      display: none;
    }

    .ff-donatePanel__proof span:nth-child(n + 3) {
      display: none;
    }

    .ff-impactChip--static {
      padding-block: 0.92rem;
    }

    .ff-campaignFooter__actions {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 0.55rem;
    }

    .ff-campaignFooter__actions .ff-button {
      width: 100%;
    }

    .ff-mobileDonateBar {
      isolation: isolate;
    }
  }

  @media (max-width: 480px) {
    .ff-heroActions .ff-button--ghost {
      font-size: 0.86rem;
    }

    .ff-campaignTrustLine {
      margin-top: 0.7rem;
    }
  }
}
'''

REPLACEMENTS = [
    (
        "hero secondary share/sponsor cluster",
        '''            <div class="ff-actions ff-actions--tight" aria-label="Secondary campaign actions">
              {{ share_button('Copy campaign link', 'ff-button ff-button--ghost') }}
              {{ sponsor_cta('View sponsor packages', 'ff-button ff-button--ghost', '#sponsors', 'Season Sponsor') }}
            </div>''',
        '''            <div class="ff-campaignTrustLine ff-campaignTrustLine--hero" aria-label="Campaign trust signals">
              <span>Secure checkout</span>
              <span>Sponsor-ready</span>
              <span>Share-ready season fund</span>
            </div>''',
    ),
    (
        "donation panel share/sponsor cluster",
        '''            <div class="ff-actions ff-actions--stack" aria-label="Share or sponsor this campaign">
              {{ share_button('Share campaign', 'ff-button ff-button--ghost ff-button--full', true) }}
              {{ sponsor_cta('Sponsor options', 'ff-button ff-button--ghost ff-button--full', '#sponsors', 'VIP Spotlight') }}
            </div>''',
        '''            <div class="ff-donatePanel__proof ff-campaignTrustLine" aria-label="Giving trust details">
              <span>Receipts by email</span>
              <span>Protected checkout</span>
              <span>Team verified</span>
            </div>''',
    ),
    (
        "impact section donate/sponsor cluster",
        '''              <div class="ff-actions">
                {{ donate_cta('Give securely', 'ff-button ff-button--primary', _donate_href) }}
                {{ sponsor_cta('Sponsor', 'ff-button ff-button--ghost', '#sponsors', 'Impact Sponsor') }}
              </div>''',
        '''              <div class="ff-campaignTrustLine ff-campaignTrustLine--impact" aria-label="Impact giving assurance">
                <span>Pick an amount above</span>
                <span>Every gift supports season costs</span>
              </div>''',
    ),
    (
        "team card donate/sponsor cluster",
        '''                    <div class="ff-actions ff-actions--stack">
                      <a class="ff-button ff-button--primary" href="{{ _donate_href }}" data-ff-open-checkout data-ff-donate-trigger data-ff-payment-trigger data-ff-team-support="{{ _team_label|e }}">{{ _team_cta }}</a>
                      {{ sponsor_cta('Claim team spotlight', 'ff-button ff-button--ghost', '#sponsor-form', _team_label ~ ' Team Sponsor') }}
                    </div>''',
        '''                    <div class="ff-actions ff-actions--stack ff-teamCard__actions">
                      <a class="ff-button ff-button--primary" href="{{ _donate_href }}" data-ff-open-checkout data-ff-donate-trigger data-ff-payment-trigger data-ff-team-support="{{ _team_label|e }}">{{ _team_cta }}</a>
                    </div>''',
    ),
    (
        "story donate/sponsor cluster",
        '''              <div class="ff-actions">
                {{ donate_cta('Support after watching', 'ff-button ff-button--primary', _donate_href) }}
                {{ sponsor_cta('Claim story spotlight', 'ff-button ff-button--ghost', '#sponsors', 'Story Video Sponsor') }}
              </div>''',
        '''              <div class="ff-campaignTrustLine ff-campaignTrustLine--story" aria-label="Story support assurance">
                <span>Give from the secure panel</span>
                <span>Sponsor recognition is reviewed</span>
              </div>''',
    ),
    (
        "footer actions top link",
        '''          {{ donate_cta('Support now', 'ff-button ff-button--primary', _donate_href) }}
          {{ share_button('Share', 'ff-button ff-button--ghost') }}
          <a class="ff-button ff-button--ghost" href="#campaign-hero">Top</a>''',
        '''          {{ donate_cta('Support now', 'ff-button ff-button--primary', _donate_href) }}
          {{ share_button('Share', 'ff-button ff-button--ghost') }}''',
    ),
]

IMPACT_BUTTON_PATTERN = re.compile(
    r'''                <button class="ff-impactChip"\s*
                        type="button"\s*
                        data-ff-checkout-amount="\{\{ _chip_amount \}\}"\s*
                        data-ff-amount-cents="\{\{ _chip_amount \* 100 \}\}"\s*
                        data-ff-open-checkout\s*
                        data-ff-donate-trigger\s*
                        data-ff-payment-trigger\s*
                        aria-label="Donate \{\{ chip\.get\('amount'\) \}\} for \{\{ chip\.get\('label'\) \}\}">\s*
                  <span>\{\{ chip\.get\('amount'\) \}\}</span>\s*
                  <strong>\{\{ chip\.get\('label'\) \}\}</strong>\s*
                  <p>\{\{ chip\.get\('copy'\)\|default\('Tap to donate this amount through secure checkout\.', true\) \}\}</p>\s*
                </button>''',
    re.MULTILINE,
)

IMPACT_ARTICLE = '''                <article class="ff-impactChip ff-impactChip--static" aria-label="{{ chip.get('amount') }} impact: {{ chip.get('label') }}">
                  <span>{{ chip.get('amount') }}</span>
                  <strong>{{ chip.get('label') }}</strong>
                  <p>{{ chip.get('copy')|default('Shows how this amount helps the season.', true) }}</p>
                </article>'''

def backup(path: Path) -> None:
    stamp = time.strftime("%Y%m%d%H%M%S")
    backup_path = path.with_suffix(path.suffix + f".bak-hoi6m-{stamp}")
    backup_path.write_text(path.read_text(errors="ignore"))
    print(f"Backup: {backup_path}")

def patch_template() -> None:
    if not TPL.exists():
        raise SystemExit(f"Missing campaign template: {TPL}")

    text = TPL.read_text(errors="ignore")
    original = text
    replaced = []

    for label, old, new in REPLACEMENTS:
        if old in text:
            text = text.replace(old, new, 1)
            replaced.append(label)
        else:
            print(f"WARNING: did not find block: {label}")

    text, impact_count = IMPACT_BUTTON_PATTERN.subn(IMPACT_ARTICLE, text)
    if impact_count:
        replaced.append(f"impact chips converted: {impact_count}")
    else:
        print("WARNING: impact chip button block not converted.")

    required_hooks = [
        "data-ff-open-checkout",
        "data-ff-donate-trigger",
        "data-ff-payment-trigger",
        "data-ff-open-sponsor",
        "data-ff-sponsor-trigger",
        "data-ff-share-trigger",
        "data-ff-qr-trigger",
        "data-ff-mobile-rail",
    ]

    missing = [hook for hook in required_hooks if hook not in text]
    if missing:
        raise SystemExit(f"Refusing to write; missing required hooks after patch: {missing}")

    if text != original:
        backup(TPL)
        TPL.write_text(text)
        print(f"Patched template: {TPL}")
        print("Replacements:")
        for item in replaced:
            print(f"  - {item}")
    else:
        print("Template unchanged.")

def patch_css() -> None:
    if not CSS.exists():
        raise SystemExit(f"Missing campaign CSS: {CSS}")

    text = CSS.read_text(errors="ignore")
    if MARKER in text:
        print("CSS already patched.")
        return

    backup(CSS)
    CSS.write_text(text.rstrip() + "\n" + CSS_BLOCK.strip() + "\n")
    print(f"Patched CSS: {CSS}")

patch_template()
patch_css()
print("HOI 6M campaign CTA compression patch complete.")
