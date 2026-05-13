from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from flask import Blueprint, current_app, jsonify, render_template

from socmint.product_artifacts import product_artifacts_manifest
from socmint.product_post_release import product_post_release_manifest
from socmint.product_release_flow import product_release_flow_manifest


product_registry_bp = Blueprint("product_registry", __name__)

REGISTRY_VERSION = "10.0.4"


DASHBOARD_OWNED_SURFACES = [
    {
        "key": "legacy_dashboard_core",
        "label": "Dashboard core and compatibility route owner",
        "module": "socmint.dashboard",
        "ownership": "dashboard-owned",
        "routes": [
            "/",
            "/product/build-control",
        ],
    },
    {
        "key": "legacy_v9_compatibility",
        "label": "v9.9.x public compatibility URLs still served by dashboard during safe extraction",
        "module": "socmint.dashboard",
        "ownership": "dashboard-owned",
        "routes": [
            "/product/release-candidate",
            "/product/final-gate",
            "/product/final-release",
            "/product/artifacts",
            "/product/release-package",
            "/product/final",
            "/product/final/handoff",
            "/product/final/self-test",
            "/product/final/v10-bootstrap",
        ],
    },
]


def _route_inventory() -> list[dict[str, Any]]:
    routes: list[dict[str, Any]] = []
    for rule in sorted(current_app.url_map.iter_rules(), key=lambda item: item.rule):
        methods = sorted(method for method in rule.methods if method not in {"HEAD", "OPTIONS"})
        routes.append(
            {
                "rule": rule.rule,
                "endpoint": rule.endpoint,
                "methods": methods,
            }
        )
    return routes


def _route_exists(route: str) -> bool:
    return any(rule.rule == route for rule in current_app.url_map.iter_rules())


def _module_surfaces() -> list[dict[str, Any]]:
    release_flow = product_release_flow_manifest()
    post_release = product_post_release_manifest()
    artifacts = product_artifacts_manifest()

    extracted = [
        {
            "key": "release_flow",
            "label": "Release Flow Extraction Phase 1",
            "module": release_flow.get("module", "socmint.product_release_flow"),
            "version": release_flow.get("version"),
            "range": release_flow.get("extracted_version_range"),
            "ownership": "extracted-module-reexport",
            "compatibility_mode": release_flow.get("compatibility_mode"),
            "routes": release_flow.get("route_family", []),
        },
        {
            "key": "post_release",
            "label": "Post-Release Extraction Phase 2",
            "module": post_release.get("module", "socmint.product_post_release"),
            "version": post_release.get("version"),
            "range": post_release.get("extracted_version_range"),
            "ownership": "extracted-module-reexport",
            "compatibility_mode": post_release.get("compatibility_mode"),
            "routes": post_release.get("route_family", []),
        },
        {
            "key": "artifact_pipeline",
            "label": "Artifact Pipeline Extraction Phase 3",
            "module": artifacts.get("module", "socmint.product_artifacts"),
            "version": artifacts.get("version"),
            "range": artifacts.get("extracted_version_range"),
            "ownership": "extracted-module-reexport",
            "compatibility_mode": artifacts.get("compatibility_mode"),
            "routes": artifacts.get("route_family", []),
        },
    ]

    return DASHBOARD_OWNED_SURFACES + extracted


