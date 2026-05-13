from __future__ import annotations

from flask import Blueprint as _Blueprint, current_app as _current_app

# v10.0.1 Product Route Extraction Phase 1
#
# Phase 1 creates the dedicated product release flow module without breaking the
# existing v9.9.x route stack. The v9.9.0-v9.9.4 route implementations remain
# registered from dashboard.py for compatibility, while this module re-exports
# their helpers so later phases can move route ownership safely.

from typing import Any

from socmint import dashboard as _dashboard


EXTRACTED_VERSION_RANGE = "v9.9.0-v9.9.4"
BLUEPRINT_NAME = "product_release_flow"
COMPATIBILITY_MODE = "re-export"

ROUTE_FAMILY = [
    "/product/release-candidate",
    "/api/v1/product/release-candidate",
    "/api/v1/product/release-candidate/write",
    "/product/final-gate",
    "/api/v1/product/final-gate",
    "/api/v1/product/final-gate/write",
    "/api/v1/product/final-gate/signoff",
    "/api/v1/product/final-gate/signoff-audit",
    "/product/final-release",
    "/api/v1/product/final-release",
    "/api/v1/product/final-release/publish",
    "/product/final-release/archive",
    "/api/v1/product/final-release/archives",
    "/product/final-release/verify",
    "/api/v1/product/final-release/verify",
]


def _export_dashboard_symbols() -> None:
    for name in dir(_dashboard):
        if name.startswith("_v99") or name in {
            "login_required",
            "admin_required",
            "audit",
            "dashboard_bp",
        }:
            globals()[name] = getattr(_dashboard, name)


_export_dashboard_symbols()


def product_release_flow_manifest() -> dict[str, Any]:
    return {
        "status": "ok",
        "version": "10.0.1",
        "module": "socmint.product_release_flow",
        "blueprint_name": BLUEPRINT_NAME,
        "compatibility_mode": COMPATIBILITY_MODE,
        "extracted_version_range": EXTRACTED_VERSION_RANGE,
        "route_family": ROUTE_FAMILY,
        "note": (
            "Phase 1 exposes the dedicated product release flow module and "
            "re-exports v9.9.0-v9.9.4 helpers from dashboard.py. Public routes "
            "remain unchanged; full blueprint ownership can move in a later phase."
        ),
    }


__all__ = [
    "product_release_flow_manifest",
    "EXTRACTED_VERSION_RANGE",
    "BLUEPRINT_NAME",
    "COMPATIBILITY_MODE",
    "ROUTE_FAMILY",
]



# ---- v10.0.7 Blueprint Migration Wave 1 GET ownership ----

try:
    product_release_flow_bp
except NameError:
    product_release_flow_bp = _Blueprint("product_release_flow", __name__)


def _v1007_dispatch_dashboard_get(rule: str, **kwargs):
    for candidate in _current_app.url_map.iter_rules():
        if candidate.rule == rule and candidate.endpoint.startswith("dashboard."):
            return _current_app.view_functions[candidate.endpoint](**kwargs)
    raise RuntimeError(f"dashboard fallback route not found for {rule}")


@product_release_flow_bp.route("/product/release-candidate", methods=["GET"])
def wave1_product_release_candidate_console():
    return _v1007_dispatch_dashboard_get("/product/release-candidate")


@product_release_flow_bp.route("/api/v1/product/release-candidate", methods=["GET"])
def wave1_api_product_release_candidate():
    return _v1007_dispatch_dashboard_get("/api/v1/product/release-candidate")


@product_release_flow_bp.route("/product/final-gate", methods=["GET"])
def wave1_product_final_gate_view():
    return _v1007_dispatch_dashboard_get("/product/final-gate")


@product_release_flow_bp.route("/api/v1/product/final-gate", methods=["GET"])
def wave1_api_product_final_gate():
    return _v1007_dispatch_dashboard_get("/api/v1/product/final-gate")
# ---- end v10.0.7 wave 1 release flow routes ----
