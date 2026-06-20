from __future__ import annotations

import os
from typing import Any

from . import database
from .dossier_assembly_workspace_v21_0 import (
    _canonical,
    _ensure_storage,
    _json_details,
    _sha,
)
from .dossier_final_export_package_v21_6 import _latest_export
from .dossier_release_authorization_v22_1 import latest_release_authorization

SCHEMA = "socmint.dossier_release_preview.v22_2"
VERSION = "v22.2.0"
ACTION = "case_dossier_release_preview"
DEFAULT_SENSITIVE_TERMS = (
    "password",
    "credential",
    "secret",
    "private key",
    "access token",
    "medical",
    "minor",
    "home address",
)


def _terms() -> tuple[str, ...]:
    configured = os.environ.get("SOCMINT_RELEASE_SENSITIVE_TERMS", "")
    values = [value.strip().lower() for value in configured.split(",") if value.strip()]
    return tuple(values) if values else DEFAULT_SENSITIVE_TERMS


def _classify_text(text: str, explicit: str | None = None) -> dict[str, Any]:
    explicit_value = str(explicit or "").strip().lower()
    matches = sorted(term for term in _terms() if term in text.lower())
    if explicit_value in {"restricted", "sensitive", "confidential"} or matches:
        classification = "restricted"
    elif explicit_value in {"public", "internal"}:
        classification = explicit_value
    else:
        classification = "internal"
    return {
        "classification": classification,
        "sensitivity_matches": matches,
        "redaction_required": classification == "restricted",
    }


def _sections(export_package: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    for section in (export_package.get("dossier_content") or {}).get("sections") or []:
        narrative = str(
            section.get("citation_ready_narrative") or section.get("narrative") or ""
        )
        findings = list(section.get("findings") or [])
        combined = " ".join(
            [narrative]
            + [
                str(item.get("citation_ready_text") or item.get("text") or "")
                for item in findings
            ]
        )
        classification = _classify_text(combined, section.get("classification"))
        redaction_confirmed = section.get("redaction_confirmed") is True
        result.append(
            {
                "section_id": section.get("section_id"),
                "title": section.get("title"),
                "position": section.get("position"),
                "narrative": narrative,
                "findings": findings,
                "finding_count": len(findings),
                **classification,
                "redaction_confirmed": redaction_confirmed,
                "release_ready": not classification["redaction_required"]
                or redaction_confirmed,
            }
        )
    return result


def _attachments(export_package: dict[str, Any]) -> list[dict[str, Any]]:
    attachments: dict[str, dict[str, Any]] = {}
    for citation in export_package.get("citation_catalog") or []:
        for artifact in citation.get("artifact_links") or []:
            key = str(
                artifact.get("artifact_id")
                or artifact.get("sha256")
                or artifact.get("path")
                or ""
            )
            if not key or key in attachments:
                continue
            text = " ".join(
                str(artifact.get(name) or "")
                for name in ("path", "name", "description")
            )
            classification = _classify_text(text, artifact.get("classification"))
            redaction_confirmed = artifact.get("redaction_confirmed") is True
            attachments[key] = {
                "attachment_id": key,
                "path": artifact.get("path"),
                "sha256": artifact.get("sha256"),
                "media_type": artifact.get("media_type") or "application/octet-stream",
                "source_claim_id": citation.get("claim_id"),
                **classification,
                "redaction_confirmed": redaction_confirmed,
                "release_ready": not classification["redaction_required"]
                or redaction_confirmed,
            }
    return sorted(attachments.values(), key=lambda item: item["attachment_id"])


def latest_release_preview(case_id: str) -> dict[str, Any] | None:
    _ensure_storage()
    session = database.Session()
    try:
        row = (
            session.query(database.AuditLog)
            .filter_by(action=ACTION, target_value=case_id)
            .order_by(database.AuditLog.created_at.desc(), database.AuditLog.id.desc())
            .first()
        )
        if row is None:
            return None
        return {
            **_json_details(row),
            "preview_record_id": row.id,
            "acknowledged_by": row.actor,
            "acknowledged_at": row.created_at.isoformat() if row.created_at else None,
        }
    finally:
        session.close()


def build_release_package_preview(case_id: str) -> dict[str, Any]:
    export_package = _latest_export(case_id)
    authorization = latest_release_authorization(case_id)
    blockers: list[dict[str, Any]] = []
    if export_package is None:
        blockers.append({"key": "generated_v21_export_required"})
    if authorization is None:
        blockers.append({"key": "release_authorization_required"})
    if export_package and authorization:
        if authorization.get("export_package_id") != export_package.get(
            "export_package_id"
        ):
            blockers.append({"key": "release_authorization_export_mismatch"})
        if authorization.get("export_package_sha256") != export_package.get(
            "export_package_sha256"
        ):
            blockers.append({"key": "release_authorization_hash_mismatch"})

    sections = _sections(export_package or {})
    attachments = _attachments(export_package or {})
    for section in sections:
        if not section["release_ready"]:
            blockers.append(
                {
                    "key": "section_redaction_required",
                    "section_id": section["section_id"],
                    "matches": section["sensitivity_matches"],
                }
            )
    for attachment in attachments:
        if not attachment["release_ready"]:
            blockers.append(
                {
                    "key": "attachment_redaction_required",
                    "attachment_id": attachment["attachment_id"],
                    "matches": attachment["sensitivity_matches"],
                }
            )

    material = {
        "export_package_id": (export_package or {}).get("export_package_id"),
        "export_package_sha256": (export_package or {}).get("export_package_sha256"),
        "authorization_id": (authorization or {}).get("authorization_id"),
        "authorization_sha256": (authorization or {}).get("authorization_sha256"),
        "recipient_id": (authorization or {}).get("recipient_id"),
        "delivery_channel": (authorization or {}).get("delivery_channel"),
        "sections": sections,
        "attachments": attachments,
    }
    preview_sha256 = _sha(material)
    ready = not blockers and bool(export_package and authorization)
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "case_id": case_id,
        "status": "ready_for_acknowledgement" if ready else "review_required",
        "release_ready": ready,
        "preview_id": f"release-preview-{preview_sha256[:24]}",
        "preview_sha256": preview_sha256,
        "authorized_release": authorization,
        "export_package": export_package,
        "included_sections": sections,
        "included_attachments": attachments,
        "section_count": len(sections),
        "attachment_count": len(attachments),
        "restricted_section_count": sum(
            1 for item in sections if item["classification"] == "restricted"
        ),
        "restricted_attachment_count": sum(
            1 for item in attachments if item["classification"] == "restricted"
        ),
        "blocker_count": len(blockers),
        "blockers": blockers,
        "operator_acknowledgement_required": True,
        "transmission_performed": False,
        "source_export_mutated": False,
        "latest_preview": latest_release_preview(case_id),
        "next_action": "acknowledge_release_preview"
        if ready
        else "resolve_redaction_and_sensitivity_blockers",
    }


