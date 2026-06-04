#!/usr/bin/env bash
set -euo pipefail

BASE="${FF_BASE_URL:-http://127.0.0.1:5000}"
STAMP="$(date +%Y%m%d%H%M%S)"
OUT="audit_outputs/production-checklist-${STAMP}"

mkdir -p "$OUT/rendered"

echo "== FutureFunded production checklist audit =="
echo "OUT=$OUT"

echo
echo "== Ensure clean server =="
if ! curl -fsS "$BASE/healthz" >/dev/null; then
  ffserver restart
fi

echo
echo "== Repo checkpoint =="
{
  echo "## Git status"
  git status --short || true
  echo
  echo "## Recent commits"
  git log --oneline --decorate -12 || true
  echo
  echo "## Green tags"
  git tag --list "*green*" | sort | tail -80 || true
} > "$OUT/git-checkpoint.txt"

echo
echo "== Secret guard =="
if git grep -nE 'access_token=[0-9a-fA-F]{64}|FF_OPERATOR_ACCESS_TOKEN=[0-9a-fA-F]{64}' -- . ':!audit_outputs' ':!.env.local' ':!.env' ':!.flaskenv' > "$OUT/secret-guard.txt"; then
  echo "❌ Possible private token found in tracked source."
  cat "$OUT/secret-guard.txt"
  exit 1
else
  echo "✅ No private dashboard token found in tracked source."
  echo "No private dashboard token found in tracked source." > "$OUT/secret-guard.txt"
fi

echo
echo "== Build Flask route map =="
python - <<'PY' > "$OUT/flask-routes.csv"
import csv
from pathlib import Path

rows = []
try:
    from apps.web.app import create_app
    app = create_app()
    for rule in sorted(app.url_map.iter_rules(), key=lambda r: str(r)):
        rows.append({
            "rule": str(rule),
            "endpoint": rule.endpoint,
            "methods": " ".join(sorted(m for m in rule.methods if m not in {"HEAD", "OPTIONS"})),
            "arguments": ",".join(sorted(rule.arguments)),
        })
except Exception as exc:
    rows.append({
        "rule": "ERROR",
        "endpoint": type(exc).__name__,
        "methods": str(exc),
        "arguments": "",
    })

w = csv.DictWriter(open("/dev/stdout", "w", newline=""), fieldnames=["rule", "endpoint", "methods", "arguments"])
w.writeheader()
w.writerows(rows)
PY

echo
echo "== Discover page/template/static candidates =="
{
  echo "## Templates"
  find apps/web/app/templates -type f | sort

  echo
  echo "## Static CSS"
  find apps/web/app/static/css -type f | sort

  echo
  echo "## Static JS"
  find apps/web/app/static/js -type f | sort

  echo
  echo "## Audit/board scripts"
  find scripts -type f | grep -Ei 'board|visual|screenshot|audit|smoke|proof|ready|check' | sort || true
} > "$OUT/source-inventory.txt"

echo
echo "== Resolve private dashboard token without printing it =="
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
echo "== Create route seed list =="
python - "$BASE" "$TOKEN" <<'PY' > "$OUT/seed-urls.txt"
import csv
import sys
from pathlib import Path

base = sys.argv[1].rstrip("/")
token = sys.argv[2].strip()

manual = [
    "/",
    "/healthz",
    "/platform/",
    "/platform/login",
    "/platform/onboarding",
    "/c/connect-atx-elite",
    "/site.webmanifest",
    "/static/site.webmanifest",
    "/static/css/ff.css",
    "/static/css/campaign.css",
    "/static/css/auth.css",
    "/static/css/onboarding.css",
    "/static/js/ff-app.js",
    "/static/js/ff-onboarding.js",
    "/static/js/ff-operator-dashboard.js",
    "/static/js/ff-campaign-runtime.js",
    "/static/js/ff-checkout-direct.js",
    "/static/js/ff-launch-completion.js",
]

if token:
    manual.append(f"/platform/dashboard?access_token={token}")
else:
    manual.append("/platform/dashboard")

# Add static-looking non-dynamic GET routes from Flask map.
routes = []
try:
    with open("audit_outputs/NO_SUCH_FILE", newline=""):
        pass
except Exception:
    pass

route_csv = Path("audit_outputs").glob("production-checklist-*/flask-routes.csv")

seen = set()
for path in manual:
    url = base + path
    if url not in seen:
      seen.add(url)
      print(url)
PY

echo
echo "== Fetch seed URLs =="
python - "$OUT/seed-urls.txt" "$OUT" <<'PY'
import csv
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

seed_file = Path(sys.argv[1])
out = Path(sys.argv[2])

rows = []
asset_rows = []

