from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .services import PlatformService, build_platform_service


@dataclass(slots=True)
class PlatformPresenter:
    service: PlatformService

    @classmethod
    def from_config(cls, config: Mapping[str, Any]) -> PlatformPresenter:
        return cls(service=build_platform_service(config))

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

    def index_context(self) -> dict[str, Any]:
        return self._page_context(
            self.service.get_platform_context(),
            page_key="platform.index",
            active_nav="platform",
        )

    def onboarding_context(self, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        safe_payload = dict(payload or {})
        return self._page_context(
            self.service.get_onboarding_context(safe_payload),
            page_key="platform.onboarding",
            active_nav="onboarding",
        )

    def dashboard_context(self) -> dict[str, Any]:
        return self._page_context(
            self.service.get_dashboard_context(),
            page_key="platform.dashboard",
            active_nav="dashboard",
        )


def build_platform_presenter(config: Mapping[str, Any]) -> PlatformPresenter:
    return PlatformPresenter.from_config(config)
