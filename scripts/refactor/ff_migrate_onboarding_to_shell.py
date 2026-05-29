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

TEMPLATE = ROOT / "apps/web/app/templates/platform/onboarding.html"
BASE = ROOT / "apps/web/app/templates/_base/site_base.html"


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def extract(pattern: str, text: str, flags: int = re.I | re.S) -> str:
    match = re.search(pattern, text, flags)
    return match.group(1).strip() if match else ""


def extract_main(text: str) -> tuple[str, int, int]:
    match = re.search(r"(<main\b[\s\S]*?</main>)", text, re.I)
    if not match:
        fail("Could not find a complete <main>...</main> region in onboarding.html")
    return match.group(1).rstrip(), match.start(), match.end()


def extract_scripts_after_main(text: str, main_end: int) -> str:
    after = text[main_end:]
    body_close = re.search(r"</body>", after, re.I)
    if body_close:
        after = after[: body_close.start()]

    scripts = re.findall(r"<script\b[\s\S]*?</script>", after, re.I)
    cleaned = "\n\n".join(s.strip() for s in scripts if s.strip())
    return cleaned


def extract_meta_tags(text: str) -> list[str]:
    keep: list[str] = []

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        is_meta = stripped.lower().startswith("<meta ")
        if not is_meta:
            continue

        lower = stripped.lower()

        # site_base usually owns charset/viewport; keep page-specific SEO/theme only.
        if 'name="description"' in lower or "name='description'" in lower:
            continue
        if "charset=" in lower or 'name="viewport"' in lower or "name='viewport'" in lower:
            continue

        if (
            'name="robots"' in lower
            or "name='robots'" in lower
            or 'name="theme-color"' in lower
            or "name='theme-color'" in lower
            or "property=\"og:" in lower
            or "property='og:" in lower
            or 'name="twitter:' in lower
            or "name='twitter:" in lower
        ):
            keep.append(stripped)

    # De-dupe while preserving order.
    seen = set()
    out = []
    for item in keep:
        if item not in seen:
            out.append(item)
            seen.add(item)

    return out


def extract_body_class(text: str) -> str:
    body_tag = extract(r"<body\b([^>]*)>", text)
    if not body_tag:
        return "ffOnboardV2Body ff-platformBrandBody"

    cls = extract(r"class=[\"']([^\"']+)[\"']", body_tag)
    if cls:
        return cls

    return "ffOnboardV2Body ff-platformBrandBody"


def extract_body_attrs(text: str) -> str:
    body_tag = extract(r"<body\b([^>]*)>", text)
    attrs: list[str] = []

    if body_tag:
        for match in re.finditer(r"\s(data-[\w:-]+)(?:=([\"'][^\"']*[\"']))?", body_tag):
            name = match.group(1)
            value = match.group(2)
            attrs.append(f"{name}={value}" if value else name)

    required = [
        'data-ff-surface="platform-onboarding"',
        'data-ff-page="platform-onboarding"',
        'data-ff-onboarding-template="site-shell-v1"',
    ]

    joined = "\n".join(attrs)
    for attr in required:
        name = attr.split("=", 1)[0]
        if name not in joined:
            attrs.append(attr)

    return "\n".join(attrs)


def indent_block(text: str, spaces: int = 2) -> str:
    pad = " " * spaces
    return "\n".join((pad + line if line.strip() else line) for line in text.splitlines())


def main() -> int:
    if not TEMPLATE.exists():
        fail(f"Missing template: {TEMPLATE}")
    if not BASE.exists():
        fail(f"Missing base shell: {BASE}")

    original = TEMPLATE.read_text(encoding="utf-8")

    if "{% extends \"_base/site_base.html\" %}" in original or "{% extends '_base/site_base.html' %}" in original:
        print("onboarding.html already extends _base/site_base.html; no migration needed.")
        return 0

    if "<!DOCTYPE html" not in original and "<!doctype html" not in original:
        fail("Expected onboarding.html to own a document shell before migration.")

    main_html, _main_start, main_end = extract_main(original)
    scripts = extract_scripts_after_main(original, main_end)

    title = extract(r"<title[^>]*>([\s\S]*?)</title>", original)
    if not title:
        title = "FutureFunded Launch Workspace"

    description = extract(
        r"<meta\s+name=[\"']description[\"']\s+content=[\"']([^\"']+)[\"']\s*/?>",
        original,
    )
    if not description:
        description = (
            "Set up a FutureFunded campaign with story, goal, brand colors, "
            "sponsor packages, and giving readiness."
        )

    body_class = extract_body_class(original)
    body_attrs = extract_body_attrs(original)
    meta_tags = extract_meta_tags(original)

    needs_header_macro = "ff_shell_header(" in main_html or "ff_shell_header(" in original
    header_import = (
        "{% from \"_partials/ff_shell_header.html\" import ff_shell_header %}\n"
        if needs_header_macro
        else ""
    )

    head_meta = "\n".join(meta_tags).strip()

    migrated_parts: list[str] = []

    migrated_parts.append(header_import.rstrip())
    migrated_parts.append("{% set html_page = 'platform-onboarding' %}")
    migrated_parts.append("{% set ff_page = 'platform-onboarding' %}")
    migrated_parts.append("{% extends \"_base/site_base.html\" %}")
    migrated_parts.append("")
    migrated_parts.append("{% block html_class %}ff-root ff-onboardRoot{% endblock %}")
    migrated_parts.append(f"{{% block body_class %}}{body_class}{{% endblock %}}")
    migrated_parts.append(f"{{% block title %}}{title}{{% endblock %}}")
    migrated_parts.append("")
    migrated_parts.append("{% block page_description %}")
    migrated_parts.append(description)
    migrated_parts.append("{% endblock %}")
    migrated_parts.append("")
    migrated_parts.append("{% block head_meta %}")
    if head_meta:
        migrated_parts.append(head_meta)
    migrated_parts.append("{% endblock %}")
    migrated_parts.append("")
    migrated_parts.append("{% block page_css %}")
    migrated_parts.append("{% endblock %}")
    migrated_parts.append("")
    migrated_parts.append("{% block body_attrs %}")
    migrated_parts.append(body_attrs)
    migrated_parts.append("{% endblock %}")
    migrated_parts.append("")
    migrated_parts.append("{% block content %}")
    migrated_parts.append(indent_block(main_html, 2))
    migrated_parts.append("{% endblock %}")
    migrated_parts.append("")

    migrated_parts.append("{% block scripts %}")
    migrated_parts.append("{{ super() }}")
    if scripts:
        migrated_parts.append("")
        migrated_parts.append(scripts)
    migrated_parts.append("{% endblock %}")
    migrated_parts.append("")

    migrated = "\n".join(part for part in migrated_parts if part is not None)
    migrated = re.sub(r"\n{4,}", "\n\n\n", migrated).rstrip() + "\n"

    OUT.mkdir(parents=True, exist_ok=True)
    backup = OUT / "onboarding.html.before-shell-migration"
    backup.write_text(original, encoding="utf-8")

    TEMPLATE.write_text(migrated, encoding="utf-8")

    if LATEST.exists() or LATEST.is_symlink():
        if LATEST.is_dir() and not LATEST.is_symlink():
            shutil.rmtree(LATEST)
        else:
            LATEST.unlink()
    shutil.copytree(OUT, LATEST)

    (LATEST / "onboarding-backup-path.txt").write_text(str(backup), encoding="utf-8")

    print("Migrated onboarding.html to _base/site_base.html")
    print(f"Backup: {backup}")
    print(f"Latest backup pointer: {LATEST / 'onboarding-backup-path.txt'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
