from __future__ import annotations

from typing import Any

from . import database
from .dossier_assembly_workspace_v21_0 import _canonical, _ensure_storage, _json_details, _sha
from .draft_dossier_revision_v31_2 import current_draft_revisions
from .publication_candidate_v31_1 import find_candidate

SCHEMA = "socmint.editorial_validation.v31_3"
VERSION = "v31.3.0"
ACTION = "draft_dossier_editorial_validation_recorded"
REQUIRED_ACKNOWLEDGEMENTS = (
    "provenance_reviewed",
    "privacy_reviewed",
    "legal_basis_confirmed",
    "audience_scope_confirmed",
)


def blocked(key: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "blocked",
        "blockers": [{"key": key}],
        "draft_revision_mutated": False,
        "release_approval_performed": False,
        "publication_performed": False,
        "published_revision_mutated": False,
    }


def editorial_validation_history() -> list[dict[str, Any]]:
    _ensure_storage()
    session = database.Session()
    try:
        rows = (
            session.query(database.AuditLog)
            .filter_by(action=ACTION)
            .order_by(database.AuditLog.created_at.asc(), database.AuditLog.id.asc())
            .all()
        )
        return [
            {
                **_json_details(row),
                "audit_record_id": row.id,
                "actor": row.actor,
                "recorded_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
    finally:
        session.close()


def validations_for_revision(draft_revision_id: str | None = None) -> list[dict[str, Any]]:
    rows = editorial_validation_history()
    if not draft_revision_id:
        return rows
    return [row for row in rows if row.get("draft_revision_id") == draft_revision_id]


def current_editorial_validations() -> list[dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    histories: dict[str, list[dict[str, Any]]] = {}
    for item in editorial_validation_history():
        validation_id = str(item.get("editorial_validation_id") or "")
        if not validation_id:
            continue
        histories.setdefault(validation_id, []).append(item)
        latest[validation_id] = dict(item)
    for validation_id, item in latest.items():
        item["validation_history"] = histories.get(validation_id, [])
    return sorted(latest.values(), key=lambda item: str(item.get("editorial_validation_id")))


def find_draft_revision(draft_revision_id: str) -> dict[str, Any] | None:
    for item in current_draft_revisions():
        if item.get("draft_revision_id") == draft_revision_id:
            return item
    return None


def _record(actor: str, target_value: str, event: dict[str, Any], ip_address: str | None) -> dict[str, Any]:
    _ensure_storage()
    session = database.Session()
    try:
        row = database.AuditLog(
            actor=actor,
            action=ACTION,
            target_value=target_value,
            ip_address=ip_address,
            details=_canonical(event),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return {
            **event,
            "audit_record_id": row.id,
            "actor": actor,
            "recorded_at": row.created_at.isoformat() if row.created_at else None,
        }
    finally:
        session.close()


def _gate_checks(
    revision: dict[str, Any],
    candidate: dict[str, Any],
    acknowledgements: dict[str, Any],
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []

    def add(key: str, passed: bool, detail: str) -> None:
        checks.append({"key": key, "passed": bool(passed), "detail": detail})

    source_manifest = revision.get("source_manifest") or {}
    contribution_entry = revision.get("candidate_contribution_entry") or {}
    sections = revision.get("draft_sections") or []
    release_scope = str(candidate.get("release_scope") or "").strip().lower()

    add("revision_state_is_draft", revision.get("revision_state") == "draft", "Revision must remain draft.")
    add("candidate_is_proposed", candidate.get("candidate_state") == "proposed", "Candidate must remain proposed.")
    add(
        "candidate_hash_matches",
        revision.get("publication_candidate_sha256") == candidate.get("publication_candidate_sha256"),
        "Draft candidate hash must match the current candidate binding.",
    )
    add("source_manifest_present", bool(source_manifest), "A source manifest is required.")
    add(
        "source_manifest_hash_present",
        bool(revision.get("source_manifest_sha256")),
        "The source manifest must be hashed.",
    )
    add("draft_sections_present", bool(sections), "At least one draft section is required.")
    add(
        "draft_sections_hash_present",
        bool(revision.get("draft_sections_sha256")),
        "The draft section snapshot must be hashed.",
    )
    add(
        "candidate_contribution_entry_present",
        bool(contribution_entry.get("dossier_contribution_id")),
        "The approved contribution entry is required.",
    )
    add(
        "target_section_present",
        bool(revision.get("target_section")),
        "A target dossier section is required.",
    )
    add(
        "assembly_gaps_resolved",
        int(revision.get("assembly_gap_count") or 0) == 0,
        "All dossier assembly gaps must be resolved before release review.",
    )
    add(
        "source_dossier_ready",
        revision.get("source_dossier_status") == "ready_for_arrangement",
        "The source dossier workspace must be ready for arrangement.",
    )
    for key in REQUIRED_ACKNOWLEDGEMENTS:
        add(key, acknowledgements.get(key) is True, f"Policy acknowledgement `{key}` is required.")
    if release_scope in {"external", "public", "third_party", "third-party"}:
        add(
            "redaction_reviewed",
            acknowledgements.get("redaction_reviewed") is True,
            "External release scope requires explicit redaction review.",
        )
    return checks


def run_editorial_validation(
    *,
    actor: str,
    draft_revision_id: str,
    editorial_summary: str,
    policy_acknowledgements: dict[str, Any],
    reason: str,
    confirmed: bool,
    ip_address: str | None = None,
) -> dict[str, Any]:
    draft_revision_id = str(draft_revision_id or "").strip()
    editorial_summary = str(editorial_summary or "").strip()
    reason = str(reason or "").strip()
    acknowledgements = (
        dict(policy_acknowledgements)
        if isinstance(policy_acknowledgements, dict)
        else {}
    )

    revision = find_draft_revision(draft_revision_id)
    if revision is None:
        return blocked("draft_dossier_revision_required")
    candidate = find_candidate(str(revision.get("publication_candidate_id") or ""))
    if candidate is None:
        return blocked("publication_candidate_binding_required")
    if confirmed is not True:
        return blocked("explicit_editorial_validation_confirmation_required")
    if not editorial_summary:
        return blocked("editorial_summary_required")
    if not reason:
        return blocked("administrative_reason_required")

    checks = _gate_checks(revision, candidate, acknowledgements)
    blockers = [
        {"key": item["key"], "detail": item["detail"]}
        for item in checks
        if not item["passed"]
    ]
    gate_status = "passed" if not blockers else "needs_revision"
    binding = {
        "draft_revision_id": draft_revision_id,
        "draft_revision_sha256": revision.get("draft_revision_sha256"),
        "publication_candidate_id": revision.get("publication_candidate_id"),
        "publication_candidate_sha256": revision.get("publication_candidate_sha256"),
        "source_manifest_sha256": revision.get("source_manifest_sha256"),
        "draft_sections_sha256": revision.get("draft_sections_sha256"),
    }
    content = {
        "event_type": ACTION,
        "gate_status": gate_status,
        "draft_revision_id": draft_revision_id,
        "draft_revision_sha256": revision.get("draft_revision_sha256"),
        "publication_candidate_id": revision.get("publication_candidate_id"),
        "case_id": revision.get("case_id"),
        "subject_id": revision.get("subject_id"),
        "release_scope": candidate.get("release_scope"),
        "editorial_summary": editorial_summary,
        "reason": reason,
        "policy_acknowledgements": acknowledgements,
        "gate_checks": checks,
        "gate_check_count": len(checks),
        "passed_check_count": sum(1 for item in checks if item["passed"]),
        "blockers": blockers,
        "blocker_count": len(blockers),
        "validation_binding": binding,
        "validation_binding_sha256": _sha(binding),
        "draft_revision_mutated": False,
        "release_approval_performed": False,
        "publication_performed": False,
        "published_revision_mutated": False,
    }
    digest = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "editorial_validation_id": f"editorial-validation-{digest[:24]}",
        "editorial_validation_sha256": digest,
    }
    if any(
        item.get("editorial_validation_sha256") == digest
        for item in editorial_validation_history()
    ):
        return blocked("editorial_validation_already_exists")

    result = _record(actor, event["editorial_validation_id"], event, ip_address)
    return {
        **result,
        "status": "editorial_validation_recorded",
        "next_action": (
            "request_human_release_approval"
            if gate_status == "passed"
            else "revise_draft_dossier_revision"
        ),
    }
