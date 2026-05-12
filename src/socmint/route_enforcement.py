from __future__ import annotations

from typing import Any

from .gate_audit import route_gate_matrix

ROUTE_ENFORCEMENT_SCHEMA = "socmint.route_enforcement.v9_0_3"

STRICT_MUTATION_PREFIXES = (
    "/api/v1/cases",
    "/api/v1/spine",
    "/api/v1/evidence",
    "/api/v1/exports",
    "/api/v1/connectors",
    "/api/v1/jobs",
    "/api/v1/responsible-use",
    "/api/v1/account",
    "/api/v1/admin",
)

EXPORT_ROUTES = ("/api/v1/exports", "export-preflight", "ultimate-dossier", "export-quality")


def _requires_strict_review(row: dict[str, Any]) -> bool:
    route = row.get("route", "")
    return bool(row.get("mutating")) and route.startswith(STRICT_MUTATION_PREFIXES)


def route_enforcement_report(app) -> dict[str, Any]:
    matrix = route_gate_matrix(app)
    rows = matrix.get("rows", [])
    violations: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    for row in rows:
        route = row.get("route", "")
        if _requires_strict_review(row):
            if not row.get("auth_required"):
                violations.append({"route": route, "issue": "mutating route missing auth requirement"})
            if row.get("responsible_use_required") and not row.get("quota_key"):
                warnings.append({"route": route, "issue": "responsible-use mutation has no inferred quota key"})
            if not row.get("audit_event_required"):
                violations.append({"route": route, "issue": "mutating route missing audit requirement"})
        if any(marker in route for marker in EXPORT_ROUTES) and row.get("mutating"):
            if not row.get("auth_required"):
                violations.append({"route": route, "issue": "export mutation must require auth"})
            if not row.get("audit_event_required"):
                violations.append({"route": route, "issue": "export mutation must require audit"})

    status = "pass" if not violations else "fail"
    return {
        "schema": ROUTE_ENFORCEMENT_SCHEMA,
        "status": status,
        "total_routes": matrix.get("total_routes", 0),
        "mutating_routes": matrix.get("mutating_routes", 0),
        "violation_count": len(violations),
        "warning_count": len(warnings),
        "violations": violations,
        "warnings": warnings,
        "matrix_status": matrix.get("status"),
    }


def route_enforcement_summary(app) -> dict[str, Any]:
    report = route_enforcement_report(app)
    return {
        "schema": ROUTE_ENFORCEMENT_SCHEMA,
        "status": report["status"],
        "mutating_routes": report["mutating_routes"],
        "violation_count": report["violation_count"],
        "warning_count": report["warning_count"],
    }
