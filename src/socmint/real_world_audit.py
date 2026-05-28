from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from flask import jsonify

from .build_audit_report import build_audit_report, build_drift_report
from .version import version_payload

SCHEMA = "socmint.v12_10_22.real_world_audit"

CORE_ROUTE_REQUIREMENTS = {
    "case_and_subject_spine": [
        "/api/v1/spine/subjects",
        "/api/v1/spine/subjects/<int:subject_id>/dossier",
    ],
    "full_report_pipeline": [
        "/api/v1/spine/subjects/<int:subject_id>/full-report",
        "/api/v1/spine/subjects/<int:subject_id>/full-report/run",
        "/api/v1/spine/subjects/<int:subject_id>/full-report/latest",
    ],
    "audit_and_drift": [
        "/api/v1/workbench/drift-report",
        "/api/v1/workbench/audit-report",
        "/api/v1/workbench/status",
    ],
    "review_and_quality": [
        "/api/v1/spine/assertions/review-queue",
        "/api/v1/spine/connectors/quality",
        "/api/v1/spine/enrichment-review",
    ],
    "graph_timeline_intelligence": [
        "/api/v1/spine/subjects/<int:subject_id>/graph",
        "/api/v1/spine/subjects/<int:subject_id>/contradictions",
    ],
    "evidence_integrity": [
        "/api/v1/evidence/integrity",
        "/api/v1/evidence/integrity/pack",
    ],
}

REAL_WORLD_BUILD_PLAN = [
    {
        "phase": "repair_first",
        "title": "Stabilize fresh deploy and version truth",
        "priority": "P0",
        "why": "Clean configure, migrate, log in, and run the dossier path.",
        "deliverables": [
            "Keep drift-report and audit-report green on current head.",
            "Keep .env.example aligned with runtime settings names.",
            "Keep version metadata, health routes, and release docs synchronized.",
            "Run a fresh-db gate before feature work merges.",
        ],
    },
    {
        "phase": "operator_flow",
        "title": "Make the happy path obvious",
        "priority": "P0",
        "why": "Usability depends on one clear case-to-dossier workflow.",
        "deliverables": [
            "Command-center checklist with next best action.",
            "Dossier readiness state: ready, draft-only, or blocked.",
            "Buttons for report generation, latest report, and integrity export.",
        ],
    },
    {
        "phase": "claim_evidence_integrity",
        "title": "Bind claims to evidence and review decisions",
        "priority": "P1",
        "why": "Dossier value comes from traceable claims, not raw connector volume.",
        "deliverables": [
            "Every promoted claim shows source, confidence, review, and evidence.",
            "Final exports include claim, evidence, and review ledgers.",
            "Hash mismatch and high-severity contradictions block final export.",
        ],
    },
    {
        "phase": "connector_normalization",
        "title": "Normalize connector output before expanding coverage",
        "priority": "P1",
        "why": "Connector volume creates noise without reviewable normalized findings.",
        "deliverables": [
            "Normalize source, type, value, raw, confidence, URL, and status.",
            "Candidate findings stay out of final dossiers until promoted.",
            "Connector quality metrics stay visible in the operator UI.",
        ],
    },
    {
        "phase": "export_packaging",
        "title": "Professional case package export",
        "priority": "P2",
        "why": "The highest-value artifact is a portable review bundle.",
        "deliverables": [
            "ZIP dossier PDF, HTML, JSON, manifests, graph, timeline, and audit.",
            "Package verification endpoint checks required files and hashes.",
            "Human-readable release and case package report.",
        ],
    },
]


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _route_set(app) -> set[str]:
    if app is None:
        return set()
    return {str(rule.rule) for rule in app.url_map.iter_rules()}


