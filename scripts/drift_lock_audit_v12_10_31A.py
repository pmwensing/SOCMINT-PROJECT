#!/usr/bin/env python3
from __future__ import annotations

import ast
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
RELEASE_DIR = ROOT / "release" / "drift_lock"
REPORT_JSON = RELEASE_DIR / "DRIFT_LOCK_AUDIT_V12_10_31A.json"
REPORT_MD = RELEASE_DIR / "DRIFT_LOCK_AUDIT_V12_10_31A.md"

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

EXPECTED_VERSION = "12.10.31A"


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


def run(cmd: List[str]) -> Tuple[int, str]:
    try:
        out = subprocess.check_output(cmd, cwd=ROOT, stderr=subprocess.STDOUT, text=True)
        return 0, out
    except Exception as exc:
        out = getattr(exc, "output", str(exc))
        return 1, out


def read(path: Path) -> str:
    try:
        return path.read_text(errors="replace")
    except Exception:
        return ""


def find_files(patterns: List[str]) -> List[Path]:
    out: List[Path] = []
    skip = {".git", ".venv", "node_modules", "__pycache__", ".pytest_cache", "storage"}
    for p in ROOT.rglob("*"):
        if any(part in skip for part in p.parts):
            continue
        if p.is_file() and any(p.match(pattern) for pattern in patterns):
            out.append(p)
    return sorted(set(out))


def detect_framework() -> Dict[str, Any]:
    py_files = find_files(["*.py"])
    flask_hits = []
    fastapi_hits = []

    for p in py_files:
        s = read(p)
        if re.search(r"from\s+flask\s+import|import\s+flask|Flask\(", s):
            flask_hits.append(str(p.relative_to(ROOT)))
        if re.search(r"from\s+fastapi\s+import|import\s+fastapi|FastAPI\(", s):
            fastapi_hits.append(str(p.relative_to(ROOT)))

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
        "flask_hits": flask_hits[:50],
        "fastapi_hits": fastapi_hits[:50],
        "flask_count": len(flask_hits),
        "fastapi_count": len(fastapi_hits),
    }


def identify_entrypoints() -> Dict[str, Any]:
    candidates = []

    for p in find_files(["*.py"]):
        s = read(p)
        rel = str(p.relative_to(ROOT))
        score = 0
        notes = []

        if "def create_app" in s:
            score += 5
            notes.append("create_app")
        if "Flask(" in s:
            score += 3
            notes.append("Flask(")
        if "FastAPI(" in s:
            score += 3
            notes.append("FastAPI(")
        if "uvicorn.run" in s:
            score += 2
            notes.append("uvicorn.run")
        if "app.run" in s:
            score += 2
            notes.append("app.run")
        if "register_blueprint" in s:
            score += 2
            notes.append("register_blueprint")
        if "include_router" in s:
            score += 2
            notes.append("include_router")

        if score:
            candidates.append({"path": rel, "score": score, "notes": notes})

    candidates.sort(key=lambda x: x["score"], reverse=True)

    return {
        "candidates": candidates[:25],
        "primary_guess": candidates[0] if candidates else None,
    }


def alembic_info() -> Dict[str, Any]:
    cfg = configparser.ConfigParser()
    cfg.read(ROOT / "alembic.ini")
    script_location = cfg.get("alembic", "script_location", fallback="alembic")
    versions_dir = ROOT / script_location / "versions"

    code_heads, heads_out = run(["alembic", "heads"])
    code_history, history_out = run(["alembic", "history", "--verbose"])

    migration_files = []
    if versions_dir.exists():
        for p in sorted(versions_dir.glob("*.py")):
            s = read(p)
            rev = re.search(r"revision\s*=\s*['\"]([^'\"]+)['\"]", s)
            down = re.search(r"down_revision\s*=\s*['\"]([^'\"]+)['\"]", s)
            migration_files.append({
                "file": str(p.relative_to(ROOT)),
                "revision": rev.group(1) if rev else None,
                "down_revision": down.group(1) if down else None,
            })

    heads = [line.split()[0] for line in heads_out.splitlines() if line.strip() and not line.startswith("Rev:")]
    revisions = [m["revision"] for m in migration_files if m["revision"]]
    down_revisions = [m["down_revision"] for m in migration_files if m["down_revision"]]

    orphan_downs = sorted(set(down_revisions) - set(revisions))
    duplicate_revs = sorted({r for r in revisions if revisions.count(r) > 1})

    return {
        "script_location": script_location,
        "versions_dir": str(versions_dir.relative_to(ROOT)) if versions_dir.exists() else str(versions_dir),
        "heads_command_ok": code_heads == 0,
        "heads": heads,
        "raw_heads": heads_out,
        "history_command_ok": code_history == 0,
        "history_excerpt": history_out[-4000:],
        "migration_files": migration_files,
        "migration_count": len(migration_files),
        "orphan_down_revisions": orphan_downs,
        "duplicate_revisions": duplicate_revs,
        "sole_expected_head": heads == ["0017_v12_10_schema_reconciliation"],
    }


