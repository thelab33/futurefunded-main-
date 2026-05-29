import re
import sys
from pathlib import Path

ROOT = Path("apps/web/app/templates")
violations = []

for path in ROOT.rglob("*.html"):
    if ".bak." in path.name:
        continue
    text = path.read_text(encoding="utf-8", errors="ignore")
    for m in re.finditer(r"<style\b|style\s*=", text):
        line_no = text[: m.start()].count("\n") + 1
        violations.append((str(path), line_no, m.group(0)))

if violations:
    print("Inline CSS/style violations found:\\n")
    for path, line_no, token in violations:
        print(f"{path}:{line_no}: {token}")
    sys.exit(1)

print("OK: no inline CSS/style violations in live templates.")
