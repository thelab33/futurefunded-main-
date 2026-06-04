#!/usr/bin/env bash
set -euo pipefail

BASE="${FF_BASE_URL:-http://127.0.0.1:5000}"
SLUG="${FF_CAMPAIGN_SLUG:-connect-atx-elite}"
STAMP="$(date +%Y%m%d%H%M%S)"
OUT="audit_outputs/launch-control-${STAMP}"

mkdir -p "$OUT"

echo "== FutureFunded launch control audit =="
echo "OUT=$OUT"

echo
echo "== Ensure server =="
if ! curl -fsS "$BASE/healthz" >/dev/null; then
  ffserver restart
fi

echo
echo "== Latest governance proof =="
LATEST_GOV="$(
  find audit_outputs -maxdepth 1 -type d -name 'route-governance-*' -printf '%T@ %p\n' \
    | sort -nr \
    | awk 'NR==1{print $2}'
)"

if [ -z "$LATEST_GOV" ] || [ ! -f "$LATEST_GOV/route-governance.csv" ]; then
  echo "❌ No route governance report found. Run scripts/audit/ff-route-governance.sh first."
  exit 1
fi

python - "$LATEST_GOV/route-governance.csv" "$OUT" <<'PY'
import csv
import sys
from collections import Counter
from pathlib import Path

csv_path = Path(sys.argv[1])
out = Path(sys.argv[2])
rows = list(csv.DictReader(csv_path.open()))

counts = Counter(r["bucket"] for r in rows)

canonical = counts["canonical_launch"]
private = counts["canonical_launch_private"]
needs_decision = counts["needs_product_decision"]
unexpected_non2xx = [
    r for r in rows
    if not str(r["status"]).startswith("2")
    and r["bucket"] != "protected_dashboard_variant_expected_403"
]

ok = (
    canonical == 3
    and private == 1
    and needs_decision == 0
    and len(unexpected_non2xx) == 0
)

with (out / "route-policy-proof.txt").open("w") as f:
    f.write(f"canonical_launch={canonical}\n")
    f.write(f"canonical_launch_private={private}\n")
    f.write(f"needs_product_decision={needs_decision}\n")
    f.write(f"unexpected_non2xx={len(unexpected_non2xx)}\n")
    f.write(f"ok={str(ok).lower()}\n")

print(f"canonical_launch={canonical}")
print(f"canonical_launch_private={private}")
print(f"needs_product_decision={needs_decision}")
print(f"unexpected_non2xx={len(unexpected_non2xx)}")
print(f"ok={str(ok).lower()}")

if not ok:
    raise SystemExit("❌ Route policy is not launch-controlled.")
PY

echo
echo "== Dynamic campaign feature smoke =="
python - "$BASE" "$SLUG" "$OUT" <<'PY'
import csv
import subprocess
import sys
from pathlib import Path

base = sys.argv[1].rstrip("/")
slug = sys.argv[2]
out = Path(sys.argv[3])

checks = [
    ("payment_config", f"/c/{slug}/payments/config", {"200"}),
    ("ledger_summary", f"/c/{slug}/ledger/summary", {"200"}),
    ("ledger_events_protected_public_check", f"/c/{slug}/ledger/events", {"200", "403"}),
    ("ledger_export_csv_protected_public_check", f"/c/{slug}/ledger/export.csv", {"200", "403"}),
    ("share_page", f"/c/{slug}/share", {"200", "302"}),
    ("thank_you_page", f"/c/{slug}/thank-you", {"200", "302"}),
    ("cancel_page", f"/c/{slug}/cancel", {"200", "302"}),
    # Session status may require query params; 400/422 is acceptable if it does not 500.
    ("checkout_status_root_alias", f"/{slug}/checkout/session-status", {"200", "400", "404", "422"}),
    ("checkout_status_campaign", f"/c/{slug}/checkout/session-status", {"200", "400", "404", "422"}),
    ("sms_incoming", "/sms/twilio/incoming", {"200", "204", "405"}),
    ("sponsors_index", "/sponsors", {"200"}),
    ("robots", "/robots.txt", {"200"}),
    ("sitemap", "/sitemap.xml", {"200"}),
    ("security", "/.well-known/security.txt", {"200"}),
]

rows = []

