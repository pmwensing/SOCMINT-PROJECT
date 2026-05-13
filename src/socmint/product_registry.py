from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from flask import Blueprint, current_app, jsonify, render_template

from socmint.product_artifacts import product_artifacts_manifest
from socmint.product_post_release import product_post_release_manifest
from socmint.product_release_flow import product_release_flow_manifest


product_registry_bp = Blueprint("product_registry", __name__)

REGISTRY_VERSION = "10.0.4"

WAVE1_BLUEPRINT_OWNED_ROUTES = {
    "/product/release-candidate": "socmint.product_release_flow",
    "/api/v1/product/release-candidate": "socmint.product_release_flow",
    "/product/final-gate": "socmint.product_release_flow",
    "/api/v1/product/final-gate": "socmint.product_release_flow",
    "/product/final": "socmint.product_post_release",
    "/api/v1/product/final": "socmint.product_post_release",
    "/product/final/handoff": "socmint.product_post_release",
    "/api/v1/product/final/handoff": "socmint.product_post_release",
    "/product/final/self-test": "socmint.product_post_release",
    "/api/v1/product/final/self-test": "socmint.product_post_release",
    "/product/final/v10-bootstrap": "socmint.product_post_release",
    "/api/v1/product/final/v10-bootstrap": "socmint.product_post_release",
    "/product/artifacts": "socmint.product_artifacts",
    "/api/v1/product/artifacts": "socmint.product_artifacts",
    "/product/release-package": "socmint.product_artifacts",
    "/api/v1/product/release-package": "socmint.product_artifacts",
}

WAVE1_TARGET_BLUEPRINTS = {
    "socmint.product_release_flow": "product_release_flow",
    "socmint.product_post_release": "product_post_release",
    "socmint.product_artifacts": "product_artifacts",
}



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



def _v1007_route_lookup_for_ownership(route_inventory: list[dict[str, Any]], route: str, normalized: str, wave1_target: str | None) -> dict[str, Any] | None:
    candidates = [
        item
        for item in route_inventory
        if item.get("rule") in {route, normalized}
    ]
    if not candidates:
        return None

    if wave1_target:
        expected_blueprint = WAVE1_TARGET_BLUEPRINTS.get(wave1_target)
        for item in candidates:
            endpoint = item.get("endpoint") or ""
            if expected_blueprint and endpoint.startswith(expected_blueprint + "."):
                return item

    for item in candidates:
        endpoint = item.get("endpoint") or ""
        if not endpoint.startswith("dashboard."):
            return item

    return candidates[0]


