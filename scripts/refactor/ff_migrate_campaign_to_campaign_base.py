#!/usr/bin/env python3
from __future__ import annotations

import re
import shutil
import time
from pathlib import Path

ROOT = Path.cwd()
STAMP = time.strftime("%Y%m%d-%H%M%S")
OUT = ROOT / "audit_outputs" / "shell-migrations" / STAMP
LATEST = ROOT / "audit_outputs" / "shell-migrations" / "latest"

TEMPLATE = ROOT / "apps/web/app/templates/campaign/index.html"
BASE = ROOT / "apps/web/app/templates/_base/campaign_base.html"


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def extract(pattern: str, text: str, flags: int = re.I | re.S) -> str:
    match = re.search(pattern, text, flags)
    return match.group(1).strip() if match else ""


def extract_body(text: str) -> tuple[str, str]:
    match = re.search(r"<body\b([^>]*)>([\s\S]*?)</body>", text, re.I)
    if not match:
        fail("Could not find <body>...</body> in campaign/index.html")
    return match.group(1).strip(), match.group(2).strip()


def extract_head(text: str) -> str:
    head = extract(r"<head\b[^>]*>([\s\S]*?)</head>", text)
    if not head:
        fail("Could not extract <head>...</head> from campaign/index.html")
    return head


def extract_html_attrs(text: str) -> tuple[str, str]:
    raw = extract(r"<html\b([^>]*)>", text)
    html_class = extract(r"class=[\"']([^\"']+)[\"']", raw) or "ff-root"

    attrs = re.sub(r"\s*lang=[\"'][^\"']+[\"']", "", raw, flags=re.I)
    attrs = re.sub(r"\s*class=[\"'][^\"']+[\"']", "", attrs, flags=re.I).strip()

    return html_class, attrs


def extract_body_class(body_attrs_raw: str) -> str:
    return extract(r"class=[\"']([^\"']+)[\"']", body_attrs_raw) or "ff-body ff-campaignBody ff-campaignBody--v1"


def extract_body_attrs(body_attrs_raw: str) -> str:
    attrs = re.sub(r"\s*class=[\"'][^\"']+[\"']", "", body_attrs_raw, flags=re.I).strip()

    required = [
        'data-ff-page="campaign"',
        'data-ff-surface="campaign"',
        'data-ff-template="campaign-index-on-campaign-base-v1"',
    ]

    lines = []
    if attrs:
        lines.append(attrs)

    joined = attrs
    for attr in required:
        name = attr.split("=", 1)[0]
        if name not in joined:
            lines.append(attr)

    return "\n".join(lines).strip()


def split_scripts_from_body(body_inner: str) -> tuple[str, str]:
    scripts = re.findall(r"<script\b[\s\S]*?</script>", body_inner, re.I)
    content = re.sub(r"\n?\s*<script\b[\s\S]*?</script>\s*\n?", "\n", body_inner, flags=re.I)
    content = re.sub(r"\n{3,}", "\n\n", content).strip()
    return content, "\n\n".join(s.strip() for s in scripts if s.strip())


def collect_setup(text: str) -> str:
    doc_match = re.search(r"<!doctype html>|<html\b|<head\b", text, re.I)
    setup = text[: doc_match.start()].strip() if doc_match else ""

    if "html_page" not in setup:
        setup += "\n{% set html_page = 'campaign' %}"
    if "ff_page" not in setup:
        setup += "\n{% set ff_page = 'campaign' %}"

    return setup.strip()


def extract_title(head: str) -> str:
    return extract(r"<title[^>]*>([\s\S]*?)</title>", head) or "{{ _team_name|default('FutureFunded Campaign', true) }}"


def extract_description(head: str) -> str:
    return extract(
        r"<meta\s+name=[\"']description[\"']\s+content=[\"']([^\"']+)[\"']\s*/?>",
        head,
    ) or "Support the campaign with a secure donation or sponsor package."


def extract_campaign_styles(head: str) -> str:
    # Preserve original CSS order from the working money page.
    tags = []
    for match in re.finditer(r"<link\b[^>]*(?:\.css)[^>]*>", head, re.I):
        tag = match.group(0).strip()
        if "ff.css" in tag:
            continue
        if tag not in tags:
            tags.append(tag)
    return "\n".join(tags)


def extract_campaign_head_extras(head: str) -> str:
    extras = []

    # Preserve JSON/script contracts and small inline head scripts.
    for match in re.finditer(r"<script\b[\s\S]*?</script>", head, re.I):
        script = match.group(0).strip()
        lower = script.lower()
        if (
            "ffsponsorcontract" in lower
            or "ffcampaignconfig" in lower
            or "application/json" in lower
            or "ff-no-js" in lower
            or "document.documentelement" in lower
        ):
            extras.append(script)

    # Preserve campaign-specific social/canonical/meta tags from the original head,
    # excluding charset, viewport, title, description, CSS links.
    for line in head.splitlines():
        stripped = line.strip()
        lower = stripped.lower()
        if not stripped:
            continue
        if lower.startswith("<title"):
            continue
        if "charset=" in lower:
            continue
        if 'name="viewport"' in lower or "name='viewport'" in lower:
            continue
        if 'name="description"' in lower or "name='description'" in lower:
            continue
        if lower.startswith("<link") and ".css" in lower:
            continue
        if lower.startswith("<script"):
            continue

        if (
            lower.startswith("<meta ")
            or lower.startswith("<link rel=\"canonical\"")
            or lower.startswith("<link rel='canonical'")
            or lower.startswith("<link rel=\"preconnect\"")
            or lower.startswith("<link rel='preconnect'")
        ):
            if stripped not in extras:
                extras.append(stripped)

    return "\n".join(extras).strip()


