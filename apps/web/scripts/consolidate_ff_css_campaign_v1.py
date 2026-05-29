import re
import sys
import time
from pathlib import Path

CSS = Path("app/static/css/ff.css")

START_TITLE = "99. CAMPAIGN V1 FLAGSHIP EXPERIENCE"
END_TITLE = "FINAL MOBILE DENSITY PASS END"

NEW_HEADER = """/* ==========================================================================
   99. CAMPAIGN EXPERIENCE V1 — CONSOLIDATED
   Canonical campaign-page styles for the FutureFunded flagship public campaign.

   Notes:
   - Consolidated from the iterative campaign V1 patch stack.
   - Cascade order is preserved.
   - Section wrapper comments were compressed for maintainability.
   - Do not append future campaign patches below this block unless temporary.
   ========================================================================== */
"""

NEW_FOOTER = """
/* ==========================================================================
   CAMPAIGN EXPERIENCE V1 — CONSOLIDATED END
   ========================================================================== */
"""

HEADER_RE = re.compile(
    r"/\*\s*=+\s*\n\s*(\d+)\.\s*([^\n]+?)\s*\n(?:.*?\n)*?\s*=+\s*\*/",
    re.S,
)

END_RE = re.compile(
    r"/\*\s*=+\s*\n\s*([A-Z0-9 .:+/,&'’()_-]+?END)\s*\n\s*=+\s*\*/",
    re.S,
)


def fail(message: str) -> None:
    print(f"❌ {message}")
    sys.exit(1)


def main() -> None:
    if not CSS.exists():
        fail(f"Missing {CSS}")

    text = CSS.read_text(encoding="utf-8")

    marker_pos = text.find(START_TITLE)
    if marker_pos == -1:
        fail(f"Could not find start marker: {START_TITLE}")

    start = text.rfind("/*", 0, marker_pos)
    if start == -1:
        fail("Could not locate opening comment for campaign CSS stack")

    end_marker_pos = text.find(END_TITLE, marker_pos)
    if end_marker_pos == -1:
        fail(f"Could not find end marker: {END_TITLE}")

    end = text.find("*/", end_marker_pos)
    if end == -1:
        fail("Could not locate closing comment for final campaign CSS stack")
    end += 2

    before = text[:start].rstrip()
    chunk = text[start:end].strip()
    after = text[end:].lstrip()

    original_len = len(chunk)

    def header_repl(match: re.Match) -> str:
        number = match.group(1).strip()
        title = " ".join(match.group(2).strip().split())
        if title.endswith("END"):
            return ""
        return f"/* campaign-v1:{number} — {title} */"

    chunk = HEADER_RE.sub(header_repl, chunk)
    chunk = END_RE.sub("", chunk)

    # Collapse excessive whitespace created by removing wrapper comments.
    chunk = re.sub(r"\n{4,}", "\n\n\n", chunk).strip()

    consolidated = f"{NEW_HEADER}\n{chunk}\n{NEW_FOOTER}"

    new_text = f"{before}\n\n{consolidated}\n"
    if after:
        new_text += f"\n{after}"

    if new_text == text:
        print("✅ No changes needed; CSS already appears consolidated.")
        return

    backup_dir = Path("../../.backup_archive/css")
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = int(time.time())
    backup = backup_dir / f"ff.css.pre-campaign-v1-consolidation-{stamp}.css"
    backup.write_text(text, encoding="utf-8")

    CSS.write_text(new_text, encoding="utf-8")

    print("✅ Consolidated campaign V1 CSS stack")
    print(f"Backup: {backup}")
    print(f"Original campaign chunk bytes: {original_len:,}")
    print(f"New campaign chunk bytes: {len(consolidated):,}")


if __name__ == "__main__":
    main()
