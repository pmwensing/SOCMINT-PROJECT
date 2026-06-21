from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from .dossier_finalization_handoff_export_verify_v7_5_9 import (
    verify_handoff_export_bundle,
)
from .dossier_finalization_handoff_export_verify_v7_5_9 import verify_handoff_export_zip

CLOSEOUT_REPORT_SCHEMA = "socmint.v7_5_10.dossier_finalization_closeout_report"
CLOSEOUT_REPORT_SUMMARY_SCHEMA = (
    "socmint.v7_5_10.dossier_finalization_closeout_report.summary"
)
APPROVED_LINE = "v7.5.10"
ACTION_CLOSEOUT = "closeout_ready"
ACTION_REVIEW = "human_review_required"
ACTION_REGENERATE = "regenerate_export"
CHAIN_STAGE = "handoff_export_verified"
ARCHIVE_READY_ACTIONS = {"archive_ready", "archive_and_deliver"}


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def recommended_closeout_action(verification_report: dict[str, Any]) -> str:
    status = str((verification_report or {}).get("status") or "").strip().lower()
    handoff_action = (
        str((verification_report or {}).get("recommended_action") or "").strip().lower()
    )
    if status == "verified" and handoff_action in ARCHIVE_READY_ACTIONS:
        return ACTION_CLOSEOUT
    if status == "needs_human_review":
        return ACTION_REVIEW
    return ACTION_REGENERATE


def summarize_closeout_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": CLOSEOUT_REPORT_SUMMARY_SCHEMA,
        "chain_stage": report.get("chain_stage"),
        "verification_status": report.get("verification_status"),
        "verified": bool(report.get("verified")),
        "recommended_action": report.get("recommended_action"),
        "closeout_action": report.get("closeout_action"),
        "file_count": int(report.get("file_count") or 0),
        "failure_count": int(report.get("failure_count") or 0),
        "warning_count": int(report.get("warning_count") or 0),
        "finding_count": len(report.get("findings") or []),
    }


def build_closeout_report(
    verification_report: dict[str, Any],
    *,
    operator: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    verification = deepcopy(verification_report or {})
    findings = [
        *list(verification.get("failures") or []),
        *list(verification.get("warnings") or []),
    ]
    present_files = list(verification.get("present_files") or [])
    file_count = len(present_files)
    if not file_count:
        file_count = len(verification.get("file_results") or [])
    report: dict[str, Any] = {
        "schema": CLOSEOUT_REPORT_SCHEMA,
        "approved_line": APPROVED_LINE,
        "generated_at": utc_now(),
        "operator": operator,
        "notes": notes,
        "chain_stage": CHAIN_STAGE,
        "verification_status": verification.get("status"),
        "verified": bool(verification.get("verified")),
        "recommended_action": verification.get("recommended_action"),
        "closeout_action": recommended_closeout_action(verification),
        "file_count": file_count,
        "failure_count": int(verification.get("failure_count") or 0),
        "warning_count": int(verification.get("warning_count") or 0),
        "missing_files": list(verification.get("missing_files") or []),
        "unexpected_files": list(verification.get("unexpected_files") or []),
        "findings": findings,
        "verification_summary": dict(verification.get("summary") or {}),
        "summary": {},
    }
    report["summary"] = summarize_closeout_report(report)
    return report


def build_closeout_report_from_bundle(
    bundle: dict[str, Any],
    *,
    operator: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    verification = verify_handoff_export_bundle(deepcopy(bundle or {}))
    return build_closeout_report(verification, operator=operator, notes=notes)


def build_closeout_report_from_zip_bytes(
    zip_bytes: bytes,
    *,
    operator: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    verification = verify_handoff_export_zip(bytes(zip_bytes or b""))
    return build_closeout_report(verification, operator=operator, notes=notes)


def _action_label(action: Any) -> str:
    return str(action or ACTION_REGENERATE).replace("_", " ").upper()


def _finding_lines(findings: list[dict[str, Any]]) -> list[str]:
    if not findings:
        return ["None."]
    return [
        f"- **{item.get('severity')}** `{item.get('code')}` {item.get('path') or ''}: {item.get('detail')} Action: {item.get('action')}".strip()
        for item in findings
    ]


def render_closeout_report_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# SOCMINT v7.5.10 Finalization Chain Closeout Report",
        "",
        f"Closeout action: {_action_label(report.get('closeout_action'))}",
        "",
        "## Chain Status",
        "",
        f"- Chain stage: `{report.get('chain_stage')}`",
        f"- Operator: `{report.get('operator') or 'unspecified'}`",
        f"- Generated at: `{report.get('generated_at')}`",
        "",
        "## Verification",
        "",
        f"- Verification status: `{report.get('verification_status')}`",
        f"- Verified: `{report.get('verified')}`",
        f"- Recommended action: `{report.get('recommended_action')}`",
        f"- File count: `{report.get('file_count')}`",
        f"- Failures: `{report.get('failure_count')}`",
        f"- Warnings: `{report.get('warning_count')}`",
        f"- Missing files: `{', '.join(report.get('missing_files') or []) or 'None'}`",
        f"- Unexpected files: `{', '.join(report.get('unexpected_files') or []) or 'None'}`",
        "",
        "## Findings",
        "",
    ]
    lines.extend(_finding_lines(list(report.get("findings") or [])))
    lines.extend(["", "## Operator Notes", "", report.get("notes") or "None."])
    return "\n".join(lines) + "\n"