def indent(text: str, spaces: int = 2) -> str:
    pad = " " * spaces
    return "\n".join((pad + line if line.strip() else line) for line in text.splitlines())


def sanity_check(output: str, base_text: str = '') -> None:
    combined = output + '\n' + base_text
    checks = {
        "extends campaign_base": '{% extends "_base/campaign_base.html" %}' in output,
        "has content block": "{% block content %}" in output,
        "has scripts block": "{% block scripts %}" in output,
        "has ffCampaignConfig": "ffCampaignConfig" in output,
        "has ffSponsorContract": "ffSponsorContract" in output,
        "has checkout hook": "data-ff-open-checkout" in output,
        "has sponsor hook": "data-ff-open-sponsor" in output,
        "has share hook": "data-ff-share-trigger" in output or "data-ff-qr-trigger" in output,
        "has campaign css": "campaign.css" in output,
        "has campaign js": "ff-campaign.js" in combined,
    }

    failed = [name for name, ok in checks.items() if not ok]
    if failed:
        fail("Migration output failed sanity checks: " + ", ".join(failed))

    if output.count("{#") != output.count("#}"):
        fail("Unbalanced Jinja comments in migrated campaign template.")

    if output.count("{% block ") != len(re.findall(r"{%\s*endblock", output)):
        fail("Block/endblock count mismatch in migrated campaign template.")


def main() -> int:
    if not TEMPLATE.exists():
        fail(f"Missing template: {TEMPLATE}")
    if not BASE.exists():
        fail(f"Missing base shell: {BASE}")

    original = TEMPLATE.read_text(encoding="utf-8")

    if "{% extends \"_base/campaign_base.html\" %}" in original or "{% extends '_base/campaign_base.html' %}" in original:
        print("campaign/index.html already extends _base/campaign_base.html; no migration needed.")
        return 0

    if "<!doctype" not in original.lower() and "<html" not in original.lower():
        fail("Expected campaign/index.html to own a document shell before migration.")

    setup = collect_setup(original)
    head = extract_head(original)
    body_attrs_raw, body_inner = extract_body(original)

    html_class, html_attrs = extract_html_attrs(original)
    body_class = extract_body_class(body_attrs_raw)
    body_attrs = extract_body_attrs(body_attrs_raw)

    content, body_scripts = split_scripts_from_body(body_inner)

    if "<main" not in content.lower():
        fail("Campaign body content does not contain <main>.")
    if "data-ff-open-checkout" not in content:
        fail("Campaign content lost checkout trigger hook.")
    if "data-ff-open-sponsor" not in content:
        fail("Campaign content lost sponsor trigger hook.")

    title = extract_title(head)
    description = extract_description(head)
    campaign_styles = extract_campaign_styles(head)
    campaign_head_extras = extract_campaign_head_extras(head)

    migrated_parts = [
        setup,
        '{% extends "_base/campaign_base.html" %}',
        "",
        "{% block html_class %}" + html_class + "{% endblock %}",
        "{% block html_attrs %}",
        html_attrs,
        "{% endblock %}",
        "{% block body_class %}" + body_class + "{% endblock %}",
        "{% block body_attrs %}",
        body_attrs,
        "{% endblock %}",
        "",
        "{% block page_title %}" + title + "{% endblock %}",
        "{% block title %}" + title + "{% endblock %}",
        "",
        "{% block page_description %}",
        description,
        "{% endblock %}",
        "",
        "{% block campaign_head_extras %}",
        campaign_head_extras,
        "{% endblock %}",
        "",
        "{% block campaign_styles %}",
        campaign_styles,
        "{% endblock %}",
        "",
        "{% block content %}",
        indent(content, 2),
        "{% endblock %}",
        "",
        "{% block scripts %}",
        "{{ super() }}",
        body_scripts,
        "{% endblock %}",
        "",
    ]

    migrated = "\n".join(migrated_parts)
    migrated = re.sub(r"\n{4,}", "\n\n\n", migrated).rstrip() + "\n"

    sanity_check(migrated, BASE.read_text(encoding="utf-8", errors="replace"))

    OUT.mkdir(parents=True, exist_ok=True)
    backup = OUT / "campaign-index.html.before-campaign-base-migration"
    backup.write_text(original, encoding="utf-8")

    TEMPLATE.write_text(migrated, encoding="utf-8")

    if LATEST.exists() or LATEST.is_symlink():
        if LATEST.is_dir() and not LATEST.is_symlink():
            shutil.rmtree(LATEST)
        else:
            LATEST.unlink()

    shutil.copytree(OUT, LATEST)
    (LATEST / "campaign-index-backup-path.txt").write_text(str(backup), encoding="utf-8")

    print("Migrated campaign/index.html to _base/campaign_base.html")
    print(f"Backup: {backup}")
    print(f"Latest backup pointer: {LATEST / 'campaign-index-backup-path.txt'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
