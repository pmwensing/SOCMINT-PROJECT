from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from .connector_compliance_v7_5 import build_connector_compliance_report
from .dossier_evidence_manifest_v7_5 import build_evidence_manifest
from .dossier_export_enforcement_v7_5 import evaluate_dossier_export
from .dossier_quality_v7_5 import evaluate_dossier_quality
from .identity_confidence_v7_5 import build_identity_confidence_report
from .policy_coverage_v7_5 import build_policy_coverage_report

FINALIZATION_SCHEMA = "socmint.v7_5_1.dossier_finalization"
FINALIZATION_SUMMARY_SCHEMA = "socmint.v7_5_1.dossier_finalization.summary"
APPROVED_LINE = "v7.5.1"
DECISION_READY = "ready"
DECISION_REVIEW = "needs_human_review"
DECISION_BLOCKED = "blocked"

COMPONENTS = (
    "quality_gate",
    "export_enforcement",
    "evidence_manifest",
    "identity_confidence",
    "connector_compliance",
    "policy_coverage",
)

ACTIONS = {
    "quality_gate_failed": "Repair unsubstantiated claims before finalization.",
    "export_blocked": "Use draft/preview mode or repair blocking findings before final export.",
    "evidence_lineage_incomplete": "Add missing evidence refs, hashes, sources, or source URLs.",
    "identity_contradiction": "Resolve identity contradictions or mark claims as rejected.",
    "connector_compliance_failed": "Complete connector compliance metadata and dry-run/human-review fields.",
    "policy_coverage_failed": "Add missing governance policy events for required operations.",
    "quality_gate_review_needed": "Complete human review before disclosure/export.",
    "evidence_review_needed": "Complete human review before disclosure/export.",
    "identity_review_needed": "Complete human review before disclosure/export.",
    "connector_compliance_missing": "Complete human review before disclosure/export.",
    "policy_coverage_review_needed": "Complete human review before disclosure/export.",
    "export_enforcement_review_needed": "Complete human review before disclosure/export.",
}


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _nonempty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, (list, tuple, set, dict, str)):
        return bool(value)
    if isinstance(value, (int, float)):
        return value > 0
    return bool(value)


def _status(report: dict[str, Any]) -> str:
    return str(report.get("status") or "").strip().lower()


def _normalize_report_status(report: dict[str, Any], *, allow_warn: bool = True) -> str:
    if not report:
        return "missing"
    value = _status(report)
    if value in {"pass", "passed", "ok", "ready", "allow", "allowed"}:
        return "pass"
    if allow_warn and value in {"warn", "warning", "needs_human_review", "review"}:
        return "warn"
    if value in {"fail", "failed", "block", "blocked", "error"}:
        return "fail"
    return "missing"


def _normalize_export_status(report: dict[str, Any]) -> str:
    if not report:
        return "missing"
    if report.get("allowed") is True:
        return "allow"
    if report.get("allowed") is False or report.get("final_export_blocked") is True:
        return "block"
    value = _status(report)
    if value in {"allow", "allowed", "ready", "pass", "passed"}:
        return "allow"
    if value in {"block", "blocked", "fail", "failed"}:
        return "block"
    return "missing"


def _finding(component: str, severity: str, code: str, detail: str) -> dict[str, Any]:
    return {
        "component": component,
        "severity": severity,
        "code": code,
        "detail": detail,
        "action": ACTIONS.get(code, "Complete human review before disclosure/export."),
    }


def _checklist() -> list[dict[str, Any]]:
    return [
        {
            "id": "identity",
            "label": "Confirm subject identity confidence and contradiction status.",
            "required": True,
        },
        {
            "id": "claims",
            "label": "Confirm every report claim has source/evidence/confidence context.",
            "required": True,
        },
        {
            "id": "evidence",
            "label": "Confirm evidence manifest has no missing hash/source fields.",
            "required": True,
        },
        {
            "id": "connectors",
            "label": "Confirm connector compliance metadata is complete or not applicable.",
            "required": True,
        },
        {
            "id": "policy",
            "label": "Confirm governance/policy coverage includes dossier build/export and artifact operations.",
            "required": True,
        },
        {
            "id": "export",
            "label": "Confirm final export mode is allowed.",
            "required": True,
        },
        {
            "id": "warnings",
            "label": "Confirm analyst reviewed all warnings before disclosure/export.",
            "required": True,
        },
    ]


