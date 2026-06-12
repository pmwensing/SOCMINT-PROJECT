from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any


CASE_DELIVERY_RECOVERY_CHAIN_CLOSURE_AUDIT_SCHEMA = "socmint.case_delivery_recovery_chain_closure_audit.v16_18"
VERSION = "v16.18.0"

CHAIN_STAGES = (
    {
        "version": "v16.3",
        "module": "src/socmint/case_delivery_recovery_v16_3.py",
        "route": "/api/v1/case-delivery/<case_id>/recovery",
        "release_note": "release/V16_3_DELIVERY_RECOVERY_LAYER.md",
        "changelog_label": "v16.3 Delivery Recovery / Retry Resolution Layer",
    },
    {
        "version": "v16.4",
        "module": "src/socmint/case_delivery_recovery_action_receipt_v16_4.py",
        "route": "/api/v1/case-delivery/<case_id>/recovery-action-receipt",
        "release_note": "release/V16_4_DELIVERY_RECOVERY_ACTION_RECEIPT.md",
        "changelog_label": "v16.4 Delivery Recovery Action Receipt",
    },
    {
        "version": "v16.5",
        "module": "src/socmint/case_delivery_recovery_action_receipt_verification_v16_5.py",
        "route": "/api/v1/case-delivery/<case_id>/recovery-action-receipt/verify",
        "release_note": "release/V16_5_DELIVERY_RECOVERY_ACTION_RECEIPT_VERIFICATION.md",
        "changelog_label": "v16.5 Delivery Recovery Action Receipt Verification",
    },
    {
        "version": "v16.6",
        "module": "src/socmint/case_delivery_recovery_closure_record_v16_6.py",
        "route": "/api/v1/case-delivery/<case_id>/recovery-closure-record",
        "release_note": "release/V16_6_DELIVERY_RECOVERY_CLOSURE_RECORD.md",
        "changelog_label": "v16.6 Delivery Recovery Closure Record",
    },
    {
        "version": "v16.7",
        "module": "src/socmint/case_delivery_recovery_closure_record_verification_v16_7.py",
        "route": "/api/v1/case-delivery/<case_id>/recovery-closure-record/verify",
        "release_note": "release/V16_7_DELIVERY_RECOVERY_CLOSURE_RECORD_VERIFICATION.md",
        "changelog_label": "v16.7 Delivery Recovery Closure Record Verification",
    },
    {
        "version": "v16.8",
        "module": "src/socmint/case_delivery_recovery_closure_audit_package_v16_8.py",
        "route": "/api/v1/case-delivery/<case_id>/recovery-closure-audit-package",
        "release_note": "release/V16_8_DELIVERY_RECOVERY_CLOSURE_AUDIT_PACKAGE.md",
        "changelog_label": "v16.8 Delivery Recovery Closure Audit Package",
    },
    {
        "version": "v16.9",
        "module": "src/socmint/case_delivery_recovery_closure_audit_package_verification_v16_9.py",
        "route": "/api/v1/case-delivery/<case_id>/recovery-closure-audit-package/verify",
        "release_note": "release/V16_9_DELIVERY_RECOVERY_CLOSURE_AUDIT_PACKAGE_VERIFICATION.md",
        "changelog_label": "v16.9 Delivery Recovery Closure Audit Package Verification",
    },
    {
        "version": "v16.10",
        "module": "src/socmint/case_delivery_recovery_finalization_record_v16_10.py",
        "route": "/api/v1/case-delivery/<case_id>/recovery-finalization-record",
        "release_note": "release/V16_10_DELIVERY_RECOVERY_FINALIZATION_RECORD.md",
        "changelog_label": "v16.10 Delivery Recovery Finalization Record",
    },
    {
        "version": "v16.11",
        "module": "src/socmint/case_delivery_recovery_finalization_record_verification_v16_11.py",
        "route": "/api/v1/case-delivery/<case_id>/recovery-finalization-record/verify",
        "release_note": "release/V16_11_DELIVERY_RECOVERY_FINALIZATION_RECORD_VERIFICATION.md",
        "changelog_label": "v16.11 Delivery Recovery Finalization Record Verification",
    },
    {
        "version": "v16.12",
        "module": "src/socmint/case_delivery_recovery_continuation_gate_v16_12.py",
        "route": "/api/v1/case-delivery/<case_id>/recovery-continuation-gate",
        "release_note": "release/V16_12_DELIVERY_RECOVERY_CONTINUATION_GATE.md",
        "changelog_label": "v16.12 Delivery Recovery Continuation Gate",
    },
    {
        "version": "v16.13",
        "module": "src/socmint/case_delivery_recovery_continuation_gate_verification_v16_13.py",
        "route": "/api/v1/case-delivery/<case_id>/recovery-continuation-gate/verify",
        "release_note": "release/V16_13_DELIVERY_RECOVERY_CONTINUATION_GATE_VERIFICATION.md",
        "changelog_label": "v16.13 Delivery Recovery Continuation Gate Verification",
    },
    {
        "version": "v16.14",
        "module": "src/socmint/case_delivery_recovery_resume_operations_snapshot_v16_14.py",
        "route": "/api/v1/case-delivery/<case_id>/recovery-resume-operations-snapshot",
        "release_note": "release/V16_14_DELIVERY_RECOVERY_RESUME_OPERATIONS_SNAPSHOT.md",
        "changelog_label": "v16.14 Delivery Recovery Resume Operations Snapshot",
    },
    {
        "version": "v16.15",
        "module": "src/socmint/case_delivery_recovery_resume_operations_snapshot_verification_v16_15.py",
        "route": "/api/v1/case-delivery/<case_id>/recovery-resume-operations-snapshot/verify",
        "release_note": "release/V16_15_DELIVERY_RECOVERY_RESUME_OPERATIONS_SNAPSHOT_VERIFICATION.md",
        "changelog_label": "v16.15 Delivery Recovery Resume Operations Snapshot Verification",
    },
    {
        "version": "v16.16",
        "module": "src/socmint/case_delivery_operations_reentry_envelope_v16_16.py",
        "route": "/api/v1/case-delivery/<case_id>/operations-reentry-envelope",
        "release_note": "release/V16_16_DELIVERY_OPERATIONS_REENTRY_ENVELOPE.md",
        "changelog_label": "v16.16 Delivery Operations Re-Entry Envelope",
    },
    {
        "version": "v16.17",
        "module": "src/socmint/case_delivery_operations_reentry_envelope_verification_v16_17.py",
        "route": "/api/v1/case-delivery/<case_id>/operations-reentry-envelope/verify",
        "release_note": "release/V16_17_DELIVERY_OPERATIONS_REENTRY_ENVELOPE_VERIFICATION.md",
        "changelog_label": "v16.17 Delivery Operations Re-Entry Envelope Verification",
    },
)

