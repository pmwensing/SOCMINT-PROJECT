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
        "why": "A real operator must be able to clone, configure, migrate, log in, and run the core dossier path without hand fixes.",
        "deliverables": [
            "Keep drift-report and audit-report green on current head.",
            "Keep .env.example aligned with runtime settings names.",
            "Keep version.py, pyproject.toml, health/status routes, and release docs synchronized.",
            "Run a fresh-db gate before feature work merges.",
        ],
    },
    {
        "phase": "operator_flow",
        "title": "Make the happy path obvious",
        "priority": "P0",
        "why": "The project already has many modules; usability depends on one clear case -> subject -> seed -> review -> dossier workflow.",
        "deliverables": [
            "Command-center checklist with next best action.",
            "Dossier readiness state: ready, draft-only, or blocked.",
            "Buttons for run full report, inspect latest report, and export integrity pack.",
        ],
    },
    {
        "phase": "claim_evidence_integrity",
        "title": "Bind claims to evidence and review decisions",
        "priority": "P1",
        "why": "Dossier value comes from traceable claims, not raw connector volume.",
        "deliverables": [
            "Every promoted claim shows source, confidence, review status, and evidence link.",
            "Final exports include claim/evidence/review CSV ledgers.",
            "Hash mismatch and unresolved contradiction warnings block final-mode export unless overridden as draft.",
        ],
    },
    {
        "phase": "connector_normalization",
        "title": "Normalize connector output before expanding coverage",
        "priority": "P1",
        "why": "More connectors create noise unless each output becomes a pending finding with source/confidence/review state.",
        "deliverables": [
            "Connector output contract: case_id, subject_id, source, finding_type, value, raw, confidence, evidence_url, collected_at, review_status.",
            "Candidate findings stay out of final dossiers until promoted.",
            "Connector quality metrics stay visible in the operator UI.",
        ],
    },
    {
        "phase": "export_packaging",
        "title": "Professional case package export",
        "priority": "P2",
        "why": "The highest-value artifact is a portable review bundle, not just an in-app graph.",
        "deliverables": [
            "ZIP bundle with dossier PDF/HTML/JSON, evidence manifest, hash manifest, graph JSON, timeline CSV, and audit report.",
            "Package verification endpoint that checks required files and hashes.",
            "Human-readable release/case package report.",
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
        score = round((len(present) / len(required_routes)) * 100) if required_routes else 100
        total += len(required_routes)
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


def _findings_from_capabilities(capabilities: list[dict[str, Any]]) -> dict[str, list[str]]:
    works: list[str] = []
    gaps: list[str] = []
    for item in capabilities:
        label = item["key"].replace("_", " ")
        if item["status"] == "works":
            works.append(f"{label}: required runtime routes are present.")
        elif item["status"] == "partial":
            gaps.append(
                f"{label}: partial route coverage; missing {len(item['missing_routes'])} required route(s)."
            )
        else:
            gaps.append(
                f"{label}: not operator-ready; missing {len(item['missing_routes'])} required route(s)."
            )
    return {"what_works": works, "what_does_not": gaps}


def build_real_world_audit(app=None) -> dict[str, Any]:
    """Return an operator-facing product audit and repair/value build plan.

    This intentionally scores concrete runtime surface area instead of marketing claims.
    It is safe to call during smoke tests because it does not execute connectors, crawlers,
    browser automation, or destructive retention actions.
    """

    drift = build_drift_report(app)
    audit = build_audit_report(app, limit=100)
    capabilities, route_score = _capability_score(app)
    findings = _findings_from_capabilities(capabilities)

    blockers = []
    if drift.get("missing_tables"):
        blockers.append("Database/schema drift: required tables are missing from the active database.")
    if drift.get("missing_routes"):
        blockers.append("Runtime route drift: required routes are missing from the active app map.")
    if drift.get("environment_findings"):
        blockers.append("Configuration warnings: runtime environment has one or more deployment-risk findings.")

    if blockers:
        readiness = "repair_before_feature_expansion"
    elif route_score < 90:
        readiness = "partial_operator_ready"
    else:
        readiness = "operator_ready_for_next_value_slice"

    value_assessment = {
        "current_value_score": route_score,
        "highest_value_center": "Full Entity Profile Dossier Builder",
        "positioning": "case -> entity -> evidence -> confidence -> human review -> dossier/report export",
        "do_not_optimize_for": "raw connector count before claim/evidence/review integrity",
    }

    return {
        "schema": SCHEMA,
        "generated_at": _utc_now(),
        "version": version_payload(),
        "readiness": readiness,
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
        # The API payload is deliberately the authoritative UI for this build:
        # it is copy/pasteable into release notes, audits, and next-step prompts.
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
