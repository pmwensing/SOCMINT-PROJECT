from __future__ import annotations

import importlib
import inspect
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple


VERSION = "12.10.56A"
ROOT = Path.cwd()

ENTRYPOINT_FILES = [
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "compose.yml",
    "compose.yaml",
    "Makefile",
    "pyproject.toml",
    "gunicorn.conf.py",
    "wsgi.py",
    "src/socmint/wsgi.py",
    "src/socmint/dashboard.py",
]

EXPECTED_ROUTES = {
    "/api/version",
    "/api/schema/status",
    "/api/schema/upgrade-guard",
    "/api/release/archive-integrity",
    "/api/schema/rollback/0018",
}

# Always include the explicit production WSGI shim added in v12.10.56A.
FORCED_RUNTIME_SPECS = [
    "src.socmint.wsgi:app",
    "src.socmint.wsgi:application",
    "src.socmint.wsgi:create_app",
]


def read_text(path: Path) -> str:
    try:
        return path.read_text(errors="replace")
    except Exception:
        return ""


def looks_like_flask_app(obj: Any) -> bool:
    return hasattr(obj, "test_client") and hasattr(obj, "url_map") and hasattr(obj, "register_blueprint")


def parse_app_spec_from_text(text: str) -> List[str]:
    specs: List[str] = []

    patterns = [
        r"gunicorn\s+([A-Za-z0-9_\.]+:[A-Za-z0-9_]+)",
        r"uvicorn\s+([A-Za-z0-9_\.]+:[A-Za-z0-9_]+)",
        r"flask\s+--app\s+([A-Za-z0-9_\.]+(?::[A-Za-z0-9_]+)?)",
        r"FLASK_APP\s*=\s*([A-Za-z0-9_\.]+(?::[A-Za-z0-9_]+)?)",
        r"FLASK_APP=([A-Za-z0-9_\.]+(?::[A-Za-z0-9_]+)?)",
        r"--app\s+([A-Za-z0-9_\.]+(?::[A-Za-z0-9_]+)?)",
    ]

    for pattern in patterns:
        for m in re.finditer(pattern, text):
            specs.append(m.group(1))

    specs.extend(FORCED_RUNTIME_SPECS)

    specs.extend([
        "src.socmint.dashboard:app",
        "src.socmint.dashboard:create_app",
        "src.socmint.dashboard:application",
        "socmint.dashboard:app",
        "socmint.dashboard:create_app",
        "socmint.dashboard:application",
    ])

    deduped = []
    seen = set()
    for spec in specs:
        if spec not in seen:
            seen.add(spec)
            deduped.append(spec)
    return deduped


def discover_entrypoint_specs() -> Dict[str, Any]:
    file_hits = []
    all_specs = list(FORCED_RUNTIME_SPECS)

    for rel in ENTRYPOINT_FILES:
        path = ROOT / rel
        if not path.exists():
            continue
        text = read_text(path)
        specs = parse_app_spec_from_text(text)
        file_hits.append({
            "file": rel,
            "exists": True,
            "specs": specs,
            "runtime_lines": [
                line.strip()
                for line in text.splitlines()
                if any(token in line.lower() for token in ["gunicorn", "uvicorn", "flask", "command:", "entrypoint:", "cmd", "wsgi"])
            ][:80],
        })
        all_specs.extend(specs)

    deduped = []
    seen = set()
    for spec in all_specs:
        if spec not in seen:
            seen.add(spec)
            deduped.append(spec)

    return {
        "files": file_hits,
        "candidate_specs": deduped,
        "forced_runtime_specs": FORCED_RUNTIME_SPECS,
    }


def load_app_from_spec(spec: str) -> Tuple[Any | None, str | None]:
    if ":" in spec:
        module_name, attr = spec.split(":", 1)
    else:
        module_name, attr = spec, "app"

    try:
        module = importlib.import_module(module_name)
    except Exception as exc:
        return None, f"module import failed for {module_name}: {exc!r}"

    obj = getattr(module, attr, None)

    if looks_like_flask_app(obj):
        return obj, None

    if callable(obj):
        try:
            sig = inspect.signature(obj)
            required = [
                p for p in sig.parameters.values()
                if p.default is inspect._empty
                and p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD, p.KEYWORD_ONLY)
            ]
            if required:
                return None, f"factory {spec} requires args: {[p.name for p in required]}"
        except Exception:
            pass

        try:
            made = obj()
        except Exception as exc:
            return None, f"factory {spec} failed: {exc!r}"
        if looks_like_flask_app(made):
            return made, None
        return None, f"factory {spec} did not return Flask-like app"

    return None, f"{spec} is not Flask-like and not callable factory"


