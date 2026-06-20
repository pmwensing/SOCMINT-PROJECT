from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from .case_delivery_operations_v16_0 import build_case_delivery_operations_from_request
from .case_delivery_recovery_chain_closure_audit_v16_18 import (
    audit_case_delivery_recovery_chain_closure,
)
from .case_delivery_workspace_v15 import build_case_delivery_workspace_from_request
from .operator_release_console_v14 import operator_release_console_payload


UNIFIED_OPERATOR_WORKFLOW_DASHBOARD_SCHEMA = (
    "socmint.unified_operator_workflow_dashboard.v17_1"
)
VERSION = "v17.1.0"


def _blocker(source: str, key: str, detail: str) -> dict[str, str]:
    return {"source": source, "key": key, "detail": detail}


def _workspace_blockers(workspace: dict[str, Any]) -> list[dict[str, str]]:
    gate = workspace.get("gate") if isinstance(workspace.get("gate"), dict) else {}
    checks = gate.get("checks") if isinstance(gate.get("checks"), list) else []
    return [
        _blocker(
            "case_delivery",
            str(check.get("key") or "delivery_gate"),
            str(check.get("detail") or "blocked"),
        )
        for check in checks
        if isinstance(check, dict) and not check.get("ok")
    ]


def _operations_blockers(operations: dict[str, Any]) -> list[dict[str, str]]:
    blockers = (
        operations.get("blockers")
        if isinstance(operations.get("blockers"), list)
        else []
    )
    return [
        _blocker(
            "operations",
            str(item.get("key") or "operations_blocker"),
            str(item.get("detail") or item.get("reason") or "blocked"),
        )
        for item in blockers
        if isinstance(item, dict)
    ]


def _recommended_action(
    workspace: dict[str, Any],
    recovery_chain: dict[str, Any],
    operations: dict[str, Any],
    release_console: dict[str, Any],
) -> dict[str, str]:
    gate = workspace.get("gate") if isinstance(workspace.get("gate"), dict) else {}
    if gate.get("status") != "pass":
        return {
            "key": str(gate.get("next_action") or "resolve_case_delivery_gate"),
            "label": "Resolve case-delivery readiness blockers",
            "href": f"/case-delivery?case_id={workspace.get('case_id')}",
            "source": "case_delivery",
        }
    if recovery_chain.get("status") != "closed":
        return {
            "key": "resolve_recovery_chain_closure_blockers",
            "label": "Resolve recovery-chain closure blockers",
            "href": f"/api/v1/case-delivery/{workspace.get('case_id')}/recovery-chain-closure-audit",
            "source": "recovery_chain",
        }
    if not operations.get("dispatchable"):
        return {
            "key": str(operations.get("next_action") or "prepare_delivery_operations"),
            "label": "Prepare normal delivery operations",
            "href": f"/api/v1/case-delivery/{workspace.get('case_id')}/operations",
            "source": "operations",
        }
    evaluation = (
        release_console.get("evaluation")
        if isinstance(release_console.get("evaluation"), dict)
        else {}
    )
    if evaluation.get("decision") == "REFRESH_RELEASE_HEALTH":
        return {
            "key": "refresh_release_health",
            "label": "Refresh operator release health",
            "href": "/operator/release-console",
            "source": "release_console",
        }
    if (
        evaluation.get("decision") == "PAUSE_FOR_REPAIR"
        or release_console.get("status") == "needs_review"
    ):
        return {
            "key": "repair_release_console_blockers",
            "label": "Repair release-console blockers",
            "href": "/operator/release-console",
            "source": "release_console",
        }
    return {
        "key": "dispatch_delivery_operations",
        "label": "Dispatch delivery operations",
        "href": f"/api/v1/case-delivery/{workspace.get('case_id')}/operations",
        "source": "operations",
    }


def build_unified_operator_workflow_dashboard(
    case_id: str,
    payload: dict[str, Any] | None = None,
    *,
    root: str | Path = ".",
    routes: list[Any] | None = None,
) -> dict[str, Any]:
    safe_payload = deepcopy(payload or {})
    root_path = Path(root)
    workspace = build_case_delivery_workspace_from_request(case_id, safe_payload)
    operations = (
        deepcopy(safe_payload["operations"])
        if isinstance(safe_payload.get("operations"), dict)
        else build_case_delivery_operations_from_request(case_id, safe_payload)
    )
    recovery_chain = audit_case_delivery_recovery_chain_closure(
        root=root_path, routes=routes
    )
    release_console = operator_release_console_payload(root_path)

    blockers = _workspace_blockers(workspace) + _operations_blockers(operations)
    blockers.extend(
        _blocker(
            "recovery_chain",
            str(item.get("key") or "recovery_chain"),
            str(item.get("detail") or "blocked"),
        )
        for item in recovery_chain.get("blockers", [])
        if isinstance(item, dict)
    )
    blockers.extend(
        _blocker(
            "release_console",
            str(item.get("key") or "release_console"),
            str(item.get("detail") or "needs review"),
        )
        for item in release_console.get("evaluation", {}).get("blockers", [])
        if isinstance(item, dict)
    )

    case_ready = workspace.get("gate", {}).get("status") == "pass"
    recovery_closed = recovery_chain.get("status") == "closed"
    operations_ready = bool(operations.get("dispatchable"))
    release_health = (
        release_console.get("release_health")
        if isinstance(release_console.get("release_health"), dict)
        else {}
    )
    release_health_state = (
        release_health.get("freshness", {}).get("status")
        or release_health.get("status")
        or "unknown"
    )
    action = _recommended_action(workspace, recovery_chain, operations, release_console)

    return {
        "schema": UNIFIED_OPERATOR_WORKFLOW_DASHBOARD_SCHEMA,
        "version": VERSION,
        "case_id": case_id,
        "status": "ready"
        if case_ready and recovery_closed and operations_ready
        else "attention_required",
        "summary": {
            "case_delivery_ready": case_ready,
            "recovery_chain_closed": recovery_closed,
            "operations_dispatchable": operations_ready,
            "release_health": release_health_state,
            "blocker_count": len(blockers),
        },
        "case_delivery": {
            "decision": workspace.get("gate", {}).get("decision"),
            "status": workspace.get("gate", {}).get("status"),
            "next_action": workspace.get("gate", {}).get("next_action"),
            "href": f"/case-delivery?case_id={case_id}",
            "payload": workspace,
        },
        "recovery_chain": {
            "status": recovery_chain.get("status"),
            "closed": recovery_chain.get("closed"),
            "stage_count": recovery_chain.get("stage_count"),
            "next_action": recovery_chain.get("next_action"),
            "payload": recovery_chain,
        },
        "operations": {
            "state": operations.get("state"),
            "dispatchable": bool(operations.get("dispatchable")),
            "next_action": operations.get("next_action"),
            "payload": operations,
        },
        "release_console": {
            "status": release_console.get("status"),
            "decision": release_console.get("decision"),
            "evaluation": release_console.get("evaluation"),
            "release_health": release_health,
            "href": "/operator/release-console",
        },
        "blockers": blockers,
        "recommended_action": action,
        "next_action": action["key"],
    }


def build_unified_operator_workflow_dashboard_from_request(
    case_id: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return build_unified_operator_workflow_dashboard(case_id, payload)
