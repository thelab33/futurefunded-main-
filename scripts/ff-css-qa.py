#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

DEFAULT_FILES = [
    "apps/web/app/static/css/ff.css",
    "apps/web/app/static/css/ff.homepage-flagship.css",
    "apps/web/app/static/css/ff.campaign-flagship.css",
    "apps/web/app/static/css/ff.campaign-polish.css",
]

ERROR_PATTERNS = {
    "merge conflict marker": re.compile(r"^(<<<<<<<|=======|>>>>>>>)", re.M),
    "unclosed template marker": re.compile(r"\{\{|\{%|%\}|\}\}"),
    "javascript url": re.compile(r"url\(\s*['\"]?javascript:", re.I),
}

WARN_PATTERNS = {
    "important usage": re.compile(r"!important"),
    "global outline none": re.compile(r"(^|[;{]\s*)outline\s*:\s*none\s*;", re.I),
    "fixed pixel body width": re.compile(r"\bwidth\s*:\s*[1-9]\d{3,}px\s*;", re.I),
}


def strip_comments_and_strings(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r'"(?:\\.|[^"\\])*"', '""', text)
    text = re.sub(r"'(?:\\.|[^'\\])*'", "''", text)
    return text


def brace_balance(text: str) -> tuple[bool, int]:
    clean = strip_comments_and_strings(text)
    depth = 0
    for ch in clean:
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth < 0:
                return False, depth
    return depth == 0, depth


def duplicate_wave_markers(text: str) -> list[str]:
    markers = re.findall(r"/\*\s*===\s*(FutureFunded[^*]+?START)\s*===\s*\*/", text)
    seen = {}
    dupes = []
    for marker in markers:
        seen[marker] = seen.get(marker, 0) + 1
    for marker, count in seen.items():
        if count > 1:
            dupes.append(f"{marker} x{count}")
    return dupes


def check_file(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    failures = 0

    print(f"\n## {path}")

    ok, depth = brace_balance(text)
    if ok:
        print("✅ braces balanced")
    else:
        print(f"❌ braces unbalanced depth={depth}")
        failures += 1

    for label, pattern in ERROR_PATTERNS.items():
        if pattern.search(text):
            print(f"❌ {label}")
            failures += 1
        else:
            print(f"✅ no {label}")

    dupes = duplicate_wave_markers(text)
    if dupes:
        print("❌ duplicate wave markers: " + ", ".join(dupes))
        failures += 1
    else:
        print("✅ no duplicate wave markers")

    for label, pattern in WARN_PATTERNS.items():
        count = len(pattern.findall(text))
        if count:
            print(f"⚠️  {label}: {count}")
        else:
            print(f"✅ no {label}")

    return failures


def main() -> int:
    files = (
        [Path(arg) for arg in sys.argv[1:]]
        if len(sys.argv) > 1
        else [Path(p) for p in DEFAULT_FILES]
    )
    missing = [str(p) for p in files if not p.exists()]
    if missing:
        print("❌ missing files:")
        for p in missing:
            print(f"  {p}")
        return 2

    failures = 0
    for path in files:
        failures += check_file(path)

    print()
    if failures:
        print(f"❌ CSS QA failed with {failures} blocking issue(s)")
        return 1

    print("✅ CSS QA passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