def acknowledge_release_package_preview(
    case_id: str,
    *,
    acknowledged: bool,
    operator: str,
    note: str = "",
    ip_address: str | None = None,
) -> dict[str, Any]:
    if acknowledged is not True:
        return {
            "schema": SCHEMA,
            "version": VERSION,
            "case_id": case_id,
            "status": "blocked",
            "blockers": [{"key": "operator_acknowledgement_required"}],
            "transmission_performed": False,
        }
    preview = build_release_package_preview(case_id)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        "case_id": case_id,
        "preview_id": preview["preview_id"],
        "preview_sha256": preview["preview_sha256"],
        "release_ready": preview["release_ready"],
        "export_package_id": (preview.get("export_package") or {}).get(
            "export_package_id"
        ),
        "authorization_id": (preview.get("authorized_release") or {}).get(
            "authorization_id"
        ),
        "recipient_id": (preview.get("authorized_release") or {}).get("recipient_id"),
        "delivery_channel": (preview.get("authorized_release") or {}).get(
            "delivery_channel"
        ),
        "included_sections": preview["included_sections"],
        "included_attachments": preview["included_attachments"],
        "blockers": preview["blockers"],
        "operator_acknowledged": True,
        "note": str(note or "").strip(),
        "transmission_performed": False,
        "source_export_mutated": False,
    }
    _ensure_storage()
    session = database.Session()
    try:
        row = database.AuditLog(
            actor=operator,
            action=ACTION,
            target_value=case_id,
            ip_address=ip_address,
            details=_canonical(event),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        record_id = row.id
        acknowledged_at = row.created_at.isoformat() if row.created_at else None
    finally:
        session.close()
    return {
        **event,
        "status": "acknowledged_ready"
        if preview["release_ready"]
        else "acknowledged_with_blockers",
        "preview_record_id": record_id,
        "acknowledged_by": operator,
        "acknowledged_at": acknowledged_at,
        "next_action": (
            "open_case_delivery_workspace"
            if preview["release_ready"]
            else "resolve_redaction_and_sensitivity_blockers"
        ),
    }