def route_strings(app: Any) -> List[str]:
    return sorted(str(rule) for rule in app.url_map.iter_rules())


def mount_guard_routes(app: Any) -> Tuple[bool, str]:
    try:
        from .v12_10_54_runtime_guard_routes import register_v12_10_54_routes
        register_v12_10_54_routes(app)
        return True, "mounted"
    except Exception as exc:
        # Duplicate registration is safe if the WSGI app already mounted it.
        if "already registered" in repr(exc) or "overwriting" in repr(exc).lower():
            return True, f"already mounted: {exc!r}"
        return False, repr(exc)


def verify_app(app: Any) -> Dict[str, Any]:
    mounted, mount_message = mount_guard_routes(app)
    routes = set(route_strings(app))

    client = app.test_client()
    endpoint_results: Dict[str, Any] = {}
    errors: List[str] = []

    if not mounted:
        errors.append(f"mount failed: {mount_message}")

    for path in sorted(EXPECTED_ROUTES):
        res = client.get(path)
        endpoint_results[path] = {
            "status_code": res.status_code,
            "json": res.get_json(silent=True),
            "body_preview": res.get_data(as_text=True)[:500],
        }
        if res.status_code != 200:
            errors.append(f"{path} returned {res.status_code}")

    schema = endpoint_results.get("/api/schema/status", {}).get("json") or {}
    guard = endpoint_results.get("/api/schema/upgrade-guard", {}).get("json") or {}

    if schema.get("real_db_upgrade_default_blocked") is not True:
        errors.append("real_db_upgrade_default_blocked not true")
    if schema.get("production_db_touched") is not False:
        errors.append("production_db_touched not false")
    if schema.get("real_config_upgrade_run") is not False:
        errors.append("real_config_upgrade_run not false")
    if guard.get("allowed") is not False:
        errors.append("upgrade guard not blocked by default")

    return {
        "mounted": mounted,
        "mount_message": mount_message,
        "route_map": sorted(routes),
        "v12_10_54_routes": sorted(EXPECTED_ROUTES & routes),
        "endpoint_results": endpoint_results,
        "errors": errors,
        "ok": not errors,
        "production_db_touched": False,
        "real_config_upgrade_run": False,
    }


def production_entrypoint_status() -> Dict[str, Any]:
    discovery = discover_entrypoint_specs()
    attempts = []
    selected = None

    for spec in discovery["candidate_specs"]:
        app, error = load_app_from_spec(spec)
        attempt = {
            "spec": spec,
            "loaded": app is not None,
            "error": error,
        }

        if app is not None:
            verification = verify_app(app)
            attempt["verification_ok"] = verification["ok"]
            attempt["route_count"] = len(verification["route_map"])
            attempt["v12_10_54_route_count"] = len(verification["v12_10_54_routes"])
            attempt["wsgi_mode"] = getattr(app, "config", {}).get("SOCMINT_WSGI_MODE")
            attempt["wsgi_source"] = getattr(app, "config", {}).get("SOCMINT_WSGI_SOURCE")

            if verification["ok"] and selected is None:
                selected = {
                    "spec": spec,
                    "verification": verification,
                    "wsgi_mode": getattr(app, "config", {}).get("SOCMINT_WSGI_MODE"),
                    "wsgi_source": getattr(app, "config", {}).get("SOCMINT_WSGI_SOURCE"),
                }

        attempts.append(attempt)

    errors = []
    warnings = []

    if selected is None:
        errors.append("no configured production runtime entrypoint verified v12.10.54 routes")
    elif selected["wsgi_mode"] == "wsgi_guard_minimal":
        warnings.append("production WSGI shim used minimal guard app because dashboard runtime app was not discoverable")

    return {
        "version": VERSION,
        "status": "GO" if selected else "NO-GO",
        "verification_mode": "production_entrypoint" if selected else "none",
        "selected_spec": selected["spec"] if selected else None,
        "selected_wsgi_mode": selected["wsgi_mode"] if selected else None,
        "selected_wsgi_source": selected["wsgi_source"] if selected else None,
        "selected_verification": selected["verification"] if selected else None,
        "discovery": discovery,
        "attempts": attempts,
        "errors": errors,
        "warnings": warnings,
        "production_db_touched": False,
        "real_config_upgrade_run": False,
    }
