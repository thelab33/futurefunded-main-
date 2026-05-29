#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fnmatch
import json
import shutil
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "artifacts" / "audit"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

TRASH_ROOT = ROOT / ".repo-cleanup-trash"

IGNORE_LINES = [
    "",
    "# FutureFunded local/runtime/generated cleanup",
    ".env.local",
    ".stripe-local-whsec",
    ".repo-cleanup-trash/",
    "__pycache__/",
    "*.py[cod]",
    ".pytest_cache/",
    ".ruff_cache/",
    ".mypy_cache/",
    ".coverage",
    "htmlcov/",
    "node_modules/",
    "test-results/",
    "artifacts/frontend-screenshots/",
    "artifacts/screenshots/",
    "artifacts/functionality/",
    "apps/web/artifacts/",
    "frontend-contract-report.json",
    "frontend-contract-report.txt",
    "*.zip",
    "*.tgz",
    "*.tar.gz",
    "*.bak",
    "*.bak-*",
    "*.bak.*",
    "*.sqlite3",
    "futurefunded.egg-info/",
]

DELETE_DIR_NAMES = {
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "htmlcov",
    "futurefunded.egg-info",
}

DELETE_PATH_PREFIXES = [
    "test-results/",
    "artifacts/frontend-screenshots/",
    "artifacts/screenshots/",
    "artifacts/functionality/",
    "apps/web/artifacts/",
]

DELETE_GLOBS = [
    "*.pyc",
    "*.pyo",
    "*.bak",
    "*.bak-*",
    "*.bak.*",
    "*.zip",
    "*.tgz",
    "*.tar.gz",
    "frontend-contract-report.json",
    "frontend-contract-report.txt",
    "*.sqlite3",
]

REVIEW_ONLY_GLOBS = [
    "futurefunded_supreme_campaign_pass.py",
    "futurefunded-campaign-partials.clean.zip",
    "futurefunded-campaign-partials.tgz",
    "futurefunded-snapshot.zip",
    "futurefunded-visual-qa.zip",
]

ACTIVE_CSS = {
    "apps/web/app/static/css/ff.css",
    "apps/web/app/static/css/ff.homepage-flagship.css",
    "apps/web/app/static/css/ff.campaign-polish.css",
    "apps/web/app/static/css/ff.operator-dashboard.css",
}

ACTIVE_JS_KEEP = {
    "apps/web/app/static/js/ff-app.js",
    "apps/web/app/static/js/ff-campaign-amount-guard.js",
    "apps/web/app/static/js/ff-campaign-launch-guard-v2.js",
    "apps/web/app/static/js/ff-campaign-live-fomo.js",
    "apps/web/app/static/js/ff-provider-quarantine.js",
    "apps/web/app/static/js/ff-sponsor-modal-contract.js",
    "apps/web/app/static/js/ff-operator-dashboard.js",
    "apps/web/app/static/js/islands/donate.js",
    "apps/web/app/static/js/islands/faq.js",
    "apps/web/app/static/js/islands/onboarding.js",
    "apps/web/app/static/js/islands/share.js",
    "apps/web/app/static/js/islands/sponsor.js",
    "apps/web/app/static/js/platform-nav.js",
    "apps/web/app/static/js/csp-safe-init.js",
}