def _component_reports(
    payload: dict[str, Any],
    connectors: list[dict[str, Any]] | None,
    policy_events: list[dict[str, Any]] | None,
    export_mode: str,
) -> dict[str, Any]:
    reports: dict[str, Any] = {}
    quality = _as_dict(payload.get("quality_gate") or payload.get("dossier_quality"))
    reports["quality_gate"] = quality or evaluate_dossier_quality(payload)

    export = _as_dict(
        payload.get("export_enforcement") or payload.get("export_decision")
    )
    reports["export_enforcement"] = export or evaluate_dossier_export(
        {**payload, "quality_gate": reports["quality_gate"]}, mode=export_mode
    )

    evidence = _as_dict(
        payload.get("evidence_manifest") or payload.get("evidence_appendix")
    )
    raw_evidence = (
        payload.get("evidence") if isinstance(payload.get("evidence"), list) else None
    )
    reports["evidence_manifest"] = evidence or build_evidence_manifest(
        payload, raw_evidence=raw_evidence
    )

    identity = _as_dict(payload.get("identity_confidence"))
    reports["identity_confidence"] = identity or build_identity_confidence_report(
        payload
    )

    connector_report = _as_dict(payload.get("connector_compliance"))
    if connector_report:
        reports["connector_compliance"] = connector_report
    elif connectors is not None:
        reports["connector_compliance"] = build_connector_compliance_report(connectors)
    else:
        reports["connector_compliance"] = {}

    policy_report = _as_dict(payload.get("policy_coverage"))
    if policy_report:
        reports["policy_coverage"] = policy_report
    elif policy_events is not None:
        reports["policy_coverage"] = build_policy_coverage_report(policy_events)
    else:
        reports["policy_coverage"] = {}
    return reports


def _evidence_incomplete(report: dict[str, Any]) -> bool:
    keys = (
        "missing_evidence_refs",
        "missing_hashes",
        "missing_sources",
        "missing_source_urls",
        "missing_refs",
        "missing_hash_evidence_ids",
        "missing_source_evidence_ids",
    )
    count_keys = (
        "missing_evidence_ref_count",
        "missing_hash_count",
        "missing_source_count",
        "missing_source_url_count",
        "missing_ref_count",
    )
    summary = _as_dict(report.get("appendix_summary"))
    return (
        any(_nonempty(report.get(k)) for k in keys)
        or any(_as_int(report.get(k)) > 0 for k in count_keys)
        or any(_as_int(summary.get(k)) > 0 for k in count_keys)
    )


def _evidence_warn(report: dict[str, Any], status: str) -> bool:
    if status in {"missing", "warn"}:
        return True
    return any(
        _as_int(report.get(k)) > 0
        for k in ("weak_evidence_count", "unresolved_count", "warning_count")
    )


def _evaluate_components(
    reports: dict[str, Any], export_mode: str
) -> tuple[dict[str, str], list[dict[str, Any]], list[dict[str, Any]]]:
    statuses = {
        "quality_gate": _normalize_report_status(_as_dict(reports.get("quality_gate"))),
        "export_enforcement": _normalize_export_status(
            _as_dict(reports.get("export_enforcement"))
        ),
        "evidence_manifest": _normalize_report_status(
            _as_dict(reports.get("evidence_manifest"))
        ),
        "identity_confidence": _normalize_report_status(
            _as_dict(reports.get("identity_confidence"))
        ),
        "connector_compliance": _normalize_report_status(
            _as_dict(reports.get("connector_compliance")), allow_warn=False
        ),
        "policy_coverage": _normalize_report_status(
            _as_dict(reports.get("policy_coverage"))
        ),
    }
    blocking: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    if statuses["quality_gate"] == "fail":
        blocking.append(
            _finding(
                "quality_gate",
                "block",
                "quality_gate_failed",
                "Dossier quality gate failed.",
            )
        )
    elif statuses["quality_gate"] in {"warn", "missing"}:
        warnings.append(
            _finding(
                "quality_gate",
                "warn",
                "quality_gate_review_needed",
                "Dossier quality gate needs review or is missing.",
            )
        )

    if export_mode == "final" and statuses["export_enforcement"] == "block":
        blocking.append(
            _finding(
                "export_enforcement",
                "block",
                "export_blocked",
                "Final export is blocked by export enforcement.",
            )
        )
    elif statuses["export_enforcement"] == "missing":
        warnings.append(
            _finding(
                "export_enforcement",
                "warn",
                "export_enforcement_review_needed",
                "Export enforcement report is missing.",
            )
        )

    evidence_report = _as_dict(reports.get("evidence_manifest"))
    if _evidence_incomplete(evidence_report):
        statuses["evidence_manifest"] = "fail"
        blocking.append(
            _finding(
                "evidence_manifest",
                "block",
                "evidence_lineage_incomplete",
                "Evidence lineage has missing refs, hashes, sources, or source URLs.",
            )
        )
    elif _evidence_warn(evidence_report, statuses["evidence_manifest"]):
        warnings.append(
            _finding(
                "evidence_manifest",
                "warn",
                "evidence_review_needed",
                "Evidence manifest needs human review.",
            )
        )

    identity_report = _as_dict(reports.get("identity_confidence"))
    if (
        statuses["identity_confidence"] == "fail"
        or _as_int(identity_report.get("contradiction_count")) > 0
    ):
        statuses["identity_confidence"] = "fail"
        blocking.append(
            _finding(
                "identity_confidence",
                "block",
                "identity_contradiction",
                "Identity confidence report contains contradictions or failed checks.",
            )
        )
    elif (
        statuses["identity_confidence"] == "warn"
        or _as_int(identity_report.get("low_confidence_count")) > 0
        or _as_int(identity_report.get("needs_review_count")) > 0
    ):
        warnings.append(
            _finding(
                "identity_confidence",
                "warn",
                "identity_review_needed",
                "Identity confidence requires analyst review.",
            )
        )

    if statuses["connector_compliance"] == "fail":
        blocking.append(
            _finding(
                "connector_compliance",
                "block",
                "connector_compliance_failed",
                "Connector compliance report failed.",
            )
        )
    elif statuses["connector_compliance"] == "missing":
        warnings.append(
            _finding(
                "connector_compliance",
                "warn",
                "connector_compliance_missing",
                "Connector compliance report or input is missing.",
            )
        )

    if statuses["policy_coverage"] == "fail":
        blocking.append(
            _finding(
                "policy_coverage",
                "block",
                "policy_coverage_failed",
                "Policy coverage report failed.",
            )
        )
    elif statuses["policy_coverage"] in {"warn", "missing"}:
        warnings.append(
            _finding(
                "policy_coverage",
                "warn",
                "policy_coverage_review_needed",
                "Policy coverage report needs review or is missing.",
            )
        )

    return statuses, blocking, warnings


