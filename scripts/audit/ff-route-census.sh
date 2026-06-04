#!/usr/bin/env bash
set -euo pipefail

BASE="${FF_BASE_URL:-http://127.0.0.1:5000}"
STAMP="$(date +%Y%m%d%H%M%S)"
OUT="audit_outputs/route-census-${STAMP}"

mkdir -p "$OUT/rendered"

echo "== FutureFunded full route census =="
echo "OUT=$OUT"

echo
echo "== Ensure server =="
if ! curl -fsS "$BASE/healthz" >/dev/null; then
  ffserver restart
fi

echo
echo "== Resolve dashboard token without printing it =="
TOKEN=""
if [ -s /tmp/ff_operator_token ]; then
  TOKEN="$(tr -d '\r\n\t ' < /tmp/ff_operator_token)"
fi

if [ -z "$TOKEN" ] && [ -f .env.local ]; then
  TOKEN="$(
    { grep -E '^[[:space:]]*FF_OPERATOR_ACCESS_TOKEN=' .env.local 2>/dev/null || true; } \
      | tail -n 1 \
      | sed -E 's/^[[:space:]]*FF_OPERATOR_ACCESS_TOKEN=//' \
      | sed -E 's/^["'\''"]|["'\''"]$//g' \
      | tr -d '\r\n'
  )"
fi

if [ -n "$TOKEN" ]; then
  echo "token_length=${#TOKEN}" > "$OUT/dashboard-token-proof.txt"
else
  echo "token_missing" > "$OUT/dashboard-token-proof.txt"
fi

echo
echo "== Build complete Flask route map =="
python - "$OUT" <<'PY'
import csv
import sys
from pathlib import Path

out = Path(sys.argv[1])
rows = []

try:
    from apps.web.app import create_app
    app = create_app()

    for rule in sorted(app.url_map.iter_rules(), key=lambda r: str(r)):
        methods = sorted(m for m in rule.methods if m not in {"HEAD", "OPTIONS"})
        rows.append({
            "rule": str(rule),
            "endpoint": rule.endpoint,
            "methods": " ".join(methods),
            "arguments": ",".join(sorted(rule.arguments)),
            "is_get": "yes" if "GET" in methods else "no",
            "is_static": "yes" if rule.endpoint == "static" or str(rule).startswith("/static") else "no",
        })
except Exception as exc:
    rows.append({
        "rule": "ERROR",
        "endpoint": type(exc).__name__,
        "methods": str(exc),
        "arguments": "",
        "is_get": "no",
        "is_static": "no",
    })

with (out / "all-routes.csv").open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["rule", "endpoint", "methods", "arguments", "is_get", "is_static"])
    w.writeheader()
    w.writerows(rows)
PY

echo
echo "== Build safe fetch seeds from route map =="
python - "$BASE" "$TOKEN" "$OUT" <<'PY'
import csv
import sys
from pathlib import Path

base = sys.argv[1].rstrip("/")
token = sys.argv[2].strip()
out = Path(sys.argv[3])

manual = [
    ("canonical", "home", "/"),
    ("alias", "platform_alias", "/platform/"),
    ("canonical", "campaign", "/c/connect-atx-elite"),
    ("canonical", "onboarding", "/platform/onboarding"),
    ("support", "login", "/platform/login"),
    ("system", "healthz", "/healthz"),
    ("system", "manifest", "/site.webmanifest"),
]

if token:
    manual.append(("canonical", "dashboard", f"/platform/dashboard?access_token={token}"))
else:
    manual.append(("locked", "dashboard_locked", "/platform/dashboard"))

routes = list(csv.DictReader((out / "all-routes.csv").open()))

seeds = []
seen = set()

def add(kind, name, path, source="manual"):
    url = base + path
    masked = url.replace(token, "***MASKED***") if token else url
    key = (kind, name, masked)
    if key in seen:
        return
    seen.add(key)
    seeds.append({
        "kind": kind,
        "name": name,
        "path": path,
        "url": url,
        "url_masked": masked,
        "source": source,
    })

for kind, name, path in manual:
    add(kind, name, path)

dynamic_unseeded = []

for r in routes:
    rule = r["rule"]
    endpoint = r["endpoint"]
    args = r["arguments"]
    is_get = r["is_get"] == "yes"

    if not is_get:
        continue

    if args:
        # Known dynamic page route already seeded.
        if rule in {"/c/<slug>", "/c/<campaign_slug>", "/campaign/<slug>"}:
            continue

        dynamic_unseeded.append({
            "rule": rule,
            "endpoint": endpoint,
            "methods": r["methods"],
            "arguments": args,
            "reason": "dynamic route requires sample data or parameter",
        })
        continue

    if rule.startswith("/static"):
        continue

    if rule in {"/", "/platform/", "/platform/login", "/platform/onboarding", "/platform/dashboard", "/healthz", "/site.webmanifest"}:
        continue

    kind = "route"
    name = endpoint.replace(".", "_")
    add(kind, name, rule, source="flask-url-map")

