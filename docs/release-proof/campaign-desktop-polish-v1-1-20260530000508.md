# Campaign Desktop Polish V1.1

Date: 2026-05-30T00:05:08-05:00

Baseline:
- Three viewport visual board workflow is active.
- Fresh board generated after V1.1 patch.

Board:
- audit_outputs/visual-boards-three-viewports/latest/desktop/index.html
- audit_outputs/visual-boards-three-viewports/latest/desktop/screenshots/campaign-desktop.png

Validation:
- Campaign page returned HTTP 200 across desktop, tablet, and mobile.
- Desktop board served successfully on local board server.
- No overflow rows were printed by the recovery proof command.

Scope:
- Campaign page only.
- Desktop media query only.
- Added a stable campaign root class.
- Replaced generic V1 desktop polish with targeted V1.1 selectors:
  - .ff-campaignHero
  - .ff-campaignHero__grid
  - .ff-campaignHero__story
  - .ff-card--hero
  - .ff-heroTitle
  - .ff-lede
  - .ff-heroActions

Intent:
- Improve desktop hero rhythm.
- Tighten donor-first hierarchy.
- Make the campaign top fold feel more premium and controlled.
- Avoid tablet/mobile changes.
