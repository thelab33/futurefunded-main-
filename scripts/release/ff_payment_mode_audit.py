from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

BASE_URL = os.environ.get("FF_BASE_URL", "https://getfuturefunded.com").rstrip("/")
SLUG = os.environ.get("FF_CAMPAIGN_SLUG", "connect-atx-elite")

ROOT = Path.cwd()

SECRET_HINTS = (
    "STRIPE",
    "PAYPAL",
    "PAYMENT",
    "CHECKOUT",
    "WEBHOOK",
    "PUBLIC_URL",
    "FF_PUBLIC",
    "FLASK_ENV",
    "APP_ENV",
)

def mask(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 10:
        return value[:3] + "…"
    return value[:8] + "…" + value[-4:]

def classify(value: str) -> str:
    if value.startswith("sk_live_"):
        return "LIVE_SECRET"
    if value.startswith("sk_test_"):
        return "TEST_SECRET"
    if value.startswith("pk_live_"):
        return "LIVE_PUBLISHABLE"
    if value.startswith("pk_test_"):
        return "TEST_PUBLISHABLE"
    if value.startswith("whsec_"):
        return "WEBHOOK_SECRET_PRESENT"
    if value.startswith("cs_live_"):
        return "LIVE_CHECKOUT_SESSION"
    if value.startswith("cs_test_"):
        return "TEST_CHECKOUT_SESSION"
    return "present"

def print_env_source(title: str, env: dict[str, str]) -> None:
    print(f"\n=== {title} ===")
    found = False
    for key in sorted(env):
        if any(hint in key.upper() for hint in SECRET_HINTS):
            found = True
            value = env.get(key, "")
            print(f"{key} = {classify(value)} [{mask(value)}]")
    if not found:
        print("No payment-related env keys found in this source.")

def read_url(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "FutureFunded payment mode audit"})
    with urllib.request.urlopen(req, timeout=20) as res:
        return res.read().decode("utf-8", errors="replace")

def scan_json_for_key_prefixes(obj, path="$"):
    hits = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            hits.extend(scan_json_for_key_prefixes(v, f"{path}.{k}"))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            hits.extend(scan_json_for_key_prefixes(v, f"{path}[{i}]"))
    elif isinstance(obj, str):
        if obj.startswith(("pk_test_", "pk_live_", "sk_test_", "sk_live_", "cs_test_", "cs_live_")):
            hits.append((path, classify(obj), mask(obj)))
    return hits

print("FutureFunded payment mode audit")
print(f"Base URL: {BASE_URL}")
print(f"Campaign: {SLUG}")

print_env_source("Current shell environment", dict(os.environ))

try:
    pm2 = subprocess.run(
        ["pm2", "env", "futurefunded-web"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=15,
    )
    pm2_env = {}
    for line in pm2.stdout.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            pm2_env[key.strip()] = value.strip()
    print_env_source("PM2 futurefunded-web environment", pm2_env)
except Exception as exc:
    print(f"\nPM2 env check skipped/error: {exc}")

print("\n=== Public payment config endpoint ===")
config_url = f"{BASE_URL}/c/{SLUG}/payments/config?mode_audit=1"
try:
    raw = read_url(config_url)
    print(f"GET {config_url} -> OK")
    try:
        data = json.loads(raw)
        hits = scan_json_for_key_prefixes(data)
        if hits:
            for path, kind, masked in hits:
                print(f"{path}: {kind} [{masked}]")
        else:
            print("No pk_/sk_/cs_ prefixed values found in JSON.")
    except json.JSONDecodeError:
        print("Response was not JSON.")
        print(raw[:500])
except Exception as exc:
    print(f"Payment config fetch failed: {exc}")

print("\n=== Existing money-loop smoke session mode ===")
try:
    smoke = subprocess.run(
        ["node", "scripts/verify/ff_campaign_v1_authority_money_loop.mjs", BASE_URL, SLUG],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    print(smoke.stdout)
    session_ids = re.findall(r"id=(cs_(?:test|live)_[A-Za-z0-9]+)", smoke.stdout)
    if session_ids:
        sid = session_ids[0]
        print(f"Detected session: {classify(sid)} [{mask(sid)}]")
        if sid.startswith("cs_test_"):
            print("BLOCKER: checkout session is TEST mode.")
            sys.exit(2)
        if sid.startswith("cs_live_"):
            print("PASS: checkout session is LIVE mode.")
            sys.exit(0)
    else:
        print("No checkout session id detected.")
        sys.exit(1)
except Exception as exc:
    print(f"Money-loop smoke failed: {exc}")
    sys.exit(1)
