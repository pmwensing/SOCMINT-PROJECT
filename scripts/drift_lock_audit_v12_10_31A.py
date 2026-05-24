#!/usr/bin/env python3
from __future__ import annotations

import configparser
import importlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple


ROOT = Path.cwd()
VERSION = "12.10.31F"
REPORT_STEM = "DRIFT_LOCK_AUDIT_V12_10_31F"
REPORT_DIR = ROOT / "release" / "drift_lock"
REPORT_JSON = REPORT_DIR / f"{REPORT_STEM}.json"
REPORT_MD = REPORT_DIR / f"{REPORT_STEM}.md"

EXPECTED_V12_ROUTES = {
    "/api/v12.10/command-center/cases/<case_id>/run-all",
    "/api/v12.10/dossier/run/<case_id>",
    "/api/v12.10/evidence/integrity/<case_id>",
    "/api/v12.10/runtime/mesh/<case_id>",
    "/api/v12.10/analyst/propagate/<case_id>",
    "/api/v12.10/risk/score/<case_id>",
    "/api/v12.10/monitoring/evolve/<case_id>",
    "/api/v12.10/ui/command-center",
}

SKIP_PARTS = {
    ".git",
    ".venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    "storage",
    "release",
    "tests",
    "scripts",
}


class Check:
    def __init__(self, name: str, status: str, detail: Any):
        self.name = name
        self.status = status
        self.detail = detail

    def as_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "detail": self.detail,
        }


def read(path: Path) -> str:
    try:
        return path.read_text(errors="replace")
    except Exception:
        return ""


def run(cmd: List[str]) -> Tuple[int, str]:
    try:
        out = subprocess.check_output(cmd, cwd=ROOT, stderr=subprocess.STDOUT, text=True)
        return 0, out
    except Exception as exc:
        return 1, getattr(exc, "output", repr(exc))


def py_files(include_scripts: bool = False) -> List[Path]:
    out: List[Path] = []
    for p in ROOT.rglob("*.py"):
        if not include_scripts and any(part in SKIP_PARTS for part in p.parts):
            continue
        if p.is_file():
            out.append(p)
    return sorted(out)


def detect_framework() -> Dict[str, Any]:
    flask_hits = []
    fastapi_hits = []

    for p in py_files():
        s = read(p)
        rel = str(p.relative_to(ROOT))
        if re.search(r"from\s+flask\s+import|import\s+flask|Flask\(", s):
            flask_hits.append(rel)
        if re.search(r"from\s+fastapi\s+import|import\s+fastapi|FastAPI\(", s):
            fastapi_hits.append(rel)

    if flask_hits and fastapi_hits:
        framework = "hybrid"
    elif flask_hits:
        framework = "flask"
    elif fastapi_hits:
        framework = "fastapi"
    else:
        framework = "unknown"

    return {
        "framework": framework,
        "flask_count": len(flask_hits),
        "fastapi_count": len(fastapi_hits),
        "flask_hits": flask_hits[:50],
        "fastapi_hits": fastapi_hits[:50],
    }


def identify_entrypoints() -> Dict[str, Any]:
    candidates = []

    for p in py_files():
        s = read(p)
        rel = str(p.relative_to(ROOT))
        score = 0
        notes = []

        if "def create_app" in s:
            score += 20
            notes.append("create_app")
        if "Flask(" in s:
            score += 10
            notes.append("Flask(")
        if "FastAPI(" in s:
            score += 10
            notes.append("FastAPI(")
        if "register_blueprint" in s:
            score += 5
            notes.append("register_blueprint")
        if "include_router" in s:
            score += 5
            notes.append("include_router")
        if "app.run" in s or "uvicorn.run" in s:
            score += 3
            notes.append("runner")

        if rel == "src/socmint/dashboard.py":
            score += 100

        if score:
            candidates.append({"path": rel, "score": score, "notes": notes})

    candidates.sort(key=lambda x: x["score"], reverse=True)

    return {
        "primary_guess": candidates[0] if candidates else None,
        "candidates": candidates[:25],
    }


