from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from typing import Any

POLICY_COVERAGE_SCHEMA = "socmint.v7_5.policy_coverage"
REQUIRED_OPERATION_TYPES = [
    "dossier_build",
    "dossier_export",
    "connector_run",
    "recursive_run",
    "artifact_upload",
    "artifact_download",
    "retention_run",
]
ALLOWED_DECISIONS = {"allow", "allow_with_warning", "needs_human_review", "block"}


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _operation_name(event: dict[str, Any]) -> str:
    return str(event.get("operation") or event.get("action") or event.get("event_type") or "")


def _decision_value(event: dict[str, Any]) -> str:
    if "decision" in event:
        return str(event.get("decision") or "")
    if "allowed" in event:
        return "allow" if event.get("allowed") else "block"
    return ""


def build_policy_coverage_report(events: list[dict[str, Any]] | None) -> dict[str, Any]:
    events = events or []
    operation_counts: Counter[str] = Counter()
    decision_counts: Counter[str] = Counter()
    findings: list[dict[str, Any]] = []

    for index, event in enumerate(events):
        if not isinstance(event, dict):
            findings.append({"status": "fail", "check": "event_type", "index": index, "detail": "Policy event must be an object."})
            continue
        operation = _operation_name(event)
        decision = _decision_value(event)
        if operation:
            operation_counts[operation] += 1
        if decision:
            decision_counts[decision] += 1
        if not operation:
            findings.append({"status": "fail", "check": "operation", "index": index, "detail": "Policy event is missing operation/action."})
        if decision not in ALLOWED_DECISIONS:
            findings.append({"status": "fail", "check": "decision", "index": index, "detail": f"Unsupported or missing decision: {decision}."})
        if event.get("case_id") in (None, "") and event.get("subject_id") in (None, ""):
            findings.append({"status": "warn", "check": "scope", "index": index, "detail": "Policy event has no case_id or subject_id scope."})

    missing_operations = [op for op in REQUIRED_OPERATION_TYPES if operation_counts[op] == 0]
    for operation in missing_operations:
        findings.append({"status": "fail", "check": "required_operation", "operation": operation, "detail": "Required v7.5 operation has no policy event coverage."})

    status = "fail" if any(item["status"] == "fail" for item in findings) else "warn" if findings else "pass"
    return {
        "schema": POLICY_COVERAGE_SCHEMA,
        "generated_at": utc_now(),
        "approved_line": "v7.5",
        "status": status,
        "event_count": len(events),
        "operation_counts": dict(sorted(operation_counts.items())),
        "decision_counts": dict(sorted(decision_counts.items())),
        "required_operation_types": REQUIRED_OPERATION_TYPES,
        "missing_operation_count": len(missing_operations),
        "missing_operations": missing_operations,
        "finding_count": len(findings),
        "findings": findings,
    }


def assert_policy_coverage(events: list[dict[str, Any]] | None) -> None:
    report = build_policy_coverage_report(events)
    if report["status"] == "fail":
        details = "; ".join(item.get("operation") or item.get("check", "unknown") for item in report["findings"] if item["status"] == "fail")
        raise AssertionError(f"v7.5 policy coverage failed: {details}")