def _route_ownership_map() -> dict[str, Any]:
    route_inventory = _route_inventory()
    route_lookup = {item["rule"]: item for item in route_inventory}
    surfaces = _module_surfaces()

    ownership_rows: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []

    for surface in surfaces:
        for route in surface.get("routes", []):
            normalized = route.replace("{package_name}", "<package_name>")
            present = _route_exists(route) or _route_exists(normalized)
            endpoint = None
            methods: list[str] = []
            if route in route_lookup:
                endpoint = route_lookup[route]["endpoint"]
                methods = route_lookup[route]["methods"]
            elif normalized in route_lookup:
                endpoint = route_lookup[normalized]["endpoint"]
                methods = route_lookup[normalized]["methods"]

            row = {
                "route": route,
                "normalized_route": normalized,
                "present": present,
                "endpoint": endpoint,
                "methods": methods,
                "surface_key": surface["key"],
                "surface_label": surface["label"],
                "module": surface["module"],
                "ownership": surface["ownership"],
                "compatibility_mode": surface.get("compatibility_mode"),
            }
            ownership_rows.append(row)
            if not present:
                missing.append(row)

    modules = [
        {
            "key": surface["key"],
            "label": surface["label"],
            "module": surface["module"],
            "ownership": surface["ownership"],
            "compatibility_mode": surface.get("compatibility_mode"),
            "route_count": len(surface.get("routes", [])),
            "present_route_count": sum(
                1
                for route in surface.get("routes", [])
                if _route_exists(route) or _route_exists(route.replace("{package_name}", "<package_name>"))
            ),
        }
        for surface in surfaces
    ]

    return {
        "status": "ok" if not missing else "warn",
        "version": REGISTRY_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "product": "SOCMINT Workbench",
        "release_line": "v10.x",
        "modules": modules,
        "dashboard_owned_surface_count": len(DASHBOARD_OWNED_SURFACES),
        "extracted_module_count": len(surfaces) - len(DASHBOARD_OWNED_SURFACES),
        "route_count": len(ownership_rows),
        "present_route_count": sum(1 for row in ownership_rows if row["present"]),
        "missing_route_count": len(missing),
        "missing_routes": missing,
        "ownership": ownership_rows,
        "route_inventory_count": len(route_inventory),
        "route_inventory": route_inventory,
    }


def write_product_module_registry() -> dict[str, Any]:
    import json
    from pathlib import Path

    payload = _route_ownership_map()
    release_dir = Path("release")
    release_dir.mkdir(exist_ok=True)

    json_path = release_dir / "V10_0_4_PRODUCT_MODULE_REGISTRY.json"
    md_path = release_dir / "V10_0_4_PRODUCT_MODULE_REGISTRY.md"

    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True))

    rows = [
        "# v10.0.4 Product Module Registry + Route Ownership Map",
        "",
        f"Generated: {payload['generated_at']}",
        f"Status: **{payload['status']}**",
        f"Product: {payload['product']}",
        f"Release line: {payload['release_line']}",
        "",
        "## Module Summary",
        "",
    ]
    for module in payload["modules"]:
        rows.append(
            f"- **{module['label']}** — `{module['module']}` — "
            f"{module['present_route_count']}/{module['route_count']} routes present — {module['ownership']}"
        )

    rows.extend(
        [
            "",
            "## Missing Routes",
            "",
        ]
    )
    rows.extend([f"- `{row['route']}` ({row['module']})" for row in payload["missing_routes"]] or ["- None"])
    rows.extend(["", "## Ownership Map", ""])
    for row in payload["ownership"]:
        rows.append(
            f"- {'PRESENT' if row['present'] else 'MISSING'} `{row['route']}` "
            f"→ `{row['module']}` / `{row['ownership']}`"
        )

    md_path.write_text("\n".join(rows) + "\n")
    payload["artifacts_written"] = {
        "json": json_path.as_posix(),
        "markdown": md_path.as_posix(),
    }
    return payload


@product_registry_bp.route("/api/v1/product/v10/modules")
def api_product_v10_modules():
    return jsonify(_route_ownership_map())


@product_registry_bp.route("/api/v1/product/v10/modules/write", methods=["POST"])
def api_product_v10_modules_write():
    return jsonify(write_product_module_registry())


@product_registry_bp.route("/api/v1/product/v10/route-ownership")
def api_product_v10_route_ownership():
    payload = _route_ownership_map()
    return jsonify(
        {
            "status": payload["status"],
            "version": payload["version"],
            "generated_at": payload["generated_at"],
            "route_count": payload["route_count"],
            "present_route_count": payload["present_route_count"],
            "missing_route_count": payload["missing_route_count"],
            "missing_routes": payload["missing_routes"],
            "ownership": payload["ownership"],
        }
    )


@product_registry_bp.route("/product/v10/modules")
def product_v10_modules_view():
    payload = _route_ownership_map()
    return render_template("product_v10_modules.html", registry=payload)