def _route_ownership_map() -> dict[str, Any]:
    route_inventory = _route_inventory()
    surfaces = _module_surfaces()

    ownership_rows: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []

    for surface in surfaces:
        for route in surface.get("routes", []):
            normalized = route.replace("{package_name}", "<package_name>")
            present = _route_exists(route) or _route_exists(normalized)
            wave1_target = WAVE1_BLUEPRINT_OWNED_ROUTES.get(route) or WAVE1_BLUEPRINT_OWNED_ROUTES.get(normalized)
            ownership_route = _v1007_route_lookup_for_ownership(route_inventory, route, normalized, wave1_target)
            endpoint = ownership_route["endpoint"] if ownership_route else None
            methods: list[str] = ownership_route["methods"] if ownership_route else []

            endpoint_owner = (endpoint or "").split(".", 1)[0]
            expected_blueprint = WAVE1_TARGET_BLUEPRINTS.get(wave1_target)
            wave1_blueprint_owned = bool(wave1_target and endpoint_owner == expected_blueprint)
            effective_ownership = "blueprint-owned" if wave1_blueprint_owned else surface["ownership"]
            row = {
                "route": route,
                "normalized_route": normalized,
                "present": present,
                "endpoint": endpoint,
                "methods": methods,
                "surface_key": surface["key"],
                "surface_label": surface["label"],
                "module": wave1_target or surface["module"],
                "ownership": effective_ownership,
                "compatibility_mode": "native-blueprint-wave1" if wave1_blueprint_owned else surface.get("compatibility_mode"),
                "wave1_blueprint_owned": wave1_blueprint_owned,
                "fallback_owner": "dashboard.py" if wave1_target else None,
                "target_blueprint": expected_blueprint,
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



# ---- v10.0.5 Product Module Health Console + Extraction Readiness Score ----
SMOKE_TARGETS_BY_MODULE = {
    "release_flow": [
        "product-route-extraction-smoke",
        "test1001",
        "route-extraction-hardening-smoke",
    ],
    "post_release": [
        "product-post-release-extraction-smoke",
        "test1002",
        "post-release-extraction-hardening-smoke",
    ],
    "artifact_pipeline": [
        "product-artifact-pipeline-extraction-smoke",
        "test1003",
        "artifact-pipeline-extraction-hardening-smoke",
    ],
    "module_registry": [
        "product-module-registry-smoke",
        "test1004",
        "module-registry-hardening-smoke",
    ],
}


def _makefile_targets() -> set[str]:
    from pathlib import Path

    path = Path("Makefile")
    if not path.exists():
        return set()

    targets: set[str] = set()
    for line in path.read_text().splitlines():
        if not line or line.startswith("\t") or line.startswith(" ") or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        name = line.split(":", 1)[0].strip()
        if name and " " not in name and not name.startswith("."):
            targets.add(name)
    return targets


def _helper_export_count(module_key: str) -> int:
    try:
        if module_key == "release_flow":
            from socmint import product_release_flow as module
            return sum(1 for name in dir(module) if name.startswith("_v99"))
        if module_key == "post_release":
            from socmint import product_post_release as module
            return sum(1 for name in dir(module) if name.startswith(("_v995", "_v996", "_v997", "_v998", "_v999")))
        if module_key == "artifact_pipeline":
            from socmint import product_artifacts as module
            return sum(1 for name in dir(module) if name.startswith(("_v984", "_v985", "_v986", "_v987", "_v988", "_v989", "_v98")))
        if module_key == "module_registry":
            from socmint import product_registry as module
            registry_helpers = {
                "_route_inventory",
                "_route_exists",
                "_module_surfaces",
                "_route_ownership_map",
                "_module_health_payload",
                "_makefile_targets",
                "_helper_export_count",
                "_expected_helper_floor",
            }
            return sum(1 for name in registry_helpers if hasattr(module, name))
    except Exception:
        return 0
    return 0


def _expected_helper_floor(module_key: str) -> int:
    return {
        "release_flow": 5,
        "post_release": 5,
        "artifact_pipeline": 5,
        "module_registry": 2,
    }.get(module_key, 0)


def _module_health_payload() -> dict[str, Any]:
    ownership = _route_ownership_map()
    targets = _makefile_targets()

    module_health = []
    for module in ownership.get("modules", []):
        key = module.get("key")
        if key not in {"release_flow", "post_release", "artifact_pipeline"}:
            continue

        route_score = 100 if module.get("route_count") == 0 else int(
            100 * module.get("present_route_count", 0) / max(1, module.get("route_count", 1))
        )
        helper_count = _helper_export_count(key)
        helper_floor = _expected_helper_floor(key)
        helper_score = 100 if helper_count >= helper_floor else int(100 * helper_count / max(1, helper_floor))

        expected_targets = SMOKE_TARGETS_BY_MODULE.get(key, [])
        present_targets = [target for target in expected_targets if target in targets]
        smoke_score = 100 if not expected_targets else int(100 * len(present_targets) / len(expected_targets))

        registry_score = 100 if module.get("module") and module.get("ownership") == "extracted-module-reexport" else 0
        total_score = int((route_score * 0.40) + (helper_score * 0.25) + (smoke_score * 0.25) + (registry_score * 0.10))

        health = {
            "key": key,
            "label": module.get("label"),
            "module": module.get("module"),
            "ownership": module.get("ownership"),
            "compatibility_mode": module.get("compatibility_mode"),
            "route_count": module.get("route_count", 0),
            "present_route_count": module.get("present_route_count", 0),
            "route_score": route_score,
            "helper_export_count": helper_count,
            "helper_export_floor": helper_floor,
            "helper_score": helper_score,
            "expected_smoke_targets": expected_targets,
            "present_smoke_targets": present_targets,
            "missing_smoke_targets": [target for target in expected_targets if target not in targets],
            "smoke_score": smoke_score,
            "registry_score": registry_score,
            "total_score": total_score,
            "status": "healthy" if total_score >= 90 and module.get("present_route_count") == module.get("route_count") else "needs_attention",
            "ready_for_deeper_extraction": total_score >= 90 and module.get("present_route_count") == module.get("route_count"),
        }
        module_health.append(health)

    # Add registry module health as its own surface.
    expected_targets = SMOKE_TARGETS_BY_MODULE["module_registry"]
    present_targets = [target for target in expected_targets if target in targets]
    registry_helper_count = _helper_export_count("module_registry")
    registry_helper_floor = _expected_helper_floor("module_registry")
    registry_module_health = {
        "key": "module_registry",
        "label": "Product Module Registry + Route Ownership Map",
        "module": "socmint.product_registry",
        "ownership": "blueprint-owned",
        "compatibility_mode": "native-v10",
        "route_count": 4,
        "present_route_count": sum(
            1
            for route in [
                "/product/v10/modules",
                "/api/v1/product/v10/modules",
                "/api/v1/product/v10/modules/write",
                "/api/v1/product/v10/route-ownership",
            ]
            if _route_exists(route)
        ),
        "route_score": 100,
        "helper_export_count": registry_helper_count,
        "helper_export_floor": registry_helper_floor,
        "helper_score": 100 if registry_helper_count >= registry_helper_floor else int(100 * registry_helper_count / max(1, registry_helper_floor)),
        "expected_smoke_targets": expected_targets,
        "present_smoke_targets": present_targets,
        "missing_smoke_targets": [target for target in expected_targets if target not in targets],
        "smoke_score": 100 if not expected_targets else int(100 * len(present_targets) / len(expected_targets)),
        "registry_score": 100,
    }
    registry_module_health["total_score"] = int(
        (registry_module_health["route_score"] * 0.40)
        + (registry_module_health["helper_score"] * 0.25)
        + (registry_module_health["smoke_score"] * 0.25)
        + (registry_module_health["registry_score"] * 0.10)
    )
    registry_module_health["status"] = "healthy" if registry_module_health["total_score"] >= 90 else "needs_attention"
    registry_module_health["ready_for_deeper_extraction"] = registry_module_health["total_score"] >= 90
    module_health.append(registry_module_health)

    overall_score = int(sum(item["total_score"] for item in module_health) / max(1, len(module_health)))
    all_ready = bool(module_health) and all(item["ready_for_deeper_extraction"] for item in module_health)

    return {
        "status": "healthy" if all_ready else "needs_attention",
        "version": "10.0.5",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall_score": overall_score,
        "module_count": len(module_health),
        "healthy_count": sum(1 for item in module_health if item["status"] == "healthy"),
        "ready_for_deeper_blueprint_extraction": all_ready,
        "modules": module_health,
        "registry": ownership,
        "makefile_target_count": len(targets),
        "makefile_targets": sorted(targets),
        "recommended_next_action": (
            "Proceed to deeper blueprint extraction."
            if all_ready
            else "Fix route/helper/smoke gaps before moving actual blueprint ownership."
        ),
    }


def write_module_health_report() -> dict[str, Any]:
    import json
    from pathlib import Path

    payload = _module_health_payload()
    release_dir = Path("release")
    release_dir.mkdir(exist_ok=True)

    json_path = release_dir / "V10_0_5_MODULE_HEALTH_READINESS_REPORT.json"
    md_path = release_dir / "V10_0_5_MODULE_HEALTH_READINESS_REPORT.md"

    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True))

    rows = [
        "# v10.0.5 Product Module Health + Extraction Readiness Report",
        "",
        f"Generated: {payload['generated_at']}",
        f"Status: **{payload['status']}**",
        f"Overall score: **{payload['overall_score']}**",
        f"Ready for deeper blueprint extraction: {payload['ready_for_deeper_blueprint_extraction']}",
        "",
        "## Module Scores",
        "",
    ]
    for item in payload["modules"]:
        rows.extend(
            [
                f"### {item['label']}",
                "",
                f"- Module: `{item['module']}`",
                f"- Status: **{item['status']}**",
                f"- Total score: {item['total_score']}",
                f"- Route score: {item['route_score']} ({item['present_route_count']}/{item['route_count']})",
                f"- Helper score: {item['helper_score']} ({item['helper_export_count']}/{item['helper_export_floor']})",
                f"- Smoke score: {item['smoke_score']}",
                f"- Missing smoke targets: {', '.join(item['missing_smoke_targets']) if item['missing_smoke_targets'] else 'None'}",
                "",
            ]
        )

    rows.extend(
        [
            "## Recommended Next Action",
            "",
            payload["recommended_next_action"],
            "",
        ]
    )

    md_path.write_text("\n".join(rows))
    payload["artifacts_written"] = {
        "json": json_path.as_posix(),
        "markdown": md_path.as_posix(),
    }
    return payload