def alembic_info() -> Dict[str, Any]:
    cfg = configparser.ConfigParser()
    cfg.read(ROOT / "alembic.ini")
    script_location = cfg.get("alembic", "script_location", fallback="alembic")
    versions_dir = ROOT / script_location / "versions"

    heads_code, heads_out = run(["alembic", "heads"])
    history_code, history_out = run(["alembic", "history", "--verbose"])

    heads = [line.split()[0] for line in heads_out.splitlines() if line.strip()]
    migrations = []

    if versions_dir.exists():
        for p in sorted(versions_dir.glob("*.py")):
            s = read(p)
            rev = re.search(r"revision\s*=\s*['\"]([^'\"]+)['\"]", s)
            down = re.search(r"down_revision\s*=\s*['\"]([^'\"]+)['\"]", s)
            migrations.append({
                "file": str(p.relative_to(ROOT)),
                "revision": rev.group(1) if rev else None,
                "down_revision": down.group(1) if down else None,
            })

    revisions = [m["revision"] for m in migrations if m["revision"]]
    duplicate_revisions = sorted({r for r in revisions if revisions.count(r) > 1})

    return {
        "script_location": script_location,
        "versions_dir": str(versions_dir.relative_to(ROOT)) if versions_dir.exists() else str(versions_dir),
        "heads_command_ok": heads_code == 0,
        "heads": heads,
        "raw_heads": heads_out,
        "history_command_ok": history_code == 0,
        "history_excerpt": history_out[-4000:],
        "migration_count": len(migrations),
        "migration_files": migrations,
        "duplicate_revisions": duplicate_revisions,
        "sole_expected_head": heads == ["0017_v12_10_schema_reconciliation"],
    }


def model_tables() -> Dict[str, Any]:
    tables: Set[str] = set()
    files = []

    for p in py_files():
        s = read(p)
        rel = str(p.relative_to(ROOT))
        local = set()

        for m in re.finditer(r"__tablename__\s*=\s*['\"]([^'\"]+)['\"]", s):
            local.add(m.group(1))
        for m in re.finditer(r"\bTable\(\s*['\"]([^'\"]+)['\"]", s):
            local.add(m.group(1))

        if local:
            tables.update(local)
            files.append({"file": rel, "tables": sorted(local)})

    return {
        "tables": sorted(tables),
        "table_count": len(tables),
        "model_files": files,
    }


def migration_tables() -> Dict[str, Any]:
    cfg = configparser.ConfigParser()
    cfg.read(ROOT / "alembic.ini")
    script_location = cfg.get("alembic", "script_location", fallback="alembic")
    versions_dir = ROOT / script_location / "versions"

    tables: Set[str] = set()
    files = []

    if not versions_dir.exists():
        return {"tables": [], "table_count": 0, "migration_files": []}

    for p in sorted(versions_dir.glob("*.py")):
        s = read(p)
        rel = str(p.relative_to(ROOT))
        local = set()

        patterns = [
            r"op\.create_table\(\s*['\"]([^'\"]+)['\"]",
            r"_create_if_missing\(\s*['\"]([^'\"]+)['\"]",
            r"op\.drop_table\(\s*['\"]([^'\"]+)['\"]",
            r"_drop_if_exists\(\s*['\"]([^'\"]+)['\"]",
        ]

        for pattern in patterns:
            for m in re.finditer(pattern, s):
                local.add(m.group(1))

        if local:
            tables.update(local)
            files.append({"file": rel, "tables": sorted(local)})

    return {
        "tables": sorted(tables),
        "table_count": len(tables),
        "migration_files": files,
    }


def compare_models_migrations() -> Dict[str, Any]:
    models = model_tables()
    migrations = migration_tables()

    model_set = set(models["tables"])
    migration_set = set(migrations["tables"])

    return {
        "models": models,
        "migrations": migrations,
        "tables_in_models_not_migrations": sorted(model_set - migration_set),
        "tables_in_migrations_not_models": sorted(migration_set - model_set),
        "models_covered_by_migrations": len(model_set - migration_set) == 0,
    }


def route_static_scan() -> Dict[str, Any]:
    routes: Set[str] = set()
    files = []

    for p in py_files(include_scripts=True):
        if any(part in {"tests", "release"} for part in p.parts):
            continue
        s = read(p)
        rel = str(p.relative_to(ROOT))
        local = set()

        for m in re.finditer(r"@\w+\.(?:route|get|post|put|delete|patch)\(\s*['\"]([^'\"]+)['\"]", s):
            local.add(m.group(1))
        for m in re.finditer(r"@(?:route|get|post|put|delete|patch)\(\s*['\"]([^'\"]+)['\"]", s):
            local.add(m.group(1))

        if local:
            routes.update(local)
            files.append({"file": rel, "routes": sorted(local)})

    return {
        "routes": sorted(routes),
        "route_count": len(routes),
        "route_files": files,
    }


