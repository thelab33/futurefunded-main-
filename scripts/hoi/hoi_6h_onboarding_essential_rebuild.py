#!/usr/bin/env python3
from __future__ import annotations

import time
from pathlib import Path

ROOT = Path.cwd()
TPL = ROOT / "apps/web/app/templates/platform/onboarding.html"
CSS = ROOT / "apps/web/app/static/css/ff.css"

CSS_MARKER = "hoi-6h-essential-onboarding-brand-kit-v1"

TEMPLATE = r'''<!doctype html>
<html lang="en" data-ff-theme="light" data-theme="light">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
  <title>Launch workspace · FutureFunded</title>
  <meta name="description" content="Set up a trusted fundraising campaign with campaign basics, brand colors, giving readiness, sponsor packages, and launch checks.">
  <link rel="stylesheet" href="{{ url_for('static', filename='css/ff.css') }}?v={{ asset_v|default('dev', true) }}">
</head>

<body class="ff-page ff-onboarding-page ffOnboardV2Body">
  <div
    class="ffOnboardV2"
    data-ff-onboard-root
    data-ff-page-root
    data-ff-surface="onboarding"
  >
    <header class="ffOnboardV2__topbar" data-ff-header>
      <a class="ffOnboardV2__brand" href="/platform/" aria-label="FutureFunded platform home">
        <span class="ffOnboardV2__logo" aria-hidden="true">FF</span>
        <span>
          <strong>FutureFunded</strong>
          <small>Launch workspace</small>
        </span>
      </a>

      <nav class="ffOnboardV2__nav" aria-label="Onboarding navigation">
        <a href="/platform/">Platform</a>
        <a href="/c/connect-atx-elite">Preview</a>
        <a href="/platform/dashboard">Dashboard</a>
      </nav>
    </header>

    <main class="ffOnboardV2__main">
      <section class="ffOnboardV2__hero" aria-labelledby="launch-title">
        <div class="ffOnboardV2__heroCopy">
          <div class="ffOnboardV2__pills" aria-label="Launch workspace status">
            <span>Private setup</span>
            <span>Brand-ready</span>
            <span>Review first</span>
          </div>

          <p class="ffOnboardV2__eyebrow">Launch command workspace</p>
          <h1 id="launch-title">Build the campaign before it goes public.</h1>
          <p class="ffOnboardV2__lede">
            Set the story, goal, brand colors, sponsor packages, and giving readiness in one private workspace.
          </p>

          <div class="ffOnboardV2__actions">
            <a class="ffOnboardV2__btn ffOnboardV2__btn--primary" href="#campaign-basics">
              Start setup
            </a>
            <a class="ffOnboardV2__btn ffOnboardV2__btn--ghost" href="/c/connect-atx-elite">
              Preview campaign
            </a>
          </div>
        </div>

        <aside class="ffOnboardV2__readiness" aria-label="Launch readiness">
          <div class="ffOnboardV2__readinessHead">
            <strong>Launch readiness</strong>
            <span>94%</span>
          </div>

          <div class="ffOnboardV2__meter" aria-hidden="true">
            <span style="width:94%"></span>
          </div>

          <dl>
            <div>
              <dt>Story</dt>
              <dd>Draft ready</dd>
            </div>
            <div>
              <dt>Brand kit</dt>
              <dd>Choose colors</dd>
            </div>
            <div>
              <dt>Sponsors</dt>
              <dd>Review packages</dd>
            </div>
            <div>
              <dt>Giving</dt>
              <dd>Verify provider</dd>
            </div>
          </dl>
        </aside>
      </section>

      <section class="ffOnboardV2__steps" aria-label="Essential setup steps">
        <article>
          <span>01</span>
          <strong>Campaign basics</strong>
          <p>Name, goal, audience, use of funds, and public summary.</p>
        </article>
        <article>
          <span>02</span>
          <strong>Brand kit</strong>
          <p>Team/school colors, logo direction, and public-page preview.</p>
        </article>
        <article>
          <span>03</span>
          <strong>Sponsor packages</strong>
          <p>Recognition tiers, sponsor benefits, and approval rules.</p>
        </article>
        <article>
          <span>04</span>
          <strong>Launch checks</strong>
          <p>Payment readiness, share links, and final operator handoff.</p>
        </article>
      </section>

      <section class="ffOnboardV2__section" id="campaign-basics" aria-labelledby="basics-title">
        <div class="ffOnboardV2__sectionHead">
          <p class="ffOnboardV2__eyebrow">Campaign essentials</p>
          <h2 id="basics-title">Only the details donors need.</h2>
          <p>Keep the public page focused: who it helps, what the money covers, and how people can give.</p>
        </div>

        <div class="ffOnboardV2__formGrid">
          <label>
            <span>Campaign name</span>
            <input name="campaign_name" value="Spring Fundraiser" autocomplete="organization-title">
          </label>

          <label>
            <span>Fundraising goal</span>
            <input name="fundraising_goal" value="$20,000" inputmode="numeric">
          </label>

          <label>
            <span>Location</span>
            <input name="location" value="Austin, TX" autocomplete="address-level2">
          </label>

          <label>
            <span>Audience</span>
            <input name="audience" value="Families, alumni, local businesses">
          </label>

          <label class="ffOnboardV2__wide">
            <span>Use of funds</span>
            <textarea name="use_of_funds" rows="4">Travel, training, tournament fees, equipment, meals, scholarships, and gym time.</textarea>
          </label>

          <label class="ffOnboardV2__wide">
            <span>Public summary</span>
            <textarea name="public_summary" rows="4">Choose a giving amount or sponsor package to help the team finish the season strong.</textarea>
          </label>
        </div>
      </section>

      <section class="ffOnboardV2__section ffOnboardV2__brandKit" aria-labelledby="brand-title">
        <div class="ffOnboardV2__sectionHead">
          <p class="ffOnboardV2__eyebrow">Brand kit</p>
          <h2 id="brand-title">Make it match the team.</h2>
          <p>Pick a theme for schools, clubs, teams, and nonprofits. This is the white-label control center.</p>
        </div>

        <div class="ffOnboardV2__brandGrid">
          <div class="ffOnboardV2__themeControls" data-ff-theme-picker>
            <div class="ffOnboardV2__presetRow" aria-label="Theme presets">
              <button type="button" data-ff-theme-preset data-primary="#ff5a1f" data-accent="#0f766e" data-soft="#fff3e7">
                Elite orange
              </button>
              <button type="button" data-ff-theme-preset data-primary="#1d4ed8" data-accent="#f59e0b" data-soft="#eff6ff">
                School blue
              </button>
              <button type="button" data-ff-theme-preset data-primary="#047857" data-accent="#111827" data-soft="#ecfdf5">
                Club green
              </button>
              <button type="button" data-ff-theme-preset data-primary="#7c3aed" data-accent="#db2777" data-soft="#f5f3ff">
                Nonprofit violet
              </button>
            </div>

            <div class="ffOnboardV2__colorGrid">
              <label>
                <span>Primary color</span>
                <input type="color" name="brand_primary" value="#ff5a1f" data-ff-color-primary>
              </label>

              <label>
                <span>Accent color</span>
                <input type="color" name="brand_accent" value="#0f766e" data-ff-color-accent>
              </label>

              <label>
                <span>Soft background</span>
                <input type="color" name="brand_soft" value="#fff3e7" data-ff-color-soft>
              </label>
            </div>

            <label>
              <span>Logo / mark direction</span>
              <input name="brand_logo_note" value="Use team logo on campaign header and sponsor cards.">
            </label>
          </div>

          <aside class="ffOnboardV2__themePreview" data-ff-theme-preview aria-label="Theme preview">
            <div class="ffOnboardV2__previewTop">
              <span class="ffOnboardV2__previewLogo">FF</span>
              <span>
                <strong>Connect ATX Elite</strong>
                <small>Live season fund</small>
              </span>
            </div>

            <h3>Fuel the season. Fund the future.</h3>
            <p>Preview how team colors shape buttons, progress, badges, and sponsor recognition.</p>

            <div class="ffOnboardV2__previewMeter">
              <span></span>
            </div>

            <button type="button">Give securely</button>
          </aside>
        </div>
      </section>

      <section class="ffOnboardV2__section" aria-labelledby="giving-title">
        <div class="ffOnboardV2__sectionHead">
          <p class="ffOnboardV2__eyebrow">Giving readiness</p>
          <h2 id="giving-title">Verify the provider. Keep public options clean.</h2>
          <p>Onboarding should only confirm the payment lane. Public Text-to-Donate appears on the campaign page only after it is complete and enabled.</p>
        </div>

        <div class="ffOnboardV2__formGrid">
          <label>
            <span>Payment provider</span>
            <select name="payment_provider">
              <option selected>Stripe + PayPal</option>
              <option>Stripe only</option>
              <option>External giving link</option>
              <option>Not ready yet</option>
            </select>
          </label>

          <label>
            <span>Fallback giving URL</span>
            <input name="fallback_giving_url" value="https://getfuturefunded.com/c/connect-atx-elite">
          </label>

          <div class="ffOnboardV2__notice ffOnboardV2__wide">
            <strong>Text-to-Donate belongs on the public campaign only when ready.</strong>
            <p>Do not expose SMS number, keyword, or provider setup here as public launch content. Use dashboard settings later for advanced giving channels.</p>
          </div>
        </div>
      </section>

      <section class="ffOnboardV2__section" aria-labelledby="sponsor-title">
        <div class="ffOnboardV2__sectionHead">
          <p class="ffOnboardV2__eyebrow">Sponsor packages</p>
          <h2 id="sponsor-title">Recognition, ready for review.</h2>
          <p>Keep sponsorship simple enough for a local business to understand in under a minute.</p>
        </div>

        <div class="ffOnboardV2__packageGrid">
          <article>
            <span>Community</span>
            <strong>$300</strong>
            <p>Family and local business recognition.</p>
            <ul>
              <li>Campaign sponsor listing</li>
              <li>Thank-you mention</li>
              <li>Optional website link</li>
            </ul>
          </article>

          <article>
            <span>Featured</span>
            <strong>$750</strong>
            <p>Elevated placement on the campaign page.</p>
            <ul>
              <li>Featured sponsor card</li>
              <li>Logo or business name</li>
              <li>Recognition path included</li>
            </ul>
          </article>

          <article>
            <span>Season</span>
            <strong>$1,500</strong>
            <p>Premium sponsor presence for the full run.</p>
            <ul>
              <li>Top sponsor placement</li>
              <li>Season-long recognition</li>
              <li>Stronger sponsor proof</li>
            </ul>
          </article>
        </div>
      </section>

      <section class="ffOnboardV2__handoff" aria-labelledby="handoff-title">
        <div>
          <p class="ffOnboardV2__eyebrow">Launch handoff</p>
          <h2 id="handoff-title">Ready when the essentials align.</h2>
          <p>Preview the campaign, confirm sponsor packages, verify giving readiness, then hand off to the operator dashboard.</p>
        </div>

        <div class="ffOnboardV2__handoffActions">
          <button type="button" class="ffOnboardV2__btn ffOnboardV2__btn--primary" data-ff-save-onboarding>
            Save launch setup
          </button>
          <a class="ffOnboardV2__btn ffOnboardV2__btn--ghost" href="/c/connect-atx-elite">
            Review campaign
          </a>
          <a class="ffOnboardV2__btn ffOnboardV2__btn--ghost" href="/platform/dashboard">
            Open dashboard
          </a>
        </div>

        <p class="ffOnboardV2__saveNote" data-ff-save-note role="status" aria-live="polite">
          Private launch workspace. Public campaign stays clean until review.
        </p>
      </section>
    </main>
  </div>

  <script>
    (() => {
      const root = document.querySelector("[data-ff-onboard-root]");
      const preview = document.querySelector("[data-ff-theme-preview]");
      const primary = document.querySelector("[data-ff-color-primary]");
      const accent = document.querySelector("[data-ff-color-accent]");
      const soft = document.querySelector("[data-ff-color-soft]");
      const save = document.querySelector("[data-ff-save-onboarding]");
      const note = document.querySelector("[data-ff-save-note]");

      const apply = () => {
        if (!root || !preview || !primary || !accent || !soft) return;
        root.style.setProperty("--onboard-primary", primary.value);
        root.style.setProperty("--onboard-accent", accent.value);
        root.style.setProperty("--onboard-soft", soft.value);
      };

      document.querySelectorAll("[data-ff-theme-preset]").forEach((button) => {
        button.addEventListener("click", () => {
          if (primary) primary.value = button.dataset.primary || primary.value;
          if (accent) accent.value = button.dataset.accent || accent.value;
          if (soft) soft.value = button.dataset.soft || soft.value;
          apply();
        });
      });

      [primary, accent, soft].forEach((input) => {
        if (input) input.addEventListener("input", apply);
      });

      if (save) {
        save.addEventListener("click", () => {
          const payload = {
            primary: primary?.value,
            accent: accent?.value,
            soft: soft?.value,
            savedAt: new Date().toISOString()
          };

          try {
            window.localStorage.setItem("futurefunded:onboarding-brand-kit", JSON.stringify(payload));
          } catch (_) {}

          if (note) {
            note.textContent = "Launch setup saved locally. Review the campaign before sharing.";
          }
        });
      }

      apply();
    })();
  </script>
</body>
</html>
'''

