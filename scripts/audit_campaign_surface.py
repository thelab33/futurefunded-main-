from __future__ import annotations

import collections
import re
import sys
from pathlib import Path

ROOT = Path.cwd()
TEMPLATES = ROOT / "apps/web/app/templates"
ENTRY = TEMPLATES / "campaign/index.html"
CSS = ROOT / "apps/web/app/static/css/ff.css"
OUT = ROOT / "tmp/campaign-surface-audit"
OUT.mkdir(parents=True, exist_ok=True)

JINJA_PATTERNS = {
    "extends": re.compile(r'{%\s*extends\s+["\']([^"\']+)["\']\s*%}'),
    "include": re.compile(r'{%\s*include\s+["\']([^"\']+)["\']'),
    "import": re.compile(r'{%\s*import\s+["\']([^"\']+)["\']'),
    "from": re.compile(r'{%\s*from\s+["\']([^"\']+)["\']\s+import\b'),
}

CLASS_ATTR = re.compile(r'class\s*=\s*(["\'])(.*?)\1', re.S)
TOKEN = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")
CSS_CLASS = re.compile(r"\.((?:ff|is)-[A-Za-z0-9_-]+)")
SELECTOR_BLOCK = re.compile(r"(^|\n)\s*([^@\n][^{]+)\{", re.M)


def rel(path: Path) -> str:
    return path.relative_to(TEMPLATES).as_posix()


def resolve(ref: str) -> Path | None:
    path = TEMPLATES / ref
    return path if path.exists() else None


def parse_refs(text: str):
    refs: dict[str, list[str]] = {k: [] for k in JINJA_PATTERNS}
    for kind, pattern in JINJA_PATTERNS.items():
        refs[kind] = pattern.findall(text)
    return refs


def walk(path: Path, graph, seen: set[Path], ordered: list[Path]):
    if path in seen:
        return
    seen.add(path)
    ordered.append(path)
    text = path.read_text(encoding="utf-8", errors="ignore")
    refs = parse_refs(text)
    graph[rel(path)] = refs
    for kind in ("extends", "include", "import", "from"):
        for ref in refs[kind]:
            target = resolve(ref)
            if target is not None:
                walk(target, graph, seen, ordered)


def render_tree(node: str, graph, depth=0, lines=None, seen=None):
    if lines is None:
        lines = []
    if seen is None:
        seen = set()
    pad = "  " * depth
    lines.append(f"{pad}- {node}")
    if node in seen:
        lines[-1] += " (seen)"
        return lines
    seen.add(node)
    refs = graph.get(node, {})
    for kind in ("extends", "include", "import", "from"):
        for ref in refs.get(kind, []):
            target = resolve(ref)
            label = ref if target is None else rel(target)
            lines.append(f"{pad}  [{kind}] {label}")
            if target is not None:
                render_tree(rel(target), graph, depth + 2, lines, seen)
    return lines


def extract_classes(text: str) -> set[str]:
    out: set[str] = set()
    for _, raw in CLASS_ATTR.findall(text):
        for token in re.split(r"\s+", raw.strip()):
            if token and TOKEN.match(token):
                out.add(token)
    return out


def main() -> int:
    if not ENTRY.exists():
        print(f"missing entry template: {ENTRY}", file=sys.stderr)
        return 1
    if not CSS.exists():
        print(f"missing css file: {CSS}", file=sys.stderr)
        return 1

    graph: dict[str, dict[str, list[str]]] = {}
    ordered: list[Path] = []
    walk(ENTRY, graph, set(), ordered)

    (OUT / "00-entry.txt").write_text(str(ENTRY.relative_to(ROOT)) + "\n", encoding="utf-8")
    (OUT / "01-include-tree.txt").write_text(
        "\n".join(render_tree(rel(ENTRY), graph)) + "\n",
        encoding="utf-8",
    )

    flattened_parts = []
    all_classes: set[str] = set()
    per_file = []

    for path in ordered:
        text = path.read_text(encoding="utf-8", errors="ignore")
        flattened_parts.append(
            f"\n<!-- BEGIN {path.relative_to(ROOT).as_posix()} -->\n{text}\n<!-- END {path.relative_to(ROOT).as_posix()} -->\n"
        )
        classes = sorted(extract_classes(text))
        all_classes.update(classes)
        per_file.append(
            f"## {path.relative_to(ROOT).as_posix()}\n"
            + ("\n".join(f"- {c}" for c in classes) if classes else "- (none)")
            + "\n"
        )

    (OUT / "02-flattened-surface.html").write_text("\n".join(flattened_parts), encoding="utf-8")
    (OUT / "03-class-map.md").write_text("\n".join(per_file), encoding="utf-8")
    (OUT / "04-used-classes.txt").write_text(
        "\n".join(sorted(all_classes)) + "\n", encoding="utf-8"
    )

    css_text = CSS.read_text(encoding="utf-8", errors="ignore")
    css_classes = sorted(set(CSS_CLASS.findall(css_text)))
    (OUT / "05-css-classes.txt").write_text("\n".join(css_classes) + "\n", encoding="utf-8")

    used_ff = {c for c in all_classes if c.startswith(("ff-", "is-"))}
    defined = set(css_classes)
    missing = sorted(used_ff - defined)
    unused = sorted(defined - used_ff)

    (OUT / "06-missing-in-css.txt").write_text(
        "\n".join(missing) + ("\n" if missing else ""), encoding="utf-8"
    )
    (OUT / "07-unused-in-surface.txt").write_text(
        "\n".join(unused) + ("\n" if unused else ""), encoding="utf-8"
    )

    counts = collections.Counter()
    for m in SELECTOR_BLOCK.finditer(css_text):
        selector = re.sub(r"\s+", " ", m.group(2)).strip()
        if selector:
            counts[selector] += 1

    duplicates = [
        f"{count:>4}  {selector}"
        for selector, count in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
        if count > 1
    ]
    (OUT / "08-duplicate-selectors.txt").write_text(
        "\n".join(duplicates) + ("\n" if duplicates else ""),
        encoding="utf-8",
    )

    campaign_tokens = sorted(
        [
            c
            for c in used_ff
            if c.startswith("ff-hero")
            or c.startswith("ff-story")
            or c.startswith("ff-sponsor")
            or c.startswith("ff-team")
            or c.startswith("ff-checkout")
            or c.startswith("ff-close")
            or c.startswith("ff-footer")
            or c.startswith("ff-topbar")
            or c.startswith("ff-drawer")
            or c.startswith("ff-modal")
        ]
    )
    (OUT / "09-campaign-component-classes.txt").write_text(
        "\n".join(campaign_tokens) + ("\n" if campaign_tokens else ""),
        encoding="utf-8",
    )

    print(f"AUDIT_DIR={OUT}")
    print(f"FILES={len(ordered)}")
    print(f"USED_CLASSES={len(all_classes)}")
    print(f"USED_FF_CLASSES={len(used_ff)}")
    print(f"CSS_DEFINED_CLASSES={len(defined)}")
    print(f"MISSING_IN_CSS={len(missing)}")
    print(f"UNUSED_IN_SURFACE={len(unused)}")
    print(f"DUPLICATE_SELECTORS={len(duplicates)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
