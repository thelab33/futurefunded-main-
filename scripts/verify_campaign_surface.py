#!/usr/bin/env python3
from pathlib import Path
import sys

index = Path("apps/web/app/templates/campaign/index.html")
css = Path("apps/web/app/static/css/ff.campaign-polish.css")
screenshot = Path("scripts/capture-campaign-screenshot.mjs")

template = index.read_text()
styles = css.read_text()

def fail(message: str) -> None:
    print(f"❌ {message}")
    sys.exit(1)

def require(text: str, token: str, label: str) -> None:
    if token not in text:
        fail(f"Missing {label}: {token}")

def block_between(text: str, start: str, end: str) -> str:
    a = text.find(start)
    if a == -1:
        fail(f"Could not find block start: {start}")
    b = text.find(end, a)
    if b == -1:
        fail(f"Could not find block end after {start}: {end}")
    return text[a:b]

required_template_tokens = {
    "locked hero": 'data-ff-hero-version="locked-v1"',
    "story v2": 'data-ff-story-version="v2"',
    "team media v2": 'data-ff-team-media-version="v2"',
    "impact v2": 'data-ff-impact-version="v2"',
    "pathway v2": 'data-ff-pathway-version="v2"',
    "faq v2": 'data-ff-faq-version="v2"',
    "share v2": 'data-ff-share-version="v2"',
    "final v2": 'data-ff-final-version="v2"',
    "footer v2": 'data-ff-footer-version="v2"',
    "donation open hook": "data-ff-open-checkout",
    "payment trigger hook": "data-ff-payment-trigger",
    "donate trigger hook": "data-ff-donate-trigger",
    "sponsor packages": 'id="sponsor-packages"',
    "sponsor trigger": "data-ff-sponsor-trigger",
    "copy share URL": "data-ff-copy-share-url",
    "QR trigger": "data-ff-qr-trigger",
    "mobile rail": "ff-mobile-rail",
}

for label, token in required_template_tokens.items():
    require(template, token, label)

hero = block_between(template, "                <!-- Hero -->", "                <!-- Trust strip -->")
forbidden_hero_tokens = [
    "ff-heroProofPanel",
    "ff-heroProofFigure",
    "ff-heroThumbGrid",
    "ff_media_urls[",
    "ff-hero--v5",
    "ff-hero-polish-v5.js",
]

for token in forbidden_hero_tokens:
    if token in hero:
        fail(f"Hero drift detected. Forbidden token inside hero: {token}")

if "ff-hero-polish-v5.js" in template:
    fail("Stale hero polish script is still referenced.")

required_css_tokens = [
    "FutureFunded Hero Lockdown Authority",
    "FutureFunded Trust Story Bridge Authority",
    "FutureFunded Sponsor Monetization Authority",
    "FutureFunded Story Proof v2 Authority",
    "FutureFunded Impact Pathway v2 Authority",
    "FutureFunded FAQ Share v2 Authority",
    "FutureFunded Final Footer v2 Authority",
    "FutureFunded Proof Media Deterministic Authority",
    "FutureFunded Mobile Proof Gallery Clamp",
    "FutureFunded Campaign Consistency Lock",
]

for token in required_css_tokens:
    require(styles, token, f"CSS authority block {token}")

required_screenshot_tokens = [
    "artifacts/frontend-screenshots",
    "campaign-desktop.png",
    "campaign-mobile.png",
    "bypassCSP",
]

if not screenshot.exists():
    fail("Screenshot capture script is missing.")

screenshot_text = screenshot.read_text()
for token in required_screenshot_tokens:
    require(screenshot_text, token, f"screenshot workflow token {token}")

print("✅ Campaign surface contracts verified.")
print("✅ Hero is locked.")
print("✅ Section versions are present.")
print("✅ Donation, sponsor, share, QR, and mobile hooks are preserved.")
print("✅ Screenshot workflow is wired.")