@product_registry_bp.route("/api/v1/product/v10/module-health")
def api_product_v10_module_health():
    return jsonify(_module_health_payload())


@product_registry_bp.route("/api/v1/product/v10/module-health/write", methods=["POST"])
def api_product_v10_module_health_write():
    return jsonify(write_module_health_report())


@product_registry_bp.route("/product/v10/module-health")
def product_v10_module_health_view():
    payload = _module_health_payload()
    return render_template("product_v10_module_health.html", health=payload)
# ---- end v10.0.5 product module health console ----



# ---- v10.0.6 Product Blueprint Ownership Migration Plan ----
TARGET_BLUEPRINT_BY_MODULE = {
    "socmint.product_release_flow": "product_release_flow_bp",
    "socmint.product_post_release": "product_post_release_bp",
    "socmint.product_artifacts": "product_artifacts_bp",
    "socmint.product_registry": "product_registry_bp",
}


def _route_method_risk(methods: list[str]) -> int:
    method_set = set(methods or [])
    if method_set <= {"GET"}:
        return 5
    if "POST" in method_set and len(method_set) == 1:
        return 18
    if "POST" in method_set:
        return 22
    return 10


def _route_semantic_risk(route: str) -> int:
    text = route.lower()
    risk = 0
    if "download" in text or "<" in text or "{" in text:
        risk += 18
    if "write" in text or "build" in text or "publish" in text or "decision" in text or "signoff" in text:
        risk += 20
    if "archive" in text or "zip" in text or "package" in text:
        risk += 12
    if "audit" in text:
        risk += 8
    if route.startswith("/api/"):
        risk += 4
    return risk


