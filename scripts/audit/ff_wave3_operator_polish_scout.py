#!/usr/bin/env python3
"""
FutureFunded • Wave 3 Operator Polish Scout

Read-only.
Checks onboarding/dashboard/operator surfaces for:
- page availability
- protected dashboard behavior
- key operator CTAs
- form/action/data contracts
- missing trust/status/workflow signals
"""

from __future__ import annotations

import json
import re
import urllib.request
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(".").resolve()
OUT_DIR = ROOT / "audit_outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

URLS = [
    "http://127.0.0.1:5000/platform/onboarding",
    "http://127.0.0.1:5000/platform/dashboard",
    "https://getfuturefunded.com/platform/onboarding",
    "https://getfuturefunded.com/platform/dashboard",
]


class OperatorParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids = set()
        self.data_attrs = {}
        self.links = []
        self.buttons = []
        self.forms = []
        self.text_chunks = []
        self._stack = []

    def handle_starttag(self, tag, attrs):
        attrs = {k.lower(): v or "" for k, v in attrs}
        if attrs.get("id"):
            self.ids.add(attrs["id"])
        for key, value in attrs.items():
            if key.startswith("data-"):
                self.data_attrs[key] = self.data_attrs.get(key, 0) + 1

        if tag in {"a", "button", "form"}:
            self._stack.append([tag, attrs, []])

    def handle_data(self, data):
        if data.strip():
            self.text_chunks.append(data.strip())
        for item in self._stack:
            item[2].append(data)

    def handle_endtag(self, tag):
        for i in range(len(self._stack) - 1, -1, -1):
            t, attrs, chunks = self._stack[i]
            if t == tag:
                text = re.sub(r"\s+", " ", " ".join(chunks)).strip()
                item = {"tag": t, "text": text, "attrs": attrs}
                if t == "a":
                    self.links.append(item)
                elif t == "button":
                    self.buttons.append(item)
                elif t == "form":
                    self.forms.append(item)
                del self._stack[i]
                break


def fetch(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "FutureFundedWave3Scout/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode(resp.headers.get_content_charset() or "utf-8", errors="replace")
            return resp.status, body, None
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return exc.code, body, None
    except Exception as exc:
        return None, "", f"{type(exc).__name__}: {exc}"


def score_page(url, status, html, err):
    parser = OperatorParser()
    parser.feed(html or "")

    text = " ".join(parser.text_chunks).lower()
    cta_text = " ".join([x["text"] for x in parser.links + parser.buttons]).lower()

    checks = {
        "fetch_ok": err is None,
        "status_ok_or_protected": status in {200, 401, 403},
        "has_launch_language": any(w in text for w in ["launch", "setup", "campaign", "fundraiser"]),
        "has_operator_language": any(w in text for w in ["operator", "dashboard", "status", "ledger", "sponsor"]),
        "has_primary_action": any(w in cta_text for w in ["start", "save", "launch", "continue", "open", "export", "view"]),
        "has_forms_or_actions": bool(parser.forms or parser.buttons or parser.links),
        "has_data_contracts": bool(parser.data_attrs),
    }

    return {
        "url": url,
        "status": status,
        "error": err,
        "checks": checks,
        "ids": sorted(parser.ids)[:80],
        "data_attrs": dict(sorted(parser.data_attrs.items())),
        "links": [{"text": x["text"], "href": x["attrs"].get("href", "")} for x in parser.links[:40]],
        "buttons": [{"text": x["text"], "type": x["attrs"].get("type", "")} for x in parser.buttons[:40]],
        "forms": [{"action": x["attrs"].get("action", ""), "method": x["attrs"].get("method", "")} for x in parser.forms],
    }


def main():
    results = []
    for url in URLS:
        status, html, err = fetch(url)
        results.append(score_page(url, status, html, err))

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    json_path = OUT_DIR / f"ff_wave3_operator_polish_scout_{stamp}.json"
    md_path = OUT_DIR / f"ff_wave3_operator_polish_scout_{stamp}.md"

    json_path.write_text(json.dumps({"generated_at": datetime.now().isoformat(timespec="seconds"), "results": results}, indent=2), encoding="utf-8")

    lines = []
    lines.append("# FutureFunded Wave 3 Operator Polish Scout")
    lines.append("")
    lines.append(f"- **Generated:** `{datetime.now().isoformat(timespec='seconds')}`")
    lines.append("")
    lines.append("## Page checks")
    lines.append("")
    lines.append("| URL | HTTP | Fetch | Protected/OK | Launch language | Operator language | Primary action | Data contracts |")
    lines.append("| --- | ---: | --- | --- | --- | --- | --- | --- |")
    for r in results:
        c = r["checks"]
        lines.append(
            f"| `{r['url']}` | {r['status']} | {'✅' if c['fetch_ok'] else '❌'} | "
            f"{'✅' if c['status_ok_or_protected'] else '❌'} | "
            f"{'✅' if c['has_launch_language'] else '⚠️'} | "
            f"{'✅' if c['has_operator_language'] else '⚠️'} | "
            f"{'✅' if c['has_primary_action'] else '⚠️'} | "
            f"{'✅' if c['has_data_contracts'] else '⚠️'} |"
        )

    lines.append("")
    lines.append("## Recommended Wave 3 patch direction")
    lines.append("")
    lines.append("1. Onboarding should feel like a guided launch workspace.")
    lines.append("2. Dashboard should clearly show campaign health, money movement, sponsor queue, and next actions.")
    lines.append("3. Protected dashboard behavior is acceptable, but the access-denied/login state should feel intentional.")
    lines.append("4. Every operator action should explain what happens next.")
    lines.append("")

    md_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"✅ Wave 3 operator polish scout: {md_path}")
    print(f"JSON: {json_path}")


if __name__ == "__main__":
    main()