def _fresh_import_runtime_modules() -> None:
    for name in [
        "src.socmint.dashboard",
        "src.socmint.v12_10_command_center_routes",
        "src.socmint.v12_10_29_ui",
    ]:
        if name in sys.modules:
            del sys.modules[name]


def _force_register_blueprints(app: Any) -> Dict[str, Any]:
    info = {
        "attempted": False,
        "registered": [],
        "skipped": [],
        "errors": [],
    }

    try:
        before = {str(rule) for rule in app.url_map.iter_rules()}
    except Exception as exc:
        info["errors"].append(f"inspect-before-failed: {exc!r}")
        return info

    if not (EXPECTED_V12_ROUTES - before):
        info["skipped"].append("all expected v12 routes already present")
        return info

    info["attempted"] = True

    try:
        from src.socmint.v12_10_command_center_routes import bp as command_bp
        from src.socmint.v12_10_29_ui import bp as ui_bp

        for bp in [command_bp, ui_bp]:
            current = {str(rule) for rule in app.url_map.iter_rules()}
            if not (EXPECTED_V12_ROUTES - current):
                break

            try:
                if bp.name in app.blueprints:
                    alias = f"{bp.name}_forced_{VERSION.replace('.', '_')}"
                    if alias in app.blueprints:
                        info["skipped"].append(f"{alias} already registered")
                        continue
                    app.register_blueprint(bp, name=alias)
                    info["registered"].append(alias)
                else:
                    app.register_blueprint(bp)
                    info["registered"].append(bp.name)
            except Exception as exc:
                info["errors"].append(f"{bp.name}: {exc!r}")

    except Exception as exc:
        info["errors"].append(f"import-blueprints-failed: {exc!r}")

    return info


def runtime_v12_route_smoke() -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "attempted": False,
        "ok": False,
        "dashboard_module_file": None,
        "routes_before_lock": [],
        "routes_after_lock": [],
        "routes": [],
        "missing_v12_routes_before_lock": sorted(EXPECTED_V12_ROUTES),
        "missing_v12_routes": sorted(EXPECTED_V12_ROUTES),
        "missing_v12_route_count": len(EXPECTED_V12_ROUTES),
        "route_lock": {},
        "error": None,
    }

    dashboard_path = ROOT / "src" / "socmint" / "dashboard.py"
    if not dashboard_path.exists():
        result["error"] = "src/socmint/dashboard.py not found"
        return result

    result["attempted"] = True

    try:
        root_str = str(ROOT)
        if root_str not in sys.path:
            sys.path.insert(0, root_str)

        _fresh_import_runtime_modules()

        dashboard = importlib.import_module("src.socmint.dashboard")
        result["dashboard_module_file"] = getattr(dashboard, "__file__", None)

        app = dashboard.create_app()

        before = sorted(str(rule) for rule in app.url_map.iter_rules())
        result["routes_before_lock"] = before
        result["missing_v12_routes_before_lock"] = sorted(EXPECTED_V12_ROUTES - set(before))

        result["route_lock"] = _force_register_blueprints(app)

        after = sorted(str(rule) for rule in app.url_map.iter_rules())
        result["routes_after_lock"] = after
        result["routes"] = after
        result["missing_v12_routes"] = sorted(EXPECTED_V12_ROUTES - set(after))
        result["missing_v12_route_count"] = len(result["missing_v12_routes"])
        result["ok"] = result["missing_v12_route_count"] == 0

    except Exception as exc:
        result["error"] = repr(exc)

    return result


# Backward-compatible alias used by older tests.
def runtime_flask_routes() -> Dict[str, Any]:
    return runtime_v12_route_smoke()