def _migration_route_phase(route: str, methods: list[str], module_key: str) -> str:
    text = route.lower()
    method_set = set(methods or [])

    if method_set <= {"GET"} and not any(token in text for token in ["download", "audit", "archive", "package"]):
        return "phase_1_low_risk_get_views"

    if route.startswith("/api/") and method_set <= {"GET"}:
        return "phase_2_read_only_api"

    if "audit" in text or "download" in text or "package" in text or "archive" in text:
        return "phase_3_stateful_artifact_and_file_routes"

    if "write" in text or "build" in text or "decision" in text or "signoff" in text or "publish" in text or "POST" in method_set:
        return "phase_4_mutating_action_routes"

    return "phase_2_read_only_api"


def _migration_plan_payload() -> dict[str, Any]:
    health = _module_health_payload()
    ownership = _route_ownership_map()

    health_by_module = {
        module.get("module"): module
        for module in health.get("modules", [])
    }

    candidates = []
    for row in ownership.get("ownership", []):
        if row.get("ownership") != "extracted-module-reexport":
            continue

        module_name = row.get("module")
        module_health = health_by_module.get(module_name, {})
        methods = row.get("methods") or []
        risk_score = min(
            100,
            _route_method_risk(methods)
            + _route_semantic_risk(row.get("route", ""))
            + (0 if row.get("present") else 50)
            + (0 if module_health.get("status") == "healthy" else 25),
        )
        readiness_gate_passed = (
            health.get("status") == "healthy"
            and module_health.get("status") == "healthy"
            and module_health.get("ready_for_deeper_extraction") is True
            and row.get("present") is True
        )

        candidate = {
            "route": row.get("route"),
            "normalized_route": row.get("normalized_route"),
            "endpoint": row.get("endpoint"),
            "methods": methods,
            "current_owner": "dashboard.py",
            "current_endpoint": row.get("endpoint"),
            "target_module": module_name,
            "target_blueprint": TARGET_BLUEPRINT_BY_MODULE.get(module_name),
            "surface_key": row.get("surface_key"),
            "surface_label": row.get("surface_label"),
            "risk_score": risk_score,
            "risk_level": "low" if risk_score < 25 else "medium" if risk_score < 55 else "high",
            "recommended_phase": _migration_route_phase(row.get("route", ""), methods, row.get("surface_key", "")),
            "safe_to_migrate": readiness_gate_passed and risk_score < 55,
            "readiness_gate_passed": readiness_gate_passed,
            "blocking_reasons": [
                reason
                for reason in [
                    None if health.get("status") == "healthy" else "module health payload is not healthy",
                    None if module_health.get("status") == "healthy" else f"{module_name} is not healthy",
                    None if module_health.get("ready_for_deeper_extraction") is True else f"{module_name} is not ready for deeper extraction",
                    None if row.get("present") is True else "route is missing",
                    None if risk_score < 55 else "route risk is too high for first migration wave",
                ]
                if reason
            ],
        }
        candidates.append(candidate)

    candidates.sort(key=lambda item: (item["risk_score"], item["route"] or ""))

    safe = [item for item in candidates if item["safe_to_migrate"]]
    blocked = [item for item in candidates if not item["safe_to_migrate"]]
    first_wave = [
        item
        for item in safe
        if item["recommended_phase"] in {"phase_1_low_risk_get_views", "phase_2_read_only_api"}
    ][:10]

    return {
        "status": "ready" if health.get("status") == "healthy" and safe else "blocked",
        "version": "10.0.6",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "module_health_status": health.get("status"),
        "module_health_overall_score": health.get("overall_score"),
        "ready_for_deeper_blueprint_extraction": health.get("ready_for_deeper_blueprint_extraction"),
        "candidate_count": len(candidates),
        "safe_candidate_count": len(safe),
        "blocked_candidate_count": len(blocked),
        "first_wave_count": len(first_wave),
        "first_wave_routes": first_wave,
        "candidates": candidates,
        "blocked_routes": blocked,
        "module_health": health,
        "ownership": ownership,
        "recommended_next_action": (
            "Move first-wave low-risk GET/view routes to extracted blueprints one route family at a time."
            if health.get("status") == "healthy" and safe
            else "Do not migrate route ownership until module health is healthy and candidate gates pass."
        ),
    }


