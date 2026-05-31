#!/usr/bin/env python3
import subprocess, urllib.request, time
from pathlib import Path

ROOT = Path.home() / "futurefunded-main"
BASE = "http://127.0.0.1:5000"
LOG = ROOT / "audit_outputs/dev-server/latest.log"

routes = [
    "/healthz",
    "/platform/",
    "/platform/onboarding",
    "/platform/login",
    "/c/connect-atx-elite",
    "/static/js/ff-app.js",
    "/static/js/ff-campaign.js",
    "/static/js/ff-embedded-checkout.js",
    "/static/js/ff-checkout-direct.js",
    "/static/css/campaign.css",
]

def run(cmd, timeout=8):
    try:
        p = subprocess.run(cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
        return p.stdout.strip()
    except Exception as exc:
        return f"ERR: {exc}"

def probe(path):
    started = time.time()
    try:
        with urllib.request.urlopen(BASE + path, timeout=5) as res:
            res.read(256)
            return f"{res.status:<3} {time.time()-started:>5.2f}s {path}"
    except Exception as exc:
        return f"ERR {time.time()-started:>5.2f}s {path} :: {exc}"

print("== FutureFunded Live Once ==")
print(f"ROOT={ROOT}")
print()
print("== Git ==")
print(run(["/usr/bin/git", "status", "--short"]))
print(run(["/usr/bin/git", "log", "-6", "--decorate", "--oneline"]))
print()
print("== Ports/processes ==")
print(run(["bash", "-lc", "ss -ltnp 2>/dev/null | grep -E ':5000|:5010' || true"]))
print(run(["bash", "-lc", "ps -eo pid,ppid,etime,cmd | grep -E 'flask|futurefunded|cloudflared|pm2' | grep -v grep || true"]))
print()
print("== Routes/assets ==")
for route in routes:
    print(probe(route))
print()
print("== Server log tail ==")
if LOG.exists():
    print("\n".join(LOG.read_text(errors="replace").splitlines()[-50:]))
else:
    print(f"No log found: {LOG}")
