from __future__ import annotations

from typing import Any

OPERATOR_SMOKE_SCHEMA = "socmint.operator_smoke.v9_6_0"

SMOKE_ROUTES = [
    {"name": "home", "method": "GET", "path": "/", "auth": False, "surface": "browser"},
    {
        "name": "health",
        "method": "GET",
        "path": "/healthz",
        "auth": False,
        "surface": "api",
    },
    {
        "name": "ready",
        "method": "GET",
        "path": "/readyz",
        "auth": False,
        "surface": "api",
    },
    {
        "name": "production_summary",
        "method": "GET",
        "path": "/api/v1/production-release/summary",
        "auth": False,
        "surface": "api",
    },
    {
        "name": "beta_onboarding",
        "method": "GET",
        "path": "/api/v1/beta/onboarding",
        "auth": False,
        "surface": "api",
    },
    {
        "name": "account_membership",
        "method": "GET",
        "path": "/api/v1/account/membership",
        "auth": True,
        "surface": "api",
    },
    {
        "name": "account_billing",
        "method": "GET",
        "path": "/api/v1/account/billing",
        "auth": True,
        "surface": "api",
    },
    {
        "name": "account_case_access",
        "method": "GET",
        "path": "/api/v1/account/case-access",
        "auth": True,
        "surface": "api",
    },
    {
        "name": "analyst_launchpad",
        "method": "GET",
        "path": "/analyst/launchpad",
        "auth": True,
        "surface": "browser",
    },
    {
        "name": "analyst_launchpad_api",
        "method": "GET",
        "path": "/api/v1/analyst/launchpad/compact",
        "auth": True,
        "surface": "api",
    },
    {
        "name": "connector_catalog",
        "method": "GET",
        "path": "/api/v1/connectors/sdk/catalog",
        "auth": True,
        "surface": "api",
    },
    {
        "name": "release_pipeline",
        "method": "GET",
        "path": "/api/v1/admin/release-pipeline/summary",
        "auth": True,
        "admin": True,
        "surface": "api",
    },
    {
        "name": "security_checklist",
        "method": "GET",
        "path": "/api/v1/admin/security/checklist",
        "auth": True,
        "admin": True,
        "surface": "api",
    },
    {
        "name": "gate_enforcement",
        "method": "GET",
        "path": "/api/v1/admin/gates/enforcement/summary",
        "auth": True,
        "admin": True,
        "surface": "api",
    },
    {
        "name": "certification",
        "method": "GET",
        "path": "/api/v1/admin/certification/summary",
        "auth": True,
        "admin": True,
        "surface": "api",
    },
]


def operator_smoke_matrix() -> dict[str, Any]:
    return {
        "schema": OPERATOR_SMOKE_SCHEMA,
        "route_count": len(SMOKE_ROUTES),
        "routes": SMOKE_ROUTES,
        "surfaces": sorted({route["surface"] for route in SMOKE_ROUTES}),
    }


def operator_smoke_summary() -> dict[str, Any]:
    matrix = operator_smoke_matrix()
    auth_required = [route for route in matrix["routes"] if route.get("auth")]
    admin_required = [route for route in matrix["routes"] if route.get("admin")]
    return {
        "schema": OPERATOR_SMOKE_SCHEMA,
        "route_count": matrix["route_count"],
        "auth_required": len(auth_required),
        "admin_required": len(admin_required),
        "public_routes": matrix["route_count"] - len(auth_required),
        "surfaces": matrix["surfaces"],
    }


def validate_smoke_routes(app) -> dict[str, Any]:
    rules = {rule.rule for rule in app.url_map.iter_rules()}
    missing = [route for route in SMOKE_ROUTES if route["path"] not in rules]
    return {
        "schema": OPERATOR_SMOKE_SCHEMA,
        "status": "pass" if not missing else "missing_routes",
        "missing_count": len(missing),
        "missing": missing,
        "route_count": len(SMOKE_ROUTES),
    }
