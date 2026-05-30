#!/usr/bin/env python3
from pathlib import Path
from html.parser import HTMLParser

class Parser(HTMLParser):
    pass

failed = False
files = sorted(Path("apps/web/app/templates").rglob("*.html"))

for file in files:
    try:
        Parser().feed(file.read_text(encoding="utf-8", errors="replace"))
        print(f"✅ HTML parse: {file}")
    except Exception as exc:
        failed = True
        print(f"❌ HTML parse failed: {file}: {exc}")

raise SystemExit(1 if failed else 0)
