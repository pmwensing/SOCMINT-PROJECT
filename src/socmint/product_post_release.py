from __future__ import annotations

from flask import Blueprint as _Blueprint, current_app as _current_app

# v10.0.2 Product Route Extraction Phase 2
#
# Phase 2 creates the dedicated post-release product module for v9.9.5-v9.9.9
# distribution/self-test/handoff/bootstrap helpers. Public URLs remain owned by
# dashboard.py during this safe migration phase; this module re-exports helpers
# and provides a manifest so later phases can move blueprint ownership safely.

from typing import Any

from . import dashboard as _dashboard


EXTRACTED_VERSION_RANGE = "v9.9.5-v9.9.9"
MODULE_NAME = "socmint.product_post_release"
COMPATIBILITY_MODE = "re-export"

ROUTE_FAMILY = [
    "/product/final-release/distribution",
    "/api/v1/product/final-release/distribution",
    "/api/v1/product/final-release/distribution/write",
    "/api/v1/product/final-release/distribution/decision",
    "/api/v1/product/final-release/distribution/audit",
    "/product/final",
    "/api/v1/product/final",
    "/api/v1/product/final/write",
    "/product/final/handoff",
    "/api/v1/product/final/handoff",
    "/api/v1/product/final/handoff/build",
    "/product/final/self-test",
    "/api/v1/product/final/self-test",
    "/api/v1/product/final/self-test/write",
    "/api/v1/product/final/self-test/maintenance",
    "/api/v1/product/final/self-test/maintenance-audit",
    "/product/final/v10-bootstrap",
    "/api/v1/product/final/v10-bootstrap",
    "/api/v1/product/final/v10-bootstrap/write",
    "/api/v1/product/final/v10-bootstrap/decision",
    "/api/v1/product/final/v10-bootstrap/audit",
]


def _export_dashboard_symbols() -> None:
    for name in dir(_dashboard):
        if (
            name.startswith("_v995")
            or name.startswith("_v996")
            or name.startswith("_v997")
            or name.startswith("_v998")
            or name.startswith("_v999")
        ):
            globals()[name] = getattr(_dashboard, name)
        elif name in {
            "login_required",
            "admin_required",
            "audit",
            "dashboard_bp",
        }:
            globals()[name] = getattr(_dashboard, name)


_export_dashboard_symbols()


def product_post_release_manifest() -> dict[str, Any]:
    return {
        "status": "ok",
        "version": "10.0.2",
        "module": MODULE_NAME,
        "compatibility_mode": COMPATIBILITY_MODE,
        "extracted_version_range": EXTRACTED_VERSION_RANGE,
        "route_family": ROUTE_FAMILY,
        "note": (
            "Phase 2 exposes the dedicated post-release module and re-exports "
            "v9.9.5-v9.9.9 helpers from dashboard.py. Public routes remain "
            "unchanged; full blueprint ownership can move in a later phase."
        ),
    }


__all__ = [
    "product_post_release_manifest",
    "EXTRACTED_VERSION_RANGE",
    "MODULE_NAME",
    "COMPATIBILITY_MODE",
    "ROUTE_FAMILY",
]


# ---- v10.0.7 Blueprint Migration Wave 1 GET ownership ----

try:
    product_post_release_bp
except NameError:
    product_post_release_bp = _Blueprint("product_post_release", __name__)


def _v1007_dispatch_dashboard_get(rule: str, **kwargs):
    for candidate in _current_app.url_map.iter_rules():
        if candidate.rule == rule and candidate.endpoint.startswith("dashboard."):
            return _current_app.view_functions[candidate.endpoint](**kwargs)
    raise RuntimeError(f"dashboard fallback route not found for {rule}")


@product_post_release_bp.route("/product/final", methods=["GET"])
def wave1_product_final_dashboard():
    return _v1007_dispatch_dashboard_get("/product/final")


@product_post_release_bp.route("/api/v1/product/final", methods=["GET"])
def wave1_api_product_final_dashboard():
    return _v1007_dispatch_dashboard_get("/api/v1/product/final")


@product_post_release_bp.route("/product/final/handoff", methods=["GET"])
def wave1_product_final_handoff_view():
    return _v1007_dispatch_dashboard_get("/product/final/handoff")


@product_post_release_bp.route("/api/v1/product/final/handoff", methods=["GET"])
def wave1_api_product_final_handoff():
    return _v1007_dispatch_dashboard_get("/api/v1/product/final/handoff")


@product_post_release_bp.route("/product/final/self-test", methods=["GET"])
def wave1_product_final_self_test_view():
    return _v1007_dispatch_dashboard_get("/product/final/self-test")


@product_post_release_bp.route("/api/v1/product/final/self-test", methods=["GET"])
def wave1_api_product_final_self_test():
    return _v1007_dispatch_dashboard_get("/api/v1/product/final/self-test")


@product_post_release_bp.route("/product/final/v10-bootstrap", methods=["GET"])
def wave1_product_v10_bootstrap_view():
    return _v1007_dispatch_dashboard_get("/product/final/v10-bootstrap")


@product_post_release_bp.route("/api/v1/product/final/v10-bootstrap", methods=["GET"])
def wave1_api_v10_bootstrap():
    return _v1007_dispatch_dashboard_get("/api/v1/product/final/v10-bootstrap")


# ---- end v10.0.7 wave 1 post-release routes ----


# ---- v10.0.9 Blueprint Migration Wave 2 read-only API ownership ----


@product_post_release_bp.route(
    "/api/v1/product/final/v10-bootstrap/audit", methods=["GET"]
)
def wave2_api_product_v10_bootstrap_audit():
    return _v1007_dispatch_dashboard_get("/api/v1/product/final/v10-bootstrap/audit")


# ---- end v10.0.9 wave 2 post-release API routes ----
