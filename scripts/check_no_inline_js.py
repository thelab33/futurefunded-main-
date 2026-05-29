NON_EXEC_SCRIPT_TYPES = {"application/ld+json", "application/json"}

import re
import sys
from pathlib import Path

ROOT = Path("apps/web/app/templates")
violations = []

script_block = re.compile(
    r"<script\b(?![^>]*\bsrc=)(?![^>]*type=['\"]application/(ld\+json|json)['\"])[^>]*>",
    re.IGNORECASE,
)
inline_handler = re.compile(r"\son[a-z]+\s*=", re.IGNORECASE)

for path in ROOT.rglob("*.html"):
    if ".bak." in path.name:
        continue
    text = path.read_text(encoding="utf-8", errors="ignore")
    for patt, label in [
        (script_block, "inline <script>"),
        (inline_handler, "inline event handler"),
    ]:
        for m in patt.finditer(text):
            line_no = text[: m.start()].count("\n") + 1
            violations.append((str(path), line_no, label))

if violations:
    print("Inline JS violations found:\\n")
    for path, line_no, label in violations:
        print(f"{path}:{line_no}: {label}")
    sys.exit(1)

print("OK: no inline JS/event-handler violations in live templates.")