def model_table_names() -> Dict[str, Any]:
    tables: Set[str] = set()
    model_files = []

    for p in find_files(["*.py"]):
        s = read(p)
        rel = str(p.relative_to(ROOT))
        local_tables = set()

        for m in re.finditer(r"__tablename__\s*=\s*['\"]([^'\"]+)['\"]", s):
            tables.add(m.group(1))
            local_tables.add(m.group(1))

        # Also catch SQLAlchemy Core Table("name", ...)
        for m in re.finditer(r"\bTable\(\s*['\"]([^'\"]+)['\"]", s):
            tables.add(m.group(1))
            local_tables.add(m.group(1))

        if local_tables:
            model_files.append({"file": rel, "tables": sorted(local_tables)})

    return {
        "tables": sorted(tables),
        "table_count": len(tables),
        "model_files": model_files,
    }


def migration_table_names() -> Dict[str, Any]:
    tables: Set[str] = set()
    migration_files = []

    cfg = configparser.ConfigParser()
    cfg.read(ROOT / "alembic.ini")
    script_location = cfg.get("alembic", "script_location", fallback="alembic")
    versions_dir = ROOT / script_location / "versions"

    if not versions_dir.exists():
        return {"tables": [], "table_count": 0, "migration_files": []}

    for p in sorted(versions_dir.glob("*.py")):
        s = read(p)
        local = set()

        for pattern in [
            r"op\.create_table\(\s*['\"]([^'\"]+)['\"]",
            r"_create_if_missing\(\s*['\"]([^'\"]+)['\"]",
            r"op\.drop_table\(\s*['\"]([^'\"]+)['\"]",
            r"_drop_if_exists\(\s*['\"]([^'\"]+)['\"]",
        ]:
            for m in re.finditer(pattern, s):
                tables.add(m.group(1))
                local.add(m.group(1))

        if local:
            migration_files.append({"file": str(p.relative_to(ROOT)), "tables": sorted(local)})

    return {
        "tables": sorted(tables),
        "table_count": len(tables),
        "migration_files": migration_files,
    }


def compare_models_migrations() -> Dict[str, Any]:
    models = model_table_names()
    migrations = migration_table_names()

    model_tables = set(models["tables"])
    migration_tables = set(migrations["tables"])

    return {
        "models": models,
        "migrations": migrations,
        "tables_in_models_not_migrations": sorted(model_tables - migration_tables),
        "tables_in_migrations_not_models": sorted(migration_tables - model_tables),
        "models_covered_by_migrations": len(model_tables - migration_tables) == 0,
    }


def route_static_scan() -> Dict[str, Any]:
    routes = set()
    route_files = []

    for p in find_files(["*.py"]):
        s = read(p)
        rel = str(p.relative_to(ROOT))
        local = set()

        # Flask decorators: @bp.get("/x"), @app.post("/x"), @route("/x")
        for m in re.finditer(r"@\w+\.(?:route|get|post|put|delete|patch)\(\s*['\"]([^'\"]+)['\"]", s):
            routes.add(m.group(1))
            local.add(m.group(1))

        for m in re.finditer(r"@(?:route|get|post|put|delete|patch)\(\s*['\"]([^'\"]+)['\"]", s):
            routes.add(m.group(1))
            local.add(m.group(1))

        # FastAPI router declarations with prefix=
        for m in re.finditer(r"APIRouter\(\s*prefix\s*=\s*['\"]([^'\"]+)['\"]", s):
            routes.add(m.group(1))
            local.add(m.group(1))

        if local:
            route_files.append({"file": rel, "routes": sorted(local)})

    return {
        "routes": sorted(routes),
        "route_count": len(routes),
        "route_files": route_files,
    }


