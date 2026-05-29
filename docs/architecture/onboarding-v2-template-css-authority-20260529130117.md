# Onboarding V2 Template + CSS Authority

Date: 2026-05-29T13:01:17-05:00

Result:
- Replaced onboarding template with ffOnboardV2 contract.
- Replaced onboarding.css with V2 authority.
- Added scoped shared shell header/rhythm completion layer.
- Preserved onboarding hooks:
  - data-ff-onboarding-root
  - data-ff-theme-picker
  - data-ff-theme-preset
  - data-ff-color-primary
  - data-ff-color-accent
  - data-ff-color-soft
  - data-ff-theme-preview
  - data-ff-save-onboarding
  - data-ff-save-note
- Preserved shared ff_shell_header contract.

Safety:
- Use latest safety tags before onboarding template/CSS replacement if rollback is needed.
