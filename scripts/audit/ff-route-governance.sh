#!/usr/bin/env bash
set -euo pipefail

STAMP="$(date +%Y%m%d%H%M%S)"
OUT="audit_outputs/route-governance-${STAMP}"
mkdir -p "$OUT"

echo "== FutureFunded route governance audit =="
echo "OUT=$OUT"

LATEST_CENSUS="$(
  find audit_outputs -maxdepth 1 -type d -name 'route-census-*' -printf '%T@ %p\n' \
    | sort -nr \
    | awk 'NR==1{print $2}'
)"

if [ -z "$LATEST_CENSUS" ]; then
  echo "❌ No route-census output found. Run scripts/audit/ff-route-census.sh first."
  exit 1
fi

echo "Using census: $LATEST_CENSUS"

python - "$LATEST_CENSUS" "$OUT" <<'PY'
import csv
import sys
from pathlib import Path
from urllib.parse import urlparse

census = Path(sys.argv[1])
out = Path(sys.argv[2])

fetched = list(csv.DictReader((census / "fetched-routes.csv").open()))
dynamic = list(csv.DictReader((census / "dynamic-routes-unseeded.csv").open()))
templates = list(csv.DictReader((census / "template-inventory.csv").open()))

def path_of(url):
    try:
        return urlparse(url).path.rstrip("/") or "/"
    except Exception:
        return ""

def classify(row):
    path = path_of(row["url_masked"])
    status = row.get("status", "")
    data_page = row.get("data_ff_page", "")
    title = row.get("title", "")

    canonical = {
        "/": "canonical_launch",
        "/c/connect-atx-elite": "canonical_launch",
        "/platform/onboarding": "canonical_launch",
        "/platform/dashboard": "canonical_launch_private",
    }

    if path in canonical and row["kind"] == "canonical":
        return canonical[path]

    if path in {"/platform"} and data_page == "platform":
        return "alias_to_home"

    if path in {"/platform/onboarding"} and row["kind"] != "canonical":
        return "alias_to_onboarding"

    if path in {"/contact"}:
        return "legal_support_public"

    if path in {"/privacy", "/terms", "/legal/privacy", "/legal/terms"}:
        return "legal_public"

    if path in {
        "/login",
        "/logout",
        "/platform/login",
        "/platform/logout",
        "/platform/forgot-password",
        "/platform/reset-password",
        "/platform/register",
        "/platform/invite",
        "/platform/mfa",
    }:
        return "auth_support"

    if path in {"/dashboard", "/platform/dashboard"} and status == "403":
        return "protected_dashboard_variant_expected_403"

    if row.get("route_class") in {"api_or_json", "non_html_route", "system"}:
        return row.get("route_class")

    if row.get("route_class") == "html_page_candidate":
        return "needs_product_decision"

    return "other"

rows = []
for row in fetched:
    bucket = classify(row)

    action = {
        "canonical_launch": "board_and_polish",
        "canonical_launch_private": "board_with_token_and_polish",
        "alias_to_home": "canonicalize_or_redirect_to_root",
        "alias_to_onboarding": "canonicalize_or_redirect_to_no_slash",
        "legal_support_public": "keep_simple_accessible_no_heavy_polish",
        "legal_public": "keep_simple_accessible_no_heavy_polish",
        "auth_support": "keep_functional_basic_polish_no_flagship_board",
        "protected_dashboard_variant_expected_403": "keep_protected_or_redirect_safely",
        "api_or_json": "functional_smoke_only",
        "non_html_route": "functional_smoke_only",
        "system": "functional_smoke_only",
        "needs_product_decision": "decide_keep_redirect_or_delete",
    }.get(bucket, "review")

    rows.append({
        "bucket": bucket,
        "action": action,
        "url_masked": row.get("url_masked", ""),
        "status": row.get("status", ""),
        "data_ff_page": row.get("data_ff_page", ""),
        "title": row.get("title", ""),
        "route_class": row.get("route_class", ""),
    })

with (out / "route-governance.csv").open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=[
        "bucket", "action", "url_masked", "status", "data_ff_page", "title", "route_class"
    ])
    w.writeheader()
    w.writerows(rows)

watch_templates = [
    r for r in templates
    if r["status"] in {"has_page_marker_unclassified", "legacy_named"}
]

needs_decision = [r for r in rows if r["bucket"] == "needs_product_decision"]
non2xx_unexpected = [
    r for r in rows
    if not str(r["status"]).startswith("2")
    and r["bucket"] != "protected_dashboard_variant_expected_403"
]

def table(items, cols):
    if not items:
        return "_None._"
    text = "| " + " | ".join(cols) + " |\n"
    text += "| " + " | ".join("---" for _ in cols) + " |\n"
    for item in items:
        text += "| " + " | ".join(str(item.get(c, "")).replace("|", "\\|") for c in cols) + " |\n"
    return text

from collections import Counter
counts = Counter(r["bucket"] for r in rows)
count_rows = [{"bucket": k, "count": v} for k, v in sorted(counts.items())]

report = f"""# FutureFunded Route Governance Report

## Executive Summary

| Area | Count |
|---|---:|
| Fetched routes classified | {len(rows)} |
| Buckets discovered | {len(counts)} |
| Needs product decision | {len(needs_decision)} |
| Unexpected non-2xx routes | {len(non2xx_unexpected)} |
| Template watch items | {len(watch_templates)} |

## Bucket Counts

{table(count_rows, ["bucket", "count"])}

## Canonical Launch Surfaces

{table([r for r in rows if r["bucket"].startswith("canonical")], ["bucket", "action", "url_masked", "status", "data_ff_page", "title"])}

## Aliases

{table([r for r in rows if r["bucket"].startswith("alias")], ["bucket", "action", "url_masked", "status", "data_ff_page", "title"])}

## Legal Routes

{table([r for r in rows if r["bucket"].startswith("legal")], ["bucket", "action", "url_masked", "status", "title"])}

## Auth Support Routes

{table([r for r in rows if r["bucket"] == "auth_support"], ["bucket", "action", "url_masked", "status", "data_ff_page", "title"])}

## Protected Dashboard Variants

{table([r for r in rows if r["bucket"] == "protected_dashboard_variant_expected_403"], ["bucket", "action", "url_masked", "status"])}

## Needs Product Decision

{table(needs_decision, ["bucket", "action", "url_masked", "status", "data_ff_page", "title"])}

## Unexpected Non-2xx Routes

{table(non2xx_unexpected, ["bucket", "action", "url_masked", "status", "title"])}

## Dynamic Routes To Smoke Test With `connect-atx-elite`

{table(dynamic, ["rule", "endpoint", "methods", "arguments", "reason"])}

## Template Watch Items

{table(watch_templates, ["template", "status", "data_ff_markers", "explicit_render_template", "bytes"])}

## Production Policy

- Only canonical launch surfaces get screenshot boards and flagship polish.
- Aliases should eventually redirect or canonicalize.
- Legal pages stay simple, accessible, and trustworthy.
- Auth support pages must work, but they do not need flagship boards.
- Protected dashboard variants returning `403` are acceptable unless product strategy says redirect.
- Dynamic routes need functional smoke tests with the real campaign slug.
"""

(out / "route-governance.md").write_text(report)
print(report)
PY

echo
echo "✅ Route governance report:"
echo "$OUT/route-governance.md"
