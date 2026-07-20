from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any

from . import database
from .durable_execution_ledger_v35_1 import GovernanceExecution
from .execution_reconciliation_read_v35_4 import _execution_payload

SCHEMA = "socmint.execution_recovery_observability.v35_5"
VERSION = "v35.5.0"
DEFAULT_PENDING_THRESHOLD_SECONDS = 30 * 60
DEFAULT_RUNNING_THRESHOLD_SECONDS = 60 * 60
ATTENTION_CLASSIFICATIONS = frozenset(
    {"attention", "integrity_alert", "reconciliation_pending"}
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_aware(value: datetime | str | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _age_seconds(updated_at: datetime | str | None, now: datetime) -> int | None:
    parsed = _as_aware(updated_at)
    if parsed is None:
        return None
    return max(0, int((now - parsed).total_seconds()))


def _age_bucket(age_seconds: int | None) -> str:
    if age_seconds is None:
        return "unknown"
    if age_seconds < 15 * 60:
        return "under_15m"
    if age_seconds < 60 * 60:
        return "15m_to_1h"
    if age_seconds < 24 * 60 * 60:
        return "1h_to_24h"
    if age_seconds < 7 * 24 * 60 * 60:
        return "1d_to_7d"
    return "over_7d"


def _action_family(action: Any) -> str:
    normalized = str(action or "unknown").strip().lower()
    if not normalized:
        return "unknown"
    for marker in ("_", ".", ":"):
        if marker in normalized:
            return normalized.split(marker, 1)[0]
    return normalized


def classify_execution(
    payload: dict[str, Any],
    *,
    now: datetime | None = None,
    pending_threshold_seconds: int = DEFAULT_PENDING_THRESHOLD_SECONDS,
    running_threshold_seconds: int = DEFAULT_RUNNING_THRESHOLD_SECONDS,
) -> dict[str, Any]:
    current_time = now or _utcnow()
    state = str(payload.get("state") or "unknown")
    age = _age_seconds(payload.get("updated_at"), current_time)
    result_exists = payload.get("result_envelope_exists") is True
    ledger_consistent = payload.get("ledger_consistent") is True
    invocation = payload.get("invocation_binding") or {}
    if not isinstance(invocation, dict):
        invocation = {}

    findings: list[str] = []
    classification = "healthy"

    if not ledger_consistent:
        findings.append("ledger_state_mismatch")
        classification = "integrity_alert"

    requires_invocation_binding = state in {
        "running",
        "succeeded",
        "failed",
        "uncertain",
        "reconciled",
    }
    if requires_invocation_binding and not invocation.get("confirmation_issue_audit_id"):
        findings.append("missing_confirmation_issuance_binding")
        classification = "integrity_alert"
    if requires_invocation_binding and not invocation.get("contract_validation_sha256"):
        findings.append("missing_contract_validation_binding")
        classification = "integrity_alert"

    if state in {"succeeded", "reconciled"} and not result_exists:
        findings.append("terminal_result_envelope_missing")
        classification = "integrity_alert"
    if state in {"pending", "running", "uncertain"} and result_exists:
        findings.append("nonterminal_result_envelope_present")
        classification = "integrity_alert"

    if classification != "integrity_alert":
        if state == "reconciled" and result_exists:
            classification = "reconciled"
        elif state == "uncertain" and not result_exists:
            findings.append("authoritative_outcome_requires_reconciliation")
            classification = "reconciliation_pending"
        elif state == "pending" and age is not None and age > pending_threshold_seconds:
            findings.append("pending_threshold_exceeded")
            classification = "attention"
        elif state == "running" and age is not None and age > running_threshold_seconds:
            findings.append("running_threshold_exceeded")
            classification = "attention"
        elif state == "failed" and not str(payload.get("last_reason") or "").strip():
            findings.append("failed_terminal_reason_missing")
            classification = "attention"

    return {
        "classification": classification,
        "findings": findings,
        "age_seconds": age,
        "age_bucket": _age_bucket(age),
        "automatic_retry": False,
        "delegate_invocation_available": False,
        "age_is_diagnostic_only": True,
    }


def _execution_payloads() -> list[dict[str, Any]]:
    database.ensure_configured()
    session = database.Session()
    try:
        rows = (
            session.query(GovernanceExecution)
            .order_by(GovernanceExecution.updated_at.asc(), GovernanceExecution.id.asc())
            .all()
        )
        return [_execution_payload(session, row) for row in rows]
    finally:
        session.close()


def _observed_payloads(
    *,
    now: datetime | None = None,
    pending_threshold_seconds: int = DEFAULT_PENDING_THRESHOLD_SECONDS,
    running_threshold_seconds: int = DEFAULT_RUNNING_THRESHOLD_SECONDS,
) -> list[dict[str, Any]]:
    current_time = now or _utcnow()
    observed = []
    for payload in _execution_payloads():
        observed.append(
            {
                **payload,
                "observability": classify_execution(
                    payload,
                    now=current_time,
                    pending_threshold_seconds=pending_threshold_seconds,
                    running_threshold_seconds=running_threshold_seconds,
                ),
            }
        )
    return observed


def _counter(items: list[dict[str, Any]], key) -> dict[str, int]:
    return dict(sorted(Counter(str(key(item) or "unknown") for item in items).items()))


def recovery_summary(
    *,
    now: datetime | None = None,
    pending_threshold_seconds: int = DEFAULT_PENDING_THRESHOLD_SECONDS,
    running_threshold_seconds: int = DEFAULT_RUNNING_THRESHOLD_SECONDS,
) -> dict[str, Any]:
    items = _observed_payloads(
        now=now,
        pending_threshold_seconds=pending_threshold_seconds,
        running_threshold_seconds=running_threshold_seconds,
    )
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "ready",
        "total": len(items),
        "by_state": _counter(items, lambda item: item.get("state")),
        "by_action": _counter(items, lambda item: item.get("governance_action")),
        "by_action_family": _counter(
            items, lambda item: _action_family(item.get("governance_action"))
        ),
        "by_delegate_service": _counter(items, lambda item: item.get("delegate_service")),
        "by_case": _counter(items, lambda item: item.get("case_id")),
        "by_integrity": _counter(
            items, lambda item: (item.get("observability") or {}).get("classification")
        ),
        "by_age_bucket": _counter(
            items, lambda item: (item.get("observability") or {}).get("age_bucket")
        ),
        "by_result_envelope": {
            "present": sum(1 for item in items if item.get("result_envelope_exists") is True),
            "absent": sum(1 for item in items if item.get("result_envelope_exists") is not True),
        },
        "attention_count": sum(
            1
            for item in items
            if (item.get("observability") or {}).get("classification")
            in ATTENTION_CLASSIFICATIONS
        ),
        "automatic_retry": False,
        "read_only": True,
    }


def attention_queue(
    *,
    limit: int = 200,
    now: datetime | None = None,
    pending_threshold_seconds: int = DEFAULT_PENDING_THRESHOLD_SECONDS,
    running_threshold_seconds: int = DEFAULT_RUNNING_THRESHOLD_SECONDS,
) -> dict[str, Any]:
    safe_limit = max(1, min(int(limit), 500))
    items = [
        item
        for item in _observed_payloads(
            now=now,
            pending_threshold_seconds=pending_threshold_seconds,
            running_threshold_seconds=running_threshold_seconds,
        )
        if (item.get("observability") or {}).get("classification")
        in ATTENTION_CLASSIFICATIONS
    ]
    items.sort(
        key=lambda item: (
            0
            if (item.get("observability") or {}).get("classification")
            == "integrity_alert"
            else 1,
            str(item.get("updated_at") or ""),
            str(item.get("execution_id") or ""),
        )
    )
    entries = [
        {
            "execution_id": item.get("execution_id"),
            "case_id": item.get("case_id"),
            "governance_action": item.get("governance_action"),
            "delegate_service": item.get("delegate_service"),
            "state": item.get("state"),
            "state_version": item.get("state_version"),
            "last_reason": item.get("last_reason"),
            "updated_at": item.get("updated_at"),
            "result_envelope_exists": item.get("result_envelope_exists") is True,
            "observability": item.get("observability"),
        }
        for item in items[:safe_limit]
    ]
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "ready",
        "executions": entries,
        "count": len(entries),
        "total": len(items),
        "limit": safe_limit,
        "automatic_retry": False,
        "read_only": True,
    }