def run_curl(url, html_path=None):
    cmd = ["curl", "-fsSL", "-o", html_path or "/tmp/ff-prod-check.tmp", "-w", "%{http_code}\t%{content_type}\t%{size_download}", url]
    try:
        cp = subprocess.run(cmd, capture_output=True, text=True, timeout=40)
        status = cp.stdout.strip().split("\t") if cp.stdout.strip() else ["000", "", "0"]
        return {
            "status": status[0] if len(status) > 0 else "000",
            "content_type": status[1] if len(status) > 1 else "",
            "bytes": status[2] if len(status) > 2 else "0",
            "curl_rc": str(cp.returncode),
            "stderr": cp.stderr.strip()[:240],
        }
    except Exception as exc:
        return {"status": "ERR", "content_type": "", "bytes": "0", "curl_rc": "EXC", "stderr": str(exc)[:240]}

for idx, url in enumerate(seed_file.read_text().splitlines(), 1):
    if not url.strip():
        continue

    parsed = urlparse(url)
    safe_name = re.sub(r"[^a-zA-Z0-9._-]+", "_", parsed.path.strip("/") or "root")
    if "dashboard" in parsed.path and parsed.query:
        safe_name += "_TOKENED"
    html_path = out / "rendered" / f"{idx:02d}_{safe_name}.html"

    result = run_curl(url, str(html_path))

    html = html_path.read_text(errors="replace") if html_path.exists() else ""
    title = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    page = re.search(r'<html[^>]*data-ff-page=["\']([^"\']+)["\']', html, re.I)
    body = re.search(r'<body[^>]*class=["\']([^"\']+)["\']', html, re.I)

    css = sorted(set(re.findall(r'href=["\']([^"\']+\.css[^"\']*)["\']', html, re.I)))
    js = sorted(set(re.findall(r'src=["\']([^"\']+\.js[^"\']*)["\']', html, re.I)))

    rows.append({
        "url_masked": re.sub(r"(access_token=)[^&]+", r"\1***MASKED***", url),
        "status": result["status"],
        "bytes": result["bytes"],
        "content_type": result["content_type"],
        "data_ff_page": page.group(1) if page else "",
        "title": " ".join(title.group(1).split()) if title else "",
        "body_class": body.group(1) if body else "",
        "css_count": len(css),
        "js_count": len(js),
        "rendered_file": str(html_path),
        "curl_rc": result["curl_rc"],
        "stderr": result["stderr"],
    })

    for href in css:
        asset_rows.append({"source_url": rows[-1]["url_masked"], "kind": "css", "asset": href})
    for src in js:
        asset_rows.append({"source_url": rows[-1]["url_masked"], "kind": "js", "asset": src})

with (out / "served-pages.csv").open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["url_masked"])
    w.writeheader()
    w.writerows(rows)

with (out / "page-assets.csv").open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["source_url", "kind", "asset"])
    w.writeheader()
    w.writerows(asset_rows)
PY

echo
echo "== Feature inventory =="
python - "$OUT" <<'PY'
import csv
import re
from pathlib import Path

out = Path(__import__("sys").argv[1])

checks = [
    ("Stripe checkout JS", ["apps/web/app/static/js/ff-checkout-direct.js"], ["Stripe", "checkout"]),
    ("Donation payload firewall", ["apps/web/app/static/js/ff-donation-payload-firewall.js"], ["payload"]),
    ("Campaign runtime", ["apps/web/app/static/js/ff-campaign-runtime.js"], ["campaign"]),
    ("Sponsor modal contract", ["apps/web/app/static/js/ff-sponsor-modal-contract.js"], ["sponsor"]),
    ("Launch completion JS", ["apps/web/app/static/js/ff-launch-completion.js"], ["launch"]),
    ("Onboarding JS", ["apps/web/app/static/js/ff-onboarding.js"], ["onboarding"]),
    ("Operator dashboard JS", ["apps/web/app/static/js/ff-operator-dashboard.js"], ["dashboard"]),
    ("Login JS", ["apps/web/app/static/js/login.js"], ["password"]),
    ("Campaign CSS", ["apps/web/app/static/css/campaign.css"], ["campaign"]),
    ("Global FF CSS", ["apps/web/app/static/css/ff.css"], ["dashboard", "campaign"]),
    ("Auth CSS", ["apps/web/app/static/css/auth.css"], ["login"]),
    ("Onboarding CSS", ["apps/web/app/static/css/onboarding.css"], ["onboarding"]),
    ("Manifest", ["apps/web/app/static/site.webmanifest"], ["FutureFunded"]),
    ("Dashboard visual board", ["scripts/audit/ff-dashboard-board.sh"], ["screenshot", "platform-dashboard"]),
    ("Served URL audit", ["scripts/audit/ff-served-url-lite.sh"], ["Broken rows"]),
    ("Fast strict proof", ["scripts/demo/ff-fast-proof-strict.sh"], ["healthz"]),
]

