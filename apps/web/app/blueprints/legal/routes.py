from __future__ import annotations
from apps.web.app.services.campaign_identity import DEFAULT_CAMPAIGN_NAME, DEFAULT_CAMPAIGN_SLUG, DEFAULT_LOCATION, DEFAULT_SPONSOR_CONTACT_EMAIL, DEFAULT_TEAM_NAME
from flask import render_template

from flask import Blueprint, current_app, render_template_string

legal_bp = Blueprint("legal", __name__)


_LEGAL_TEMPLATE = """
<!DOCTYPE html>
<html
  lang="en"
  class="ff-root"
  data-theme="{{ theme|e }}"
  data-density="{{ density|e }}"
>
  <head>
    <meta charset="utf-8" />
    <meta http-equiv="x-ua-compatible" content="ie=edge" />
    <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover, maximum-scale=5" />
    <meta name="format-detection" content="telephone=no,date=no,address=no,email=no" />
    <meta name="referrer" content="strict-origin-when-cross-origin" />
    <meta name="color-scheme" content="light dark" />
    <meta name="description" content="{{ description|e }}" />
    <meta name="theme-color" media="(prefers-color-scheme: light)" content="{{ theme_color|e }}" />
    <meta name="theme-color" media="(prefers-color-scheme: dark)" content="{{ theme_color_dark|e }}" />
    <title>{{ title|e }}</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/ff.css') }}?v={{ asset_v|e }}" />
  </head>
  <body class="ff-body ff-platformBody" data-ff-body="" data-ff-page="legal">
    <nav class="ff-skiplinks" aria-label="Skip links">
      <a href="#content" class="ff-skip">Skip to content</a>
    </nav>

    <div class="ff-shell ff-shell--platform">
      <div class="ff-shellBg" aria-hidden="true"></div>

      <header class="ff-chrome">
        <div class="ff-container">
          <div class="ff-topbar__capsule ff-glass ff-surface">
            <div class="ff-row ff-wrap ff-gap-3 ff-ais ff-jcb">
              <a href="{{ url_for('platform.index') }}" class="ff-platformBrand ff-nounderline" aria-label="{{ brand_name }} home">
                <span class="ff-platformBrand__disc" aria-hidden="true"></span>
                <span class="ff-stack">
                  <span class="ff-platformBrand__wordmark">{{ brand_name }}</span>
                  <span class="ff-brandStack__meta">Legal</span>
                </span>
              </a>

              <nav class="ff-row ff-wrap ff-gap-2" aria-label="Legal navigation">
                <a href="{{ url_for('platform.index') }}" class="ff-btn ff-btn--ghost">Platform</a>
                <a href="{{ url_for('campaign.campaign_page', slug=campaign_slug) }}" class="ff-btn ff-btn--ghost">Campaign</a>
                <a href="{{ url_for('legal.terms') }}" class="ff-btn ff-btn--secondary">Terms</a>
                <a href="{{ url_for('legal.privacy') }}" class="ff-btn ff-btn--secondary">Privacy</a>
              </nav>
            </div>
          </div>
        </div>
      </header>

      <main id="content" class="ff-main ff-main--platform">
        <section class="ff-section ff-section--hero">
          <div class="ff-container">
            <div class="ff-storyGrid">
              <article class="ff-card-strong ff-p-6">
                <div class="ff-stack ff-gap-3">
                  <p class="ff-eyebrow">{{ eyebrow }}</p>
                  <h1 class="ff-h1">{{ heading }}</h1>
                  <p class="ff-sectionLead">{{ intro }}</p>
                  <div class="ff-callout ff-callout--muted">
                    <p class="ff-help">
                      Last updated: {{ updated_at }} · Contact:
                      <a class="ff-link" href="mailto:{{ support_email|e }}">{{ support_email }}</a>
                    </p>
                  </div>
                </div>
              </article>

              <aside class="ff-card ff-p-6">
                <div class="ff-stack ff-gap-3">
                  <p class="ff-kicker">Why this page exists</p>
                  <h2 class="ff-h3">Clear legal expectations help donors, sponsors, and organizations trust the platform.</h2>
                  <p class="ff-help">
                    FutureFunded is built for public fundraising surfaces that should feel calm, understandable, and appropriate
                    for schools, nonprofits, teams, clubs, families, and local businesses.
                  </p>
                </div>
              </aside>
            </div>
          </div>
        </section>

        <section class="ff-section">
          <div class="ff-container">
            <div class="ff-stack ff-gap-3">
              {% for section in sections %}
                <article class="ff-card ff-p-6">
                  <div class="ff-stack ff-gap-3">
                    <h2 class="ff-h2">{{ section.title }}</h2>
                    {% for paragraph in section.body %}
                      <p class="ff-help">{{ paragraph }}</p>
                    {% endfor %}
                  </div>
                </article>
              {% endfor %}
            </div>
          </div>
        </section>
      </main>

      <footer class="ff-footer">
        <div class="ff-container">
          <div class="ff-footer__inner">
            <div class="ff-row ff-wrap ff-gap-3 ff-jcb">
              <div class="ff-stack ff-gap-2">
                <strong class="ff-platformBrand__wordmark">{{ brand_name }}</strong>
                <p class="ff-help">{{ description }}</p>
              </div>

              <div class="ff-row ff-wrap ff-gap-2">
                <a href="{{ url_for('legal.terms') }}" class="ff-link">Terms</a>
                <a href="{{ url_for('legal.privacy') }}" class="ff-link">Privacy</a>
                <a href="{{ url_for('platform.index') }}" class="ff-link">Platform</a>
              </div>
            </div>
          </div>
        </div>
      </footer>
    </div>

    <script src="{{ url_for('static', filename='js/ff-app.js') }}?v={{ asset_v|e }}" defer></script>
  </body>
</html>
"""


