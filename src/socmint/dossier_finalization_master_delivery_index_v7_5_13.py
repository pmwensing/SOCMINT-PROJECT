from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from .dossier_finalization_closeout_export_verify_v7_5_12 import verify_closeout_export_bundle
from .dossier_finalization_closeout_export_verify_v7_5_12 import verify_closeout_export_zip

MASTER_DELIVERY_INDEX_SCHEMA = "socmint.v7_5_13.dossier_finalization_master_delivery_index"
MASTER_DELIVERY_INDEX_SUMMARY_SCHEMA = "socmint.v7_5_13.dossier_finalization_master_delivery_index.summary"
APPROVED_LINE = "v7.5.13"
ACTION_DELIVER_READY = "deliver_ready"
ACTION_REVIEW = "human_review_required"
ACTION_REGENERATE = "regenerate_export"
DELIVERY_STAGE = "closeout_export_verified"


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def recommended_delivery_action(verification_report: dict[str, Any]) -> str:
    report = verification_report or {}
    status = report.get("status")
    if status == "verified" and report.get("verified") is True:
        return ACTION_DELIVER_READY
    if status == "needs_human_review":
        return ACTION_REVIEW
    return ACTION_REGENERATE


def _finding_from_report(item: dict[str, Any], default_severity: str) -> dict[str, Any]:
    source = item or {}
    return {
        "severity": source.get("severity") or default_severity,
        "code": source.get("code"),
        "path": source.get("path"),
        "detail": source.get("detail"),
        "action": source.get("action"),
    }


def _combined_findings(verification_report: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for item in verification_report.get("failures") or []:
        findings.append(_finding_from_report(item, "fail"))
    for item in verification_report.get("warnings") or []:
        findings.append(_finding_from_report(item, "warn"))
    return findings


def summarize_master_delivery_index(index: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": MASTER_DELIVERY_INDEX_SUMMARY_SCHEMA,
        "delivery_action": index.get("delivery_action"),
        "verification_status": index.get("verification_status"),
        "verified": bool(index.get("verified")),
        "closeout_action": index.get("closeout_action"),
        "file_count": int(index.get("file_count") or 0),
        "failure_count": int(index.get("failure_count") or 0),
        "warning_count": int(index.get("warning_count") or 0),
        "missing_files": list(index.get("missing_files") or []),
        "unexpected_files": list(index.get("unexpected_files") or []),
    }


def build_master_delivery_index(
    verification_report: dict[str, Any],
    *,
    operator: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    report = deepcopy(verification_report or {})
    manifest = report.get("manifest") if isinstance(report.get("manifest"), dict) else {}
    manifest_files = manifest.get("files") if isinstance(manifest.get("files"), list) else []
    file_count = int(manifest.get("file_count") or len(report.get("present_files") or manifest_files or []))
    index: dict[str, Any] = {
        "schema": MASTER_DELIVERY_INDEX_SCHEMA,
        "approved_line": APPROVED_LINE,
        "generated_at": utc_now(),
        "operator": operator,
        "notes": notes,
        "delivery_stage": DELIVERY_STAGE,
        "delivery_action": recommended_delivery_action(report),
        "verification_status": report.get("status"),
        "verified": bool(report.get("verified")),
        "closeout_action": report.get("closeout_action"),
        "file_count": file_count,
        "required_files": list(report.get("required_files") or []),
        "present_files": list(report.get("present_files") or []),
        "missing_files": list(report.get("missing_files") or []),
        "unexpected_files": list(report.get("unexpected_files") or []),
        "failure_count": int(report.get("failure_count") or 0),
        "warning_count": int(report.get("warning_count") or 0),
        "findings": _combined_findings(report),
        "verification_summary": deepcopy(report.get("summary") or {}),
        "summary": {},
    }
    index["summary"] = summarize_master_delivery_index(index)
    return index


def build_master_delivery_index_from_bundle(
    bundle: dict[str, Any],
    *,
    operator: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    report = verify_closeout_export_bundle(deepcopy(bundle or {}))
    return build_master_delivery_index(report, operator=operator, notes=notes)


def build_master_delivery_index_from_zip_bytes(
    zip_bytes: bytes,
    *,
    operator: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    report = verify_closeout_export_zip(bytes(zip_bytes or b""))
    return build_master_delivery_index(report, operator=operator, notes=notes)


def render_master_delivery_index_markdown(index: dict[str, Any]) -> str:
    data = index or {}
    findings = data.get("findings") or []
    lines = [
        "# SOCMINT v7.5.13 Master Dossier Delivery Index",
        "",
        f"Delivery action: {str(data.get('delivery_action') or '').upper()}",
        "",
        "## Delivery Status",
        "",
        f"- Delivery stage: `{data.get('delivery_stage')}`",
        f"- Delivery action: `{data.get('delivery_action')}`",
        f"- Operator: `{data.get('operator') or ''}`",
        "",
        "## Closeout Export Verification",
        "",
        f"- Verification status: `{data.get('verification_status')}`",
        f"- Verified: `{bool(data.get('verified'))}`",
        f"- Closeout action: `{data.get('closeout_action')}`",
        f"- Failures: `{int(data.get('failure_count') or 0)}`",
        f"- Warnings: `{int(data.get('warning_count') or 0)}`",
        "",
        "## File Inventory",
        "",
        f"- File count: `{int(data.get('file_count') or 0)}`",
        f"- Required files: `{len(data.get('required_files') or [])}`",
        f"- Present files: `{len(data.get('present_files') or [])}`",
        f"- Missing files: `{', '.join(data.get('missing_files') or [])}`",
        f"- Unexpected files: `{', '.join(data.get('unexpected_files') or [])}`",
        "",
        "## Findings",
        "",
    ]
    if findings:
        for item in findings:
            lines.append(
                f"- `{item.get('severity')}` `{item.get('code')}` `{item.get('path') or ''}` — {item.get('detail') or ''}"
            )
    else:
        lines.append("- No failures or warnings reported.")
    lines.extend(
        [
            "",
            "## Operator Notes",
            "",
            str(data.get("notes") or ""),
            "",
        ]
    )
    return "\n".join(lines)
