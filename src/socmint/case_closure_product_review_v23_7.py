from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

SCHEMA = "socmint.case_closure_product_review.v23_7"
VERSION = "v23.7.0"

REQUIRED_MODULES = (
    "src/socmint/case_closure_workspace_v23_0.py",
    "src/socmint/case_closure_readiness_review_v23_1.py",
    "src/socmint/case_closure_decision_v23_2.py",
    "src/socmint/case_retention_assignment_v23_3.py",
    "src/socmint/case_archive_package_v23_4.py",
    "src/socmint/case_reopen_control_v23_5.py",
    "src/socmint/case_closure_history_v23_6.py",
)
REQUIRED_ASSETS = (
    "src/socmint/templates/case_closure_workspace_v23_0.html",
    "src/socmint/templates/case_closure_history_v23_6.html",
    "src/socmint/static/case_closure_workspace_v23_0.js",
    "scripts/run_v23_7_case_closure_browser_e2e.py",
)
REQUIRED_NOTES = (
    "release/V23_0_CASE_CLOSURE_WORKSPACE.md",
    "release/V23_1_CLOSURE_READINESS_REVIEW.md",
    "release/V23_2_SUPERVISOR_CLOSURE_DECISION.md",
    "release/V23_3_RETENTION_POLICY_ASSIGNMENT.md",
    "release/V23_4_CASE_ARCHIVE_PACKAGE.md",
    "release/V23_5_REOPEN_CONTROLS.md",
    "release/V23_6_CLOSURE_ARCHIVE_HISTORY.md",
)
REQUIRED_ROUTES = (
    "/case-closure/<case_id>",
    "/api/v1/case-closure/<case_id>",
    "/api/v1/case-closure/<case_id>/readiness-review",
    "/api/v1/case-closure/<case_id>/closure-decision",
    "/api/v1/case-closure/<case_id>/retention-assignment",
    "/api/v1/case-closure/<case_id>/archive-package",
    "/api/v1/case-closure/<case_id>/reopen-request",
    "/api/v1/case-closure/<case_id>/reopen-authorization",
    "/case-closure/<case_id>/history",
    "/api/v1/case-closure/<case_id>/history",
)


def build_case_closure_product_review(
    root: str | Path = ".", *, routes: list[Any] | None = None
) -> dict[str, Any]:
    root_path = Path(root)
    blockers: list[dict[str, str]] = []

    def check_paths(paths: tuple[str, ...], blocker: str) -> list[dict[str, Any]]:
        checks = []
        for item in paths:
            ok = (root_path / item).exists()
            checks.append({"path": item, "ok": ok})
            if not ok:
                blockers.append({"key": blocker, "detail": item})
        return checks

    module_checks = check_paths(REQUIRED_MODULES, "missing_v23_module")
    asset_checks = check_paths(REQUIRED_ASSETS, "missing_v23_asset")
    release_note_checks = check_paths(REQUIRED_NOTES, "missing_v23_release_note")

    route_rules = set()
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
    for route in REQUIRED_ROUTES:
        registered = route in route_rules if routes is not None else None
        route_checks.append({"route": route, "registered": registered})
        if routes is not None and not registered:
            blockers.append({"key": "missing_v23_route", "detail": route})

    duplicate_routes = [
        {"route": rule, "methods": list(methods), "count": count}
        for (rule, methods), count in Counter(route_keys).items()
        if count > 1 and rule.startswith(("/case-closure", "/api/v1/case-closure"))
    ]
    if duplicate_routes:
        blockers.append({"key": "duplicate_v23_route", "detail": str(duplicate_routes)})

    migrations = sorted(
        str(path.relative_to(root_path))
        for directory in (root_path / "migrations", root_path / "alembic")
        if directory.exists()
        for path in directory.rglob("*")
        if path.is_file() and "v23" in path.name.lower()
    )
    if migrations:
        blockers.append(
            {"key": "unexpected_v23_migration", "detail": ", ".join(migrations)}
        )

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
        "next_action": "run_v23_browser_e2e"
        if not blockers
        else "resolve_v23_product_blockers",
    }
