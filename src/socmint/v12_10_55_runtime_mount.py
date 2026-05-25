from __future__ import annotations

import importlib
import inspect
from dataclasses import dataclass, asdict
from typing import Any, Callable, Dict, List, Tuple


VERSION = "12.10.55"

CANDIDATE_MODULES = [
    "src.socmint.dashboard",
    "socmint.dashboard",
    "src.socmint.app",
    "socmint.app",
    "src.socmint.main",
    "socmint.main",
    "src.socmint.wsgi",
    "socmint.wsgi",
]

APP_ATTRS = ["app", "application"]
FACTORY_ATTRS = ["create_app", "make_app", "get_app", "build_app"]


def looks_like_flask_app(obj: Any) -> bool:
    return hasattr(obj, "test_client") and hasattr(obj, "url_map") and hasattr(obj, "register_blueprint")


def route_strings(app: Any) -> List[str]:
    try:
        return sorted(str(rule) for rule in app.url_map.iter_rules())
    except Exception:
        return []


def endpoint_names(app: Any) -> List[str]:
    try:
        return sorted(str(rule.endpoint) for rule in app.url_map.iter_rules())
    except Exception:
        return []


def register_guard_routes(app: Any) -> Tuple[bool, str]:
    try:
        from .v12_10_54_runtime_guard_routes import register_v12_10_54_routes
    except Exception as exc:
        return False, f"import register_v12_10_54_routes failed: {exc!r}"

    before = set(route_strings(app))
    try:
        register_v12_10_54_routes(app)
    except Exception as exc:
        return False, f"register_v12_10_54_routes failed: {exc!r}"

    after = set(route_strings(app))
    added = sorted(after - before)
    return True, f"registered; added={added}"


def instantiate_from_module(module_name: str) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []

    try:
        module = importlib.import_module(module_name)
    except Exception as exc:
        return [{
            "module": module_name,
            "kind": "module_import",
            "name": module_name,
            "ok": False,
            "error": repr(exc),
        }]

    for attr in APP_ATTRS:
        obj = getattr(module, attr, None)
        results.append({
            "module": module_name,
            "kind": "app_attr",
            "name": attr,
            "ok": looks_like_flask_app(obj),
            "error": None if looks_like_flask_app(obj) else "not a Flask app-like object",
            "object_type": type(obj).__name__ if obj is not None else None,
        })

    for attr in FACTORY_ATTRS:
        factory = getattr(module, attr, None)
        if not callable(factory):
            results.append({
                "module": module_name,
                "kind": "factory",
                "name": attr,
                "ok": False,
                "error": "not callable or missing",
                "object_type": type(factory).__name__ if factory is not None else None,
            })
            continue

        try:
            sig = inspect.signature(factory)
            required = [
                p for p in sig.parameters.values()
                if p.default is inspect._empty
                and p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD, p.KEYWORD_ONLY)
            ]
            if required:
                results.append({
                    "module": module_name,
                    "kind": "factory",
                    "name": attr,
                    "ok": False,
                    "error": f"factory requires args: {[p.name for p in required]}",
                    "object_type": "callable",
                })
                continue
        except Exception:
            pass

        try:
            obj = factory()
        except Exception as exc:
            results.append({
                "module": module_name,
                "kind": "factory",
                "name": attr,
                "ok": False,
                "error": repr(exc),
                "object_type": "callable",
            })
            continue

        results.append({
            "module": module_name,
            "kind": "factory",
            "name": attr,
            "ok": looks_like_flask_app(obj),
            "error": None if looks_like_flask_app(obj) else "factory return is not Flask app-like",
            "object_type": type(obj).__name__,
        })

    return results


def candidate_app_objects() -> List[Tuple[str, Any, Dict[str, Any]]]:
    out: List[Tuple[str, Any, Dict[str, Any]]] = []

    for module_name in CANDIDATE_MODULES:
        try:
            module = importlib.import_module(module_name)
        except Exception:
            continue

        for attr in APP_ATTRS:
            obj = getattr(module, attr, None)
            if looks_like_flask_app(obj):
                meta = {"module": module_name, "kind": "app_attr", "name": attr}
                out.append((f"{module_name}:{attr}", obj, meta))

        for attr in FACTORY_ATTRS:
            factory = getattr(module, attr, None)
            if not callable(factory):
                continue

            try:
                sig = inspect.signature(factory)
                required = [
                    p for p in sig.parameters.values()
                    if p.default is inspect._empty
                    and p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD, p.KEYWORD_ONLY)
                ]
                if required:
                    continue
            except Exception:
                pass

            try:
                obj = factory()
            except Exception:
                continue

            if looks_like_flask_app(obj):
                meta = {"module": module_name, "kind": "factory", "name": attr}
                out.append((f"{module_name}:{attr}()", obj, meta))

    return out


