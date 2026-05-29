#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "audit"
OUT.mkdir(parents=True, exist_ok=True)

KEYS = [
    "STRIPE_SECRET_KEY",
    "FF_STRIPE_WEBHOOK_SECRET",
    "STRIPE_WEBHOOK_SECRET",
    "STRIPE_WEBHOOK_SIGNING_SECRET",
    "FF_OPERATOR_ACCESS_TOKEN",
    "FLASK_APP",
    "FLASK_ENV",
]


def mask(value: str | None) -> dict:
    value = (value or "").strip()
    return {
        "present": bool(value),
        "prefix": value[:8] + "…" if value else "",
        "length": len(value),
        "valid_stripe_secret": value.startswith(("sk_test_", "sk_live_")) if value else False,
        "valid_webhook_secret": value.startswith("whsec_") if value else False,
    }


def load_env_file(path: Path) -> dict[str, str]:
    data = {}
    if not path.exists():
        return data

    for line in path.read_text().splitlines():
        if not line.strip() or line.lstrip().startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        data[k.strip()] = v.strip()

    return data


def run(cmd: list[str]) -> str:
    try:
        return subprocess.check_output(cmd, cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return ""


def pids_on_5000() -> list[str]:
    out = run(["bash", "-lc", "lsof -ti tcp:5000 || true"])
    return [x.strip() for x in out.splitlines() if x.strip().isdigit()]


def proc_env(pid: str) -> dict[str, str]:
    path = Path(f"/proc/{pid}/environ")
    if not path.exists():
        return {}

    raw = path.read_bytes()
    data = {}

    for item in raw.split(b"\x00"):
        if b"=" not in item:
            continue
        k, v = item.split(b"=", 1)
        data[k.decode(errors="replace")] = v.decode(errors="replace")

    return data


def cmdline(pid: str) -> str:
    path = Path(f"/proc/{pid}/cmdline")
    if not path.exists():
        return ""
    return path.read_bytes().replace(b"\x00", b" ").decode(errors="replace").strip()


def main() -> int:
    dotenv = load_env_file(ROOT / ".env.local")
    tmp_token = (
        Path("/tmp/ff_operator_token").read_text().strip()
        if Path("/tmp/ff_operator_token").exists()
        else ""
    )
    whsec_file = (
        Path(".stripe-local-whsec").read_text().strip()
        if Path(".stripe-local-whsec").exists()
        else ""
    )

    pids = pids_on_5000()

    report = {
        "repo": str(ROOT),
        "port_5000_pids": pids,
        "files": {
            ".env.local_exists": (ROOT / ".env.local").exists(),
            ".stripe-local-whsec_exists": (ROOT / ".stripe-local-whsec").exists(),
            "/tmp/ff_operator_token_exists": Path("/tmp/ff_operator_token").exists(),
            ".env.local": {k: mask(dotenv.get(k)) for k in KEYS},
            ".stripe-local-whsec": mask(whsec_file),
            "/tmp/ff_operator_token": mask(tmp_token),
        },
        "processes": [],
        "failures": [],
    }

    if not pids:
        report["failures"].append("No process is listening on tcp:5000.")

    for pid in pids:
        env = proc_env(pid)
        proc = {
            "pid": pid,
            "cmdline": cmdline(pid),
            "env": {k: mask(env.get(k)) for k in KEYS},
        }
        report["processes"].append(proc)

        if not env.get("STRIPE_SECRET_KEY", "").startswith(("sk_test_", "sk_live_")):
            report["failures"].append(f"PID {pid} missing valid STRIPE_SECRET_KEY.")

        webhook_present = any(
            env.get(k, "").startswith("whsec_")
            for k in [
                "FF_STRIPE_WEBHOOK_SECRET",
                "STRIPE_WEBHOOK_SECRET",
                "STRIPE_WEBHOOK_SIGNING_SECRET",
            ]
        )
        if not webhook_present:
            report["failures"].append(f"PID {pid} missing valid webhook whsec_ secret.")

        if tmp_token and env.get("FF_OPERATOR_ACCESS_TOKEN", "") != tmp_token:
            report["failures"].append(
                f"PID {pid} FF_OPERATOR_ACCESS_TOKEN does not match /tmp/ff_operator_token."
            )

    json_path = OUT / "ff_process_env_audit.json"
    md_path = OUT / "ff_process_env_audit.md"

    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = [
        "# FutureFunded Process Env Audit",
        "",
        f"Failures: **{len(report['failures'])}**",
        "",
    ]

    if report["failures"]:
        lines.extend(f"- ❌ {f}" for f in report["failures"])
    else:
        lines.append("- ✅ Flask process env matches required local secrets.")

    lines += [
        "",
        "## Port 5000 PIDs",
        "",
        "```txt",
        "\n".join(pids) or "(none)",
        "```",
        "",
        "## File Env Presence",
        "",
        "| Source | STRIPE_SECRET_KEY | Webhook secret | Operator token |",
        "|---|---:|---:|---:|",
        f"| .env.local | {mask(dotenv.get('STRIPE_SECRET_KEY'))['present']} | {any(mask(dotenv.get(k))['valid_webhook_secret'] for k in ['FF_STRIPE_WEBHOOK_SECRET','STRIPE_WEBHOOK_SECRET','STRIPE_WEBHOOK_SIGNING_SECRET'])} | {mask(dotenv.get('FF_OPERATOR_ACCESS_TOKEN'))['present']} |",
        f"| .stripe-local-whsec | — | {mask(whsec_file)['valid_webhook_secret']} | — |",
        f"| /tmp/ff_operator_token | — | — | {mask(tmp_token)['present']} |",
        "",
        "## Process Env Presence",
        "",
        "| PID | STRIPE_SECRET_KEY | Webhook secret | Operator token | Command |",
        "|---|---:|---:|---:|---|",
    ]

    for proc in report["processes"]:
        env = proc["env"]
        webhook = any(
            env[k]["valid_webhook_secret"]
            for k in [
                "FF_STRIPE_WEBHOOK_SECRET",
                "STRIPE_WEBHOOK_SECRET",
                "STRIPE_WEBHOOK_SIGNING_SECRET",
            ]
        )
        lines.append(
            f"| {proc['pid']} | {env['STRIPE_SECRET_KEY']['valid_stripe_secret']} | {webhook} | {env['FF_OPERATOR_ACCESS_TOKEN']['present']} | `{proc['cmdline'][:90]}` |"
        )

    md_path.write_text("\n".join(lines), encoding="utf-8")

    print("\nFutureFunded process env audit")
    print("==============================")
    print(f"Failures: {len(report['failures'])}")
    for failure in report["failures"]:
        print(f"❌ {failure}")
    if not report["failures"]:
        print("✅ Flask process env is valid")
    print(f"\nMarkdown: {md_path}")
    print(f"JSON:     {json_path}")

    return 1 if report["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