def runtime_flask_routes() -> Dict[str, Any]:
    result = {
        "attempted": False,
        "ok": False,
        "routes": [],
        "missing_v12_routes": sorted(EXPECTED_V12_ROUTES),
        "error": None,
    }

    dashboard_path = ROOT / "src" / "socmint" / "dashboard.py"
    if not dashboard_path.exists():
        result["error"] = "src/socmint/dashboard.py not found"
        return result

    result["attempted"] = True

    try:
        sys.path.insert(0, str(ROOT))
        dashboard = importlib.import_module("src.socmint.dashboard")
        app = dashboard.create_app()
        routes = sorted(str(rule) for rule in app.url_map.iter_rules())
        result["ok"] = True
        result["routes"] = routes
        result["missing_v12_routes"] = sorted(EXPECTED_V12_ROUTES - set(routes))
        return result
    except Exception as exc:
        result["error"] = repr(exc)
        return result


def version_metadata() -> Dict[str, Any]:
    items: Dict[str, Any] = {}

    init_py = ROOT / "src" / "socmint" / "__init__.py"
    pyproject = ROOT / "pyproject.toml"
    release_manifest = ROOT / "release" / "V12_10_29_RELEASE_MANIFEST.json"

    init_text = read(init_py)
    pyproject_text = read(pyproject)

    init_match = re.search(r"__version__\s*=\s*['\"]([^'\"]+)['\"]", init_text)
    pyproject_match = re.search(r"version\s*=\s*['\"]([^'\"]+)['\"]", pyproject_text)

    items["src/socmint/__init__.py"] = init_match.group(1) if init_match else None
    items["pyproject.toml"] = pyproject_match.group(1) if pyproject_match else None

    if release_manifest.exists():
        try:
            items["release/V12_10_29_RELEASE_MANIFEST.json"] = json.loads(release_manifest.read_text()).get("version")
        except Exception as exc:
            items["release/V12_10_29_RELEASE_MANIFEST.json"] = f"ERROR: {exc}"

    versions = [v for v in items.values() if isinstance(v, str)]
    unique = sorted(set(versions))

    return {
        "items": items,
        "unique_versions": unique,
        "metadata_consistent": len(unique) <= 1,
        "expected_current": EXPECTED_VERSION,
    }


def write_reports(checks: List[Check], summary: Dict[str, Any]) -> None:
    RELEASE_DIR.mkdir(parents=True, exist_ok=True)

    payload = {
        "audit": "v12.10.31A Drift Lock Audit",
        "summary": summary,
        "checks": [c.as_dict() for c in checks],
    }

    REPORT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True))

    lines = []
    lines.append("# v12.10.31A Drift Lock Audit Report")
    lines.append("")
    lines.append(f"Overall: **{summary['overall_status']}**")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    for k, v in summary.items():
        lines.append(f"- **{k}**: `{v}`")
    lines.append("")
    lines.append("## Checks")
    lines.append("")
    for c in checks:
        lines.append(f"### {c.name}: {c.status}")
        lines.append("")
        if isinstance(c.detail, (dict, list)):
            lines.append("```json")
            lines.append(json.dumps(c.detail, indent=2, sort_keys=True))
            lines.append("```")
        else:
            lines.append(str(c.detail))
        lines.append("")

    REPORT_MD.write_text("\n".join(lines))


def main() -> int:
    checks: List[Check] = []

    framework = detect_framework()
    framework_ok = framework["framework"] in {"flask", "fastapi", "hybrid"}
    checks.append(Check("framework_detection", "PASS" if framework_ok else "FAIL", framework))

    entrypoints = identify_entrypoints()
    entry_ok = bool(entrypoints["primary_guess"])
    checks.append(Check("entrypoint_detection", "PASS" if entry_ok else "FAIL", entrypoints))

    alembic = alembic_info()
    alembic_ok = bool(alembic["heads"]) and not alembic["duplicate_revisions"]
    checks.append(Check("alembic_heads_and_chain", "PASS" if alembic_ok else "FAIL", alembic))

    model_migration = compare_models_migrations()
    # Warning, not hard fail: legacy repos can have reflected/runtime tables.
    model_ok = model_migration["models_covered_by_migrations"]
    checks.append(Check("models_vs_migrations", "PASS" if model_ok else "WARN", model_migration))

    static_routes = route_static_scan()
    runtime_routes = runtime_flask_routes()

    route_ok = not runtime_routes["missing_v12_routes"] if runtime_routes["ok"] else False
    checks.append(Check("static_route_scan", "PASS", static_routes))
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
        "primary_entrypoint": entrypoints["primary_guess"]["path"] if entrypoints["primary_guess"] else None,
        "alembic_heads": ",".join(alembic["heads"]),
        "missing_v12_routes": len(runtime_routes["missing_v12_routes"]),
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
