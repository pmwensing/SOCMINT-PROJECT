from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from .case_delivery_recovery_chain_closure_audit_v16_18 import audit_case_delivery_recovery_chain_closure


PRODUCT_READINESS_OPERATOR_WORKFLOW_SCHEMA = "socmint.product_readiness_operator_workflow.v17_0"
VERSION = "v17.0.0"
NEXT_ACTION = "resume_product_level_delivery_work"

PRODUCT_ROUTES = (
    "/case-delivery",
    "/api/v1/case-delivery/<case_id>",
    "/api/v1/case-delivery/<case_id>/operations",
    "/api/v1/case-delivery/<case_id>/recovery-chain-closure-audit",
    "/api/v1/operator/release-console",
    "/operator/release-console",
)

PRODUCT_MODULES = (
    "src/socmint/case_delivery_workspace_v15.py",
    "src/socmint/case_delivery_workspace_routes_v15.py",
    "src/socmint/case_delivery_operations_v16_0.py",
    "src/socmint/case_delivery_recovery_chain_closure_audit_v16_18.py",
    "src/socmint/operator_release_console_v14.py",
    "src/socmint/operator_release_console_routes_v14.py",
)

PRODUCT_RELEASE_NOTES = (
    "release/V16_18_RECOVERY_CHAIN_CLOSURE_AUDIT.md",
    "release/V17_0_PRODUCT_READINESS_OPERATOR_WORKFLOW_INTEGRATION.md",
)

PRODUCT_CHANGELOG_LABEL = "v17.0 Product Readiness / Operator Workflow Integration"


def _blocker(key: str, detail: str) -> dict[str, str]:
    return {"key": key, "detail": detail}


def _route_rules(routes: list[Any] | None) -> set[str]:
    return {str(getattr(route, "rule", route)) for route in routes or []}


def _route_keys(routes: list[Any] | None) -> list[tuple[str, tuple[str, ...]]]:
    keys = []
    for route in routes or []:
        rule = str(getattr(route, "rule", route))
        methods = getattr(route, "methods", None)
        methods_tuple = ("UNKNOWN",) if methods is None else tuple(sorted(method for method in methods if method not in {"HEAD", "OPTIONS"}))
        keys.append((rule, methods_tuple))
    return keys


def _exists(root: Path, relative_path: str) -> bool:
    return (root / relative_path).exists()


def _read(root: Path, relative_path: str) -> str:
    path = root / relative_path
    return path.read_text(encoding="utf-8") if path.exists() else ""


def build_product_readiness_operator_workflow_snapshot(root: str | Path = ".", routes: list[Any] | None = None) -> dict[str, Any]:
    root_path = Path(root)
    route_rules = _route_rules(routes)
    route_counts = Counter(_route_keys(routes))
    changelog = _read(root_path, "CHANGELOG.md")
    recovery_chain = audit_case_delivery_recovery_chain_closure(root=root_path, routes=routes)
    blockers: list[dict[str, str]] = []

    module_checks = []
    for module in PRODUCT_MODULES:
        ok = _exists(root_path, module)
        module_checks.append({"module": module, "ok": ok})
        if not ok:
            blockers.append(_blocker("missing_product_module", module))

    route_checks = []
    for route in PRODUCT_ROUTES:
        ok = route in route_rules if routes is not None else None
        route_checks.append({"route": route, "registered": ok})
        if routes is not None and not ok:
            blockers.append(_blocker("missing_product_route", route))

    release_note_checks = []
    for note in PRODUCT_RELEASE_NOTES:
        ok = _exists(root_path, note)
        release_note_checks.append({"release_note": note, "ok": ok})
        if not ok:
            blockers.append(_blocker("missing_product_release_note", note))

    changelog_present = PRODUCT_CHANGELOG_LABEL in changelog
    if not changelog_present:
        blockers.append(_blocker("missing_product_changelog_entry", PRODUCT_CHANGELOG_LABEL))

    duplicate_routes = [
        {"route": rule, "methods": list(methods), "count": count}
        for (rule, methods), count in sorted(route_counts.items())
        if count > 1 and (rule.startswith("/api/v1/case-delivery/") or rule.startswith("/api/v1/operator/"))
    ]
    if duplicate_routes:
        blockers.append(_blocker("duplicate_product_route_drift", f"{len(duplicate_routes)} duplicate product routes"))

    if recovery_chain.get("status") != "closed":
        blockers.append(_blocker("recovery_chain_not_closed", "v16.18 recovery chain closure audit is not closed"))

    operations_route_ready = "/api/v1/case-delivery/<case_id>/operations" in route_rules if routes is not None else None
    release_console_ready = "/api/v1/operator/release-console" in route_rules if routes is not None else None
    case_delivery_ux_ready = "/case-delivery" in route_rules and "/api/v1/case-delivery/<case_id>" in route_rules if routes is not None else None
    end_to_end_ready = not blockers and recovery_chain.get("closed") is True and operations_route_ready is True

    status = "ready" if end_to_end_ready else "blocked"
    return {
        "schema": PRODUCT_READINESS_OPERATOR_WORKFLOW_SCHEMA,
        "version": VERSION,
        "status": status,
        "ready": status == "ready",
        "operator_workflow_ready": case_delivery_ux_ready is True and release_console_ready is True,
        "case_delivery_ux_ready": case_delivery_ux_ready,
        "release_console_aligned": release_console_ready,
        "operations_route_ready": operations_route_ready,
        "recovery_chain_closed": recovery_chain.get("closed") is True,
        "end_to_end_ready": end_to_end_ready,
        "module_checks": module_checks,
        "route_checks": route_checks,
        "release_note_checks": release_note_checks,
        "changelog_present": changelog_present,
        "duplicate_routes": duplicate_routes,
        "recovery_chain": recovery_chain,
        "blocker_count": len(blockers),
        "blockers": blockers,
        "next_action": NEXT_ACTION if status == "ready" else "resolve_product_readiness_blockers",
    }


def build_product_readiness_operator_workflow_snapshot_from_request(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    safe_payload = payload or {}
    root = safe_payload.get("root", ".") if isinstance(safe_payload, dict) else "."
    return build_product_readiness_operator_workflow_snapshot(root=root)
