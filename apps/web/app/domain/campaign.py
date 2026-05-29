from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .sponsor import SponsorTier, SponsorWallItem


def _clean(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip() or default


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(slots=True)
class GalleryItem:
    src: str
    alt: str
    caption: str = ""
    body: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> GalleryItem:
        data = data or {}
        return cls(
            src=_clean(data.get("src")),
            alt=_clean(data.get("alt"), "Campaign image"),
            caption=_clean(data.get("caption")),
            body=_clean(data.get("body")),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SupportArea:
    amount: int
    title: str
    body: str
    featured: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> SupportArea:
        data = data or {}
        return cls(
            amount=_int(data.get("amount"), 0),
            title=_clean(data.get("title"), "Support Area"),
            body=_clean(data.get("body")),
            featured=_bool(data.get("featured")),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class TeamSpotlight:
    id: str
    name: str
    tier: str = ""
    meta: str = ""
    goal: int = 0
    raised: int = 0
    featured: bool = False
    needs: bool = False
    restricted: bool = False
    photo: str = ""
    ask: str = ""
    label: str = "Program support"

    @property
    def progress_percent(self) -> int:
        if self.goal <= 0:
            return 0
        percent = int((self.raised / self.goal) * 100)
        return max(0, min(100, percent))

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> TeamSpotlight:
        data = data or {}
        return cls(
            id=_clean(data.get("id"), "team"),
            name=_clean(data.get("name"), "Team"),
            tier=_clean(data.get("tier")),
            meta=_clean(data.get("meta")),
            goal=_int(data.get("goal"), 0),
            raised=_int(data.get("raised"), 0),
            featured=_bool(data.get("featured")),
            needs=_bool(data.get("needs")),
            restricted=_bool(data.get("restricted")),
            photo=_clean(data.get("photo")),
            ask=_clean(data.get("ask")),
            label=_clean(data.get("label"), "Program support"),
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["progress_percent"] = self.progress_percent
        return payload


@dataclass(slots=True)
class FAQItem:
    question: str
    answer: str

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> FAQItem:
        data = data or {}
        return cls(
            question=_clean(data.get("question"), "Question"),
            answer=_clean(data.get("answer")),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Campaign:
    slug: str
    org_name: str
    campaign_name: str
    headline: str
    subhead: str
    tagline: str
    location: str = ""
    raised: int = 0
    goal: int = 0
    supporters: int = 0
    story_title: str = "Why this campaign matters right now"
    story_intro: str = ""
    story_body: str = ""
    story_body_2: str = ""
    gallery: list[GalleryItem] = field(default_factory=list)
    support_areas: list[SupportArea] = field(default_factory=list)
    teams: list[TeamSpotlight] = field(default_factory=list)
    faq: list[FAQItem] = field(default_factory=list)
    sponsor_tiers: list[SponsorTier] = field(default_factory=list)
    sponsor_wall: list[SponsorWallItem] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def progress_percent(self) -> int:
        if self.goal <= 0:
            return 0
        percent = int((self.raised / self.goal) * 100)
        return max(0, min(100, percent))

    @property
    def remaining(self) -> int:
        return max(0, self.goal - self.raised)

    @property
    def next_push(self) -> int:
        remaining = self.remaining
        if remaining >= 1500:
            return 250
        if remaining >= 600:
            return 150
        if remaining > 0:
            return remaining
        return 100

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> Campaign:
        data = data or {}
        return cls(
            slug=_clean(data.get("slug"), "campaign"),
            org_name=_clean(data.get("org_name"), "Organization"),
            campaign_name=_clean(
                data.get("campaign_name"), _clean(data.get("org_name"), "Campaign")
            ),
            headline=_clean(data.get("headline"), "Help close the gap for Connect ATX Elite."),
            subhead=_clean(data.get("subhead"), "Back the athletes of"),
            tagline=_clean(
                data.get("tagline"),
                "Support Connect ATX Elite’s full season through one secure campaign for travel, tournaments, meals, gear, and player development.",
            ),
            location=_clean(data.get("location")),
            raised=_int(data.get("raised"), 0),
            goal=_int(data.get("goal"), 0),
            supporters=_int(data.get("supporters"), 0),
            story_title=_clean(data.get("story_title"), "Why this campaign matters right now"),
            story_intro=_clean(data.get("story_intro")),
            story_body=_clean(data.get("story_body")),
            story_body_2=_clean(data.get("story_body_2")),
            gallery=[GalleryItem.from_dict(item) for item in list(data.get("gallery") or [])],
            support_areas=[
                SupportArea.from_dict(item) for item in list(data.get("support_areas") or [])
            ],
            teams=[TeamSpotlight.from_dict(item) for item in list(data.get("teams") or [])],
            faq=[FAQItem.from_dict(item) for item in list(data.get("faq") or [])],
            sponsor_tiers=[
                SponsorTier.from_dict(item) for item in list(data.get("sponsor_tiers") or [])
            ],
            sponsor_wall=[
                SponsorWallItem.from_dict(item) for item in list(data.get("sponsor_wall") or [])
            ],
            metadata=dict(data.get("metadata") or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "slug": self.slug,
            "org_name": self.org_name,
            "campaign_name": self.campaign_name,
            "headline": self.headline,
            "subhead": self.subhead,
            "tagline": self.tagline,
            "location": self.location,
            "raised": self.raised,
            "goal": self.goal,
            "supporters": self.supporters,
            "progress_percent": self.progress_percent,
            "remaining": self.remaining,
            "next_push": self.next_push,
            "story_title": self.story_title,
            "story_intro": self.story_intro,
            "story_body": self.story_body,
            "story_body_2": self.story_body_2,
            "gallery": [item.to_dict() for item in self.gallery],
            "support_areas": [item.to_dict() for item in self.support_areas],
            "teams": [item.to_dict() for item in self.teams],
            "faq": [item.to_dict() for item in self.faq],
            "sponsor_tiers": [item.to_dict() for item in self.sponsor_tiers],
            "sponsor_wall": [item.to_dict() for item in self.sponsor_wall],
            "metadata": dict(self.metadata),
        }
