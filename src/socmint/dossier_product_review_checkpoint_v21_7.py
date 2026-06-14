from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

SCHEMA = "socmint.dossier_product_review_checkpoint.v21_7"
VERSION = "v21.7.0"

REQUIRED_MODULES = (
    "src/socmint/dossier_assembly_workspace_v21_0.py",
    "src/socmint/dossier_package_import_v21_1.py",
    "src/socmint/dossier_section_builder_v21_2.py",
    "src/socmint/dossier_citation_mapping_v21_3.py",
    "src/socmint/dossier_quality_review_v21_4.py",
    "src/socmint/dossier_supervisor_approval_v21_5.py",
    "src/socmint/dossier_final_export_package_v21_6.py",
)
REQUIRED_ASSETS = (
    "src/socmint/templates/dossier_assembly_workspace_v21_0.html",
    "src/socmint/templates/dossier_citation_mapping_v21_3.html",
    "src/socmint/templates/dossier_quality_review_v21_4.html",
    "src/socmint/templates/dossier_supervisor_approval_v21_5.html",
    "src/socmint/templates/dossier_final_export_v21_6.html",
    "scripts/run_v21_7_dossier_browser_e2e.py",
)
REQUIRED_NOTES = (
    "release/V21_0_DOSSIER_ASSEMBLY_WORKSPACE.md",
    "release/V21_1_IMPORT_APPROVED_FINDINGS_PACKAGE.md",
    "release/V21_2_DOSSIER_SECTION_BUILDER.md",
    "release/V21_3_SOURCE_EVIDENCE_CITATION_MAPPING.md",
    "release/V21_4_DOSSIER_QUALITY_COMPLETENESS_REVIEW.md",
    "release/V21_5_SUPERVISOR_DOSSIER_APPROVAL.md",
    "release/V21_6_PACKAGE_GENERATION.md",
)
REQUIRED_ROUTES = (
    "/dossier-assembly/<case_id>",
    "/api/v1/dossier-assembly/<case_id>/package-import",
    "/api/v1/dossier-assembly/<case_id>/arrangement",
    "/api/v1/dossier-assembly/<case_id>/draft",
    "/dossier-assembly/<case_id>/citations",
    "/api/v1/dossier-assembly/<case_id>/citations",
    "/dossier-assembly/<case_id>/quality-review",
    "/api/v1/dossier-assembly/<case_id>/quality-review",
    "/dossier-assembly/<case_id>/supervisor-approval",
    "/api/v1/dossier-assembly/<case_id>/supervisor-decision",
    "/dossier-assembly/<case_id>/final-export",
    "/api/v1/dossier-assembly/<case_id>/final-export",
)


def build_dossier_product_review_checkpoint(
    root: str | Path = ".", *, routes: list[Any] | None = None
) -> dict[str, Any]:
    root_path = Path(root)
    blockers: list[dict[str, str]] = []

    def checks(paths: tuple[str, ...], blocker: str) -> list[dict[str, Any]]:
        result = []
        for item in paths:
            ok = (root_path / item).exists()
            result.append({"path": item, "ok": ok})
            if not ok:
                blockers.append({"key": blocker, "detail": item})
        return result

    module_checks = checks(REQUIRED_MODULES, "missing_v21_module")
    asset_checks = checks(REQUIRED_ASSETS, "missing_v21_asset")
    release_note_checks = checks(REQUIRED_NOTES, "missing_v21_release_note")

    route_checks = []
    route_keys: list[tuple[str, tuple[str, ...]]] = []
    route_rules = set()
    for route in routes or []:
        rule = str(getattr(route, "rule", route))
        methods = getattr(route, "methods", None)
        method_tuple = tuple(sorted(
            item for item in (methods or {"UNKNOWN"})
            if item not in {"HEAD", "OPTIONS"}
        ))
        route_rules.add(rule)
        route_keys.append((rule, method_tuple))
    for route in REQUIRED_ROUTES:
        registered = route in route_rules if routes is not None else None
        route_checks.append({"route": route, "registered": registered})
        if routes is not None and not registered:
            blockers.append({"key": "missing_v21_route", "detail": route})

    duplicate_routes = [
        {"route": rule, "methods": list(methods), "count": count}
        for (rule, methods), count in Counter(route_keys).items()
        if count > 1 and rule.startswith(("/dossier-assembly", "/api/v1/dossier-assembly"))
    ]
    if duplicate_routes:
        blockers.append({"key": "duplicate_v21_route", "detail": str(duplicate_routes)})

    migrations = sorted(
        str(path.relative_to(root_path))
        for directory in (root_path / "migrations", root_path / "alembic")
        if directory.exists()
        for path in directory.rglob("*")
        if path.is_file() and "v21" in path.name.lower()
    )
    if migrations:
        blockers.append({"key": "unexpected_v21_migration", "detail": ", ".join(migrations)})

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
        "next_action": "run_v21_browser_e2e" if not blockers else "resolve_v21_product_blockers",
    }