rows = []
for name, paths, markers in checks:
    existing = [p for p in paths if Path(p).exists()]
    text = "\n".join(Path(p).read_text(errors="replace")[:200000] for p in existing if Path(p).is_file())
    marker_hits = [m for m in markers if m.lower() in text.lower()]
    rows.append({
        "feature": name,
        "status": "present" if existing else "missing",
        "paths": " | ".join(existing),
        "marker_hits": ", ".join(marker_hits),
        "needs_review": "no" if existing and len(marker_hits) == len(markers) else "yes",
    })

with (out / "feature-inventory.csv").open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["feature", "status", "paths", "marker_hits", "needs_review"])
    w.writeheader()
    w.writerows(rows)
PY

echo
echo "== Board / green tag coverage =="
python - "$OUT" <<'PY'
import csv
import subprocess
from pathlib import Path

out = Path(__import__("sys").argv[1])

page_keywords = [
    ("Homepage / platform", "platform", "/", "platform homepage"),
    ("Public campaign", "campaign", "/c/connect-atx-elite", "campaign fundraiser"),
    ("Login / organizer access", "login", "/platform/login", "auth login"),
    ("Onboarding", "onboarding", "/platform/onboarding", "campaign setup"),
    ("Private dashboard", "dashboard", "/platform/dashboard", "operator dashboard"),
]

tags = subprocess.run(["git", "tag", "--list"], capture_output=True, text=True).stdout.splitlines()
scripts = "\n".join(str(p) for p in Path("scripts").glob("**/*") if p.is_file())

rows = []
for label, keyword, url, notes in page_keywords:
    green_tags = [t for t in tags if keyword in t.lower() and "green" in t.lower()]
    board_scripts = [line for line in scripts.splitlines() if keyword in line.lower() and ("board" in line.lower() or "visual" in line.lower() or "screenshot" in line.lower())]
    rows.append({
        "page": label,
        "url": url,
        "green_tag_count": len(green_tags),
        "latest_green_tag": green_tags[-1] if green_tags else "",
        "board_script_count": len(board_scripts),
        "board_scripts": " | ".join(board_scripts[:4]),
        "recommended_status": "locked" if green_tags and board_scripts else ("polished-no-board" if green_tags else "needs-audit"),
        "notes": notes,
    })

with (out / "page-coverage.csv").open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
PY

echo
echo "== Generate production checklist report =="
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

served = read_csv("served-pages.csv")
features = read_csv("feature-inventory.csv")
coverage = read_csv("page-coverage.csv")

broken = [r for r in served if not str(r.get("status", "")).startswith("2")]
needs_feature_review = [r for r in features if r.get("needs_review") == "yes"]
needs_page_work = [r for r in coverage if r.get("recommended_status") != "locked"]

def table(rows, cols):
    if not rows:
        return "_None._"
    head = "| " + " | ".join(cols) + " |\n"
    sep = "| " + " | ".join("---" for _ in cols) + " |\n"
    body = ""
    for r in rows:
        body += "| " + " | ".join(str(r.get(c, "")).replace("|", "\\|") for c in cols) + " |\n"
    return head + sep + body

report = f"""# FutureFunded Production Checklist Audit

Generated: `{out.name}`

## Executive Summary

| Area | Count |
|---|---:|
| Served URLs checked | {len(served)} |
| Broken / non-2xx URLs | {len(broken)} |
| Feature checks | {len(features)} |
| Feature checks needing review | {len(needs_feature_review)} |
| Core pages checked | {len(coverage)} |
| Pages not fully locked with board + green tag | {len(needs_page_work)} |

## Page Coverage

{table(coverage, ["page", "url", "recommended_status", "latest_green_tag", "board_script_count"])}

## Served URL Results

{table(served, ["url_masked", "status", "data_ff_page", "title", "css_count", "js_count"])}

## Features / Functionality Inventory

{table(features, ["feature", "status", "needs_review", "paths", "marker_hits"])}

## Pages Needing Work

{table(needs_page_work, ["page", "url", "recommended_status", "notes"])}

## Broken URLs

{table(broken, ["url_masked", "status", "content_type", "stderr"])}

## Recommended Next Order

1. Fix any broken/non-2xx URL first.
2. For pages marked `needs-audit`, create a screenshot board before visual polish.
3. For pages marked `polished-no-board`, create a board and lock a green tag.
4. For feature checks marked `needs_review`, run focused functional smoke tests.
5. After all pages are locked, run final live-readiness: routes, payments, forms, env, security headers, sitemap/robots, mobile screenshots, and demo script.

## Files

- `git-checkpoint.txt`
- `secret-guard.txt`
- `flask-routes.csv`
- `served-pages.csv`
- `page-assets.csv`
- `feature-inventory.csv`
- `page-coverage.csv`
- `source-inventory.txt`
- `rendered/`
"""

(out / "production-checklist.md").write_text(report)
print(report)
PY

echo
echo "✅ Production checklist:"
echo "$OUT/production-checklist.md"
