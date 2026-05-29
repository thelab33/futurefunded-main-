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

TEMPLATE = ROOT / "apps/web/app/templates/platform/dashboard.html"
BASE = ROOT / "apps/web/app/templates/_base/site_base.html"


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def first_index(text: str, patterns: list[str]) -> int | None:
    indexes = []
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            indexes.append(match.start())
    return min(indexes) if indexes else None


def extract(pattern: str, text: str, flags: int = re.I | re.S) -> str:
    match = re.search(pattern, text, flags)
    return match.group(1).strip() if match else ""


def collect_setup(text: str, body_start: int) -> str:
    doc_start = first_index(text, [r"<!doctype html>", r"<html\b", r"<head\b"])
    if doc_start is None:
        doc_start = 0

    prefix = text[:doc_start].strip()
    head_region = text[doc_start:body_start]

    extra = []
    for line in head_region.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if not (stripped.startswith("{%") or stripped.startswith("{#")):
            continue
        if any(x in stripped for x in ("extends", "block ", "endblock")):
            continue
        extra.append(stripped)

    parts = []
    if prefix:
        parts.append(prefix)
    if extra:
        parts.append("\n".join(extra))

    setup = "\n".join(parts).strip()

    if "html_page" not in setup:
        setup += "\n{% set html_page = 'platform-dashboard' %}"
    if "ff_page" not in setup:
        setup += "\n{% set ff_page = 'platform-dashboard' %}"

    return setup.strip()


def extract_body(text: str) -> tuple[str, str]:
    match = re.search(r"<body\b([^>]*)>([\s\S]*?)</body>", text, re.I)
    if not match:
        fail("Could not find <body>...</body> in dashboard.html")

    return match.group(1).strip(), match.group(2).strip()


def extract_body_class(body_attrs_raw: str) -> str:
    cls = extract(r"class=[\"']([^\"']+)[\"']", body_attrs_raw)
    return cls or "ff-page ff-dashboard-page ffDashBody ff-platformBrandBody"


def extract_body_attrs(body_attrs_raw: str) -> str:
    attrs = re.sub(r"\s*class=[\"'][^\"']+[\"']", "", body_attrs_raw).strip()

    required = [
        'data-ff-surface="platform-dashboard"',
        'data-ff-page="platform-dashboard"',
        'data-ff-dashboard-template="site-shell-v1"',
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


def split_scripts(body_inner: str) -> tuple[str, str]:
    scripts = re.findall(r"<script\b[\s\S]*?</script>", body_inner, re.I)
    content = re.sub(r"\n?\s*<script\b[\s\S]*?</script>\s*\n?", "\n", body_inner, flags=re.I)
    content = re.sub(r"\n{3,}", "\n\n", content).strip()
    return content, "\n\n".join(s.strip() for s in scripts if s.strip())


def extract_title(text: str) -> str:
    title = extract(r"<title[^>]*>([\s\S]*?)</title>", text)
    return title or "FutureFunded Operator Dashboard"


def extract_description(text: str) -> str:
    description = extract(
        r"<meta\s+name=[\"']description[\"']\s+content=[\"']([^\"']+)[\"']\s*/?>",
        text,
    )
    return description or (
        "FutureFunded operator dashboard for campaign readiness, donation records, "
        "sponsor review, and launch follow-up."
    )


def extract_meta_tags(text: str) -> str:
    keep = []

    for line in text.splitlines():
        stripped = line.strip()
        lower = stripped.lower()

        if not lower.startswith("<meta "):
            continue
        if "charset=" in lower or 'name="viewport"' in lower or "name='viewport'" in lower:
            continue
        if 'name="description"' in lower or "name='description'" in lower:
            continue

        if (
            'name="robots"' in lower
            or "name='robots'" in lower
            or 'name="theme-color"' in lower
            or "name='theme-color'" in lower
            or 'property="og:' in lower
            or "property='og:" in lower
            or 'name="twitter:' in lower
            or "name='twitter:" in lower
        ):
            keep.append(stripped)

    seen = set()
    out = []
    for item in keep:
        if item not in seen:
            out.append(item)
            seen.add(item)

    if not any("robots" in item.lower() for item in out):
        out.insert(0, '<meta name="robots" content="noindex,nofollow">')

    return "\n".join(out).strip()


def indent(text: str, spaces: int = 2) -> str:
    pad = " " * spaces
    return "\n".join((pad + line if line.strip() else line) for line in text.splitlines())


def main() -> int:
    if not TEMPLATE.exists():
        fail(f"Missing template: {TEMPLATE}")
    if not BASE.exists():
        fail(f"Missing base shell: {BASE}")

    original = TEMPLATE.read_text(encoding="utf-8")

    if "{% extends \"_base/site_base.html\" %}" in original or "{% extends '_base/site_base.html' %}" in original:
        print("dashboard.html already extends _base/site_base.html; no migration needed.")
        return 0

    if "<!doctype" not in original.lower() and "<html" not in original.lower():
        fail("Expected dashboard.html to own a document shell before migration.")

    body_match = re.search(r"<body\b", original, re.I)
    if not body_match:
        fail("Could not locate body start for setup extraction.")

    setup = collect_setup(original, body_match.start())
    body_attrs_raw, body_inner = extract_body(original)
    body_class = extract_body_class(body_attrs_raw)
    body_attrs = extract_body_attrs(body_attrs_raw)
    content, scripts = split_scripts(body_inner)

    if "<main" not in content.lower():
        fail("Migrated dashboard content does not contain <main>.")

    title = extract_title(original)
    description = extract_description(original)
    meta_tags = extract_meta_tags(original)

    migrated_parts = [
        setup,
        '{% extends "_base/site_base.html" %}',
        "",
        "{% block html_class %}ff-root ff-dashboardRoot{% endblock %}",
        f"{{% block body_class %}}{body_class}{{% endblock %}}",
        f"{{% block title %}}{title}{{% endblock %}}",
        "",
        "{% block page_description %}",
        description,
        "{% endblock %}",
        "",
        "{% block head_meta %}",
        meta_tags,
        "{% endblock %}",
        "",
        "{% block page_css %}",
        "{% endblock %}",
        "",
        "{% block body_attrs %}",
        body_attrs,
        "{% endblock %}",
        "",
        "{% block content %}",
        indent(content, 2),
        "{% endblock %}",
        "",
        "{% block scripts %}",
        "{{ super() }}",
    ]

    if scripts:
        migrated_parts.extend(["", scripts])

    migrated_parts.extend(["{% endblock %}", ""])

    migrated = "\n".join(migrated_parts)
    migrated = re.sub(r"\n{4,}", "\n\n\n", migrated).rstrip() + "\n"

    OUT.mkdir(parents=True, exist_ok=True)
    backup = OUT / "dashboard.html.before-shell-migration"
    backup.write_text(original, encoding="utf-8")

    TEMPLATE.write_text(migrated, encoding="utf-8")

    if LATEST.exists() or LATEST.is_symlink():
        if LATEST.is_dir() and not LATEST.is_symlink():
            shutil.rmtree(LATEST)
        else:
            LATEST.unlink()

    shutil.copytree(OUT, LATEST)
    (LATEST / "dashboard-backup-path.txt").write_text(str(backup), encoding="utf-8")

    print("Migrated dashboard.html to _base/site_base.html")
    print(f"Backup: {backup}")
    print(f"Latest backup pointer: {LATEST / 'dashboard-backup-path.txt'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