CSS_BLOCK = r'''

/* ==========================================================================
   FutureFunded HOI 6H — Essential Onboarding + Brand Kit
   Marker: hoi-6h-essential-onboarding-brand-kit-v1
========================================================================== */

@layer platform, components, utilities {
  .ffOnboardV2,
  .ffOnboardV2 * {
    box-sizing: border-box;
  }

  .ffOnboardV2 {
    --onboard-primary: #ff5a1f;
    --onboard-accent: #0f766e;
    --onboard-soft: #fff3e7;
    min-height: 100svh;
    color: #160f0b;
    background:
      radial-gradient(circle at 8% 0%, rgba(255, 122, 48, 0.12), transparent 30rem),
      radial-gradient(circle at 92% 0%, rgba(15, 118, 110, 0.12), transparent 30rem),
      linear-gradient(180deg, #f6efe2 0%, #e8dcc9 100%);
    font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    letter-spacing: -0.015em;
    text-rendering: geometricPrecision;
    -webkit-font-smoothing: antialiased;
  }

  .ffOnboardV2__topbar {
    width: min(1180px, calc(100% - 2rem));
    margin: 1rem auto 0;
    min-height: 58px;
    padding: 0.55rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    border: 1px solid rgba(148, 163, 184, 0.2);
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.72);
    box-shadow: 0 18px 60px rgba(15, 23, 42, 0.08);
    backdrop-filter: blur(18px);
  }

  .ffOnboardV2__brand,
  .ffOnboardV2__nav {
    display: flex;
    align-items: center;
  }

  .ffOnboardV2__brand {
    min-width: 0;
    gap: 0.7rem;
    color: inherit;
    text-decoration: none;
  }

  .ffOnboardV2__brand strong {
    display: block;
    font-size: 0.96rem;
    line-height: 1;
    letter-spacing: -0.035em;
  }

  .ffOnboardV2__brand small {
    display: block;
    margin-top: 0.18rem;
    color: rgba(22, 15, 11, 0.56);
    font-size: 0.68rem;
    font-weight: 900;
    letter-spacing: 0.16em;
    text-transform: uppercase;
  }

  .ffOnboardV2__logo,
  .ffOnboardV2__previewLogo {
    width: 40px;
    height: 40px;
    flex: 0 0 auto;
    display: grid;
    place-items: center;
    border-radius: 14px;
    color: #fff;
    background: #3b2418;
    font-weight: 950;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.2);
  }

  .ffOnboardV2__nav {
    gap: 0.25rem;
  }

  .ffOnboardV2__nav a {
    min-height: 38px;
    padding: 0.7rem 0.95rem;
    display: inline-flex;
    align-items: center;
    border-radius: 999px;
    color: rgba(22, 15, 11, 0.72);
    text-decoration: none;
    font-size: 0.85rem;
    font-weight: 850;
  }

  .ffOnboardV2__nav a:hover,
  .ffOnboardV2__nav a:focus-visible {
    background: rgba(255,255,255,0.75);
    color: #160f0b;
  }

  .ffOnboardV2__main {
    width: min(1180px, calc(100% - 2rem));
    margin: 1rem auto 0;
    padding-bottom: 3rem;
  }

  .ffOnboardV2__hero,
  .ffOnboardV2__section,
  .ffOnboardV2__handoff {
    border: 1px solid rgba(148, 163, 184, 0.2);
    border-radius: clamp(26px, 4vw, 42px);
    background:
      radial-gradient(circle at 88% 0%, color-mix(in srgb, var(--onboard-primary) 24%, transparent), transparent 28rem),
      linear-gradient(135deg, rgba(255,255,255,0.78), rgba(255,255,255,0.58));
    box-shadow: 0 24px 80px rgba(15, 23, 42, 0.1);
  }

  .ffOnboardV2__hero {
    min-height: 440px;
    padding: clamp(1.4rem, 4vw, 3.5rem);
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(280px, 360px);
    gap: clamp(1.2rem, 4vw, 3.5rem);
    align-items: center;
  }

  .ffOnboardV2__pills,
  .ffOnboardV2__actions,
  .ffOnboardV2__presetRow,
  .ffOnboardV2__handoffActions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.55rem;
    align-items: center;
  }

  .ffOnboardV2__pills span,
  .ffOnboardV2__themeControls button,
  .ffOnboardV2__readiness dd {
    min-height: 30px;
    padding: 0.42rem 0.78rem;
    display: inline-flex;
    align-items: center;
    border: 1px solid rgba(148, 163, 184, 0.22);
    border-radius: 999px;
    background: rgba(255,255,255,0.72);
    color: rgba(22, 15, 11, 0.68);
    font-size: 0.78rem;
    font-weight: 900;
    letter-spacing: 0.1em;
  }

  .ffOnboardV2__eyebrow {
    margin: 1.25rem 0 0.8rem;
    color: #a94319;
    font-size: 0.78rem;
    font-weight: 950;
    letter-spacing: 0.18em;
    text-transform: uppercase;
  }

  .ffOnboardV2 h1,
  .ffOnboardV2 h2,
  .ffOnboardV2 h3,
  .ffOnboardV2 p {
    margin: 0;
  }

  .ffOnboardV2 h1 {
    max-width: 11.5ch;
    font-size: clamp(2.35rem, 6vw, 5.25rem);
    line-height: 0.92;
    letter-spacing: -0.068em;
    text-wrap: balance;
  }

  .ffOnboardV2 h2 {
    max-width: 12.5ch;
    font-size: clamp(1.7rem, 3.6vw, 3rem);
    line-height: 0.98;
    letter-spacing: -0.055em;
    text-wrap: balance;
  }

  .ffOnboardV2 h3 {
    font-size: clamp(1.15rem, 1.4vw, 1.45rem);
    line-height: 1.05;
    letter-spacing: -0.035em;
  }

  .ffOnboardV2__lede,
  .ffOnboardV2__sectionHead > p:last-child,
  .ffOnboardV2__handoff p {
    max-width: 62ch;
    margin-top: 0.8rem;
    color: rgba(22, 15, 11, 0.66);
    font-size: clamp(1rem, 0.65vw + 0.92rem, 1.16rem);
    line-height: 1.48;
  }

  .ffOnboardV2__actions {
    margin-top: 1.2rem;
  }

  .ffOnboardV2__btn,
  .ffOnboardV2 button,
  .ffOnboardV2 input,
  .ffOnboardV2 select,
  .ffOnboardV2 textarea {
    font: inherit;
  }

  .ffOnboardV2__btn,
  .ffOnboardV2__themeControls button,
  .ffOnboardV2__handoffActions button {
    min-height: 44px;
    padding: 0.8rem 1.1rem;
    border: 0;
    border-radius: 999px;
    cursor: pointer;
    text-decoration: none;
    font-size: 0.88rem;
    font-weight: 950;
  }

  .ffOnboardV2__btn--primary,
  .ffOnboardV2__handoffActions button,
  .ffOnboardV2__themePreview button {
    color: #fff;
    background: linear-gradient(135deg, var(--onboard-primary), #ff7a35);
    box-shadow: 0 16px 42px color-mix(in srgb, var(--onboard-primary) 28%, transparent);
  }

  .ffOnboardV2__btn--ghost {
    color: #160f0b;
    background: rgba(255,255,255,0.76);
  }

  .ffOnboardV2__readiness,
  .ffOnboardV2__themePreview {
    padding: 1.2rem;
    border: 1px solid rgba(148, 163, 184, 0.2);
    border-radius: 28px;
    background: rgba(255,255,255,0.72);
    box-shadow: 0 18px 50px rgba(15, 23, 42, 0.08);
  }

  .ffOnboardV2__readinessHead,
  .ffOnboardV2__previewTop {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
  }

  .ffOnboardV2__readinessHead strong {
    color: rgba(22, 15, 11, 0.58);
    font-size: 0.82rem;
    font-weight: 950;
    letter-spacing: 0.16em;
    text-transform: uppercase;
  }

  .ffOnboardV2__readinessHead span {
    color: var(--onboard-accent);
    font-weight: 950;
  }

  .ffOnboardV2__meter,
  .ffOnboardV2__previewMeter {
    height: 9px;
    margin: 0.9rem 0;
    overflow: hidden;
    border-radius: 999px;
    background: rgba(15, 23, 42, 0.08);
  }

  .ffOnboardV2__meter span,
  .ffOnboardV2__previewMeter span {
    display: block;
    height: 100%;
    width: 68%;
    border-radius: inherit;
    background: linear-gradient(90deg, var(--onboard-primary), var(--onboard-accent));
  }

  .ffOnboardV2 dl {
    display: grid;
    gap: 0.55rem;
    margin: 0;
  }

  .ffOnboardV2 dl div {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    padding: 0.7rem 0.8rem;
    border-radius: 16px;
    background: rgba(255,255,255,0.64);
  }

  .ffOnboardV2 dt {
    color: rgba(22, 15, 11, 0.48);
    font-size: 0.74rem;
    font-weight: 950;
    letter-spacing: 0.12em;
    text-transform: uppercase;
  }

  .ffOnboardV2__steps,
  .ffOnboardV2__packageGrid {
    display: grid;
    gap: 0.9rem;
  }

  .ffOnboardV2__steps {
    grid-template-columns: repeat(4, minmax(0, 1fr));
    margin: 1rem 0;
  }

  .ffOnboardV2__steps article,
  .ffOnboardV2__packageGrid article,
  .ffOnboardV2__notice {
    padding: 1.05rem;
    border: 1px solid rgba(148, 163, 184, 0.2);
    border-radius: 22px;
    background: rgba(255,255,255,0.72);
    box-shadow: 0 12px 34px rgba(15, 23, 42, 0.06);
  }

  .ffOnboardV2__steps span,
  .ffOnboardV2__packageGrid span {
    color: #a94319;
    font-size: 0.75rem;
    font-weight: 950;
    letter-spacing: 0.12em;
    text-transform: uppercase;
  }

  .ffOnboardV2__steps strong,
  .ffOnboardV2__packageGrid strong {
    display: block;
    margin-top: 0.35rem;
    font-size: 1rem;
    line-height: 1.08;
    letter-spacing: -0.03em;
  }

  .ffOnboardV2__steps p,
  .ffOnboardV2__packageGrid p,
  .ffOnboardV2__notice p {
    margin-top: 0.45rem;
    color: rgba(22, 15, 11, 0.62);
    font-size: 0.9rem;
    line-height: 1.42;
  }

  .ffOnboardV2__section,
  .ffOnboardV2__handoff {
    margin-top: 1rem;
    padding: clamp(1.2rem, 3.2vw, 2.25rem);
  }

  .ffOnboardV2__sectionHead {
    margin-bottom: 1.2rem;
  }

  .ffOnboardV2__formGrid,
  .ffOnboardV2__brandGrid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.85rem;
  }

  .ffOnboardV2 label {
    display: grid;
    gap: 0.42rem;
    min-width: 0;
  }

  .ffOnboardV2 label span {
    color: rgba(22, 15, 11, 0.72);
    font-size: 0.82rem;
    font-weight: 900;
  }

  .ffOnboardV2 input,
  .ffOnboardV2 select,
  .ffOnboardV2 textarea {
    width: 100%;
    min-height: 46px;
    padding: 0.78rem 0.9rem;
    border: 1px solid rgba(148, 163, 184, 0.2);
    border-radius: 16px;
    background: rgba(255,255,255,0.72);
    color: #160f0b;
    outline: none;
  }

  .ffOnboardV2 textarea {
    resize: vertical;
  }

  .ffOnboardV2 input:focus,
  .ffOnboardV2 select:focus,
  .ffOnboardV2 textarea:focus,
  .ffOnboardV2 a:focus-visible,
  .ffOnboardV2 button:focus-visible {
    outline: 3px solid color-mix(in srgb, var(--onboard-primary) 42%, transparent);
    outline-offset: 3px;
  }

  .ffOnboardV2__wide {
    grid-column: 1 / -1;
  }

  .ffOnboardV2__themeControls {
    display: grid;
    gap: 1rem;
  }

  .ffOnboardV2__colorGrid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.75rem;
  }

  .ffOnboardV2 input[type="color"] {
    height: 50px;
    padding: 0.3rem;
  }

  .ffOnboardV2__themePreview {
    display: grid;
    align-content: center;
    gap: 0.9rem;
    background:
      radial-gradient(circle at 100% 0%, color-mix(in srgb, var(--onboard-primary) 24%, transparent), transparent 14rem),
      linear-gradient(180deg, var(--onboard-soft), rgba(255,255,255,0.8));
  }

  .ffOnboardV2__previewTop {
    justify-content: flex-start;
  }

  .ffOnboardV2__previewTop strong,
  .ffOnboardV2__previewTop small {
    display: block;
  }

  .ffOnboardV2__previewTop small {
    color: rgba(22, 15, 11, 0.56);
    font-size: 0.72rem;
    font-weight: 900;
    letter-spacing: 0.14em;
    text-transform: uppercase;
  }

  .ffOnboardV2__themePreview h3 {
    max-width: 11ch;
    font-size: clamp(1.55rem, 3vw, 2.4rem);
  }

  .ffOnboardV2__themePreview p {
    color: rgba(22, 15, 11, 0.64);
    line-height: 1.45;
  }

  .ffOnboardV2__themePreview button {
    min-height: 46px;
    border: 0;
    border-radius: 999px;
    font-weight: 950;
  }

  .ffOnboardV2__packageGrid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .ffOnboardV2__packageGrid ul {
    margin: 0.8rem 0 0;
    padding-left: 1.05rem;
    color: rgba(22, 15, 11, 0.62);
    font-size: 0.88rem;
    line-height: 1.55;
  }

  .ffOnboardV2__handoff {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 1rem;
    align-items: center;
  }

  .ffOnboardV2__saveNote {
    grid-column: 1 / -1;
    min-height: 42px;
    padding: 0.75rem 1rem;
    border-radius: 16px;
    background: color-mix(in srgb, var(--onboard-accent) 12%, white);
    color: color-mix(in srgb, var(--onboard-accent) 72%, #160f0b);
    font-size: 0.9rem;
    font-weight: 800;
  }

  @media (max-width: 900px) {
    .ffOnboardV2__hero,
    .ffOnboardV2__formGrid,
    .ffOnboardV2__brandGrid,
    .ffOnboardV2__handoff {
      grid-template-columns: 1fr;
    }

    .ffOnboardV2__steps,
    .ffOnboardV2__packageGrid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  @media (max-width: 640px) {
    .ffOnboardV2__topbar,
    .ffOnboardV2__main {
      width: min(100% - 1rem, 1180px);
    }

    .ffOnboardV2__topbar {
      border-radius: 24px;
      align-items: flex-start;
    }

    .ffOnboardV2__brand {
      max-width: 44vw;
    }

    .ffOnboardV2__brand strong {
      max-width: 9rem;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .ffOnboardV2__brand small {
      display: none;
    }

    .ffOnboardV2__nav {
      justify-content: flex-end;
      flex-wrap: wrap;
      gap: 0.2rem;
    }

    .ffOnboardV2__nav a {
      min-height: 34px;
      padding: 0.55rem 0.65rem;
      font-size: 0.76rem;
    }

    .ffOnboardV2__hero,
    .ffOnboardV2__section,
    .ffOnboardV2__handoff {
      border-radius: 24px;
      padding: 1rem;
    }

    .ffOnboardV2__hero {
      min-height: 0;
      align-items: start;
    }

    .ffOnboardV2 h1 {
      max-width: 10.8ch;
      font-size: clamp(2.1rem, 12vw, 3.25rem);
      line-height: 0.95;
    }

    .ffOnboardV2 h2 {
      max-width: 11ch;
      font-size: clamp(1.55rem, 8vw, 2.25rem);
    }

    .ffOnboardV2__steps,
    .ffOnboardV2__packageGrid,
    .ffOnboardV2__colorGrid {
      grid-template-columns: 1fr;
    }

    .ffOnboardV2__actions,
    .ffOnboardV2__handoffActions {
      align-items: stretch;
      flex-direction: column;
    }

    .ffOnboardV2__btn,
    .ffOnboardV2__handoffActions button {
      width: 100%;
      justify-content: center;
      text-align: center;
    }
  }
}
'''

def backup(path: Path) -> None:
    if path.exists():
        stamp = time.strftime("%Y%m%d%H%M%S")
        b = path.with_suffix(path.suffix + f".bak-hoi6h-{stamp}")
        b.write_text(path.read_text(errors="ignore"))
        print(f"Backup: {b}")

if not TPL.exists():
    raise SystemExit(f"Missing onboarding template: {TPL}")

backup(TPL)
TPL.write_text(TEMPLATE)
print(f"Rebuilt template: {TPL}")

if not CSS.exists():
    raise SystemExit(f"Missing CSS file: {CSS}")

css = CSS.read_text(errors="ignore")
if CSS_MARKER in css:
    print("CSS marker already present; not appending duplicate.")
else:
    backup(CSS)
    CSS.write_text(css.rstrip() + "\n" + CSS_BLOCK.strip() + "\n")
    print(f"Patched CSS: {CSS}")

print("HOI 6H essential onboarding rebuild complete.")