def _capability_score(app) -> tuple[list[dict[str, Any]], int]:
    routes = _route_set(app)
    capabilities = []
    total = 0
    available = 0
    for key, required_routes in CORE_ROUTE_REQUIREMENTS.items():
        present = [route for route in required_routes if route in routes]
        missing = [route for route in required_routes if route not in routes]
        route_count = len(required_routes)
        score = round((len(present) / route_count) * 100) if route_count else 100
        total += route_count
        available += len(present)
        if score == 100:
            status = "works"
        elif score >= 50:
            status = "partial"
        else:
            status = "needs_repair"
        capabilities.append(
            {
                "key": key,
                "status": status,
                "score": score,
                "available_routes": present,
                "missing_routes": missing,
            }
        )
    overall = round((available / total) * 100) if total else 0
    return capabilities, overall


def _gap_message(label: str, missing_count: int, status: str) -> str:
    if status == "partial":
        prefix = "partial route coverage"
    else:
        prefix = "not operator-ready"
    return f"{label}: {prefix}; missing {missing_count} required route(s)."


def _findings_from_capabilities(
    capabilities: list[dict[str, Any]],
) -> dict[str, list[str]]:
    works: list[str] = []
    gaps: list[str] = []
    for item in capabilities:
        label = item["key"].replace("_", " ")
        status = item["status"]
        missing_count = len(item["missing_routes"])
        if status == "works":
            works.append(f"{label}: required runtime routes are present.")
        else:
            gaps.append(_gap_message(label, missing_count, status))
    return {"what_works": works, "what_does_not": gaps}


def _blockers_from_drift(drift: dict[str, Any]) -> list[str]:
    blockers = []
    if drift.get("missing_tables"):
        blockers.append("Database/schema drift: required tables are missing.")
    if drift.get("missing_routes"):
        blockers.append("Runtime route drift: required routes are missing.")
    if drift.get("environment_findings"):
        blockers.append("Configuration warnings: deployment risk findings exist.")
    return blockers


def _readiness(blockers: list[str], route_score: int) -> str:
    if blockers:
        return "repair_before_feature_expansion"
    if route_score < 90:
        return "partial_operator_ready"
    return "operator_ready_for_next_value_slice"


def build_real_world_audit(app=None) -> dict[str, Any]:
    """Return an operator-facing product audit and repair/value build plan."""

    drift = build_drift_report(app)
    audit = build_audit_report(app, limit=100)
    capabilities, route_score = _capability_score(app)
    findings = _findings_from_capabilities(capabilities)
    blockers = _blockers_from_drift(drift)

    value_assessment = {
        "current_value_score": route_score,
        "highest_value_center": "Full Entity Profile Dossier Builder",
        "positioning": "case to evidence to review to dossier export",
        "do_not_optimize_for": "raw connector count before traceability",
    }

    return {
        "schema": SCHEMA,
        "generated_at": _utc_now(),
        "version": version_payload(),
        "readiness": _readiness(blockers, route_score),
        "blockers": blockers,
        "capability_score": route_score,
        "capabilities": capabilities,
        "what_works": findings["what_works"],
        "what_does_not": findings["what_does_not"],
        "value_assessment": value_assessment,
        "build_plan": REAL_WORLD_BUILD_PLAN,
        "drift_summary": {
            "status": drift.get("status"),
            "missing_tables": drift.get("missing_tables", []),
            "missing_routes": drift.get("missing_routes", []),
            "environment_findings": drift.get("environment_findings", []),
        },
        "audit_summary": {
            "status": audit.get("status"),
            "counts": audit.get("counts", {}),
            "job_status_counts": audit.get("job_status_counts", {}),
        },
    }


def register_real_world_audit_routes(app) -> None:
    if "api_real_world_audit" in app.view_functions:
        return

    from .dashboard import login_required

    @login_required
    def api_real_world_audit():
        return jsonify(build_real_world_audit(app))

    @login_required
    def real_world_audit_view():
        return jsonify(build_real_world_audit(app))

    app.add_url_rule(
        "/api/v1/workbench/real-world-audit",
        endpoint="api_real_world_audit",
        view_func=api_real_world_audit,
        methods=["GET"],
    )
    app.add_url_rule(
        "/workbench/real-world-audit",
        endpoint="real_world_audit_view",
        view_func=real_world_audit_view,
        methods=["GET"],
    )
