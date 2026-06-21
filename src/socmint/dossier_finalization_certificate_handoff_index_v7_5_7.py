from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from .dossier_finalization_certificate_bundle_verify_v7_5_6 import (
    verify_certificate_bundle,
)
from .dossier_finalization_certificate_bundle_verify_v7_5_6 import (
    verify_certificate_bundle_zip,
)

HANDOFF_INDEX_SCHEMA = "socmint.v7_5_7.dossier_finalization_certificate_handoff_index"
HANDOFF_INDEX_SUMMARY_SCHEMA = (
    "socmint.v7_5_7.dossier_finalization_certificate_handoff_index.summary"
)
APPROVED_LINE = "v7.5.7"
ACTION_ARCHIVE = "archive_ready"
ACTION_REVIEW = "human_review_required"
ACTION_REGENERATE = "regenerate_bundle"


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def recommended_action(verification_report: dict[str, Any]) -> str:
    status = str((verification_report or {}).get("status") or "").strip().lower()
    cert_status = (
        str((verification_report or {}).get("certificate_status") or "").strip().lower()
    )
    if status == "verified" and cert_status == "valid":
        return ACTION_ARCHIVE
    if status == "needs_human_review":
        return ACTION_REVIEW
    return ACTION_REGENERATE


def _file_index_from_report(report: dict[str, Any]) -> list[dict[str, Any]]:
    manifest = (
        report.get("manifest") if isinstance(report.get("manifest"), dict) else {}
    )
    rows = manifest.get("files") if isinstance(manifest.get("files"), list) else []
    verified_paths = {
        item.get("path")
        for item in report.get("file_results", [])
        if isinstance(item, dict) and item.get("hash_match") and item.get("size_match")
    }
    if rows:
        return [
            {
                "path": row.get("path"),
                "content_type": row.get("content_type"),
                "size_bytes": row.get("size_bytes"),
                "sha256": row.get("sha256"),
                "verified": row.get("path") in verified_paths
                or bool(report.get("verified")),
            }
            for row in rows
            if isinstance(row, dict)
        ]
    return [
        {
            "path": path,
            "content_type": None,
            "size_bytes": None,
            "sha256": None,
            "verified": False,
        }
        for path in report.get("present_files", [])
    ]


def summarize_handoff_index(index: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": HANDOFF_INDEX_SUMMARY_SCHEMA,
        "recommended_action": index.get("recommended_action"),
        "verification_status": index.get("verification_status"),
        "verified": bool(index.get("verified")),
        "certificate_status": index.get("certificate_status"),
        "certificate_valid": bool(index.get("certificate_valid")),
        "file_count": int(index.get("file_count") or 0),
        "finding_count": len(index.get("findings") or []),
        "bundle_name": index.get("bundle_name"),
    }


def build_handoff_index(
    verification_report: dict[str, Any],
    *,
    bundle_name: str | None = None,
    operator: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    report = deepcopy(verification_report or {})
    file_index = _file_index_from_report(report)
    findings = [
        *list(report.get("failures") or []),
        *list(report.get("warnings") or []),
    ]
    index: dict[str, Any] = {
        "schema": HANDOFF_INDEX_SCHEMA,
        "approved_line": APPROVED_LINE,
        "generated_at": utc_now(),
        "bundle_name": bundle_name,
        "operator": operator,
        "notes": notes,
        "verification_status": report.get("status"),
        "verified": bool(report.get("verified")),
        "certificate_status": report.get("certificate_status"),
        "certificate_valid": bool(report.get("certificate_valid")),
        "recommended_action": recommended_action(report),
        "file_count": len(file_index),
        "required_files": list(report.get("required_files") or []),
        "present_files": list(report.get("present_files") or []),
        "missing_files": list(report.get("missing_files") or []),
        "unexpected_files": list(report.get("unexpected_files") or []),
        "file_index": file_index,
        "findings": findings,
        "verification_summary": dict(report.get("summary") or {}),
        "summary": {},
    }
    index["summary"] = summarize_handoff_index(index)
    return index


def build_handoff_index_from_bundle(
    bundle: dict[str, Any],
    *,
    operator: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    bundle_copy = deepcopy(bundle or {})
    report = verify_certificate_bundle(bundle_copy)
    return build_handoff_index(
        report,
        bundle_name=bundle_copy.get("bundle_name"),
        operator=operator,
        notes=notes,
    )


def build_handoff_index_from_zip_bytes(
    zip_bytes: bytes,
    *,
    bundle_name: str | None = None,
    operator: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    report = verify_certificate_bundle_zip(bytes(zip_bytes or b""))
    return build_handoff_index(
        report, bundle_name=bundle_name, operator=operator, notes=notes
    )


def _action_label(action: Any) -> str:
    return str(action or ACTION_REGENERATE).replace("_", " ").upper()


def _finding_lines(findings: list[dict[str, Any]]) -> list[str]:
    if not findings:
        return ["None."]
    return [
        f"- **{item.get('severity')}** `{item.get('code')}` {item.get('path') or ''}: {item.get('detail')} Action: {item.get('action')}".strip()
        for item in findings
    ]


def render_handoff_index_markdown(index: dict[str, Any]) -> str:
    lines = [
        "# SOCMINT v7.5.7 Certificate Bundle Handoff Index",
        "",
        f"Recommended action: {_action_label(index.get('recommended_action'))}",
        "",
        "## Bundle",
        "",
        f"- Bundle name: `{index.get('bundle_name') or 'unspecified'}`",
        f"- Operator: `{index.get('operator') or 'unspecified'}`",
        f"- Generated at: `{index.get('generated_at')}`",
        "",
        "## Verification",
        "",
        f"- Verification status: `{index.get('verification_status')}`",
        f"- Verified: `{index.get('verified')}`",
        f"- Certificate status: `{index.get('certificate_status')}`",
        f"- Certificate valid: `{index.get('certificate_valid')}`",
        f"- Missing files: `{', '.join(index.get('missing_files') or []) or 'None'}`",
        f"- Unexpected files: `{', '.join(index.get('unexpected_files') or []) or 'None'}`",
        "",
        "## File Index",
        "",
    ]
    file_index = index.get("file_index") or []
    if file_index:
        lines.extend(
            f"- `{item.get('path')}` — {item.get('content_type') or 'unknown'}, {item.get('size_bytes') or 'unknown'} bytes, verified={item.get('verified')}"
            for item in file_index
        )
    else:
        lines.append("None.")
    lines.extend(["", "## Findings", ""])
    lines.extend(_finding_lines(list(index.get("findings") or [])))
    lines.extend(["", "## Notes", "", index.get("notes") or "None."])
    return "\n".join(lines) + "\n"