def run(cmd: list[str]) -> str:
    try:
        return subprocess.check_output(cmd, cwd=ROOT, text=True, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError as exc:
        return exc.output or ""


def git_files() -> set[str]:
    tracked = run(["git", "ls-files"]).splitlines()
    others = run(["git", "ls-files", "--others", "--exclude-standard"]).splitlines()
    return set(tracked + others)


def is_git_tracked(path: str) -> bool:
    out = run(["git", "ls-files", "--error-unmatch", path])
    return bool(out.strip())


def normalize(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def has_reference(needle: str) -> bool:
    search_roots = [
        ROOT / "apps" / "web" / "app" / "templates",
        ROOT / "apps" / "web" / "app" / "static" / "js",
        ROOT / "apps" / "web" / "app" / "static" / "css",
        ROOT / "scripts",
    ]

    for root in search_roots:
        if not root.exists():
            continue
        for p in root.rglob("*"):
            if p.is_dir():
                continue
            if p.suffix.lower() not in {".html", ".js", ".css", ".py", ".mjs", ".sh"}:
                continue
            try:
                if needle in p.read_text(encoding="utf-8", errors="ignore"):
                    return True
            except Exception:
                continue
    return False


def classify(path: Path) -> tuple[str, str]:
    rel = normalize(path)

    if rel in ACTIVE_CSS or rel in ACTIVE_JS_KEEP:
        return "keep", "active frontend asset"

    if rel == "apps/web/app/static/css/ff.product-handoff.css":
        if has_reference("ff.product-handoff.css"):
            return "review", "unused handoff css has references; inspect before deleting"
        return "delete", "unused experimental handoff css not referenced at runtime"

    if any(rel.startswith(prefix) for prefix in DELETE_PATH_PREFIXES):
        return "delete", "generated artifact directory"

    if any(part in DELETE_DIR_NAMES for part in path.parts):
        return "delete", "generated/cache directory"

    name = path.name

    for pat in DELETE_GLOBS:
        if fnmatch.fnmatch(name, pat) or fnmatch.fnmatch(rel, pat):
            return "delete", f"matches generated/backup pattern {pat}"

    for pat in REVIEW_ONLY_GLOBS:
        if fnmatch.fnmatch(name, pat) or fnmatch.fnmatch(rel, pat):
            return "review", f"large/generated project artifact: {pat}"

    return "keep", "source or active asset"


def move_to_trash(path: Path, stamp: str) -> None:
    rel = normalize(path)
    dest = TRASH_ROOT / stamp / rel
    dest.parent.mkdir(parents=True, exist_ok=True)

    if path.is_dir():
        shutil.move(str(path), str(dest))
    else:
        shutil.move(str(path), str(dest))


def update_gitignore() -> None:
    p = ROOT / ".gitignore"
    existing = p.read_text(encoding="utf-8") if p.exists() else ""
    lines = existing.splitlines()

    changed = False
    for line in IGNORE_LINES:
        if line and line not in lines:
            lines.append(line)
            changed = True
        elif not line:
            continue

    if changed:
        p.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply", action="store_true", help="Move delete candidates into .repo-cleanup-trash"
    )
    args = parser.parse_args()

    files = sorted(git_files())
    rows = []

    # Include tracked/visible files plus generated dirs that git may ignore.
    extra_roots = [
        ROOT / "artifacts",
        ROOT / "apps" / "web" / "artifacts",
        ROOT / "futurefunded.egg-info",
    ]

    candidates = set(files)

    for extra in extra_roots:
        if extra.exists():
            for p in extra.rglob("*"):
                candidates.add(normalize(p))

    for rel in sorted(candidates):
        p = ROOT / rel
        if not p.exists():
            continue

        action, reason = classify(p)
        if action == "keep":
            continue

        rows.append(
            {
                "path": rel,
                "action": action,
                "reason": reason,
                "tracked": is_git_tracked(rel),
                "is_dir": p.is_dir(),
            }
        )

    stamp = time.strftime("%Y%m%d-%H%M%S")

    if args.apply:
        update_gitignore()

        # Move deepest paths first so files inside dirs do not race dir moves.
        for row in sorted(
            [r for r in rows if r["action"] == "delete"],
            key=lambda r: r["path"].count("/"),
            reverse=True,
        ):
            p = ROOT / row["path"]
            if p.exists():
                move_to_trash(p, stamp)

    report = {
        "apply": args.apply,
        "trash": str(TRASH_ROOT / stamp) if args.apply else None,
        "delete_count": sum(1 for r in rows if r["action"] == "delete"),
        "review_count": sum(1 for r in rows if r["action"] == "review"),
        "items": rows,
    }

    out_json = REPORT_DIR / "ff_cleanup_repo_report.json"
    out_md = REPORT_DIR / "ff_cleanup_repo_report.md"

    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = []
    lines.append("# FutureFunded Repo Cleanup Report")
    lines.append("")
    lines.append(f"Applied: **{args.apply}**")
    lines.append(f"Delete candidates: **{report['delete_count']}**")
    lines.append(f"Review-only candidates: **{report['review_count']}**")
    if args.apply:
        lines.append(f"Trash: `{report['trash']}`")
    lines.append("")
    lines.append("## Delete Candidates")
    lines.append("")
    lines.append("| Path | Tracked | Reason |")
    lines.append("|---|---:|---|")
    for row in rows:
        if row["action"] != "delete":
            continue
        lines.append(f"| `{row['path']}` | {row['tracked']} | {row['reason']} |")
    lines.append("")
    lines.append("## Review Only")
    lines.append("")
    lines.append("| Path | Tracked | Reason |")
    lines.append("|---|---:|---|")
    for row in rows:
        if row["action"] != "review":
            continue
        lines.append(f"| `{row['path']}` | {row['tracked']} | {row['reason']} |")

    out_md.write_text("\n".join(lines), encoding="utf-8")

    print("FutureFunded cleanup scan complete")
    print(f"Applied: {args.apply}")
    print(f"Delete candidates: {report['delete_count']}")
    print(f"Review-only candidates: {report['review_count']}")
    print(f"Report: {out_md}")

    if not args.apply:
        print("")
        print("Dry run only. Review the report, then run:")
        print("  python scripts/ff_cleanup_repo.py --apply")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
