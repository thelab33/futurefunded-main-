#!/usr/bin/env python3
from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


ROOT = Path.cwd()
OUTPUT_DIR = ROOT / "docs" / "audits" / "backend-inventory"

PY_EXTENSIONS = {".py"}
TEXT_EXTENSIONS = {
    ".py", ".html", ".jinja", ".jinja2", ".css", ".js", ".mjs", ".json", ".toml",
    ".yaml", ".yml", ".ini", ".cfg", ".txt", ".md", ".env", ".example", ".sh",
}

IGNORE_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
    ".next",
    "coverage",
}

# Folders that may contain intentionally broken historical snapshots.
# They should be inventoried as risky artifacts, but not parsed as active Python.
ARCHIVE_DIRS = {
    "tmp",
    ".ff-backups",
    ".template-backups",
}

RISKY_FILE_MARKERS = [
    ".bak",
    ".before-",
    ".backup",
    ":Zone.Identifier",
    ".orig",
    ".tmp",
]

HARDCODED_ASSET_PATTERNS = [
    "campaign-premium-v3-20260505",
    "production-v1-20260507",
    "cta_hierarchy=20260507v1",
    "local-stripe-test",
    "demo-hardening",
]

SECRETISH_KEYS = (
    "SECRET",
    "TOKEN",
    "PASSWORD",
    "PRIVATE",
    "KEY",
    "DSN",
    "WEBHOOK",
    "DATABASE_URL",
    "STRIPE_SECRET",
    "PAYPAL",
)


HTTP_METHODS = {"get", "post", "put", "patch", "delete", "route"}


@dataclass
class RouteInfo:
    file: str
    line: int
    owner: str
    function: str
    path: str
    methods: list[str]
    decorator: str


@dataclass
class BlueprintInfo:
    file: str
    line: int
    variable: str
    name: str | None


@dataclass
class RouterInfo:
    file: str
    line: int
    variable: str
    framework: str


@dataclass
class ModelInfo:
    file: str
    line: int
    class_name: str
    bases: list[str]
    table_name: str | None = None


@dataclass
class AppFactoryInfo:
    file: str
    line: int
    kind: str
    name: str


@dataclass
class RegisterInfo:
    file: str
    line: int
    call: str


@dataclass
class Finding:
    severity: str
    title: str
    detail: str
    file: str | None = None
    line: int | None = None


@dataclass
class BackendInventory:
    generated_at: str
    root: str
    git: dict[str, Any]
    files: dict[str, Any]
    entrypoints: dict[str, list[str]]
    python_modules: dict[str, Any]
    flask: dict[str, Any]
    fastapi: dict[str, Any]
    models: list[dict[str, Any]]
    config_env: dict[str, Any]
    payments_notifications: dict[str, Any]
    deploy_runtime: dict[str, Any]
    stale_or_risky_files: list[str]
    hardcoded_asset_references: list[dict[str, Any]]
    findings: list[dict[str, Any]]


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except Exception:
        return path.as_posix()


def is_archive_path(path: Path) -> bool:
    return bool(set(path.parts).intersection(ARCHIVE_DIRS))


def is_generated_audit_path(path: Path) -> bool:
    r = rel(path)
    return r.startswith((
        "docs/audits/backend-inventory/",
        "docs/audits/release-gate/",
    ))


def should_scan_for_active_asset_drift(path: Path) -> bool:
    r = rel(path)

    if is_archive_path(path) or is_generated_audit_path(path):
        return False

    if r == "scripts/audit/backend_inventory.py":
        return False

    return r.startswith((
        "apps/web/app/templates/",
        "apps/web/app/static/",
        "apps/web/app/__init__.py",
        "run.py",
        "Procfile",
        "render.yaml",
    ))