OPERATIONS_RETURN_ROUTE = "/api/v1/case-delivery/<case_id>/operations"


def _exists(root: Path, relative_path: str) -> bool:
    return (root / relative_path).exists()


def _read_text(root: Path, relative_path: str) -> str:
    path = root / relative_path
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _route_rules(routes: list[Any] | None) -> list[str]:
    if not routes:
        return []
    return [str(getattr(route, "rule", route)) for route in routes]


def _route_keys(routes: list[Any] | None) -> list[tuple[str, tuple[str, ...]]]:
    keys = []
    for route in routes or []:
        rule = str(getattr(route, "rule", route))
        methods = getattr(route, "methods", None)
        if methods is None:
            methods_tuple = ("UNKNOWN",)
        else:
            methods_tuple = tuple(sorted(method for method in methods if method not in {"HEAD", "OPTIONS"}))
        keys.append((rule, methods_tuple))
    return keys


def audit_case_delivery_recovery_chain_closure(root: str | Path = ".", routes: list[Any] | None = None) -> dict[str, Any]:
    root_path = Path(root)
    route_rules = set(_route_rules(routes))
    route_counts = Counter(_route_keys(routes))
    changelog = _read_text(root_path, "CHANGELOG.md")
    blockers: list[dict[str, str]] = []
    stages = []

    for stage in CHAIN_STAGES:
        module_exists = _exists(root_path, stage["module"])
        release_note_exists = _exists(root_path, stage["release_note"])
        route_registered = stage["route"] in route_rules if routes is not None else None
        changelog_present = stage["changelog_label"] in changelog
        stage_result = {
            **stage,
            "module_exists": module_exists,
            "route_registered": route_registered,
            "release_note_exists": release_note_exists,
            "changelog_present": changelog_present,
        }
        stages.append(stage_result)
        if not module_exists:
            blockers.append({"key": "missing_module", "detail": stage["module"]})
        if routes is not None and not route_registered:
            blockers.append({"key": "missing_route", "detail": stage["route"]})
        if not release_note_exists:
            blockers.append({"key": "missing_release_note", "detail": stage["release_note"]})
        if not changelog_present:
            blockers.append({"key": "missing_changelog_entry", "detail": stage["changelog_label"]})

    operations_route_registered = OPERATIONS_RETURN_ROUTE in route_rules if routes is not None else None
    if routes is not None and not operations_route_registered:
        blockers.append({"key": "operations_return_route_missing", "detail": OPERATIONS_RETURN_ROUTE})

    duplicate_routes = [
        {"route": rule, "methods": list(methods), "count": count}
        for (rule, methods), count in sorted(route_counts.items())
        if count > 1 and rule.startswith("/api/v1/case-delivery/")
    ]
    if duplicate_routes:
        blockers.append({"key": "duplicate_route_drift", "detail": f"{len(duplicate_routes)} duplicate case-delivery routes"})

    migration_candidates = sorted(
        str(path.relative_to(root_path))
        for migrations_root in (root_path / "migrations", root_path / "alembic")
        if migrations_root.exists()
        for path in migrations_root.rglob("*")
        if path.is_file() and ("v16_" in path.name or "recovery" in path.name or "reentry" in path.name)
    )
    if migration_candidates:
        blockers.append({"key": "unexpected_migration_artifact", "detail": ", ".join(migration_candidates)})

    orphaned_artifacts = [
        stage["version"]
        for stage in stages
        if not (stage["module_exists"] and stage["release_note_exists"] and stage["changelog_present"])
        or (routes is not None and not stage["route_registered"])
    ]
    if orphaned_artifacts:
        blockers.append({"key": "orphaned_recovery_artifacts", "detail": ", ".join(orphaned_artifacts)})

    status = "closed" if not blockers else "blocked"
    return {
        "schema": CASE_DELIVERY_RECOVERY_CHAIN_CLOSURE_AUDIT_SCHEMA,
        "version": VERSION,
        "status": status,
        "closed": not blockers,
        "stage_count": len(CHAIN_STAGES),
        "stages": stages,
        "operations_return_route": OPERATIONS_RETURN_ROUTE,
        "operations_return_route_registered": operations_route_registered,
        "duplicate_routes": duplicate_routes,
        "migration_artifacts": migration_candidates,
        "orphaned_artifacts": orphaned_artifacts,
        "blocker_count": len(blockers),
        "blockers": blockers,
        "next_action": "return_to_product_level_work" if not blockers else "resolve_recovery_chain_closure_blockers",
    }


def audit_case_delivery_recovery_chain_closure_from_request(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    safe_payload = payload or {}
    root = safe_payload.get("root", ".") if isinstance(safe_payload, dict) else "."
    return audit_case_delivery_recovery_chain_closure(root=root)
