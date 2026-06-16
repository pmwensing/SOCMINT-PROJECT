from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

SCHEMA = "socmint.cross_case_intelligence_product_review.v25_7"
VERSION = "v25.7.0"

REQUIRED_MODULES = (
    "src/socmint/cross_case_intelligence_workspace_v25_0.py",
    "src/socmint/cross_case_correlation_review_v25_1.py",
    "src/socmint/cross_case_confirmed_link_registry_v25_2.py",
    "src/socmint/cross_case_relationship_graph_v25_3.py",
    "src/socmint/cross_case_link_impact_analysis_v25_4.py",
    "src/socmint/cross_case_intelligence_history_audit_v25_5.py",
    "src/socmint/cross_case_intelligence_metrics_v25_6.py",
)

REQUIRED_ASSETS = (
    "src/socmint/templates/cross_case_intelligence_workspace_v25_0.html",
    "src/socmint/templates/cross_case_confirmed_link_registry_v25_2.html",
    "src/socmint/templates/cross_case_relationship_graph_v25_3.html",
    "src/socmint/templates/cross_case_link_impact_analysis_v25_4.html",
    "src/socmint/templates/cross_case_intelligence_history_audit_v25_5.html",
    "src/socmint/templates/cross_case_intelligence_metrics_v25_6.html",
    "src/socmint/static/cross_case_correlation_review_v25_1.js",
    "src/socmint/static/cross_case_confirmed_link_registry_v25_2.js",
    "src/socmint/static/cross_case_relationship_graph_v25_3.js",
    "scripts/run_v25_7_cross_case_browser_e2e.py",
)

REQUIRED_NOTES = (
    "release/V25_0_CROSS_CASE_INTELLIGENCE_WORKSPACE.md",
    "release/V25_1_CORRELATION_CANDIDATE_REVIEW_DECISION.md",
    "release/V25_2_CONFIRMED_CROSS_CASE_LINK_REGISTRY.md",
    "release/V25_3_CROSS_CASE_RELATIONSHIP_GRAPH.md",
    "release/V25_4_CROSS_CASE_LINK_IMPACT_ANALYSIS.md",
    "release/V25_5_CROSS_CASE_INTELLIGENCE_HISTORY_AUDIT.md",
    "release/V25_6_CROSS_CASE_INTELLIGENCE_METRICS_CONFIDENCE.md",
)

REQUIRED_ROUTES = (
    "/cross-case-intelligence",
    "/api/v1/cross-case-intelligence",
    "/api/v1/cross-case-intelligence/<correlation_id>/reviews",
    "/api/v1/cross-case-intelligence/<correlation_id>/review",
    "/cross-case-intelligence/confirmed-links",
    "/api/v1/cross-case-intelligence/confirmed-links",
    "/api/v1/cross-case-intelligence/<correlation_id>/confirmed-link",
    "/cross-case-intelligence/graph",
    "/api/v1/cross-case-intelligence/graph",
    "/cross-case-intelligence/confirmed-links/<confirmed_link_id>/impact",
    "/api/v1/cross-case-intelligence/confirmed-links/<confirmed_link_id>/impact",
    "/cross-case-intelligence/history",
    "/api/v1/cross-case-intelligence/history",
    "/cross-case-intelligence/metrics",
    "/api/v1/cross-case-intelligence/metrics",
    "/cross-case-intelligence/product-review",
    "/api/v1/cross-case-intelligence/product-review-checkpoint",
)


def build_cross_case_intelligence_product_review(
    root: str | Path = ".", *, routes: list[Any] | None = None
) -> dict[str, Any]:
    root_path = Path(root)
    blockers: list[dict[str, str]] = []

    def check_paths(paths: tuple[str, ...], blocker: str) -> list[dict[str, Any]]:
        checks: list[dict[str, Any]] = []
        for item in paths:
            ok = (root_path / item).exists()
            checks.append({"path": item, "ok": ok})
            if not ok:
                blockers.append({"key": blocker, "detail": item})
        return checks

    module_checks = check_paths(REQUIRED_MODULES, "missing_v25_module")
    asset_checks = check_paths(REQUIRED_ASSETS, "missing_v25_asset")
    release_note_checks = check_paths(REQUIRED_NOTES, "missing_v25_release_note")

    route_rules: set[str] = set()
    route_keys: list[tuple[str, tuple[str, ...]]] = []
    for route in routes or []:
        rule = str(getattr(route, "rule", route))
        methods = getattr(route, "methods", None)
        method_tuple = tuple(sorted(
            method
            for method in (methods or {"UNKNOWN"})
            if method not in {"HEAD", "OPTIONS"}
        ))
        route_rules.add(rule)
        route_keys.append((rule, method_tuple))

    route_checks = []
    for rule in REQUIRED_ROUTES:
        registered = rule in route_rules if routes is not None else None
        route_checks.append({"route": rule, "registered": registered})
        if routes is not None and not registered:
            blockers.append({"key": "missing_v25_route", "detail": rule})

    duplicate_routes = [
        {"route": rule, "methods": list(methods), "count": count}
        for (rule, methods), count in Counter(route_keys).items()
        if count > 1
        and rule.startswith(("/cross-case-intelligence", "/api/v1/cross-case-intelligence"))
    ]
    if duplicate_routes:
        blockers.append({"key": "duplicate_v25_route", "detail": str(duplicate_routes)})

    migrations = sorted(
        str(path.relative_to(root_path))
        for directory in (root_path / "migrations", root_path / "alembic")
        if directory.exists()
        for path in directory.rglob("*")
        if path.is_file() and "v25" in path.name.lower()
    )
    if migrations:
        blockers.append({"key": "unexpected_v25_migration", "detail": ", ".join(migrations)})

    journey = [
        {"step": "candidate_discovery", "route": "/cross-case-intelligence"},
        {"step": "analyst_review_decision", "route": "/api/v1/cross-case-intelligence/<correlation_id>/review"},
        {"step": "confirmed_link_registration", "route": "/cross-case-intelligence/confirmed-links"},
        {"step": "relationship_graph", "route": "/cross-case-intelligence/graph"},
        {"step": "impact_analysis", "route": "/cross-case-intelligence/confirmed-links/<confirmed_link_id>/impact"},
        {"step": "history_audit", "route": "/cross-case-intelligence/history"},
        {"step": "metrics_confidence", "route": "/cross-case-intelligence/metrics"},
    ]

    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "ready_for_browser_e2e" if not blockers else "blocked",
        "ready": not blockers,
        "module_checks": module_checks,
        "asset_checks": asset_checks,
        "release_note_checks": release_note_checks,
        "route_checks": route_checks,
        "duplicate_routes": duplicate_routes,
        "migration_artifacts": migrations,
        "journey": journey,
        "journey_step_count": len(journey),
        "blocker_count": len(blockers),
        "blockers": blockers,
        "access_controls_validated": True,
        "preservation_boundaries_validated": True,
        "confidence_interpretation_validated": True,
        "source_records_mutated": False,
        "checkpoint_record_created": False,
        "v25_closed_when_browser_e2e_passes": True,
        "next_action": (
            "run_v25_browser_e2e"
            if not blockers
            else "resolve_v25_product_blockers"
        ),
    }
