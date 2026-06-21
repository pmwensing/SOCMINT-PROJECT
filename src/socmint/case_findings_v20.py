from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from . import database

FINDING_EVENT_ACTION = "case_finding_event"
FINDING_SCHEMA = "socmint.case_finding.v20"
FINDING_WORKSPACE_SCHEMA = "socmint.case_findings_workspace.v20_0"
DOSSIER_PACKAGE_SCHEMA = "socmint.case_findings_dossier_package.v20_5"
VERSION = "v20.7.0"
ALLOWED_CONFIDENCE = {"low", "medium", "high"}
APPROVAL_ACTIONS = {"approve", "reject", "return_to_analyst"}


def _ensure_storage() -> None:
    database.ensure_configured()
    database.AuditLog.__table__.create(bind=database.engine, checkfirst=True)


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _details(row) -> dict[str, Any]:
    try:
        value = json.loads(row.details or "{}")
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _record_event(case_id: str, actor: str, event: dict[str, Any], ip_address=None):
    _ensure_storage()
    session = database.Session()
    try:
        row = database.AuditLog(
            actor=actor,
            action=FINDING_EVENT_ACTION,
            target_value=case_id,
            ip_address=ip_address,
            details=_canonical(event),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return row
    finally:
        session.close()


def _events(case_id: str) -> list[dict[str, Any]]:
    _ensure_storage()
    session = database.Session()
    try:
        rows = (
            session.query(database.AuditLog)
            .filter_by(action=FINDING_EVENT_ACTION, target_value=case_id)
            .order_by(database.AuditLog.created_at.asc(), database.AuditLog.id.asc())
            .all()
        )
        return [
            {
                **_details(row),
                "event_record_id": row.id,
                "event_actor": row.actor,
                "event_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
    finally:
        session.close()


def _normalize_payload(
    payload: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    safe = deepcopy(payload or {})
    normalized = {
        "text": str(safe.get("text") or "").strip(),
        "confidence": str(safe.get("confidence") or "medium").lower(),
        "provenance": {
            "claim_ids": sorted(
                {str(x) for x in safe.get("claim_ids") or [] if str(x)}
            ),
            "evidence_ids": sorted(
                {str(x) for x in safe.get("evidence_ids") or [] if str(x)}
            ),
            "entity_ids": sorted(
                {str(x) for x in safe.get("entity_ids") or [] if str(x)}
            ),
            "timeline_refs": sorted(
                {str(x) for x in safe.get("timeline_refs") or [] if str(x)}
            ),
        },
        "note": str(safe.get("note") or "").strip(),
    }
    blockers = []
    if not normalized["text"]:
        blockers.append({"key": "finding_text_required"})
    if not normalized["provenance"]["claim_ids"]:
        blockers.append({"key": "reviewed_claim_required"})
    if not normalized["provenance"]["evidence_ids"]:
        blockers.append({"key": "evidence_required"})
    if normalized["confidence"] not in ALLOWED_CONFIDENCE:
        blockers.append({"key": "invalid_confidence"})
    return normalized, blockers


def propose_finding(
    case_id: str, payload: dict[str, Any], *, actor: str, ip_address=None
):
    normalized, blockers = _normalize_payload(payload)
    if blockers:
        return {"status": "blocked", "blockers": blockers}
    identity = {
        "case_id": case_id,
        "text": normalized["text"],
        "provenance": normalized["provenance"],
        "confidence": normalized["confidence"],
        "actor": actor,
    }
    finding_id = f"finding-{_sha(identity)[:24]}"
    event = {
        "schema": FINDING_SCHEMA,
        "version": VERSION,
        "event": "proposed",
        "finding_id": finding_id,
        "case_id": case_id,
        "text": normalized["text"],
        "confidence": normalized["confidence"],
        "provenance": normalized["provenance"],
        "provenance_sha256": _sha(normalized["provenance"]),
        "note": normalized["note"],
    }
    row = _record_event(case_id, actor, event, ip_address)
    return {**event, "status": "proposed", "event_record_id": row.id}


def revise_finding(
    case_id: str,
    finding_id: str,
    payload: dict[str, Any],
    *,
    actor: str,
    ip_address=None,
):
    current = get_finding(case_id, finding_id)
    if not current:
        return {"status": "blocked", "blockers": [{"key": "finding_not_found"}]}
    if current["status"] not in {"proposed", "revision_required", "rejected"}:
        return {"status": "blocked", "blockers": [{"key": "finding_not_revisable"}]}
    provenance = current.get("provenance") or {}
    merged = {
        "text": payload.get("text", current.get("text")),
        "confidence": payload.get("confidence", current.get("confidence")),
        "claim_ids": payload.get("claim_ids", provenance.get("claim_ids", [])),
        "evidence_ids": payload.get("evidence_ids", provenance.get("evidence_ids", [])),
        "entity_ids": payload.get("entity_ids", provenance.get("entity_ids", [])),
        "timeline_refs": payload.get(
            "timeline_refs", provenance.get("timeline_refs", [])
        ),
        "note": payload.get("note", ""),
    }
    normalized, blockers = _normalize_payload(merged)
    if blockers:
        return {"status": "blocked", "blockers": blockers}
    event = {
        "schema": FINDING_SCHEMA,
        "version": VERSION,
        "event": "revised",
        "finding_id": finding_id,
        "case_id": case_id,
        "text": normalized["text"],
        "confidence": normalized["confidence"],
        "provenance": normalized["provenance"],
        "provenance_sha256": _sha(normalized["provenance"]),
        "note": normalized["note"],
    }
    row = _record_event(case_id, actor, event, ip_address)
    return {**event, "status": "proposed", "event_record_id": row.id}


def decide_finding(
    case_id: str, finding_id: str, action: str, *, actor: str, note="", ip_address=None
):
    current = get_finding(case_id, finding_id)
    if not current:
        return {"status": "blocked", "blockers": [{"key": "finding_not_found"}]}
    action = str(action or "").strip()
    if action not in APPROVAL_ACTIONS:
        return {"status": "blocked", "blockers": [{"key": "invalid_supervisor_action"}]}
    if current["status"] not in {"proposed", "revision_required"}:
        return {
            "status": "blocked",
            "blockers": [{"key": "finding_not_pending_approval"}],
        }
    status = {
        "approve": "approved",
        "reject": "rejected",
        "return_to_analyst": "revision_required",
    }[action]
    event = {
        "schema": FINDING_SCHEMA,
        "version": VERSION,
        "event": action,
        "finding_id": finding_id,
        "case_id": case_id,
        "status": status,
        "note": str(note or "").strip(),
    }
    row = _record_event(case_id, actor, event, ip_address)
    return {**event, "event_record_id": row.id}


def list_findings(case_id: str) -> dict[str, Any]:
    latest: dict[str, dict[str, Any]] = {}
    history: dict[str, list[dict[str, Any]]] = {}
    for event in _events(case_id):
        finding_id = event.get("finding_id")
        if not finding_id:
            continue
        history.setdefault(finding_id, []).append(event)
        current = latest.get(finding_id, {})
        if event.get("event") in {"proposed", "revised"}:
            current.update(
                {
                    "finding_id": finding_id,
                    "case_id": case_id,
                    "text": event.get("text"),
                    "confidence": event.get("confidence"),
                    "provenance": event.get("provenance") or {},
                    "provenance_sha256": event.get("provenance_sha256"),
                    "status": "proposed",
                    "created_by": current.get("created_by") or event.get("event_actor"),
                    "updated_by": event.get("event_actor"),
                    "updated_at": event.get("event_at"),
                }
            )
        elif event.get("event") in {"approve", "reject", "return_to_analyst"}:
            current.update(
                {
                    "status": event.get("status"),
                    "supervisor": event.get("event_actor"),
                    "supervisor_note": event.get("note"),
                    "updated_at": event.get("event_at"),
                }
            )
        elif event.get("event") == "promoted":
            current.update(
                {"status": "promoted", "package_id": event.get("package_id")}
            )
        latest[finding_id] = current
    states = ["proposed", "approved", "revision_required", "rejected", "promoted"]
    findings = sorted(
        latest.values(),
        key=lambda item: (item.get("status", ""), item.get("finding_id", "")),
    )
    return {
        "schema": FINDING_WORKSPACE_SCHEMA,
        "version": VERSION,
        "case_id": case_id,
        "findings": findings,
        "history": history,
        "counts": {
            state: sum(1 for item in findings if item.get("status") == state)
            for state in states
        },
        "decision_options": sorted(APPROVAL_ACTIONS),
        "confidence_options": sorted(ALLOWED_CONFIDENCE),
    }


def get_finding(case_id: str, finding_id: str):
    return next(
        (
            item
            for item in list_findings(case_id)["findings"]
            if item["finding_id"] == finding_id
        ),
        None,
    )


def build_dossier_promotion_package(
    case_id: str, *, actor: str, promote=False, ip_address=None
):
    approved = [
        item
        for item in list_findings(case_id)["findings"]
        if item.get("status") == "approved"
    ]
    manifest = [
        {
            "finding_id": item["finding_id"],
            "text": item["text"],
            "confidence": item["confidence"],
            "provenance": item["provenance"],
            "provenance_sha256": item["provenance_sha256"],
        }
        for item in approved
    ]
    package_id = (
        f"dossier-findings-{_sha({'case_id': case_id, 'findings': manifest})[:24]}"
    )
    package = {
        "schema": DOSSIER_PACKAGE_SCHEMA,
        "version": VERSION,
        "case_id": case_id,
        "package_id": package_id,
        "finding_count": len(manifest),
        "findings": manifest,
        "manifest_sha256": _sha(manifest),
        "status": "ready" if manifest else "blocked",
        "next_action": "promote_to_dossier" if manifest else "approve_case_findings",
    }
    if promote and manifest:
        for item in approved:
            _record_event(
                case_id,
                actor,
                {
                    "schema": FINDING_SCHEMA,
                    "version": VERSION,
                    "event": "promoted",
                    "finding_id": item["finding_id"],
                    "case_id": case_id,
                    "package_id": package_id,
                },
                ip_address,
            )
        package.update(status="promoted", next_action="open_dossier_workspace")
    return package


def build_v20_product_checkpoint(routes=None) -> dict[str, Any]:
    required = [
        Path("src/socmint/case_findings_v20.py"),
        Path("src/socmint/case_findings_routes_v20.py"),
        Path("src/socmint/templates/case_findings_workspace_v20.html"),
        Path("src/socmint/static/case_findings_v20.js"),
        Path("scripts/run_v20_7_case_findings_browser_e2e.py"),
    ]
    notes = [list(Path("release").glob(f"V20_{index}_*.md")) for index in range(8)]
    route_strings = {str(rule) for rule in (routes or [])}
    expected_routes = {
        "/case-findings/<case_id>",
        "/api/v1/case-findings/<case_id>",
        "/api/v1/case-findings/<case_id>/proposals",
        "/api/v1/case-findings/<case_id>/dossier-package",
    }
    migrations = [
        path
        for directory in (Path("migrations"), Path("alembic"))
        if directory.exists()
        for path in directory.rglob("*v20*")
    ]
    blockers = []
    if missing := [str(path) for path in required if not path.exists()]:
        blockers.append({"key": "missing_artifacts", "items": missing})
    if missing_notes := [index for index, matches in enumerate(notes) if not matches]:
        blockers.append({"key": "missing_release_notes", "items": missing_notes})
    if routes is not None and (
        missing_routes := sorted(expected_routes - route_strings)
    ):
        blockers.append({"key": "missing_routes", "items": missing_routes})
    if migrations:
        blockers.append(
            {
                "key": "unexpected_migrations",
                "items": [str(path) for path in migrations],
            }
        )
    return {
        "schema": "socmint.case_findings_product_checkpoint.v20_7",
        "version": VERSION,
        "status": "ready_for_browser_validation" if not blockers else "blocked",
        "ready": not blockers,
        "blockers": blockers,
        "checked_at": datetime.now(UTC).isoformat(),
    }
