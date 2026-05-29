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

TEMPLATE = ROOT / "apps/web/app/templates/platform/index.html"
BASE = ROOT / "apps/web/app/templates/_base/site_base.html"


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def extract(pattern: str, text: str, flags: int = re.I | re.S) -> str:
    match = re.search(pattern, text, flags)
    return match.group(1).strip() if match else ""


def first_index(text: str, patterns: list[str]) -> int | None:
    indexes = []
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            indexes.append(match.start())
    return min(indexes) if indexes else None


def clean_orphan_jinja_comments(text: str) -> str:
    # Remove unclosed top-level banner comments before the first setup variable.
    while text.count("{#") != text.count("#}"):
        start = text.find("{#")
        if start == -1:
            break
        next_set = text.find("{% set", start)
        close = text.find("#}", start)
        if next_set != -1 and (close == -1 or next_set < close):
            text = text[:start].rstrip() + "\n" + text[next_set:].lstrip()
        else:
            break
    return text


def collect_setup(text: str, body_start: int) -> str:
    doc_start = first_index(text, [r"<!doctype html>", r"<html\b", r"<head\b"])
    if doc_start is None:
        doc_start = 0

    prefix = clean_orphan_jinja_comments(text[:doc_start].strip())
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
        setup += "\n{% set html_page = 'platform' %}"
    if "ff_page" not in setup:
        setup += "\n{% set ff_page = 'platform' %}"

    return setup.strip()


def extract_html_attrs(text: str) -> str:
    raw = extract(r"<html\b([^>]*)>", text)
    raw = re.sub(r"\s*lang=[\"'][^\"']+[\"']", "", raw, flags=re.I)
    raw = re.sub(r"\s*class=[\"'][^\"']+[\"']", "", raw, flags=re.I).strip()

    attrs = []
    if raw:
        attrs.append(raw)

    joined = raw
    required = [
        'data-ff-page="platform"',
        'data-ff-shell="site-base-v1"',
    ]

    for attr in required:
        name = attr.split("=", 1)[0]
        if name not in joined:
            attrs.append(attr)

    return "\n".join(attrs).strip()


def extract_body(text: str) -> tuple[str, str]:
    match = re.search(r"<body\b([^>]*)>([\s\S]*?)</body>", text, re.I)
    if not match:
        fail("Could not find <body>...</body> in platform/index.html")
    return match.group(1).strip(), match.group(2).strip()


def extract_body_class(body_attrs_raw: str) -> str:
    cls = extract(r"class=[\"']([^\"']+)[\"']", body_attrs_raw)
    return cls or "ff-page ff-platformBody ff-platformBrandBody"


def extract_body_attrs(body_attrs_raw: str) -> str:
    attrs = re.sub(r"\s*class=[\"'][^\"']+[\"']", "", body_attrs_raw).strip()

    lines = []
    if attrs:
        lines.append(attrs)

    joined = attrs
    required = [
        'data-ff-surface="platform"',
        'data-ff-page="platform"',
        'data-ff-platform-template="site-shell-v1"',
    ]

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


def extract_head(text: str) -> str:
    head = extract(r"<head\b[^>]*>([\s\S]*?)</head>", text)
    if not head:
        fail("Could not extract <head>...</head> from platform/index.html")
    return head


def extract_title(head: str) -> str:
    title = extract(r"<title[^>]*>([\s\S]*?)</title>", head)
    return title or "FutureFunded"


def extract_description(head: str) -> str:
    description = extract(
        r"<meta\s+name=[\"']description[\"']\s+content=[\"']([^\"']+)[\"']\s*/?>",
        head,
    )
    return description or (
        "FutureFunded helps teams, schools, clubs, and nonprofits launch trusted "
        "fundraising campaigns with donations, sponsors, and operator-ready workflows."
    )


def extract_head_scripts(head: str) -> str:
    scripts = re.findall(r"<script\b[\s\S]*?</script>", head, re.I)
    return "\n\n".join(s.strip() for s in scripts if s.strip())


def extract_head_meta_and_links(head: str) -> str:
    cleaned = re.sub(r"<script\b[\s\S]*?</script>", " ", head, flags=re.I)

    keep: list[str] = []
    for line in cleaned.splitlines():
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

        # CSS is owned by site_base now. Keep SEO, social, theme, icons, canonical, preconnect.
        if (
            lower.startswith("<meta ")
            or lower.startswith("<link ")
        ):
            if ".css" in lower or "rel=\"stylesheet\"" in lower or "rel='stylesheet'" in lower:
                continue
            if "rel=\"preload\"" in lower and ".css" in lower:
                continue
            keep.append(stripped)

    seen = set()
    out = []
    for item in keep:
        if item not in seen:
            out.append(item)
            seen.add(item)

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
        print("platform/index.html already extends _base/site_base.html; no migration needed.")
        return 0

    if "<!doctype" not in original.lower() and "<html" not in original.lower():
        fail("Expected platform/index.html to own a document shell before migration.")

    body_match = re.search(r"<body\b", original, re.I)
    if not body_match:
        fail("Could not locate body start.")

    head = extract_head(original)
    setup = collect_setup(original, body_match.start())
    html_attrs = extract_html_attrs(original)
    body_attrs_raw, body_inner = extract_body(original)
    body_class = extract_body_class(body_attrs_raw)
    body_attrs = extract_body_attrs(body_attrs_raw)
    content, body_scripts = split_scripts(body_inner)

    if "<main" not in content.lower():
        fail("Migrated platform homepage content does not contain <main>.")

    title = extract_title(head)
    description = extract_description(head)
    head_meta = extract_head_meta_and_links(head)
    head_scripts = extract_head_scripts(head)

    scripts = "\n\n".join(x for x in [head_scripts, body_scripts] if x.strip())

    migrated_parts = [
        setup,
        '{% extends "_base/site_base.html" %}',
        "",
        "{% block html_class %}ff-root ff-platformRoot{% endblock %}",
        "{% block html_attrs %}",
        html_attrs,
        "{% endblock %}",
        f"{{% block body_class %}}{body_class}{{% endblock %}}",
        f"{{% block title %}}{title}{{% endblock %}}",
        "",
        "{% block page_description %}",
        description,
        "{% endblock %}",
        "",
        "{% block head_meta %}",
        head_meta,
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
    backup = OUT / "platform-index.html.before-shell-migration"
    backup.write_text(original, encoding="utf-8")

    TEMPLATE.write_text(migrated, encoding="utf-8")

    if LATEST.exists() or LATEST.is_symlink():
        if LATEST.is_dir() and not LATEST.is_symlink():
            shutil.rmtree(LATEST)
        else:
            LATEST.unlink()

    shutil.copytree(OUT, LATEST)
    (LATEST / "platform-index-backup-path.txt").write_text(str(backup), encoding="utf-8")

    print("Migrated platform/index.html to _base/site_base.html")
    print(f"Backup: {backup}")
    print(f"Latest backup pointer: {LATEST / 'platform-index-backup-path.txt'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
