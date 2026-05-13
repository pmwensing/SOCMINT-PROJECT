from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flask import Blueprint, Response, current_app, jsonify, render_template


product_v10_bp = Blueprint("product_v10", __name__)

V10_VERSION = "10.0.0"
V9_FINAL_LINE = "v9.9.x"
V10_RELEASE_LINE = "v10.x"


V9_COMPATIBILITY_ROUTES = [
    "/product/final/v10-bootstrap",
    "/api/v1/product/final/v10-bootstrap",
    "/api/v1/product/final/v10-bootstrap/write",
    "/api/v1/product/final/v10-bootstrap/decision",
    "/api/v1/product/final/v10-bootstrap/audit",
    "/product/final/self-test",
    "/api/v1/product/final/self-test",
    "/product/final/handoff",
    "/api/v1/product/final/handoff",
    "/product/final",
    "/api/v1/product/final",
    "/product/final-release/distribution",
    "/api/v1/product/final-release/distribution",
    "/product/final-release/verify",
    "/api/v1/product/final-release/verify",
    "/product/final-release/archive",
    "/api/v1/product/final-release/archives",
    "/product/final-release",
    "/api/v1/product/final-release",
    "/product/final-gate",
    "/api/v1/product/final-gate",
    "/product/release-candidate",
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


def _route_exists(rule_text: str) -> bool:
    return any(rule.rule == rule_text for rule in current_app.url_map.iter_rules())


def _v10_architecture_manifest() -> dict[str, Any]:
    route_inventory = _route_inventory()
    compatibility = [
        {
            "route": route,
            "present": _route_exists(route),
            "role": "v9.9.x final release compatibility alias",
        }
        for route in V9_COMPATIBILITY_ROUTES
    ]

    return {
        "status": "ok" if all(item["present"] for item in compatibility) else "warn",
        "version": V10_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "product": "SOCMINT Workbench",
        "release_line": V10_RELEASE_LINE,
        "source_closed_line": V9_FINAL_LINE,
        "foundation": {
            "goal": "Clean architecture split without breaking v9.9.x final release routes.",
            "strategy": [
                "Keep dashboard.py v9.9.x routes as compatibility aliases during v10 migration.",
                "Introduce dedicated product_v10 blueprint for v10 architecture, route inventory, and migration checks.",
                "Move future v10 product code into dedicated modules before removing any v9.9.x aliases.",
                "Use smoke tests to prove final v9.9.9 routes still respond after the split foundation.",
                "v10.0.1 introduces product_release_flow.py as the safe migration module for v9.9.0-v9.9.4 release-flow helpers.",
                "v10.0.2 introduces product_post_release.py as the safe migration module for v9.9.5-v9.9.9 post-release helpers.",
                "v10.0.3 introduces product_artifacts.py as the safe migration module for artifact browser/review/audit/export/package helpers.",
                "v10.0.1 extracts v9.9.0-v9.9.4 final release flow routes into product_release_flow.py while preserving original URLs.",
            ],
            "new_blueprint": "product_v10.product_v10_bp",
            "extracted_modules": ["product_release_flow.product_release_flow_manifest", "product_post_release.product_post_release_manifest", "product_artifacts.product_artifacts_manifest"],
            "extracted_blueprints": ["product_release_flow.product_release_flow_bp"],
            "compatibility_policy": "All v9.9.x final release endpoints must remain routable until v10 replacement routes are stable.",
        },
        "compatibility": {
            "required_route_count": len(compatibility),
            "present_route_count": sum(1 for item in compatibility if item["present"]),
            "routes": compatibility,
            "missing": [item["route"] for item in compatibility if not item["present"]],
        },
        "route_inventory_count": len(route_inventory),
        "route_inventory": route_inventory,
    }


def write_v10_architecture_manifest() -> dict[str, Any]:
    manifest = _v10_architecture_manifest()
    release_dir = Path("release")
    release_dir.mkdir(exist_ok=True)

    json_path = release_dir / "V10_0_0_PRODUCT_ARCHITECTURE_MANIFEST.json"
    md_path = release_dir / "V10_0_0_PRODUCT_ARCHITECTURE_MANIFEST.md"

    json_path.write_text(json.dumps(manifest, indent=2, sort_keys=True))

    rows = [
        "# v10.0.0 Product Architecture Manifest",
        "",
        f"Generated: {manifest['generated_at']}",
        f"Status: **{manifest['status']}**",
        f"Product: {manifest['product']}",
        f"Release line: {manifest['release_line']}",
        f"Source closed line: {manifest['source_closed_line']}",
        "",
        "## Foundation Strategy",
        "",
    ]
    rows.extend(f"- {item}" for item in manifest["foundation"]["strategy"])
    rows.extend(
        [
            "",
            "## Compatibility",
            "",
            f"Required routes present: {manifest['compatibility']['present_route_count']}/{manifest['compatibility']['required_route_count']}",
            "",
            "## Missing Routes",
            "",
        ]
    )
    rows.extend([f"- `{route}`" for route in manifest["compatibility"]["missing"]] or ["- None"])
    rows.extend(["", "## v9.9.x Compatibility Routes", ""])
    for item in manifest["compatibility"]["routes"]:
        rows.append(f"- {'PRESENT' if item['present'] else 'MISSING'} `{item['route']}`")

    md_path.write_text("\n".join(rows) + "\n")
    manifest["artifacts_written"] = {
        "json": json_path.as_posix(),
        "markdown": md_path.as_posix(),
    }
    return manifest


@product_v10_bp.route("/api/v1/product/v10/architecture")
def api_product_v10_architecture() -> Response:
    return jsonify(_v10_architecture_manifest())


@product_v10_bp.route("/api/v1/product/v10/architecture/write", methods=["POST"])
def api_product_v10_architecture_write() -> Response:
    return jsonify(write_v10_architecture_manifest())


@product_v10_bp.route("/api/v1/product/v10/compatibility")
def api_product_v10_compatibility() -> Response:
    manifest = _v10_architecture_manifest()
    return jsonify(
        {
            "status": manifest["status"],
            "version": V10_VERSION,
            "generated_at": manifest["generated_at"],
            "compatibility": manifest["compatibility"],
        }
    )


@product_v10_bp.route("/product/v10")
def product_v10_dashboard() -> str:
    manifest = _v10_architecture_manifest()
    return render_template("product_v10.html", manifest=manifest)


@product_v10_bp.route("/product/v10/bootstrap-compat")
def product_v10_bootstrap_compat() -> str:
    manifest = _v10_architecture_manifest()
    return render_template("product_v10.html", manifest=manifest)
