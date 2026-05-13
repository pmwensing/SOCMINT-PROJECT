from __future__ import annotations

# v10.0.3 Product Route Extraction Phase 3: Artifact Pipeline Split
#
# Phase 3 creates the dedicated artifact pipeline module for the v9.8.4-v9.8.9
# artifact browser/review/audit/export/package surface. Public URLs remain owned
# by dashboard.py during this safe migration phase; this module re-exports helper
# functions and exposes a manifest so later phases can move route ownership
# safely route-by-route.

from typing import Any

from socmint import dashboard as _dashboard


EXTRACTED_VERSION_RANGE = "v9.8.4-v9.8.9"
MODULE_NAME = "socmint.product_artifacts"
COMPATIBILITY_MODE = "re-export"

ROUTE_FAMILY = [
    "/product/artifacts",
    "/api/v1/product/artifacts",
    "/product/artifacts/review",
    "/api/v1/product/artifacts/review",
    "/api/v1/product/artifact-review-state",
    "/product/artifacts/audit/<path:relpath>",
    "/api/v1/product/artifact-review-audit",
    "/product/artifacts/export-manifest",
    "/api/v1/product/artifact-export-manifest",
    "/product/release-package",
    "/api/v1/product/release-package",
    "/api/v1/product/release-package/build",
    "/api/v1/product/release-packages",
    "/product/release-package/download/{package_name}",
]


def _export_dashboard_symbols() -> None:
    prefixes = (
        "_v984",
        "_v985",
        "_v986",
        "_v987",
        "_v988",
        "_v989",
        "_v98",
    )
    shared_names = {
        "login_required",
        "admin_required",
        "audit",
        "dashboard_bp",
    }

    for name in dir(_dashboard):
        if name.startswith(prefixes) or name in shared_names:
            globals()[name] = getattr(_dashboard, name)


_export_dashboard_symbols()


def product_artifacts_manifest() -> dict[str, Any]:
    exported_helper_count = sum(
        1
        for name in globals()
        if name.startswith(("_v984", "_v985", "_v986", "_v987", "_v988", "_v989", "_v98"))
    )
    return {
        "status": "ok",
        "version": "10.0.3",
        "module": MODULE_NAME,
        "compatibility_mode": COMPATIBILITY_MODE,
        "extracted_version_range": EXTRACTED_VERSION_RANGE,
        "exported_helper_count": exported_helper_count,
        "route_family": ROUTE_FAMILY,
        "note": (
            "Phase 3 exposes the dedicated artifact pipeline module and re-exports "
            "artifact browser/review/audit/export/package helpers from dashboard.py. "
            "Public routes remain unchanged; full blueprint ownership can move in a "
            "later phase."
        ),
    }


__all__ = [
    "product_artifacts_manifest",
    "EXTRACTED_VERSION_RANGE",
    "MODULE_NAME",
    "COMPATIBILITY_MODE",
    "ROUTE_FAMILY",
]