with (out / "fetch-seeds.csv").open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["kind", "name", "path", "url_masked", "source"])
    w.writeheader()
    for s in seeds:
        row = dict(s)
        row.pop("url", None)
        w.writerow(row)

with (out / "dynamic-routes-unseeded.csv").open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["rule", "endpoint", "methods", "arguments", "reason"])
    w.writeheader()
    w.writerows(dynamic_unseeded)

# Keep real URL seeds local-only for fetch step.
with (out / ".fetch-seeds-private.tsv").open("w") as f:
    for s in seeds:
        f.write(f"{s['kind']}\t{s['name']}\t{s['url']}\t{s['url_masked']}\t{s['source']}\n")
PY

echo
echo "== Fetch every safe route seed =="
python - "$OUT" <<'PY'
import csv
import hashlib
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

out = Path(sys.argv[1])

rows = []
page_candidates = []

def classify(kind, name, path, status, content_type, data_page, title):
    if kind == "canonical":
        return "canonical"
    if kind == "alias":
        return "alias"
    if kind == "support":
        return "support"
    if kind == "system":
        return "system"
    if "/api/" in path or content_type.startswith("application/json"):
        return "api_or_json"
    if content_type.startswith("text/html") or data_page or title:
        return "html_page_candidate"
    return "non_html_route"

private = out / ".fetch-seeds-private.tsv"
for idx, line in enumerate(private.read_text().splitlines(), 1):
    if not line.strip():
        continue

    kind, name, url, url_masked, source = line.split("\t", 4)
    path = urlparse(url).path

    safe_name = re.sub(r"[^a-zA-Z0-9._-]+", "_", f"{idx:02d}_{kind}_{name}")
    dest = out / "rendered" / f"{safe_name}.html"

    cmd = ["curl", "-fsSL", "-o", str(dest), "-w", "%{http_code}\t%{content_type}\t%{size_download}", url]
    try:
        cp = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
        parts = cp.stdout.strip().split("\t") if cp.stdout.strip() else ["000", "", "0"]
        status = parts[0] if len(parts) > 0 else "000"
        content_type = parts[1] if len(parts) > 1 else ""
        bytes_ = parts[2] if len(parts) > 2 else "0"
        stderr = cp.stderr.strip()[:220]
        rc = cp.returncode
    except Exception as exc:
        status, content_type, bytes_, stderr, rc = "ERR", "", "0", str(exc)[:220], "EXC"

    text = dest.read_text(errors="replace") if dest.exists() else ""

    title = re.search(r"<title[^>]*>(.*?)</title>", text, re.I | re.S)
    page = re.search(r'<html[^>]*data-ff-page=["\']([^"\']+)["\']', text, re.I)
    body = re.search(r'<body[^>]*class=["\']([^"\']+)["\']', text, re.I)

    data_page = page.group(1) if page else ""
    title_text = " ".join(title.group(1).split()) if title else ""
    body_class = body.group(1) if body else ""

    normalized = re.sub(r"access_token=[^&\"'> ]+", "access_token=MASKED", text)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    html_hash = hashlib.sha256(normalized.encode()).hexdigest()[:16] if normalized else ""

    route_class = classify(kind, name, path, status, content_type, data_page, title_text)

    row = {
        "kind": kind,
        "name": name,
        "source": source,
        "url_masked": url_masked,
        "status": status,
        "content_type": content_type,
        "bytes": bytes_,
        "data_ff_page": data_page,
        "title": title_text,
        "body_class": body_class,
        "html_hash": html_hash,
        "route_class": route_class,
        "rendered_file": str(dest),
        "curl_rc": rc,
        "stderr": stderr,
    }
    rows.append(row)

    if route_class == "html_page_candidate":
        page_candidates.append(row)

with (out / "fetched-routes.csv").open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["kind"])
    w.writeheader()
    w.writerows(rows)

with (out / "hidden-html-page-candidates.csv").open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["kind"])
    w.writeheader()
    w.writerows(page_candidates)
PY

echo
echo "== Template inventory and possible legacy/orphan pages =="
python - "$OUT" <<'PY'
import csv
import re
from pathlib import Path
import sys

out = Path(sys.argv[1])

templates = sorted(Path("apps/web/app/templates").glob("**/*.html"))
py_files = sorted(Path("apps/web/app").glob("**/*.py"))

