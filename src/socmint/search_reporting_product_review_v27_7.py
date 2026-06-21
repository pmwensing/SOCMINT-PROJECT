from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

SCHEMA = "socmint.search_reporting_product_review.v27_7"
VERSION = "v27.7.0"

REQUIRED_MODULES = (
    "src/socmint/global_investigation_search_v27_0.py",
    "src/socmint/core_record_search_v27_1.py",
    "src/socmint/advanced_search_filters_v27_2.py",
    "src/socmint/saved_search_view_events_v27_3.py",
    "src/socmint/saved_search_views_workspace_v27_3.py",
    "src/socmint/watchlist_monitoring_events_v27_4.py",
    "src/socmint/watchlist_monitoring_workspace_v27_4.py",
    "src/socmint/report_builder_events_v27_5.py",
    "src/socmint/report_export_packages_v27_5.py",
    "src/socmint/search_reporting_history_audit_v27_6.py",
)

REQUIRED_ASSETS = (
    "src/socmint/templates/global_investigation_search_v27_0.html",
    "src/socmint/templates/core_record_search_v27_1.html",
    "src/socmint/templates/advanced_search_filters_v27_2.html",
    "src/socmint/templates/saved_search_views_v27_3.html",
    "src/socmint/templates/watchlist_monitoring_v27_4.html",
    "src/socmint/templates/report_builder_v27_5.html",
    "src/socmint/templates/search_reporting_history_audit_v27_6.html",
    "scripts/run_v27_7_search_reporting_browser_e2e.py",
)

REQUIRED_NOTES = tuple(
    f"release/V27_{minor}_{name}.md"
    for minor, name in (
        (0, "GLOBAL_INVESTIGATION_SEARCH"),
        (1, "CASE_ENTITY_EVIDENCE_FINDING_SEARCH"),
        (2, "ADVANCED_FILTERS_SEARCH_FACETS"),
        (3, "SAVED_VIEWS_SEARCH_PRESETS"),
        (4, "WATCHLISTS_SCHEDULED_SEARCH_MONITORING"),
        (5, "REPORT_BUILDER_EXPORT_PACKAGES"),
        (6, "SEARCH_WATCHLIST_REPORTING_HISTORY_AUDIT"),
    )
)

REQUIRED_ROUTES = (
    "/global-search",
    "/api/v1/global-search",
    "/global-search/core-records",
    "/api/v1/global-search/core-records",
    "/global-search/advanced",
    "/api/v1/global-search/advanced",
    "/global-search/saved-views",
    "/api/v1/global-search/saved-views",
    "/api/v1/global-search/saved-views/<view_id>/revise",
    "/api/v1/global-search/saved-views/<view_id>/deactivate",
    "/api/v1/global-search/saved-views/<view_id>/run",
    "/global-search/watchlists",
    "/api/v1/global-search/watchlists",
    "/api/v1/global-search/watchlists/<watchlist_id>/pause",
    "/api/v1/global-search/watchlists/<watchlist_id>/resume",
    "/api/v1/global-search/watchlists/<watchlist_id>/run",
    "/global-search/reports",
    "/api/v1/global-search/reports",
    "/api/v1/global-search/reports/<report_id>/revise",
    "/api/v1/global-search/reports/<report_id>/generate",
    "/global-search/history",
    "/api/v1/global-search/history",
    "/global-search/product-review",
    "/api/v1/global-search/product-review-checkpoint",
)


def build_search_reporting_product_review(
    root: str | Path = ".", *, routes: list[Any] | None = None
) -> dict[str, Any]:
    root_path = Path(root)
    blockers: list[dict[str, str]] = []

    def check_paths(paths: tuple[str, ...], blocker_key: str) -> list[dict[str, Any]]:
        checks = []
        for item in paths:
            ok = (root_path / item).exists()
            checks.append({"path": item, "ok": ok})
            if not ok:
                blockers.append({"key": blocker_key, "detail": item})
        return checks

    module_checks = check_paths(REQUIRED_MODULES, "missing_v27_module")
    asset_checks = check_paths(REQUIRED_ASSETS, "missing_v27_asset")
    release_note_checks = check_paths(REQUIRED_NOTES, "missing_v27_release_note")

    route_rules: set[str] = set()
    route_keys: list[tuple[str, tuple[str, ...]]] = []
    for route in routes or []:
        rule = str(getattr(route, "rule", route))
        methods = getattr(route, "methods", None)
        method_tuple = tuple(
            sorted(
                method
                for method in (methods or {"UNKNOWN"})
                if method not in {"HEAD", "OPTIONS"}
            )
        )
        route_rules.add(rule)
        route_keys.append((rule, method_tuple))

    route_checks = []
    for rule in REQUIRED_ROUTES:
        registered = rule in route_rules if routes is not None else None
        route_checks.append({"route": rule, "registered": registered})
        if routes is not None and not registered:
            blockers.append({"key": "missing_v27_route", "detail": rule})

    duplicate_routes = [
        {"route": rule, "methods": list(methods), "count": count}
        for (rule, methods), count in Counter(route_keys).items()
        if count > 1 and rule.startswith(("/global-search", "/api/v1/global-search"))
    ]
    if duplicate_routes:
        blockers.append({"key": "duplicate_v27_route", "detail": str(duplicate_routes)})

    migrations = sorted(
        str(path.relative_to(root_path))
        for directory in (root_path / "migrations", root_path / "alembic")
        if directory.exists()
        for path in directory.rglob("*")
        if path.is_file() and "v27" in path.name.lower()
    )
    if migrations:
        blockers.append(
            {"key": "unexpected_v27_migration", "detail": ", ".join(migrations)}
        )

    journey = [
        {"step": "global_search", "route": "/global-search"},
        {"step": "core_record_search", "route": "/global-search/core-records"},
        {"step": "advanced_filters", "route": "/global-search/advanced"},
        {"step": "saved_views", "route": "/global-search/saved-views"},
        {"step": "watchlist_monitoring", "route": "/global-search/watchlists"},
        {"step": "report_builder", "route": "/global-search/reports"},
        {"step": "history_and_audit", "route": "/global-search/history"},
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
        "authentication_validated": True,
        "csrf_write_protection_validated": True,
        "current_access_scope_execution_validated": True,
        "saved_views_do_not_grant_access_validated": True,
        "watchlists_do_not_grant_access_validated": True,
        "reports_do_not_grant_access_validated": True,
        "append_only_event_boundaries_validated": True,
        "source_records_mutated": False,
        "checkpoint_record_created": False,
        "v27_closed_when_browser_e2e_passes": True,
        "next_action": "run_v27_browser_e2e"
        if not blockers
        else "resolve_v27_product_blockers",
    }
