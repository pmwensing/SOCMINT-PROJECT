from __future__ import annotations

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