def reconciled_executions(*, limit: int = 200) -> dict[str, Any]:
    safe_limit = max(1, min(int(limit), 500))
    items = [item for item in _observed_payloads() if item.get("state") == "reconciled"]
    items.sort(key=lambda item: str(item.get("updated_at") or ""), reverse=True)
    entries = []
    for item in items[:safe_limit]:
        entries.append(
            {
                "execution_id": item.get("execution_id"),
                "case_id": item.get("case_id"),
                "governance_action": item.get("governance_action"),
                "delegate_service": item.get("delegate_service"),
                "state": item.get("state"),
                "state_version": item.get("state_version"),
                "invocation_binding": item.get("invocation_binding"),
                "uncertain_outcome": item.get("uncertain_outcome"),
                "result_envelope": item.get("result_envelope"),
                "reconciliation_operator_metadata": item.get(
                    "reconciliation_operator_metadata"
                ),
                "updated_at": item.get("updated_at"),
                "observability": item.get("observability"),
            }
        )
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "ready",
        "executions": entries,
        "count": len(entries),
        "total": len(items),
        "limit": safe_limit,
        "automatic_retry": False,
        "read_only": True,
    }


def execution_recovery_workspace() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "ready",
        "summary": recovery_summary(),
        "attention": attention_queue(),
        "reconciled": reconciled_executions(),
        "automatic_retry": False,
        "delegate_invocation_available": False,
        "reconciliation_action_available": False,
        "read_only": True,
    }
