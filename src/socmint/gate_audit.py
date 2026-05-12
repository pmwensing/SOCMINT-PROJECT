from __future__ import annotations

from dataclasses import dataclass
from typing import Any

GATE_AUDIT_SCHEMA = "socmint.gate_audit.v9_0_1"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
PUBLIC_ENDPOINTS = {"healthz", "readyz", "static", "api_production_release_summary"}
KNOWN_AUTH_PREFIXES = (
    "/account",
    "/admin",
    "/analyst",
    "/api/v1/account",
    "/api/v1/admin",
    "/api/v1/analyst",
    "/api/v1/cases",
    "/api/v1/connectors",
    "/api/v1/evidence",
    "/api/v1/exports",
    "/api/v1/jobs",
    "/api/v1/responsible-use",
    "/api/v1/spine",
    "/api/v1/tor",
    "/cases",
    "/connectors",
    "/evidence",
    "/exports",
    "/jobs",
    "/responsible-use",
    "/spine",
)
ADMIN_PREFIXES = ("/admin", "/api/v1/admin")
QUOTA_ACTIONS = {
    "case": "active_cases",
    "subject": "subjects_per_month",
    "connector": "connector_runs_per_day",
    "capture": "browser_captures_per_day",
    "account-discovery": "account_ingests_per_day",
    "export": "signed_exports_per_month",
    "graph": "graph_builds_per_day",
}
RESPONSIBLE_USE_KEYWORDS = ("case", "subject", "connector", "capture", "export", "graph", "account-discovery")


@dataclass(frozen=True)
class RouteGateRow:
    route: str
    endpoint: str
    methods: list[str]
    mutating: bool
    auth_required: bool
    admin_required: bool
    quota_key: str | None
    responsible_use_required: bool
    audit_event_required: bool
    status: str
    notes: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "route": self.route,
            "endpoint": self.endpoint,
            "methods": self.methods,
            "mutating": self.mutating,
            "auth_required": self.auth_required,
            "admin_required": self.admin_required,
            "quota_key": self.quota_key,
            "responsible_use_required": self.responsible_use_required,
            "audit_event_required": self.audit_event_required,
            "status": self.status,
            "notes": self.notes,
        }


def _quota_for_route(route: str) -> str | None:
    normalized = route.lower()
    for key, quota in QUOTA_ACTIONS.items():
        if key in normalized:
            return quota
    return None


def _responsible_use_required(route: str) -> bool:
    normalized = route.lower()
    return any(keyword in normalized for keyword in RESPONSIBLE_USE_KEYWORDS)


def _auth_required(route: str, endpoint: str) -> bool:
    if endpoint in PUBLIC_ENDPOINTS:
        return False
    if route in {"/", "/login", "/logout", "/signup", "/healthz", "/readyz"}:
        return False
    return route.startswith(KNOWN_AUTH_PREFIXES) or route.startswith("/api/v1")


def route_gate_matrix(app) -> dict[str, Any]:
    rows: list[RouteGateRow] = []
    for rule in sorted(app.url_map.iter_rules(), key=lambda item: item.rule):
        methods = sorted((set(rule.methods or []) - {"HEAD", "OPTIONS"}))
        mutating = bool(set(methods) & MUTATING_METHODS)
        auth_required = _auth_required(rule.rule, rule.endpoint)
        admin_required = rule.rule.startswith(ADMIN_PREFIXES)
        quota_key = _quota_for_route(rule.rule) if mutating else None
        responsible = _responsible_use_required(rule.rule) if mutating else False
        audit_required = mutating
        notes: list[str] = []
        status = "ok"
        if mutating and not auth_required:
            status = "needs_review"
            notes.append("Mutating route should require authentication unless explicitly public and justified.")
        if mutating and responsible and not quota_key:
            status = "needs_review"
            notes.append("Responsible-use scoped mutation has no inferred quota key.")
        if mutating and rule.rule.startswith("/api/v1") and not audit_required:
            status = "needs_review"
            notes.append("API mutation should emit an audit event.")
        rows.append(
            RouteGateRow(
                route=rule.rule,
                endpoint=rule.endpoint,
                methods=methods,
                mutating=mutating,
                auth_required=auth_required,
                admin_required=admin_required,
                quota_key=quota_key,
                responsible_use_required=responsible,
                audit_event_required=audit_required,
                status=status,
                notes=notes,
            )
        )
    payload_rows = [row.as_dict() for row in rows]
    mutating_rows = [row for row in payload_rows if row["mutating"]]
    review_rows = [row for row in payload_rows if row["status"] != "ok"]
    return {
        "schema": GATE_AUDIT_SCHEMA,
        "total_routes": len(payload_rows),
        "mutating_routes": len(mutating_rows),
        "needs_review": len(review_rows),
        "status": "needs_review" if review_rows else "ok",
        "rows": payload_rows,
        "review_rows": review_rows,
    }


def gate_audit_summary(app) -> dict[str, Any]:
    matrix = route_gate_matrix(app)
    return {
        "schema": GATE_AUDIT_SCHEMA,
        "total_routes": matrix["total_routes"],
        "mutating_routes": matrix["mutating_routes"],
        "needs_review": matrix["needs_review"],
        "status": matrix["status"],
    }