def summarize_finalization_decision(packet: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": FINALIZATION_SUMMARY_SCHEMA,
        "decision": packet.get("decision"),
        "ready": bool(packet.get("ready")),
        "blocking_count": _as_int(packet.get("blocking_count")),
        "warning_count": _as_int(packet.get("warning_count")),
        "component_status": dict(packet.get("component_status") or {}),
    }


def build_dossier_finalization_packet(
    dossier_payload: dict[str, Any],
    *,
    connectors: list[dict[str, Any]] | None = None,
    policy_events: list[dict[str, Any]] | None = None,
    export_mode: str = "final",
) -> dict[str, Any]:
    payload = deepcopy(dossier_payload or {})
    mode = str(export_mode or "final").strip().lower()
    reports = _component_reports(payload, connectors, policy_events, mode)
    statuses, blocking, warnings = _evaluate_components(reports, mode)
    decision = (
        DECISION_BLOCKED
        if blocking
        else DECISION_REVIEW
        if warnings
        else DECISION_READY
    )
    packet = {
        "schema": FINALIZATION_SCHEMA,
        "approved_line": APPROVED_LINE,
        "generated_at": utc_now(),
        "export_mode": mode,
        "decision": decision,
        "ready": decision == DECISION_READY,
        "blocking_count": len(blocking),
        "warning_count": len(warnings),
        "component_status": {
            component: statuses.get(component, "missing") for component in COMPONENTS
        },
        "blocking_findings": blocking,
        "warnings": warnings,
        "human_review_checklist": _checklist(),
        "recommended_actions": list(
            dict.fromkeys(item["action"] for item in [*blocking, *warnings])
        ),
        "component_reports": reports,
    }
    packet["summary"] = summarize_finalization_decision(packet)
    return packet


def attach_dossier_finalization(
    dossier_payload: dict[str, Any],
    *,
    connectors: list[dict[str, Any]] | None = None,
    policy_events: list[dict[str, Any]] | None = None,
    export_mode: str = "final",
) -> dict[str, Any]:
    enriched = dict(dossier_payload or {})
    enriched["dossier_finalization"] = build_dossier_finalization_packet(
        dossier_payload or {},
        connectors=connectors,
        policy_events=policy_events,
        export_mode=export_mode,
    )
    return enriched


def _decision_label(decision: Any) -> str:
    return str(decision or DECISION_REVIEW).replace("_", " ").upper()


def _lines_for_findings(items: list[dict[str, Any]]) -> list[str]:
    if not items:
        return ["None."]
    return [
        f"- **{item.get('component')}** `{item.get('code')}`: {item.get('detail')} Action: {item.get('action')}"
        for item in items
    ]


def render_finalization_markdown(packet: dict[str, Any]) -> str:
    component_status = packet.get("component_status") or {}
    checklist = packet.get("human_review_checklist") or []
    actions = packet.get("recommended_actions") or []
    lines = [
        "# SOCMINT v7.5.1 Dossier Finalization Packet",
        "",
        f"Decision: {_decision_label(packet.get('decision'))}",
        "",
        "## Component Status",
        "",
    ]
    if component_status:
        lines.extend(
            f"- **{component}**: `{status}`"
            for component, status in sorted(component_status.items())
        )
    else:
        lines.append("None.")
    lines.extend(["", "## Blocking Findings", ""])
    lines.extend(_lines_for_findings(list(packet.get("blocking_findings") or [])))
    lines.extend(["", "## Warnings", ""])
    lines.extend(_lines_for_findings(list(packet.get("warnings") or [])))
    lines.extend(["", "## Human Review Checklist", ""])
    if checklist:
        lines.extend(
            f"- [{' ' if item.get('required') else 'x'}] {item.get('label')}"
            for item in checklist
        )
    else:
        lines.append("None.")
    lines.extend(["", "## Recommended Actions", ""])
    if actions:
        lines.extend(f"- {action}" for action in actions)
    else:
        lines.append("None.")
    return "\n".join(lines) + "\n"