def write_migration_plan_report() -> dict[str, Any]:
    import json
    from pathlib import Path

    payload = _migration_plan_payload()
    release_dir = Path("release")
    release_dir.mkdir(exist_ok=True)

    json_path = release_dir / "V10_0_6_BLUEPRINT_MIGRATION_PLAN.json"
    md_path = release_dir / "V10_0_6_BLUEPRINT_MIGRATION_PLAN.md"

    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True))

    rows = [
        "# v10.0.6 Blueprint Ownership Migration Plan",
        "",
        f"Generated: {payload['generated_at']}",
        f"Status: **{payload['status']}**",
        f"Module health: **{payload['module_health_status']}**",
        f"Overall module health score: {payload['module_health_overall_score']}",
        f"Safe candidates: {payload['safe_candidate_count']}/{payload['candidate_count']}",
        f"First wave routes: {payload['first_wave_count']}",
        "",
        "## First Wave Routes",
        "",
    ]

    if payload["first_wave_routes"]:
        for item in payload["first_wave_routes"]:
            rows.append(
                f"- `{item['route']}` → `{item['target_module']}` / `{item['target_blueprint']}` "
                f"(risk {item['risk_score']}, {item['risk_level']})"
            )
    else:
        rows.append("- None")

    rows.extend(["", "## Blocked Routes", ""])
    if payload["blocked_routes"]:
        for item in payload["blocked_routes"]:
            rows.append(
                f"- `{item['route']}` risk={item['risk_score']} reasons={'; '.join(item['blocking_reasons'])}"
            )
    else:
        rows.append("- None")

    rows.extend(
        [
            "",
            "## Recommended Next Action",
            "",
            payload["recommended_next_action"],
            "",
        ]
    )

    md_path.write_text("\n".join(rows))
    payload["artifacts_written"] = {
        "json": json_path.as_posix(),
        "markdown": md_path.as_posix(),
    }
    return payload


@product_registry_bp.route("/api/v1/product/v10/migration-plan")
def api_product_v10_migration_plan():
    return jsonify(_migration_plan_payload())


@product_registry_bp.route("/api/v1/product/v10/migration-plan/write", methods=["POST"])
def api_product_v10_migration_plan_write():
    return jsonify(write_migration_plan_report())


@product_registry_bp.route("/product/v10/migration-plan")
def product_v10_migration_plan_view():
    payload = _migration_plan_payload()
    return render_template("product_v10_migration_plan.html", plan=payload)
# ---- end v10.0.6 product blueprint ownership migration plan ----
