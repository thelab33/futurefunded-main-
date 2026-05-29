from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from apps.web.app.domain.organization import Organization


@dataclass(slots=True)
class PlatformViewModel:
    page_title: str = "FutureFunded Platform"
    page_description: str = (
        "Launch branded fundraising pages with cleaner donor trust, sponsor credibility, and a calmer operator workflow."
    )
    pills: list[str] = field(default_factory=list)
    metrics: list[dict[str, str]] = field(default_factory=list)
    audiences: list[dict[str, str]] = field(default_factory=list)
    features: list[dict[str, str]] = field(default_factory=list)
    onboarding_steps: list[dict[str, str]] = field(default_factory=list)
    sponsor_lane_title: str = ""
    sponsor_lane_body: str = ""
    close_title: str = ""
    close_body: str = ""
    brand_name: str = "FutureFunded"
    theme: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_organization(cls, organization: Organization | None = None) -> PlatformViewModel:
        organization = organization or Organization.from_dict(
            {
                "slug": "futurefunded",
                "name": "FutureFunded",
                "support_email": "support@getfuturefunded.com",
            }
        )

        return cls(
            pills=[
                "Turnkey fundraising",
                "Sponsor-ready",
                "White-label launch",
                "Mobile-first",
            ],
            metrics=[
                {"label": "Launch path", "value": "Logo to live page"},
                {"label": "Public surface", "value": "Donor clarity first"},
                {"label": "Sponsor lane", "value": "Business-safe visibility"},
                {"label": "Operator model", "value": "Built to scale"},
            ],
            audiences=[
                {
                    "title": "For donors",
                    "body": "A clearer giving path with stronger trust, calmer layout, and better mobile checkout behavior.",
                },
                {
                    "title": "For sponsors",
                    "body": "A more credible lane for businesses to review packages, submit interest, and be seen appropriately.",
                },
                {
                    "title": "For operators",
                    "body": "A repeatable launch flow with less duct tape, less chasing, and better handoff discipline.",
                },
                {
                    "title": "For institutions",
                    "body": "A presentation layer that feels sponsor-safe, school-safe, and mature enough to share publicly.",
                },
            ],
            features=[
                {
                    "title": "Flagship campaign page",
                    "body": "A premium public funnel with story, progress, donate rail, sponsor lane, FAQ, and trustworthy checkout entry.",
                },
                {
                    "title": "Brand-ready launch system",
                    "body": "Logo, colors, goal, story, sponsor tiers, and campaign framing set up in a clean operator flow.",
                },
                {
                    "title": "Payment foundation",
                    "body": "Structured support for modern payment flows, confirmation states, and future reporting paths.",
                },
                {
                    "title": "White-label readiness",
                    "body": "Built so the same product can serve youth teams, schools, nonprofits, and clubs without looking generic.",
                },
            ],
            onboarding_steps=[
                {
                    "step": "Step 1",
                    "title": "Set the brand and campaign basics",
                    "body": "Logo, colors, organization identity, goal, location, and the core fundraising story.",
                },
                {
                    "step": "Step 2",
                    "title": "Connect payments and sponsor structure",
                    "body": "Prepare the page for real donations and a sponsor lane businesses can review quickly.",
                },
                {
                    "step": "Step 3",
                    "title": "Launch a public page that already feels established",
                    "body": "Go live with a campaign surface that feels calm, trustworthy, and ready to share widely.",
                },
            ],
            sponsor_lane_title="A cleaner path for businesses to support the program and feel represented well.",
            sponsor_lane_body=(
                "Sponsor placement, package framing, and lead capture are designed to feel organized, visible, and credible — not bolted on as an afterthought."
            ),
            close_title=(
                "A better public fundraising system for organizations that want to look ready from day one."
            ),
            close_body=(
                "Start with a cleaner donor experience, a stronger sponsor lane, and a launch path that feels more mature than a patchwork fundraiser stack."
            ),
            brand_name=organization.display_name,
            theme=organization.theme.to_dict(),
        )

    def to_template_context(self) -> dict[str, Any]:
        return asdict(self)