def _base_context() -> dict[str, str]:
    config = current_app.config
    return {
        "brand_name": str(config.get("BRAND_NAME", "FutureFunded")).strip() or "FutureFunded",
        "support_email": str(config.get("SUPPORT_EMAIL", "support@getfuturefunded.com")).strip()
        or "support@getfuturefunded.com",
        "asset_v": str(config.get("ASSET_V", "1")).strip() or "1",
        "theme": str(config.get("DEFAULT_THEME", "light")).strip() or "light",
        "density": str(config.get("DEFAULT_DENSITY", "compact")).strip() or "compact",
        "theme_color": str(config.get("THEME_COLOR", "#f97316")).strip() or "#f97316",
        "theme_color_dark": str(config.get("THEME_COLOR_DARK", "#0b0f17")).strip() or "#0b0f17",
        "campaign_slug": str(config.get("DEMO_CAMPAIGN_SLUG", DEFAULT_CAMPAIGN_SLUG)).strip()
        or DEFAULT_CAMPAIGN_SLUG,
        "updated_at": str(config.get("LEGAL_LAST_UPDATED", "April 20, 2026")).strip()
        or "April 20, 2026",
    }


@legal_bp.get("/terms")
@legal_bp.get("/legal/terms")
def terms():
    context = _base_context()
    context.update(
        {
            "title": "Terms • FutureFunded",
            "description": "Terms governing the use of FutureFunded fundraising pages, sponsor flows, and platform services.",
            "eyebrow": "Platform terms",
            "heading": "Terms for using FutureFunded",
            "intro": (
                "These terms explain the basic expectations for organizations, donors, and sponsors using FutureFunded "
                "to launch or interact with a public fundraising surface."
            ),
            "sections": [
                {
                    "title": "1. Platform use",
                    "body": [
                        "FutureFunded provides organizations with a public fundraising surface, sponsor lane, and related platform tools. Organizations are responsible for the accuracy of the content, goals, branding, and campaign claims they publish.",
                        "Use of the platform must remain lawful, appropriate for the intended audience, and consistent with school-safe, sponsor-safe, and community-safe public presentation.",
                    ],
                },
                {
                    "title": "2. Donations and sponsor interest",
                    "body": [
                        "Submitting a donation or sponsor interest form does not transfer ownership of the platform, campaign, or supporting materials. Payment processing and sponsor follow-up may involve third-party providers and organization-side review.",
                        "Organizations are responsible for how they use funds and how they respond to sponsor leads generated through the page.",
                    ],
                },
                {
                    "title": "3. Content, branding, and communications",
                    "body": [
                        "Organizations must have the right to use logos, names, images, and campaign materials they upload or publish through the platform.",
                        "FutureFunded may remove or suspend content that appears misleading, harmful, unlawful, or materially inconsistent with safe public fundraising use.",
                    ],
                },
                {
                    "title": "4. Service availability and changes",
                    "body": [
                        "The platform may evolve over time as features, payment flows, sponsor tools, and campaign structures improve. We may update workflows, integrations, and presentation layers while preserving core functionality where reasonably possible.",
                        "No guarantee is made that any specific feature, provider, or campaign structure will remain unchanged forever.",
                    ],
                },
            ],
        }
    )
    return render_template_string(_LEGAL_TEMPLATE, **context)


@legal_bp.get("/privacy")
@legal_bp.get("/legal/privacy")
def privacy():
    context = _base_context()
    context.update(
        {
            "title": "Privacy • FutureFunded",
            "description": "Privacy information for FutureFunded fundraising pages, supporter interactions, and sponsor inquiries.",
            "eyebrow": "Privacy",
            "heading": "Privacy for donors, sponsors, and organizations",
            "intro": (
                "This page explains the kind of information that may be collected through FutureFunded and how it is used "
                "to support fundraising, sponsor interest, and basic platform operations."
            ),
            "sections": [
                {
                    "title": "1. Information collected",
                    "body": [
                        "Depending on the workflow, the platform may collect names, email addresses, donation amounts, sponsor inquiry details, onboarding information, and technical request data needed to operate the service.",
                        "Payment details are typically handled through connected payment providers rather than being fully stored directly in the public fundraising page itself.",
                    ],
                },
                {
                    "title": "2. How information is used",
                    "body": [
                        "Information is used to operate fundraising pages, confirm support activity, respond to sponsor inquiries, support onboarding, improve platform reliability, and maintain the public-facing campaign experience.",
                        "Organizations may receive donor or sponsor-related information needed to complete follow-up, acknowledgment, or campaign administration.",
                    ],
                },
                {
                    "title": "3. Sharing and service providers",
                    "body": [
                        "FutureFunded may rely on service providers for payments, analytics, hosting, notifications, and related operations. Information may be processed through those providers as needed to complete platform functions.",
                        "We do not treat supporter or sponsor information as a public asset for resale. Information should be handled in ways appropriate to a fundraising and organization-support context.",
                    ],
                },
                {
                    "title": "4. Questions and requests",
                    "body": [
                        "If you have a privacy question, a data-handling concern, or a request related to information submitted through the platform, contact the support address listed on this page.",
                        "Organizations using FutureFunded are also responsible for their own handling of campaign-related data they receive through the platform.",
                    ],
                },
            ],
        }
    )
    return render_template_string(_LEGAL_TEMPLATE, **context)

@legal_bp.route("/contact")
def contact():
    """Public contact page for prospective teams, sponsors, and partners."""
    return render_template("legal/contact.html")
