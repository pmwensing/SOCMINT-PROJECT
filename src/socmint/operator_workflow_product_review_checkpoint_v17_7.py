from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any


OPERATOR_WORKFLOW_PRODUCT_REVIEW_CHECKPOINT_SCHEMA = "socmint.operator_workflow_product_review_checkpoint.v17_7"
VERSION = "v17.7.0"
NEXT_ACTION = "run_browser_e2e_validation"

REQUIRED_MODULES = (
    "src/socmint/product_readiness_operator_workflow_v17_0.py",
    "src/socmint/unified_operator_workflow_dashboard_v17_1.py",
    "src/socmint/operator_workflow_action_launcher_v17_2.py",
    "src/socmint/operator_workflow_action_receipt_v17_3.py",
    "src/socmint/operator_workflow_action_receipt_verification_v17_4.py",
    "src/socmint/operator_action_session_timeline_v17_5.py",
)

REQUIRED_ASSETS = (
    "src/socmint/templates/unified_operator_workflow_dashboard.html",
    "src/socmint/static/operator_workflow_dashboard_v17_6.js",
    "scripts/run_v17_7_operator_dashboard_browser_e2e.py",
)

REQUIRED_ROUTES = (
    "/operator/workflow-dashboard",
    "/api/v1/operator/workflow-dashboard/<case_id>",
    "/api/v1/operator/workflow-dashboard/<case_id>/actions",
    "/api/v1/operator/workflow-dashboard/<case_id>/actions/verify",
    "/api/v1/operator/workflow-dashboard/<case_id>/actions/history",
)

REQUIRED_RELEASE_NOTES = tuple(
    f"release/V17_{index}_{suffix}.md"
    for index, suffix in (
        (0, "PRODUCT_READINESS_OPERATOR_WORKFLOW_INTEGRATION"),
        (1, "UNIFIED_OPERATOR_WORKFLOW_DASHBOARD"),
        (2, "OPERATOR_WORKFLOW_ACTION_LAUNCHER"),
        (3, "OPERATOR_ACTION_RECEIPT_AUDIT_TRAIL"),
        (4, "OPERATOR_ACTION_RECEIPT_VERIFICATION"),
        (5, "OPERATOR_ACTION_HISTORY_SESSION_TIMELINE"),
        (6, "OPERATOR_WORKFLOW_DASHBOARD_UX_HARDENING"),
    )
)


def _blocker(key: str, detail: str) -> dict[str, str]:
    return {"key": key, "detail": detail}


def _route_keys(routes: list[Any] | None) -> list[tuple[str, tuple[str, ...]]]:
    keys = []
    for route in routes or []:
        rule = str(getattr(route, "rule", route))
        methods = getattr(route, "methods", None)
        method_tuple = ("UNKNOWN",) if methods is None else tuple(sorted(item for item in methods if item not in {"HEAD", "OPTIONS"}))
        keys.append((rule, method_tuple))
    return keys


def build_operator_workflow_product_review_checkpoint(
    root: str | Path = ".",
    *,
    routes: list[Any] | None = None,
) -> dict[str, Any]:
    root_path = Path(root)
    route_rules = {str(getattr(route, "rule", route)) for route in routes or []}
    route_counts = Counter(_route_keys(routes))
    changelog_path = root_path / "CHANGELOG.md"
    changelog = changelog_path.read_text(encoding="utf-8") if changelog_path.exists() else ""
    blockers: list[dict[str, str]] = []

    module_checks = []
    for item in REQUIRED_MODULES:
        ok = (root_path / item).exists()
        module_checks.append({"path": item, "ok": ok})
        if not ok:
            blockers.append(_blocker("missing_product_module", item))

    asset_checks = []
    for item in REQUIRED_ASSETS:
        ok = (root_path / item).exists()
        asset_checks.append({"path": item, "ok": ok})
        if not ok:
            blockers.append(_blocker("missing_product_asset", item))

    release_note_checks = []
    for item in REQUIRED_RELEASE_NOTES:
        ok = (root_path / item).exists()
        release_note_checks.append({"path": item, "ok": ok})
        if not ok:
            blockers.append(_blocker("missing_release_note", item))

    route_checks = []
    for item in REQUIRED_ROUTES:
        registered = item in route_rules if routes is not None else None
        route_checks.append({"route": item, "registered": registered})
        if routes is not None and not registered:
            blockers.append(_blocker("missing_operator_workflow_route", item))

    duplicate_routes = [
        {"route": rule, "methods": list(methods), "count": count}
        for (rule, methods), count in sorted(route_counts.items())
        if count > 1 and rule.startswith("/api/v1/operator/workflow-dashboard")
    ]
    if duplicate_routes:
        blockers.append(_blocker("duplicate_operator_workflow_route", str(duplicate_routes)))

    changelog_versions = {}
    for index in range(7):
        token = f"v17.{index}"
        present = token in changelog
        changelog_versions[token] = present
        if not present:
            blockers.append(_blocker("missing_changelog_entry", token))

    migration_artifacts = sorted(
        str(path.relative_to(root_path))
        for directory in (root_path / "migrations", root_path / "alembic")
        if directory.exists()
        for path in directory.rglob("*")
        if path.is_file() and ("v17" in path.name.lower() or "operator_workflow" in path.name.lower())
    )
    if migration_artifacts:
        blockers.append(_blocker("unexpected_v17_migration", ", ".join(migration_artifacts)))

    status = "ready_for_browser_validation" if not blockers else "blocked"
    return {
        "schema": OPERATOR_WORKFLOW_PRODUCT_REVIEW_CHECKPOINT_SCHEMA,
        "version": VERSION,
        "status": status,
        "ready": not blockers,
        "module_checks": module_checks,
        "asset_checks": asset_checks,
        "route_checks": route_checks,
        "release_note_checks": release_note_checks,
        "changelog_versions": changelog_versions,
        "duplicate_routes": duplicate_routes,
        "migration_artifacts": migration_artifacts,
        "blocker_count": len(blockers),
        "blockers": blockers,
        "next_action": NEXT_ACTION if not blockers else "resolve_product_review_blockers",
    }
