#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import datetime as dt
import re
import subprocess
import shutil

ROOT = Path.cwd()
STAMP = dt.datetime.now().strftime("%Y%m%d%H%M%S")

FILES_TO_QUARANTINE = [
    "apps/web/app/static/css/campaign.public.css",
    "apps/web/app/static/css/ff-checkout-csp.css",
    "apps/web/app/templates/campaign_premium.html",
]

COMMENT_FIXES = {
    "apps/web/app/static/css/campaign.css": [
        ("campaign.public.css", "legacy public campaign rules"),
        ("ff-checkout-csp.css", "legacy checkout CSP helpers"),
        ("/* ===== BEGIN campaign.public.css authority ===== */", "/* ===== BEGIN absorbed public campaign authority ===== */"),
        ("/* ===== END campaign.public.css authority ===== */", "/* ===== END absorbed public campaign authority ===== */"),
    ],
    "apps/web/app/static/css/ff.css": [
        ("campaign_premium.html", "legacy premium campaign template"),
    ],
}

QUARANTINE_ROOT = ROOT / "apps/web/app/_quarantine" / f"ui-core-final-blockers-{STAMP}"
REPORT = ROOT / "docs/release-proof" / f"ui-core-final-blockers-{STAMP}.md"


def run(cmd: list[str]) -> tuple[int, str]:
    p = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)
    return p.returncode, (p.stdout + p.stderr).strip()


def is_tracked(path: Path) -> bool:
    code, _ = run(["git", "ls-files", "--error-unmatch", path.relative_to(ROOT).as_posix()])
    return code == 0


def git_mv_or_move(src: Path, dst: Path) -> str:
    dst.parent.mkdir(parents=True, exist_ok=True)

    if is_tracked(src):
        code, out = run(["git", "mv", src.relative_to(ROOT).as_posix(), dst.relative_to(ROOT).as_posix()])
        if code != 0:
            raise RuntimeError(out)
        return "git-mv"

    shutil.move(str(src), str(dst))
    return "moved"


def grep_active_refs() -> str:
    code, out = run([
        "grep", "-RIn",
        "--exclude-dir=_quarantine",
        "--exclude=*.bak-*",
        "-E",
        r"campaign\.public\.css|ff-checkout-csp\.css|campaign_premium\.html",
        "apps/web/app/templates",
        "apps/web/app/static/css",
        "apps/web/app/static/js",
    ])
    return out


def main() -> int:
    before = grep_active_refs()

    changed_comments = []
    for rel, replacements in COMMENT_FIXES.items():
        p = ROOT / rel
        if not p.exists():
            continue

        s = p.read_text(encoding="utf-8", errors="replace")
        original = s

        for old, new in replacements:
            s = s.replace(old, new)

        if s != original:
            p.write_text(s, encoding="utf-8")
            changed_comments.append(rel)

    moved = []
    missing = []

    for rel in FILES_TO_QUARANTINE:
        src = ROOT / rel
        if not src.exists():
            missing.append(rel)
            continue

        dst = QUARANTINE_ROOT / rel
        action = git_mv_or_move(src, dst)
        moved.append((rel, dst.relative_to(ROOT).as_posix(), action))

    after = grep_active_refs()

    lines = [
        "# FutureFunded Final UI Core Blocker Cleanup",
        "",
        f"- Timestamp: `{STAMP}`",
        f"- Quarantine root: `{QUARANTINE_ROOT.relative_to(ROOT)}`",
        "",
        "## Comment references cleaned",
        "",
    ]

    if changed_comments:
        for rel in changed_comments:
            lines.append(f"- `{rel}`")
    else:
        lines.append("- none")

    lines += [
        "",
        "## Files quarantined",
        "",
    ]

    for rel, dst, action in moved:
        lines.append(f"- `{rel}` → `{dst}` ({action})")

    if missing:
        lines += ["", "## Missing", ""]
        for rel in missing:
            lines.append(f"- `{rel}`")

    lines += [
        "",
        "## Active references before",
        "",
        "```",
        before or "(none)",
        "```",
        "",
        "## Active references after",
        "",
        "```",
        after or "(none)",
        "```",
    ]

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("\n".join(lines))

    if after.strip():
        raise SystemExit("Active references still remain. Review report before committing.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
