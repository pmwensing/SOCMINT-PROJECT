from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

SCHEMA = "socmint.portfolio_product_review.v24_7"
VERSION = "v24.7.0"

REQUIRED_MODULES = (
    "src/socmint/portfolio_operations_dashboard_v24_0.py",
    "src/socmint/portfolio_case_stage_overview_v24_1.py",
    "src/socmint/portfolio_workload_monitoring_v24_2.py",
    "src/socmint/portfolio_blocked_overdue_queue_v24_3.py",
    "src/socmint/portfolio_supervisor_escalation_v24_4.py",
    "src/socmint/portfolio_operational_metrics_v24_5.py",
    "src/socmint/portfolio_history_audit_v24_6.py",
)

REQUIRED_ASSETS = (
    "src/socmint/templates/portfolio_operations_dashboard_v24_0.html",
    "src/socmint/templates/portfolio_supervisor_escalations_v24_4.html",
    "src/socmint/templates/portfolio_history_audit_v24_6.html",
    "src/socmint/static/portfolio_supervisor_escalations_v24_4.js",
    "scripts/run_v24_7_portfolio_browser_e2e.py",
)

REQUIRED_NOTES = (
    "release/V24_0_PORTFOLIO_OPERATIONS_DASHBOARD.md",
    "release/V24_1_CASE_STATUS_STAGE_OVERVIEW.md",
    "release/V24_2_WORKLOAD_ASSIGNMENT_MONITORING.md",
    "release/V24_3_BLOCKED_OVERDUE_CASE_QUEUE.md",
    "release/V24_4_SUPERVISOR_ESCALATION_CONTROLS.md",
    "release/V24_5_OPERATIONAL_METRICS_THROUGHPUT.md",
    "release/V24_6_PORTFOLIO_HISTORY_AUDIT.md",
)

REQUIRED_ROUTES = (
    "/portfolio-operations",
    "/api/v1/portfolio-operations",
    "/api/v1/portfolio-operations/stage-overview",
    "/api/v1/portfolio-operations/workload-monitoring",
    "/api/v1/portfolio-operations/blocked-overdue",
    "/portfolio-operations/escalations",
    "/api/v1/portfolio-operations/escalations",
    "/api/v1/portfolio-operations/<case_id>/escalate",
    "/api/v1/portfolio-operations/<case_id>/acknowledge",
    "/api/v1/portfolio-operations/<case_id>/reassign",
    "/api/v1/portfolio-operations/<case_id>/resolve",
    "/api/v1/portfolio-operations/metrics",
    "/portfolio-operations/history",
    "/api/v1/portfolio-operations/history",
    "/api/v1/portfolio-operations/product-review-checkpoint",
)


def build_portfolio_product_review(
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

    module_checks = check_paths(REQUIRED_MODULES, "missing_v24_module")
    asset_checks = check_paths(REQUIRED_ASSETS, "missing_v24_asset")
    release_note_checks = check_paths(REQUIRED_NOTES, "missing_v24_release_note")

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
            blockers.append({"key": "missing_v24_route", "detail": rule})

    duplicate_routes = [
        {"route": rule, "methods": list(methods), "count": count}
        for (rule, methods), count in Counter(route_keys).items()
        if count > 1 and rule.startswith(("/portfolio-operations", "/api/v1/portfolio-operations"))
    ]
    if duplicate_routes:
        blockers.append({"key": "duplicate_v24_route", "detail": str(duplicate_routes)})

    migrations = sorted(
        str(path.relative_to(root_path))
        for directory in (root_path / "migrations", root_path / "alembic")
        if directory.exists()
        for path in directory.rglob("*")
        if path.is_file() and "v24" in path.name.lower()
    )
    if migrations:
        blockers.append({"key": "unexpected_v24_migration", "detail": ", ".join(migrations)})

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
        "blocker_count": len(blockers),
        "blockers": blockers,
        "source_records_mutated": False,
        "checkpoint_record_created": False,
        "next_action": "run_v24_browser_e2e" if not blockers else "resolve_v24_product_blockers",
    }
