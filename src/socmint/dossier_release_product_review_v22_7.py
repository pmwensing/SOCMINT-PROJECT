from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

SCHEMA = "socmint.dossier_release_product_review.v22_7"
VERSION = "v22.7.0"

REQUIRED_MODULES = (
    "src/socmint/dossier_release_workspace_v22_0.py",
    "src/socmint/dossier_release_authorization_v22_1.py",
    "src/socmint/dossier_release_preview_v22_2.py",
    "src/socmint/dossier_secure_distribution_v22_3.py",
    "src/socmint/dossier_delivery_receipt_v22_4.py",
    "src/socmint/dossier_delivery_recovery_controls_v22_5.py",
    "src/socmint/dossier_release_history_v22_6.py",
)
REQUIRED_ASSETS = (
    "src/socmint/templates/dossier_release_workspace_v22_0.html",
    "src/socmint/templates/dossier_release_history_v22_6.html",
    "src/socmint/static/dossier_release_workspace_v22_0.js",
    "scripts/run_v22_7_dossier_release_browser_e2e.py",
)
REQUIRED_NOTES = (
    "release/V22_0_DOSSIER_RELEASE_WORKSPACE.md",
    "release/V22_1_RECIPIENT_DELIVERY_AUTHORIZATION.md",
    "release/V22_2_RELEASE_PACKAGE_PREVIEW_REDACTION_CHECK.md",
    "release/V22_3_SECURE_DISTRIBUTION_ACTION.md",
    "release/V22_4_DELIVERY_RECEIPT_RECIPIENT_ACKNOWLEDGEMENT.md",
    "release/V22_5_FAILED_DELIVERY_RECALL_REISSUE_CONTROLS.md",
    "release/V22_6_RELEASE_DELIVERY_HISTORY_CASE_CLOSURE_SUMMARY.md",
)
REQUIRED_ROUTES = (
    "/dossier-release/<case_id>",
    "/api/v1/dossier-release/<case_id>/authorize",
    "/api/v1/dossier-release/<case_id>/package-preview",
    "/api/v1/dossier-release/<case_id>/package-preview/acknowledge",
    "/api/v1/dossier-release/<case_id>/distribution-readiness",
    "/api/v1/dossier-release/<case_id>/dispatch",
    "/api/v1/dossier-release/<case_id>/delivery-state",
    "/api/v1/dossier-release/<case_id>/delivery-receipt",
    "/api/v1/dossier-release/<case_id>/recipient-acknowledgement",
    "/api/v1/dossier-release/<case_id>/delivery-recovery",
    "/api/v1/dossier-release/<case_id>/failed-delivery-review",
    "/api/v1/dossier-release/<case_id>/recall",
    "/api/v1/dossier-release/<case_id>/reissue-authorization",
    "/dossier-release/<case_id>/history",
    "/api/v1/dossier-release/<case_id>/history",
)


def build_dossier_release_product_review(
    root: str | Path = ".", *, routes: list[Any] | None = None
) -> dict[str, Any]:
    root_path = Path(root)
    blockers: list[dict[str, str]] = []

    def check_paths(paths: tuple[str, ...], blocker: str) -> list[dict[str, Any]]:
        values = []
        for item in paths:
            ok = (root_path / item).exists()
            values.append({"path": item, "ok": ok})
            if not ok:
                blockers.append({"key": blocker, "detail": item})
        return values

    module_checks = check_paths(REQUIRED_MODULES, "missing_v22_module")
    asset_checks = check_paths(REQUIRED_ASSETS, "missing_v22_asset")
    release_note_checks = check_paths(REQUIRED_NOTES, "missing_v22_release_note")

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
            blockers.append({"key": "missing_v22_route", "detail": route})

    duplicate_routes = [
        {"route": rule, "methods": list(methods), "count": count}
        for (rule, methods), count in Counter(route_keys).items()
        if count > 1
        and rule.startswith(("/dossier-release", "/api/v1/dossier-release"))
    ]
    if duplicate_routes:
        blockers.append({"key": "duplicate_v22_route", "detail": str(duplicate_routes)})

    migrations = sorted(
        str(path.relative_to(root_path))
        for directory in (root_path / "migrations", root_path / "alembic")
        if directory.exists()
        for path in directory.rglob("*")
        if path.is_file() and "v22" in path.name.lower()
    )
    if migrations:
        blockers.append(
            {"key": "unexpected_v22_migration", "detail": ", ".join(migrations)}
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
        "next_action": "run_v22_browser_e2e"
        if not blockers
        else "resolve_v22_product_blockers",
    }
