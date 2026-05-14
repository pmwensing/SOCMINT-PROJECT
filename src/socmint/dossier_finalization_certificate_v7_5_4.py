from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from .dossier_finalization_export_verify_v7_5_3 import verify_finalization_export_packet
from .dossier_finalization_export_verify_v7_5_3 import verify_finalization_export_zip

CERTIFICATE_SCHEMA = "socmint.v7_5_4.dossier_finalization_verification_certificate"
CERTIFICATE_SUMMARY_SCHEMA = "socmint.v7_5_4.dossier_finalization_verification_certificate.summary"
APPROVED_LINE = "v7.5.4"
CERT_VALID = "valid"
CERT_REVIEW = "needs_human_review"
CERT_FAILED = "failed"


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def _status_from_verification(status: Any) -> str:
    value = str(status or "").strip().lower()
    if value == "verified":
        return CERT_VALID
    if value == "needs_human_review":
        return CERT_REVIEW
    return CERT_FAILED


def _certificate_digest_payload(certificate: dict[str, Any]) -> dict[str, Any]:
    payload = deepcopy(certificate or {})
    payload["certificate_sha256"] = ""
    return payload


def certificate_digest(certificate: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(_certificate_digest_payload(certificate)).encode("utf-8")).hexdigest()


def summarize_certificate(certificate: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": CERTIFICATE_SUMMARY_SCHEMA,
        "status": certificate.get("status"),
        "valid": bool(certificate.get("valid")),
        "verification_status": certificate.get("verification_status"),
        "verification_verified": bool(certificate.get("verification_verified")),
        "failure_count": int(certificate.get("failure_count") or 0),
        "warning_count": int(certificate.get("warning_count") or 0),
        "certificate_sha256": certificate.get("certificate_sha256"),
        "packet_name": certificate.get("packet_name"),
    }


def build_verification_certificate(
    verification_report: dict[str, Any],
    *,
    packet_name: str | None = None,
    reviewer: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    report = deepcopy(verification_report or {})
    verification_status = str(report.get("status") or "failed")
    status = _status_from_verification(verification_status)
    findings = [*list(report.get("failures") or []), *list(report.get("warnings") or [])]
    certificate: dict[str, Any] = {
        "schema": CERTIFICATE_SCHEMA,
        "approved_line": APPROVED_LINE,
        "generated_at": utc_now(),
        "packet_name": packet_name,
        "reviewer": reviewer,
        "notes": notes,
        "status": status,
        "valid": status == CERT_VALID,
        "verification_status": verification_status,
        "verification_verified": bool(report.get("verified")),
        "failure_count": int(report.get("failure_count") or 0),
        "warning_count": int(report.get("warning_count") or 0),
        "required_files": list(report.get("required_files") or []),
        "present_files": list(report.get("present_files") or []),
        "missing_files": list(report.get("missing_files") or []),
        "unexpected_files": list(report.get("unexpected_files") or []),
        "findings": findings,
        "certificate_sha256": "",
        "verification_summary": dict(report.get("summary") or {}),
        "summary": {},
    }
    certificate["certificate_sha256"] = certificate_digest(certificate)
    certificate["summary"] = summarize_certificate(certificate)
    return certificate


def build_certificate_from_packet(
    packet: dict[str, Any],
    *,
    packet_name: str | None = None,
    reviewer: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    report = verify_finalization_export_packet(deepcopy(packet or {}))
    return build_verification_certificate(report, packet_name=packet_name, reviewer=reviewer, notes=notes)


def build_certificate_from_zip_bytes(
    zip_bytes: bytes,
    *,
    packet_name: str | None = None,
    reviewer: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    report = verify_finalization_export_zip(bytes(zip_bytes or b""))
    return build_verification_certificate(report, packet_name=packet_name, reviewer=reviewer, notes=notes)


def _status_label(status: Any) -> str:
    return str(status or CERT_FAILED).replace("_", " ").upper()


def _finding_lines(findings: list[dict[str, Any]]) -> list[str]:
    if not findings:
        return ["None."]
    return [
        f"- **{item.get('severity')}** `{item.get('code')}` {item.get('path') or ''}: {item.get('detail')} Action: {item.get('action')}".strip()
        for item in findings
    ]


def render_certificate_markdown(certificate: dict[str, Any]) -> str:
    findings = list(certificate.get("findings") or [])
    lines = [
        "# SOCMINT v7.5.4 Finalization Verification Certificate",
        "",
        f"Status: {_status_label(certificate.get('status'))}",
        "",
        "## Packet",
        "",
        f"- Packet name: `{certificate.get('packet_name') or 'unspecified'}`",
        f"- Reviewer: `{certificate.get('reviewer') or 'unspecified'}`",
        f"- Generated at: `{certificate.get('generated_at')}`",
        "",
        "## Verification Summary",
        "",
        f"- Verification status: `{certificate.get('verification_status')}`",
        f"- Verification verified: `{certificate.get('verification_verified')}`",
        f"- Failures: `{certificate.get('failure_count')}`",
        f"- Warnings: `{certificate.get('warning_count')}`",
        f"- Missing files: `{', '.join(certificate.get('missing_files') or []) or 'None'}`",
        f"- Unexpected files: `{', '.join(certificate.get('unexpected_files') or []) or 'None'}`",
        "",
        "## Findings",
        "",
    ]
    lines.extend(_finding_lines(findings))
    lines.extend(
        [
            "",
            "## Certificate Digest",
            "",
            f"`{certificate.get('certificate_sha256')}`",
            "",
            "## Notes",
            "",
            certificate.get("notes") or "None.",
        ]
    )
    return "\n".join(lines) + "\n"
