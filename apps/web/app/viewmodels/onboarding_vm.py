from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from apps.web.app.domain.onboarding import OnboardingSubmission
from apps.web.app.domain.organization import Organization


@dataclass(slots=True)
class OnboardingViewModel:
    page_title: str = "Onboarding • FutureFunded"
    page_description: str = (
        "Set up a premium fundraising surface with structured brand, story, sponsor, and payment inputs."
    )
    pills: list[str] = field(default_factory=list)
    metrics: list[dict[str, str]] = field(default_factory=list)
    steps: list[dict[str, str]] = field(default_factory=list)
    prepared_inputs: list[str] = field(default_factory=list)
    operator_note: str = ""
    submission_summary: str = ""
    missing_fields: list[str] = field(default_factory=list)
    organization_name: str = ""
    campaign_name: str = ""
    location: str = ""
    goal: int = 0
    operator_email: str = ""
    support_story: str = ""
    campaign_summary: str = ""
    primary_sponsor_package: str = ""
    payment_stack: str = ""
    theme: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_submission(
        cls,
        submission: OnboardingSubmission | None = None,
        organization: Organization | None = None,
    ) -> OnboardingViewModel:
        submission = submission or OnboardingSubmission()
        organization = organization or Organization.from_dict(
            {
                "slug": "futurefunded",
                "name": "FutureFunded",
                "support_email": "support@getfuturefunded.com",
            }
        )

        return cls(
            pills=["Operator setup", "Brand-first", "Payment-ready", "White-label launch"],
            metrics=[
                {"label": "Brand system", "value": "Logo, colors, story"},
                {"label": "Money path", "value": "Support + sponsors"},
                {"label": "Operator flow", "value": "Short, structured setup"},
                {"label": "Launch quality", "value": "Public-ready output"},
            ],
            steps=[
                {
                    "step": "Step 1",
                    "title": "Define the organization identity",
                    "body": "Name, logo, location, colors, and the public-facing description of the program or institution.",
                },
                {
                    "step": "Step 2",
                    "title": "Set the campaign structure",
                    "body": "Goal, campaign name, support story, what the funding covers, and the reasons supporters should act now.",
                },
                {
                    "step": "Step 3",
                    "title": "Shape the sponsor lane",
                    "body": "Create packages, sponsor copy, and business-facing visibility that feels appropriate and credible.",
                },
                {
                    "step": "Step 4",
                    "title": "Connect payments and launch settings",
                    "body": "Prepare donation handling, confirmation behavior, and launch-ready settings for the public page.",
                },
            ],
            prepared_inputs=[
                "logo and preferred colors",
                "campaign goal and deadline",
                "short public-facing story",
                "support categories and real costs",
                "sponsor package structure",
                "payment account ownership",
            ],
            operator_note=(
                "Keep the campaign summary clear, grounded, and appropriate for families, schools, clubs, alumni, and local businesses who may be seeing the organization for the first time."
            ),
            submission_summary=submission.summary,
            missing_fields=submission.missing_fields,
            organization_name=submission.organization_name,
            campaign_name=submission.campaign_name,
            location=submission.location,
            goal=submission.goal,
            operator_email=submission.operator_email,
            support_story=submission.support_story,
            campaign_summary=submission.campaign_summary,
            primary_sponsor_package=submission.primary_sponsor_package,
            payment_stack=submission.payment_stack,
            theme=organization.theme.to_dict(),
        )

    def to_template_context(self) -> dict[str, Any]:
        return asdict(self)
