from __future__ import annotations

from collections import Counter
from typing import Any

from .collection_job_contract_v29_1 import (
    FAILURE_STATES,
    STATES,
    current_contracts,
    history,
)

SCHEMA = "socmint.collection_job_workspace.v29_1"
VERSION = "v29.1.0"


def build_collection_job_workspace() -> dict[str, Any]:
    contracts = current_contracts()
    events = history()
    state_counts = Counter(
        str(item.get("current_state") or "unknown") for item in contracts
    )
    retryable = [
        item
        for item in contracts
        if item.get("current_state") in FAILURE_STATES and item.get("retry_eligible")
    ]
    blocked = [item for item in contracts if item.get("current_state") == "blocked"]
    unresolved = [
        item
        for item in contracts
        if item.get("current_state") not in {"completed", "cancelled", "superseded"}
    ]
    findings = []
    for item in contracts:
        if not item.get("authorization_binding"):
            findings.append(
                {
                    "severity": "high",
                    "key": "missing_authorization_binding",
                    "collection_job_id": item.get("collection_job_id"),
                }
            )
        if not item.get("idempotency_key"):
            findings.append(
                {
                    "severity": "high",
                    "key": "missing_idempotency_key",
                    "collection_job_id": item.get("collection_job_id"),
                }
            )
        if not any((item.get("case_id"), item.get("entity_id"), item.get("source_id"))):
            findings.append(
                {
                    "severity": "medium",
                    "key": "missing_collection_scope_binding",
                    "collection_job_id": item.get("collection_job_id"),
                }
            )
        if item.get("current_state") in FAILURE_STATES and not item.get(
            "failure_category"
        ):
            findings.append(
                {
                    "severity": "high",
                    "key": "missing_failure_category",
                    "collection_job_id": item.get("collection_job_id"),
                }
            )
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "ready",
        "states": list(STATES),
        "contracts": contracts,
        "contract_count": len(contracts),
        "state_counts": dict(sorted(state_counts.items())),
        "retryable_contracts": retryable,
        "retryable_contract_count": len(retryable),
        "blocked_contracts": blocked,
        "blocked_contract_count": len(blocked),
        "unresolved_contracts": unresolved,
        "unresolved_contract_count": len(unresolved),
        "contract_findings": findings,
        "contract_finding_count": len(findings),
        "collection_job_history": events[-250:],
        "collection_job_event_count": len(events),
        "append_only": True,
        "legacy_scan_jobs_mutated": False,
        "connector_execution_available": False,
        "retry_execution_available": False,
        "case_access_scope_changed": False,
        "next_action": "review_collection_job_contracts",
    }