source_text = "\n".join(p.read_text(errors="replace") for p in py_files)
explicit_templates = set(re.findall(r'render_template\(\s*["\']([^"\']+\.html)["\']', source_text))

canonical_templates = {
    "platform/index.html",
    "platform/onboarding.html",
    "platform/dashboard.html",
    "platform/login.html",
}

campaign_patterns = {
    "campaign.html",
    "campaign/index.html",
    "campaign/show.html",
}

rows = []
for p in templates:
    rel = p.relative_to("apps/web/app/templates").as_posix()
    text = p.read_text(errors="replace")
    markers = sorted(set(re.findall(r'data-ff-page=["\']([^"\']+)["\']', text)))

    if rel in canonical_templates:
        status = "canonical_or_support"
    elif rel in explicit_templates:
        status = "rendered_by_source"
    elif any(part in rel.lower() for part in ["old", "legacy", "backup", "bak"]):
        status = "legacy_named"
    elif markers:
        status = "has_page_marker_unclassified"
    else:
        status = "partial_or_unreferenced"

    rows.append({
        "template": rel,
        "status": status,
        "data_ff_markers": ", ".join(markers),
        "explicit_render_template": "yes" if rel in explicit_templates else "no",
        "bytes": p.stat().st_size,
    })

with (out / "template-inventory.csv").open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["template", "status", "data_ff_markers", "explicit_render_template", "bytes"])
    w.writeheader()
    w.writerows(rows)
PY

echo
echo "== Generate census report =="
python - "$OUT" <<'PY'
import csv
from pathlib import Path
import sys

out = Path(sys.argv[1])

def read_csv(name):
    p = out / name
    if not p.exists():
        return []
    return list(csv.DictReader(p.open()))

routes = read_csv("all-routes.csv")
fetched = read_csv("fetched-routes.csv")
hidden = read_csv("hidden-html-page-candidates.csv")
dynamic = read_csv("dynamic-routes-unseeded.csv")
templates = read_csv("template-inventory.csv")

non2xx = [r for r in fetched if not str(r.get("status", "")).startswith("2")]
template_watch = [
    r for r in templates
    if r["status"] in {"has_page_marker_unclassified", "legacy_named"}
]

def table(rows, cols):
    if not rows:
        return "_None._"
    text = "| " + " | ".join(cols) + " |\n"
    text += "| " + " | ".join("---" for _ in cols) + " |\n"
    for row in rows:
        text += "| " + " | ".join(str(row.get(c, "")).replace("|", "\\|") for c in cols) + " |\n"
    return text

report = f"""# FutureFunded Full Route Census

## Executive Summary

| Area | Count |
|---|---:|
| Flask routes discovered | {len(routes)} |
| Safe routes fetched | {len(fetched)} |
| Non-2xx fetched routes | {len(non2xx)} |
| Hidden HTML page candidates | {len(hidden)} |
| Dynamic routes requiring sample params | {len(dynamic)} |
| Templates inventoried | {len(templates)} |
| Template watch items | {len(template_watch)} |

## Hidden HTML Page Candidates

These are fetched HTML pages that are **not** one of the 4 canonical launch surfaces, alias, support, system, or API routes.

{table(hidden, ["name", "url_masked", "status", "data_ff_page", "title", "route_class"])}

## Dynamic Routes Requiring Sample Params

{table(dynamic, ["rule", "endpoint", "methods", "arguments", "reason"])}

## Non-2xx Fetched Routes

{table(non2xx, ["name", "url_masked", "status", "content_type", "stderr"])}

## Template Watch Items

Templates that look like legacy pages or have page markers but are not clearly part of the canonical launch set.

{table(template_watch, ["template", "status", "data_ff_markers", "explicit_render_template", "bytes"])}

## All Fetched Routes

{table(fetched, ["kind", "name", "url_masked", "status", "data_ff_page", "title", "route_class"])}

## Interpretation

- `Hidden HTML Page Candidates = 0` means no extra safe GET HTML pages were found outside the canonical/support/alias set.
- `Dynamic routes requiring sample params` are not necessarily pages; they may be API or parameterized routes.
- `Template Watch Items` helps find old templates still sitting in the repo even if they are not served.
- The canonical launch board remains the source of truth for visual polishing.

## Files

- `all-routes.csv`
- `fetch-seeds.csv`
- `fetched-routes.csv`
- `hidden-html-page-candidates.csv`
- `dynamic-routes-unseeded.csv`
- `template-inventory.csv`
- `rendered/`
"""

(out / "route-census.md").write_text(report)
print(report)
PY

echo
echo "✅ Route census:"
echo "$OUT/route-census.md"
