from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from apps.web.app.domain.campaign import Campaign
from apps.web.app.domain.organization import Organization


@dataclass(slots=True)
class CampaignViewModel:
    page_title: str
    page_description: str
    org_name: str
    campaign_name: str
    location: str
    headline: str
    subhead: str
    tagline: str
    raised: int
    goal: int
    supporters: int
    progress_percent: int
    remaining: int
    next_push: int
    share_url: str
    canonical_url: str
    hero_points: list[str] = field(default_factory=list)
    quick_amounts: list[dict[str, Any]] = field(default_factory=list)
    story_title: str = "Why this campaign matters right now"
    story_intro: str = ""
    story_body: str = ""
    story_body_2: str = ""
    gallery: list[dict[str, Any]] = field(default_factory=list)
    support_areas: list[dict[str, Any]] = field(default_factory=list)
    teams: list[dict[str, Any]] = field(default_factory=list)
    faq_items: list[dict[str, Any]] = field(default_factory=list)
    sponsor_tiers: list[dict[str, Any]] = field(default_factory=list)
    sponsor_wall: list[dict[str, Any]] = field(default_factory=list)
    sponsor_points: list[str] = field(default_factory=list)
    sponsor_benefits: list[dict[str, Any]] = field(default_factory=list)
    sponsor_contact_email: str = ""
    organizer_email: str = ""
    theme: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_domain(
        cls,
        campaign: Campaign,
        organization: Organization,
        public_base_url: str = "",
    ) -> CampaignViewModel:
        public_base_url = public_base_url.rstrip("/")
        canonical_url = (
            f"{public_base_url}/c/{campaign.slug}" if public_base_url else f"/c/{campaign.slug}"
        )

        hero_points = [
            "Support local, travel, Gold, Platinum, and national circuit pathways through one shared season goal.",
            "Give through a cleaner page built for families, alumni, and local supporters.",
            "Sponsor the program through packages businesses can review quickly.",
        ]

        quick_amounts = [
            {"amount": 25, "label": "Quick help"},
            {"amount": 50, "label": "Essentials"},
            {"amount": 100, "label": "Momentum"},
            {"amount": 250, "label": "Big lift"},
        ]

        sponsor_points = [
            "Clear package structure instead of improvised sponsor asks.",
            "Business-safe placement on a calmer, more credible public page.",
            "A cleaner follow-up path for logos, confirmations, and next steps.",
        ]

        sponsor_benefits = [
            {
                "title": "Visible community support",
                "body": "Sponsors can be shown in a way that feels professional to families, alumni, boosters, and local supporters.",
            },
            {
                "title": "Simple review path",
                "body": "Businesses should be able to choose a package without reading through cluttered or vague sponsorship language.",
            },
            {
                "title": "Cleaner public presentation",
                "body": "The sponsor lane is integrated into the campaign surface instead of feeling bolted on after the fact.",
            },
        ]

        return cls(
            page_title=f"{campaign.org_name} • Fundraiser",
            page_description=f"Support {campaign.campaign_name} with a clear, sponsor-ready fundraising experience.",
            org_name=campaign.org_name,
            campaign_name=campaign.campaign_name,
            location=campaign.location,
            headline=campaign.headline,
            subhead=campaign.subhead,
            tagline=campaign.tagline,
            raised=campaign.raised,
            goal=campaign.goal,
            supporters=campaign.supporters,
            progress_percent=campaign.progress_percent,
            remaining=campaign.remaining,
            next_push=campaign.next_push,
            share_url=canonical_url,
            canonical_url=canonical_url,
            hero_points=hero_points,
            quick_amounts=quick_amounts,
            story_title=campaign.story_title,
            story_intro=campaign.story_intro,
            story_body=campaign.story_body,
            story_body_2=campaign.story_body_2,
            gallery=[item.to_dict() for item in campaign.gallery],
            support_areas=[item.to_dict() for item in campaign.support_areas],
            teams=[item.to_dict() for item in campaign.teams],
            faq_items=[item.to_dict() for item in campaign.faq],
            sponsor_tiers=[item.to_dict() for item in campaign.sponsor_tiers],
            sponsor_wall=[item.to_dict() for item in campaign.sponsor_wall],
            sponsor_points=sponsor_points,
            sponsor_benefits=sponsor_benefits,
            sponsor_contact_email=organization.primary_contact_email,
            organizer_email=organization.support_email,
            theme=organization.theme.to_dict(),
        )

    def to_template_context(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["campaign"] = {
            "slug": self.share_url.rsplit("/", 1)[-1],
            "org_name": self.org_name,
            "campaign_name": self.campaign_name,
            "headline": self.headline,
            "subhead": self.subhead,
            "tagline": self.tagline,
            "location": self.location,
            "raised": self.raised,
            "goal": self.goal,
            "supporters": self.supporters,
        }
        payload["share_url"] = self.share_url
        payload["canonical_url"] = self.canonical_url
        payload["faq_items"] = self.faq_items
        payload["sponsor_tiers"] = self.sponsor_tiers
        payload["sponsor_wall"] = self.sponsor_wall
        return payload