def make_isolated_probe_app() -> Any:
    from flask import Flask
    from .v12_10_54_runtime_guard_routes import register_v12_10_54_routes

    app = Flask("v12_10_55_isolated_probe")
    register_v12_10_54_routes(app)
    return app


def choose_real_runtime_app() -> Tuple[str, Any, Dict[str, Any], List[Dict[str, Any]]]:
    discovery_attempts: List[Dict[str, Any]] = []
    for module in CANDIDATE_MODULES:
        discovery_attempts.extend(instantiate_from_module(module))

    candidates = candidate_app_objects()

    if candidates:
        name, app, meta = candidates[0]
        return name, app, meta, discovery_attempts

    app = make_isolated_probe_app()
    meta = {"module": "isolated_probe", "kind": "fallback", "name": "Flask"}
    return "isolated_probe", app, meta, discovery_attempts


def verify_runtime_app(app: Any) -> Dict[str, Any]:
    ok, register_message = register_guard_routes(app)

    client = app.test_client()
    endpoints = [
        "/api/version",
        "/api/schema/status",
        "/api/schema/upgrade-guard",
        "/api/release/archive-integrity",
        "/api/schema/rollback/0018",
    ]

    results: Dict[str, Any] = {}
    errors: List[str] = []

    if not ok:
        errors.append(register_message)

    for path in endpoints:
        try:
            res = client.get(path)
            body = res.get_json(silent=True)
            results[path] = {
                "status_code": res.status_code,
                "json": body,
                "body_preview": res.get_data(as_text=True)[:500],
            }
            if res.status_code != 200:
                errors.append(f"{path} returned {res.status_code}")
        except Exception as exc:
            results[path] = {
                "status_code": None,
                "json": None,
                "exception": repr(exc),
            }
            errors.append(f"{path} crashed: {exc!r}")

    version_json = results.get("/api/version", {}).get("json") or {}
    if version_json.get("version") != "12.10.54":
        errors.append(f"/api/version expected 12.10.54, got {version_json.get('version')}")

    schema_json = results.get("/api/schema/status", {}).get("json") or {}
    if schema_json.get("real_db_upgrade_default_blocked") is not True:
        errors.append("schema status did not confirm real_db_upgrade_default_blocked=True")
    if schema_json.get("production_db_touched") is not False:
        errors.append("schema status did not confirm production_db_touched=False")
    if schema_json.get("real_config_upgrade_run") is not False:
        errors.append("schema status did not confirm real_config_upgrade_run=False")

    guard_json = results.get("/api/schema/upgrade-guard", {}).get("json") or {}
    if guard_json.get("allowed") is not False:
        errors.append("upgrade guard was not blocked by default")

    return {
        "ok": not errors,
        "register_message": register_message,
        "endpoint_results": results,
        "errors": errors,
        "route_map": route_strings(app),
        "endpoint_names": endpoint_names(app),
        "production_db_touched": False,
        "real_config_upgrade_run": False,
    }


def runtime_mount_status() -> Dict[str, Any]:
    name, app, meta, attempts = choose_real_runtime_app()
    verification = verify_runtime_app(app)
    mode = "real_runtime" if name != "isolated_probe" else "isolated_probe"

    return {
        "version": VERSION,
        "selected_runtime": name,
        "verification_mode": mode,
        "selected_meta": meta,
        "discovery_attempts": attempts,
        "verification": verification,
        "route_count": len(verification["route_map"]),
        "v12_10_54_routes": [
            r for r in verification["route_map"]
            if r in {
                "/api/version",
                "/api/schema/status",
                "/api/schema/upgrade-guard",
                "/api/release/archive-integrity",
                "/api/schema/rollback/0018",
            }
        ],
        "status": "GO" if verification["ok"] else "NO-GO",
        "production_db_touched": False,
        "real_config_upgrade_run": False,
    }