def run_cmd(args: list[str]) -> str:
    try:
        return subprocess.check_output(args, cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return ""


def iter_files(*, include_ignored: bool = False) -> list[Path]:
    out: list[Path] = []

    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue

        parts = set(path.parts)
        if not include_ignored and parts.intersection(IGNORE_DIRS):
            continue

        out.append(path)

    return sorted(out)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def get_fullname(node: ast.AST | None) -> str:
    if node is None:
        return ""

    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        prefix = get_fullname(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr

    if isinstance(node, ast.Call):
        return get_fullname(node.func)

    if isinstance(node, ast.Subscript):
        return get_fullname(node.value)

    return ""


def get_constant_string(node: ast.AST | None) -> str | None:
    if node is None:
        return None

    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value

    if isinstance(node, ast.JoinedStr):
        return "<f-string>"

    return None


def get_constant_list(node: ast.AST | None) -> list[str]:
    if node is None:
        return []

    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        out = []
        for item in node.elts:
            value = get_constant_string(item)
            if value:
                out.append(value.upper())
        return out

    value = get_constant_string(node)
    return [value.upper()] if value else []


def get_keyword(call: ast.Call, name: str) -> ast.AST | None:
    for kw in call.keywords:
        if kw.arg == name:
            return kw.value
    return None


def safe_unparse(node: ast.AST) -> str:
    try:
        return ast.unparse(node)
    except Exception:
        return get_fullname(node)


def target_names(targets: list[ast.expr]) -> list[str]:
    names: list[str] = []

    for target in targets:
        if isinstance(target, ast.Name):
            names.append(target.id)
        elif isinstance(target, ast.Tuple):
            for item in target.elts:
                if isinstance(item, ast.Name):
                    names.append(item.id)

    return names


def parse_python_file(path: Path) -> dict[str, Any]:
    text = read_text(path)
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError as exc:
        return {
            "syntax_error": {
                "file": rel(path),
                "line": exc.lineno or 0,
                "message": str(exc),
            },
            "routes": [],
            "blueprints": [],
            "routers": [],
            "models": [],
            "factories": [],
            "registers": [],
            "imports": [],
            "config_classes": [],
        }

    routes: list[RouteInfo] = []
    blueprints: list[BlueprintInfo] = []
    routers: list[RouterInfo] = []
    models: list[ModelInfo] = []
    factories: list[AppFactoryInfo] = []
    registers: list[RegisterInfo] = []
    imports: list[str] = []
    config_classes: list[dict[str, Any]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)

        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                imports.append(f"{module}.{alias.name}" if module else alias.name)

        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            value = node.value if isinstance(node, ast.Assign) else node.value
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]

            if isinstance(value, ast.Call):
                call_name = get_fullname(value.func)
                names = target_names(targets)

                if call_name.endswith("Blueprint"):
                    bp_name = None
                    if value.args:
                        bp_name = get_constant_string(value.args[0])
                    for name in names:
                        blueprints.append(
                            BlueprintInfo(
                                file=rel(path),
                                line=getattr(node, "lineno", 0),
                                variable=name,
                                name=bp_name,
                            )
                        )

                if call_name.endswith("APIRouter"):
                    for name in names:
                        routers.append(
                            RouterInfo(
                                file=rel(path),
                                line=getattr(node, "lineno", 0),
                                variable=name,
                                framework="FastAPI",
                            )
                        )

                if call_name.endswith("Flask"):
                    for name in names:
                        factories.append(
                            AppFactoryInfo(
                                file=rel(path),
                                line=getattr(node, "lineno", 0),
                                kind="Flask app instance",
                                name=name,
                            )
                        )

                if call_name.endswith("FastAPI"):
                    for name in names:
                        factories.append(
                            AppFactoryInfo(
                                file=rel(path),
                                line=getattr(node, "lineno", 0),
                                kind="FastAPI app instance",
                                name=name,
                            )
                        )

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == "create_app":
                factories.append(
                    AppFactoryInfo(
                        file=rel(path),
                        line=node.lineno,
                        kind="app factory",
                        name=node.name,
                    )
                )

            for deco in node.decorator_list:
                call = deco if isinstance(deco, ast.Call) else None
                func = call.func if call else deco
                decorator_name = get_fullname(func)
                last = decorator_name.split(".")[-1].lower()

                if last not in HTTP_METHODS:
                    continue

                route_path = ""
                methods: list[str] = []

                if call and call.args:
                    route_path = get_constant_string(call.args[0]) or "<dynamic>"

                if last == "route":
                    methods = get_constant_list(get_keyword(call, "methods")) if call else []
                    if not methods:
                        methods = ["GET"]
                else:
                    methods = [last.upper()]

                owner = decorator_name.rsplit(".", 1)[0] if "." in decorator_name else decorator_name

                routes.append(
                    RouteInfo(
                        file=rel(path),
                        line=node.lineno,
                        owner=owner,
                        function=node.name,
                        path=route_path,
                        methods=methods,
                        decorator=decorator_name,
                    )
                )

        elif isinstance(node, ast.ClassDef):
            bases = [get_fullname(base) for base in node.bases]
            is_model = any(
                base.endswith("Model")
                or base.endswith("db.Model")
                or base.endswith("Base")
                or base.endswith("SQLModel")
                for base in bases
            )

            table_name = None
            for item in node.body:
                if isinstance(item, ast.Assign):
                    for target in item.targets:
                        if isinstance(target, ast.Name) and target.id == "__tablename__":
                            table_name = get_constant_string(item.value)

            if is_model:
                models.append(
                    ModelInfo(
                        file=rel(path),
                        line=node.lineno,
                        class_name=node.name,
                        bases=bases,
                        table_name=table_name,
                    )
                )

            if node.name.endswith("Config") or node.name in {"Config", "BaseConfig"}:
                config_classes.append(
                    {
                        "file": rel(path),
                        "line": node.lineno,
                        "class_name": node.name,
                        "bases": bases,
                    }
                )

        elif isinstance(node, ast.Call):
            call_name = get_fullname(node.func)
            if call_name.endswith("register_blueprint") or call_name.endswith("include_router"):
                registers.append(
                    RegisterInfo(
                        file=rel(path),
                        line=getattr(node, "lineno", 0),
                        call=safe_unparse(node),
                    )
                )

    return {
        "syntax_error": None,
        "routes": [asdict(item) for item in routes],
        "blueprints": [asdict(item) for item in blueprints],
        "routers": [asdict(item) for item in routers],
        "models": [asdict(item) for item in models],
        "factories": [asdict(item) for item in factories],
        "registers": [asdict(item) for item in registers],
        "imports": sorted(set(imports)),
        "config_classes": config_classes,
    }


def classify_file(path: Path) -> str:
    r = rel(path)

    if r.startswith("apps/web/app/blueprints/"):
        return "web_blueprint"
    if r.startswith("apps/web/app/templates/"):
        return "web_template"
    if r.startswith("apps/web/app/static/"):
        return "web_static"
    if r.startswith("apps/web/app/"):
        return "web_app"
    if r.startswith("apps/api/app/routers/"):
        return "api_router"
    if r.startswith("apps/api/app/"):
        return "api_app"
    if r.startswith("migrations/") or "alembic" in r.lower():
        return "migration"
    if r.startswith("scripts/audit/"):
        return "audit_script"
    if r.startswith("scripts/deploy/"):
        return "deploy_script"
    if r.startswith("scripts/"):
        return "script"
    if r.startswith(".github/workflows/"):
        return "github_workflow"
    if r.startswith("tests/"):
        return "test"
    if path.name in {"run.py", "wsgi.py", "asgi.py", "manage.py", "app.py"}:
        return "entrypoint"
    if path.name in {"requirements.txt", "pyproject.toml", "Pipfile", "poetry.lock", "package.json"}:
        return "dependency_manifest"

    return "other"


def scan_env_files(files: list[Path]) -> dict[str, Any]:
    env_files = [p for p in files if p.name.startswith(".env") or p.name.endswith(".env")]
    env_report: dict[str, Any] = {}
    alerts: list[Finding] = []

    for path in sorted(env_files):
        keys: list[dict[str, Any]] = []
        local_values: dict[str, str] = {}

        for index, raw in enumerate(read_text(path).splitlines(), start=1):
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if not key:
                continue

            local_values[key] = value

            keys.append(
                {
                    "line": index,
                    "key": key,
                    "sensitive": any(marker in key.upper() for marker in SECRETISH_KEYS),
                    "value_kind": classify_env_value(key, value),
                }
            )

        env_report[rel(path)] = keys

        env_name = (
            local_values.get("FF_ENV")
            or local_values.get("FLASK_ENV")
            or local_values.get("ENV")
            or local_values.get("APP_ENV")
            or ""
        ).lower()

        if env_name == "production":
            db_url = local_values.get("DATABASE_URL", "")
            if db_url.startswith("sqlite"):
                alerts.append(
                    Finding(
                        severity="warning",
                        title="Production-like env uses SQLite",
                        detail="This may be intentional for demo, but production fundraising should usually use a managed DB.",
                        file=rel(path),
                    )
                )

            stripe_secret = local_values.get("STRIPE_SECRET_KEY", "")
            if stripe_secret.startswith("sk_test_"):
                alerts.append(
                    Finding(
                        severity="warning",
                        title="Production-like env uses Stripe test key",
                        detail="Good for demo mode, unsafe for live fundraising unless explicitly intended.",
                        file=rel(path),
                    )
                )

            if local_values.get("MAIL_ENABLED", "").lower() in {"0", "false", "no"}:
                alerts.append(
                    Finding(
                        severity="info",
                        title="Production-like env has MAIL_ENABLED=false",
                        detail="Operator/customer emails may be stubbed or outbox-only.",
                        file=rel(path),
                    )
                )

    return {
        "env_files": env_report,
        "env_alerts": [asdict(item) for item in alerts],
    }


def classify_env_value(key: str, value: str) -> str:
    if not value:
        return "empty"
    if any(marker in key.upper() for marker in SECRETISH_KEYS):
        if value.startswith("sk_test_"):
            return "stripe_test_secret"
        if value.startswith("sk_live_"):
            return "stripe_live_secret"
        if value.startswith("pk_test_"):
            return "stripe_test_publishable"
        if value.startswith("pk_live_"):
            return "stripe_live_publishable"
        if value.startswith("sqlite"):
            return "database_sqlite_url"
        if value.startswith("postgres"):
            return "database_postgres_url"
        return "sensitive_set"
    if value.lower() in {"true", "false", "1", "0", "yes", "no"}:
        return "boolean"
    if value.startswith("http://") or value.startswith("https://"):
        return "url"
    return "set"


def scan_hardcoded_assets(files: list[Path]) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []

    for path in files:
        if not should_scan_for_active_asset_drift(path):
            continue

        if path.suffix not in TEXT_EXTENSIONS and not path.name.startswith(".env"):
            continue

        text = read_text(path)
        if not text:
            continue

        for line_no, line in enumerate(text.splitlines(), start=1):
            for pattern in HARDCODED_ASSET_PATTERNS:
                if pattern in line:
                    hits.append(
                        {
                            "file": rel(path),
                            "line": line_no,
                            "pattern": pattern,
                            "line_preview": line.strip()[:220],
                        }
                    )

    return hits


def scan_stale_files(files: list[Path]) -> list[str]:
    stale = []

    for path in files:
        r = rel(path)
        if any(marker in r for marker in RISKY_FILE_MARKERS):
            stale.append(r)

    return sorted(stale)


def find_existing(paths: list[str]) -> list[str]:
    return [item for item in paths if (ROOT / item).exists()]


def scan_payments_notifications(files: list[Path]) -> dict[str, Any]:
    keywords = {
        "stripe": [],
        "paypal": [],
        "mail": [],
        "email": [],
        "notification": [],
        "outbox": [],
        "sponsor": [],
        "ledger": [],
    }

    interesting_exts = {".py", ".js", ".html", ".md", ".sh"}

    for path in files:
        if path.suffix not in interesting_exts:
            continue

        r = rel(path).lower()

        for key in keywords:
            if key in r:
                keywords[key].append(rel(path))

    return {key: sorted(set(value))[:80] for key, value in keywords.items()}


def scan_db_artifacts(files: list[Path]) -> dict[str, Any]:
    db_files = []
    migration_files = []

    for path in files:
        r = rel(path)

        if path.suffix.lower() in {".db", ".sqlite", ".sqlite3"}:
            try:
                size = path.stat().st_size
            except Exception:
                size = 0

            db_files.append(
                {
                    "file": r,
                    "size_bytes": size,
                }
            )

        if "migration" in r.lower() or "alembic" in r.lower():
            migration_files.append(r)

    return {
        "db_files": sorted(db_files, key=lambda x: x["file"]),
        "migration_files": sorted(migration_files)[:120],
    }


def scan_dependency_manifests(files: list[Path]) -> dict[str, Any]:
    names = {
        "requirements.txt",
        "requirements-dev.txt",
        "pyproject.toml",
        "Pipfile",
        "poetry.lock",
        "package.json",
        "pnpm-lock.yaml",
        "package-lock.json",
        "yarn.lock",
    }

    found = [rel(p) for p in files if p.name in names]

    return {
        "found": sorted(found),
    }


def build_inventory() -> BackendInventory:
    files = iter_files()

    py_files = [p for p in files if p.suffix == ".py"]

    active_py_files = [
        p for p in py_files
        if not is_archive_path(p)
    ]

    parsed = [parse_python_file(p) for p in active_py_files]

    syntax_errors = [item["syntax_error"] for item in parsed if item.get("syntax_error")]

    routes = [route for item in parsed for route in item["routes"]]
    blueprints = [bp for item in parsed for bp in item["blueprints"]]
    routers = [router for item in parsed for router in item["routers"]]
    models = [model for item in parsed for model in item["models"]]
    factories = [factory for item in parsed for factory in item["factories"]]
    registers = [reg for item in parsed for reg in item["registers"]]
    config_classes = [cls for item in parsed for cls in item["config_classes"]]

    category_counts = Counter(classify_file(path) for path in files)
    py_category_counts = Counter(classify_file(path) for path in py_files)

    routes_by_file = Counter(route["file"] for route in routes)
    routes_by_owner = Counter(route["owner"] for route in routes)
    methods = Counter(method for route in routes for method in route["methods"])

    git_status = run_cmd(["git", "status", "--short"])
    git_branch = run_cmd(["git", "branch", "--show-current"])
    git_commit = run_cmd(["git", "rev-parse", "--short", "HEAD"])

    hardcoded_assets = scan_hardcoded_assets(files)
    stale_files = scan_stale_files(files)
    env_report = scan_env_files(files)

    db_report = scan_db_artifacts(files)

    findings: list[Finding] = []

    if git_status:
        findings.append(
            Finding(
                severity="info",
                title="Working tree has uncommitted changes",
                detail="Run `git status --short` before deploy/merge.",
            )
        )

    for item in syntax_errors:
        findings.append(
            Finding(
                severity="error",
                title="Python syntax error",
                detail=item["message"],
                file=item["file"],
                line=item["line"],
            )
        )

    if hardcoded_assets:
        findings.append(
            Finding(
                severity="warning",
                title="Hardcoded/stale asset version strings found",
                detail="These can cause Cloudflare/browser cache drift. Prefer FF_ASSET_V / git SHA.",
            )
        )

    app_backup_files = [f for f in stale_files if f.startswith("apps/")]
    if app_backup_files:
        findings.append(
            Finding(
                severity="warning",
                title="Backup/WIP files exist inside app directories",
                detail="These can confuse audits, deploys, and grep-based patching. Remove before production.",
            )
        )

    if not routes:
        findings.append(
            Finding(
                severity="warning",
                title="No route decorators detected",
                detail="The scan may be missing your app route definitions or the backend uses non-decorator registration.",
            )
        )

    if not factories:
        findings.append(
            Finding(
                severity="warning",
                title="No app factory or app instance detected",
                detail="Expected to find Flask/FastAPI app factory or app instance.",
            )
        )

    for env_alert in env_report["env_alerts"]:
        findings.append(Finding(**env_alert))

    if not db_report["migration_files"]:
        findings.append(
            Finding(
                severity="info",
                title="No migrations detected",
                detail="If this app persists records, verify migrations/alembic/flask-migrate are configured.",
            )
        )

    entrypoints = {
        "python_entrypoints": find_existing([
            "run.py",
            "wsgi.py",
            "asgi.py",
            "manage.py",
            "app.py",
            "apps/web/app/__init__.py",
            "apps/api/app/main.py",
            "apps/api/main.py",
        ]),
        "deploy_files": find_existing([
            "Procfile",
            "Dockerfile",
            "docker-compose.yml",
            "render.yaml",
            "fly.toml",
            "railway.json",
            "systemd/futurefunded.service",
            ".github/workflows/deploy.yml",
            ".github/workflows/ci.yml",
            "scripts/deploy/purge_cloudflare_assets.sh",
        ]),
    }

    deploy_runtime = {
        "entrypoints": entrypoints,
        "dependencies": scan_dependency_manifests(files),
        "db": db_report,
        "scripts": {
            "audit_scripts": sorted(rel(p) for p in files if rel(p).startswith("scripts/audit/"))[:120],
            "deploy_scripts": sorted(rel(p) for p in files if rel(p).startswith("scripts/deploy/"))[:120],
            "setup_scripts": sorted(rel(p) for p in files if p.name.startswith("setup_") or "setup" in rel(p))[:120],
        },
    }

    return BackendInventory(
        generated_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        root=str(ROOT),
        git={
            "branch": git_branch,
            "commit": git_commit,
            "status_short": git_status.splitlines() if git_status else [],
        },
        files={
            "total_scanned": len(files),
            "python_files": len(py_files),
            "active_python_files": len(active_py_files),
            "archived_python_files": len(py_files) - len(active_py_files),
            "category_counts": dict(sorted(category_counts.items())),
            "python_category_counts": dict(sorted(py_category_counts.items())),
        },
        entrypoints=entrypoints,
        python_modules={
            "syntax_errors": syntax_errors,
            "config_classes": config_classes,
            "top_imports": Counter(
                imp.split(".")[0]
                for item in parsed
                for imp in item.get("imports", [])
                if imp
            ).most_common(40),
        },
        flask={
            "app_factories_and_instances": factories,
            "blueprints": blueprints,
            "register_calls": registers,
            "routes": routes,
            "route_counts": {
                "total": len(routes),
                "by_file": routes_by_file.most_common(80),
                "by_owner": routes_by_owner.most_common(80),
                "by_method": dict(sorted(methods.items())),
            },
        },
        fastapi={
            "routers": routers,
            "possible_routes": [
                route for route in routes if "router" in route["owner"].lower()
            ],
        },
        models=models,
        config_env=env_report,
        payments_notifications=scan_payments_notifications(files),
        deploy_runtime=deploy_runtime,
        stale_or_risky_files=stale_files[:300],
        hardcoded_asset_references=hardcoded_assets[:300],
        findings=[asdict(item) for item in findings],
    )


def write_json(report: BackendInventory) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / "backend-inventory.json"
    path.write_text(json.dumps(asdict(report), indent=2), encoding="utf-8")
    return path


def md_table(headers: list[str], rows: list[list[Any]]) -> str:
    out = []
    out.append("| " + " | ".join(headers) + " |")
    out.append("|" + "|".join("---" for _ in headers) + "|")
    for row in rows:
        out.append("| " + " | ".join(str(cell).replace("|", "\\|") for cell in row) + " |")
    return "\n".join(out)


def write_markdown(report: BackendInventory) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / "backend-inventory.md"

    data = asdict(report)

    findings = data["findings"]
    routes = data["flask"]["routes"]
    blueprints = data["flask"]["blueprints"]
    registers = data["flask"]["register_calls"]
    models = data["models"]
    factories = data["flask"]["app_factories_and_instances"]
    env_files = data["config_env"]["env_files"]
    assets = data["hardcoded_asset_references"]

    lines: list[str] = []

    lines.append("# FutureFunded Backend Inventory")
    lines.append("")
    lines.append(f"- Generated: `{data['generated_at']}`")
    lines.append(f"- Repo: `{data['root']}`")
    lines.append(f"- Branch: `{data['git']['branch']}`")
    lines.append(f"- Commit: `{data['git']['commit']}`")
    lines.append("")

    lines.append("## Executive summary")
    lines.append("")
    lines.append(md_table(
        ["Area", "Count"],
        [
            ["Files scanned", data["files"]["total_scanned"]],
            ["Python files", data["files"]["python_files"]],
            ["Routes detected", data["flask"]["route_counts"]["total"]],
            ["Blueprints detected", len(blueprints)],
            ["Register/include calls", len(registers)],
            ["Models detected", len(models)],
            ["Hardcoded asset refs", len(assets)],
            ["Risky/backups listed", len(data["stale_or_risky_files"])],
            ["Findings", len(findings)],
        ],
    ))
    lines.append("")

    lines.append("## Findings")
    lines.append("")
    if findings:
        lines.append(md_table(
            ["Severity", "Title", "File", "Line", "Detail"],
            [
                [
                    item["severity"],
                    item["title"],
                    item.get("file") or "",
                    item.get("line") or "",
                    item["detail"],
                ]
                for item in findings
            ],
        ))
    else:
        lines.append("No findings detected.")
    lines.append("")

    lines.append("## Entrypoints and deploy files")
    lines.append("")
    lines.append("### Python entrypoints")
    lines.append("")
    for item in data["entrypoints"]["python_entrypoints"]:
        lines.append(f"- `{item}`")
    if not data["entrypoints"]["python_entrypoints"]:
        lines.append("- None detected")
    lines.append("")

    lines.append("### Deploy/runtime files")
    lines.append("")
    for item in data["entrypoints"]["deploy_files"]:
        lines.append(f"- `{item}`")
    if not data["entrypoints"]["deploy_files"]:
        lines.append("- None detected")
    lines.append("")

    lines.append("## File categories")
    lines.append("")
    lines.append(md_table(
        ["Category", "Files"],
        [[key, value] for key, value in data["files"]["category_counts"].items()],
    ))
    lines.append("")

    lines.append("## App factories / app instances")
    lines.append("")
    if factories:
        lines.append(md_table(
            ["Kind", "Name", "File", "Line"],
            [[item["kind"], item["name"], item["file"], item["line"]] for item in factories],
        ))
    else:
        lines.append("None detected.")
    lines.append("")

    lines.append("## Flask blueprints")
    lines.append("")
    if blueprints:
        lines.append(md_table(
            ["Variable", "Blueprint name", "File", "Line"],
            [[item["variable"], item.get("name") or "", item["file"], item["line"]] for item in blueprints],
        ))
    else:
        lines.append("None detected.")
    lines.append("")

    lines.append("## Blueprint/register calls")
    lines.append("")
    if registers:
        lines.append(md_table(
            ["File", "Line", "Call"],
            [[item["file"], item["line"], item["call"][:180]] for item in registers[:120]],
        ))
    else:
        lines.append("None detected.")
    lines.append("")

    lines.append("## Routes")
    lines.append("")
    if routes:
        lines.append(md_table(
            ["Methods", "Path", "Owner", "Function", "File", "Line"],
            [
                [
                    ",".join(item["methods"]),
                    item["path"],
                    item["owner"],
                    item["function"],
                    item["file"],
                    item["line"],
                ]
                for item in routes[:300]
            ],
        ))
        if len(routes) > 300:
            lines.append("")
            lines.append(f"_Only first 300 routes shown. Full list in JSON._")
    else:
        lines.append("None detected.")
    lines.append("")

    lines.append("## Models / persistence")
    lines.append("")
    if models:
        lines.append(md_table(
            ["Class", "Table", "Bases", "File", "Line"],
            [
                [
                    item["class_name"],
                    item.get("table_name") or "",
                    ", ".join(item.get("bases") or []),
                    item["file"],
                    item["line"],
                ]
                for item in models
            ],
        ))
    else:
        lines.append("None detected.")
    lines.append("")

    lines.append("### Database artifacts")
    lines.append("")
    db_files = data["deploy_runtime"]["db"]["db_files"]
    if db_files:
        lines.append(md_table(
            ["DB file", "Size bytes"],
            [[item["file"], item["size_bytes"]] for item in db_files],
        ))
    else:
        lines.append("No SQLite/db files detected.")
    lines.append("")

    lines.append("### Migration artifacts")
    lines.append("")
    migration_files = data["deploy_runtime"]["db"]["migration_files"]
    if migration_files:
        for item in migration_files[:80]:
            lines.append(f"- `{item}`")
    else:
        lines.append("No migration/alembic files detected.")
    lines.append("")

    lines.append("## Environment/config files")
    lines.append("")
    if env_files:
        for filename, keys in env_files.items():
            lines.append(f"### `{filename}`")
            lines.append("")
            lines.append(md_table(
                ["Line", "Key", "Sensitive?", "Value kind"],
                [
                    [
                        item["line"],
                        item["key"],
                        "yes" if item["sensitive"] else "no",
                        item["value_kind"],
                    ]
                    for item in keys
                ],
            ))
            lines.append("")
    else:
        lines.append("No .env files detected.")
        lines.append("")

    lines.append("## Payments, notifications, sponsors, ledger files")
    lines.append("")
    for key, values in data["payments_notifications"].items():
        lines.append(f"### {key}")
        if values:
            for item in values[:60]:
                lines.append(f"- `{item}`")
        else:
            lines.append("- None detected")
        lines.append("")

    lines.append("## Hardcoded asset/version references")
    lines.append("")
    if assets:
        lines.append(md_table(
            ["Pattern", "File", "Line", "Preview"],
            [
                [
                    item["pattern"],
                    item["file"],
                    item["line"],
                    item["line_preview"],
                ]
                for item in assets
            ],
        ))
    else:
        lines.append("No hardcoded/stale asset markers detected.")
    lines.append("")

    lines.append("## Stale / backup / WIP files")
    lines.append("")
    stale_files = data["stale_or_risky_files"]
    if stale_files:
        for item in stale_files[:300]:
            lines.append(f"- `{item}`")
    else:
        lines.append("No stale backup markers detected.")
    lines.append("")

    lines.append("## Next actions")
    lines.append("")
    lines.append("1. Fix any `error` findings first.")
    lines.append("2. Remove `.bak`, `.before-*`, and `Zone.Identifier` files inside `apps/` before deploy.")
    lines.append("3. Remove hardcoded asset version strings and use `FF_ASSET_V` / deploy SHA.")
    lines.append("4. Confirm production app restart actually deploys the current git commit.")
    lines.append("5. Run demo/platform audits after every deploy.")
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def print_console_summary(report: BackendInventory, md_path: Path, json_path: Path) -> None:
    data = asdict(report)

    print()
    print("🚀 FutureFunded backend inventory")
    print("=" * 40)
    print(f"Branch:      {data['git']['branch']}")
    print(f"Commit:      {data['git']['commit']}")
    print(f"Files:       {data['files']['total_scanned']}")
    print(f"Python:      {data['files']['python_files']}")
    print(f"Routes:      {data['flask']['route_counts']['total']}")
    print(f"Blueprints:  {len(data['flask']['blueprints'])}")
    print(f"Models:      {len(data['models'])}")
    print(f"Findings:    {len(data['findings'])}")
    print()
    print(f"📝 Markdown: {md_path}")
    print(f"🧾 JSON:     {json_path}")
    print()

    if data["findings"]:
        print("Top findings:")
        for item in data["findings"][:12]:
            location = ""
            if item.get("file"):
                location = f" ({item['file']}:{item.get('line') or ''})"
            print(f" - [{item['severity']}] {item['title']}{location}")
        print()


def main() -> int:
    report = build_inventory()
    json_path = write_json(report)
    md_path = write_markdown(report)
    print_console_summary(report, md_path, json_path)

    has_error = any(item["severity"] == "error" for item in asdict(report)["findings"])
    return 1 if has_error else 0


if __name__ == "__main__":
    raise SystemExit(main())
