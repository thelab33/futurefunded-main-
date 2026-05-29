from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .services import CampaignService, build_campaign_service


@dataclass(slots=True)
class CampaignPresenter:
    service: CampaignService

    @classmethod
    def from_config(cls, config: Mapping[str, Any]) -> CampaignPresenter:
        return cls(service=build_campaign_service(config))

    def _page_context(
        self,
        context: Mapping[str, Any] | None,
        *,
        page_key: str,
        active_nav: str,
    ) -> dict[str, Any]:
        base = dict(context or {})
        base["page_key"] = page_key
        base["active_nav"] = active_nav
        return base

    def page_context(self, slug: str) -> dict[str, Any]:
        context = self.service.get_campaign_context(slug)
        return self._page_context(
            context,
            page_key="campaign.index",
            active_nav="campaign",
        )


def build_campaign_presenter(config: Mapping[str, Any]) -> CampaignPresenter:
    return CampaignPresenter.from_config(config)