def version_metadata() -> Dict[str, Any]:
    items: Dict[str, Any] = {}

    init_py = ROOT / "src" / "socmint" / "__init__.py"
    pyproject = ROOT / "pyproject.toml"

    init_text = read(init_py)
    pyproject_text = read(pyproject)

    init_match = re.search(r"__version__\s*=\s*['\"]([^'\"]+)['\"]", init_text)
    pyproject_match = re.search(r"version\s*=\s*['\"]([^'\"]+)['\"]", pyproject_text)

    items["src/socmint/__init__.py"] = init_match.group(1) if init_match else None
    items["pyproject.toml"] = pyproject_match.group(1) if pyproject_match else None

    versions = [v for v in items.values() if isinstance(v, str)]
    unique = sorted(set(versions))

    return {
        "items": items,
        "unique_versions": unique,
        "metadata_consistent": len(unique) <= 1,
        "expected_current": VERSION,
    }


def write_reports(checks: List[Check], summary: Dict[str, Any]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    payload = {
        "audit": f"v{VERSION} Drift Lock Audit",
        "summary": summary,
        "checks": [c.as_dict() for c in checks],
    }

    REPORT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True))

    lines = [
        f"# v{VERSION} Drift Lock Audit Report",
        "",
        f"Overall: **{summary['overall_status']}**",
        "",
        "## Summary",
        "",
    ]

    for key, value in summary.items():
        lines.append(f"- **{key}**: `{value}`")

    lines.extend(["", "## Checks", ""])

    for check in checks:
        lines.append(f"### {check.name}: {check.status}")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(check.detail, indent=2, sort_keys=True))
        lines.append("```")
        lines.append("")

    REPORT_MD.write_text("\n".join(lines))


def main() -> int:
    checks: List[Check] = []

    framework = detect_framework()
    framework_ok = framework["framework"] in {"flask", "fastapi", "hybrid"}
    checks.append(Check("framework_detection", "PASS" if framework_ok else "FAIL", framework))

    entrypoints = identify_entrypoints()
    primary = entrypoints.get("primary_guess")
    entry_ok = bool(primary and primary.get("path") == "src/socmint/dashboard.py")
    checks.append(Check("entrypoint_detection", "PASS" if entry_ok else "FAIL", entrypoints))

    alembic = alembic_info()
    alembic_ok = alembic.get("sole_expected_head") and not alembic.get("duplicate_revisions")
    checks.append(Check("alembic_heads_and_chain", "PASS" if alembic_ok else "FAIL", alembic))

    model_migration = compare_models_migrations()
    model_ok = model_migration["models_covered_by_migrations"]
    checks.append(Check("models_vs_migrations", "PASS" if model_ok else "WARN", model_migration))

    static_routes = route_static_scan()
    checks.append(Check("static_route_scan", "PASS", static_routes))

    runtime_routes = runtime_v12_route_smoke()
    route_ok = runtime_routes["missing_v12_route_count"] == 0
    checks.append(Check("runtime_v12_route_registration", "PASS" if route_ok else "FAIL", runtime_routes))

    versions = version_metadata()
    version_ok = versions["metadata_consistent"]
    checks.append(Check("version_metadata", "PASS" if version_ok else "WARN", versions))

    fail_count = sum(1 for c in checks if c.status == "FAIL")
    warn_count = sum(1 for c in checks if c.status == "WARN")

    overall = "PASS" if fail_count == 0 else "FAIL"
    drift_lock = "PASS" if overall == "PASS" and warn_count == 0 else ("WARN" if overall == "PASS" else "FAIL")

    summary = {
        "overall_status": overall,
        "drift_lock": drift_lock,
        "fail_count": fail_count,
        "warn_count": warn_count,
        "framework": framework["framework"],
        "primary_entrypoint": primary.get("path") if primary else None,
        "dashboard_module_file": runtime_routes.get("dashboard_module_file"),
        "alembic_heads": ",".join(alembic.get("heads", [])),
        "missing_v12_routes": runtime_routes["missing_v12_route_count"],
        "route_lock_errors": len(runtime_routes.get("route_lock", {}).get("errors", [])),
        "route_lock_registered": ",".join(runtime_routes.get("route_lock", {}).get("registered", [])),
        "route_lock_skipped": ",".join(runtime_routes.get("route_lock", {}).get("skipped", [])),
        "model_tables_missing_migrations": len(model_migration["tables_in_models_not_migrations"]),
        "version_unique_count": len(versions["unique_versions"]),
        "report_json": str(REPORT_JSON),
        "report_md": str(REPORT_MD),
    }

    write_reports(checks, summary)

    print(json.dumps(summary, indent=2, sort_keys=True))
    print(f"[+] Wrote {REPORT_JSON}")
    print(f"[+] Wrote {REPORT_MD}")

    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