for name, path, allowed in checks:
    url = base + path
    cmd = ["curl", "-sSL", "-o", "/tmp/ff-launch-control.tmp", "-w", "%{http_code}\t%{content_type}\t%{size_download}", url]
    try:
        cp = subprocess.run(cmd, capture_output=True, text=True, timeout=35)
        parts = cp.stdout.strip().split("\t") if cp.stdout.strip() else ["000", "", "0"]
        status = parts[0] if len(parts) > 0 else "000"
        content_type = parts[1] if len(parts) > 1 else ""
        size = parts[2] if len(parts) > 2 else "0"
        stderr = cp.stderr.strip()[:200]
    except Exception as exc:
        status, content_type, size, stderr = "ERR", "", "0", str(exc)[:200]

    ok = status in allowed and not str(status).startswith("5")
    rows.append({
        "name": name,
        "url": url,
        "status": status,
        "allowed": ",".join(sorted(allowed)),
        "content_type": content_type,
        "bytes": size,
        "ok": "yes" if ok else "no",
        "stderr": stderr,
    })

with (out / "dynamic-feature-smoke.csv").open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["name", "url", "status", "allowed", "content_type", "bytes", "ok", "stderr"])
    w.writeheader()
    w.writerows(rows)

bad = [r for r in rows if r["ok"] != "yes"]

for r in rows:
    print(f"{r['ok']:3s} {r['status']:>3s} {r['name']}")

if bad:
    print()
    print("❌ Dynamic smoke failures:")
    for r in bad:
        print(r)
    raise SystemExit(1)
PY

echo
echo "== Canonical board proof =="
LATEST_BOARD="$(
  find audit_outputs -maxdepth 1 -type d -name 'launch-surface-board-*' -printf '%T@ %p\n' \
    | sort -nr \
    | awk 'NR==1{print $2}'
)"

if [ -n "$LATEST_BOARD" ] && [ -f "$LATEST_BOARD/screenshot-proof.txt" ]; then
  cp "$LATEST_BOARD/screenshot-proof.txt" "$OUT/canonical-board-proof.txt"
  cat "$OUT/canonical-board-proof.txt"
else
  echo "WARN: no canonical launch board proof found" | tee "$OUT/canonical-board-proof.txt"
fi

echo
echo "== Served URL lite proof =="
bash scripts/audit/ff-served-url-lite.sh >/dev/null

LATEST_SERVE="$(
  find audit_outputs -maxdepth 1 -type d -name 'served-url-lite-*' -printf '%T@ %p\n' \
    | sort -nr \
    | awk 'NR==1{print $2}'
)"

grep -E "Served rows|Broken rows" "$LATEST_SERVE/README.md" | tee "$OUT/served-url-proof.txt"

echo
echo "== Generate launch control checklist =="
cat > "$OUT/launch-control.md" <<MD
# FutureFunded Launch Control Checklist

Generated: \`$OUT\`

## Source of Truth

- Launch surface registry: \`docs/launch/LAUNCH_SURFACE_REGISTRY.md\`
- Route governance: \`$LATEST_GOV/route-governance.md\`
- Canonical launch board: \`${LATEST_BOARD:-missing}\`
- Served URL audit: \`$LATEST_SERVE\`

## Required launch surfaces

| Surface | Status |
|---|---|
| Homepage \`/\` | canonical flagship |
| Campaign \`/c/connect-atx-elite\` | canonical flagship |
| Onboarding \`/platform/onboarding\` | canonical flagship |
| Private Dashboard \`/platform/dashboard?access_token=...\` | canonical private flagship |

## Governance proof

\`\`\`
$(cat "$OUT/route-policy-proof.txt")
\`\`\`

## Dynamic feature smoke

\`\`\`
$(awk -F, 'NR==1{next}{print $7 " " $3 " " $1}' "$OUT/dynamic-feature-smoke.csv")
\`\`\`

## Served URL proof

\`\`\`
$(cat "$OUT/served-url-proof.txt")
\`\`\`

## Next visual page

Recommended next flagship page: **Homepage**.

Reason:
- Dashboard is locked.
- Onboarding is locked.
- Campaign has a mature board.
- Homepage is the SaaS sales surface and currently appears in the canonical board as the broadest product funnel.
MD

cat "$OUT/launch-control.md"

echo
echo "✅ Launch control report:"
echo "$OUT/launch-control.md"
