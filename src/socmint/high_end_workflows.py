from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from . import database as db
from .evidence import assertion_review_queue, connector_quality_metrics
from .evidence_custody import record_custody_event
from .evidence_intake import evidence_root
from .jobs import scan_job_health
from .report_export_center import export_center_payload
from .spine import build_dossier
from .ultimate_dossier import ultimate_dossier_payload
from .connectors import CONNECTORS


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _json_loads(value: str | None, default: Any) -> Any:
    try:
        return json.loads(value or "")
    except json.JSONDecodeError:
        return default


def _safe_slug(value: str) -> str:
    parsed = urlparse(value)
    raw = parsed.netloc or parsed.path or value or "capture"
    safe = "".join(char if char.isalnum() else "-" for char in raw.lower())
    return safe.strip("-")[:80] or "capture"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def capture_root() -> Path:
    root = evidence_root() / "captures"
    root.mkdir(parents=True, exist_ok=True)
    return root


def default_scope() -> dict[str, Any]:
    return {
        "schema": "socmint.responsible_use_scope.v8_0",
        "authorization_banner": (
            "Use only on targets you are authorized to investigate."
        ),
        "allowed_targets": [],
        "blocked_targets": [],
        "rate_limits": {
            "captures_per_hour": 60,
            "connector_runs_per_hour": 120,
            "exports_per_hour": 30,
        },
        "sensitive_redaction_default": True,
        "export_warning": "Review sensitive data and authorization before export.",
    }


def load_scope() -> dict[str, Any]:
    row = db.get_responsible_use_scope()
    if not row:
        row = db.save_responsible_use_scope(default_scope())
    payload = _json_loads(row.payload_json, {})
    return {**default_scope(), **payload, "updated_at": row.updated_at.isoformat()}


def save_scope(payload: dict[str, Any], actor: str | None = None) -> dict[str, Any]:
    merged = {**default_scope(), **(payload or {})}
    row = db.save_responsible_use_scope(merged, actor=actor)
    return {**merged, "updated_at": row.updated_at.isoformat()}


def scope_review(target: str) -> dict[str, Any]:
    scope = load_scope()
    text = str(target or "").lower()
    blocked = [str(item).lower() for item in scope.get("blocked_targets") or []]
    allowed = [str(item).lower() for item in scope.get("allowed_targets") or []]
    if any(item and item in text for item in blocked):
        state = "blocked"
        reason = "Target matches blocked scope."
    elif allowed and not any(item and item in text for item in allowed):
        state = "needs_authorization_review"
        reason = "Target does not match configured allowed scope."
    else:
        state = "authorized"
        reason = "Target is authorized or no allowlist is configured."
    return {
        "schema": "socmint.scope_review.v8_0",
        "target": target,
        "state": state,
        "reason": reason,
        "authorization_banner": scope.get("authorization_banner"),
        "redaction_default": bool(scope.get("sensitive_redaction_default", True)),
    }


def gate_action(action: str, target: str, actor: str | None = None) -> dict[str, Any]:
    review = scope_review(target)
    allowed = review["state"] != "blocked"
    event_id = db.record_policy_gate_event(
        action,
        allowed,
        [review["reason"]],
        {"target": target, "scope_state": review["state"]},
        actor=actor,
    )
    return {
        "schema": "socmint.responsible_use_gate.v8_0",
        "event_id": event_id,
        "allowed": allowed,
        "scope_review": review,
        "rate_limits": load_scope().get("rate_limits"),
    }


def create_case(
    title: str,
    case_key: str | None = None,
    tags: list[str] | None = None,
    actor: str | None = None,
) -> dict[str, Any]:
    key = case_key or _safe_slug(title)
    row = db.upsert_case_record(key, title, tags=tags or [], actor=actor)
    db.add_case_event(key, "case_create", actor=actor)
    return case_payload(row.case_key)


def update_case(
    case_key: str,
    actor: str | None = None,
    **changes: Any,
) -> dict[str, Any]:
    row = db.get_case_record(case_key)
    if not row:
        raise ValueError("Case not found.")
    payload = _json_loads(row.payload_json, {})
    payload.update(changes.get("payload") or {})
    db.upsert_case_record(
        case_key,
        changes.get("title") or row.title,
        tags=changes.get("tags") or _json_loads(row.tags_json, []),
        status=changes.get("status") or row.status,
        priority=changes.get("priority") or row.priority,
        review_state=changes.get("review_state") or row.review_state,
        due_at=changes.get("due_at", row.due_at),
        payload=payload,
        actor=actor,
    )
    db.add_case_event(case_key, "case_update", payload=changes, actor=actor)
    return case_payload(case_key)


def add_case_event(
    case_key: str,
    event_type: str,
    actor: str | None = None,
    **payload: Any,
) -> dict[str, Any]:
    db.add_case_event(
        case_key,
        event_type,
        subject_id=payload.get("subject_id"),
        note=payload.get("note") or payload.get("comment"),
        assignee=payload.get("assignee"),
        payload=payload,
        actor=actor,
    )
    return case_payload(case_key)


def case_payload(case_key: str) -> dict[str, Any]:
    row = db.get_case_record(case_key)
    if not row:
        raise ValueError("Case not found.")
    events = db.list_case_events(case_key, limit=500)
    captures = db.list_evidence_captures(case_key=case_key, limit=500)
    return {
        "schema": "socmint.case.v8_0",
        "case_key": row.case_key,
        "title": row.title,
        "status": row.status,
        "priority": row.priority,
        "review_state": row.review_state,
        "due_at": row.due_at,
        "tags": _json_loads(row.tags_json, []),
        "payload": _json_loads(row.payload_json, {}),
        "subjects": sorted(
            {
                event.subject_id
                for event in events
                if event.subject_id is not None
            }
        ),
        "events": [_case_event_dict(event) for event in events],
        "captures": [_capture_dict(item) for item in captures],
        "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
    }


def list_cases(limit: int = 100) -> list[dict[str, Any]]:
    return [case_payload(row.case_key) for row in db.list_case_records(limit=limit)]


def _case_event_dict(event) -> dict[str, Any]:
    return {
        "id": event.id,
        "case_id": event.case_id,
        "event_type": event.event_type,
        "subject_id": event.subject_id,
        "note": event.note,
        "assignee": event.assignee,
        "payload": _json_loads(event.payload_json, {}),
        "actor": event.actor,
        "created_at": event.created_at.isoformat(),
    }


def capture_snapshot(
    url: str,
    html: str,
    case_key: str | None = None,
    subject_id: int | None = None,
    actor: str | None = None,
    headers: dict[str, Any] | None = None,
    cookies: list[dict[str, Any]] | None = None,
    screenshot_bytes: bytes | None = None,
    pdf_bytes: bytes | None = None,
) -> dict[str, Any]:
    gate = gate_action("capture", url, actor=actor)
    if not gate["allowed"]:
        raise PermissionError(gate["scope_review"]["reason"])

    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S_%f")
    slug = _safe_slug(url)
    artifacts = [
        ("html", f"{stamp}_{slug}.html", (html or "").encode(), "text/html"),
    ]
    if screenshot_bytes:
        artifacts.append(("screenshot", f"{stamp}_{slug}.png", screenshot_bytes, "image/png"))
    if pdf_bytes:
        artifacts.append(("pdf", f"{stamp}_{slug}.pdf", pdf_bytes, "application/pdf"))

    stored = []
    for artifact_type, name, data, mime_type in artifacts:
        path = capture_root() / name
        path.write_bytes(data)
        digest = _sha256_bytes(data)
        capture_id = f"{digest[:16]}-{artifact_type}"
        item = db.create_evidence_capture(
            capture_id,
            url,
            artifact_type,
            str(path),
            digest,
            mime_type,
            len(data),
            case_key=case_key,
            subject_id=subject_id,
            headers=headers or {},
            cookies=cookies or [],
            payload={"automation": capture_automation_plan(url)},
            actor=actor,
        )
        record_custody_event(
            evidence_id=capture_id,
            action="capture",
            actor=actor,
            sha256=digest,
            status="stored",
            details={"url": url, "case_key": case_key, "subject_id": subject_id},
        )
        if case_key:
            db.add_case_event(
                case_key,
                "capture_attach",
                subject_id=subject_id,
                payload={"capture_id": capture_id, "sha256": digest},
                actor=actor,
            )
        stored.append(_capture_dict(item))

    return {
        "schema": "socmint.evidence_capture.v8_0",
        "url": url,
        "case_key": case_key,
        "subject_id": subject_id,
        "captures": stored,
        "gate": gate,
    }


def _capture_dict(item) -> dict[str, Any]:
    return {
        "capture_id": item.capture_id,
        "url": item.url,
        "case_key": item.case_key,
        "subject_id": item.subject_id,
        "artifact_type": item.artifact_type,
        "path": item.path,
        "sha256": item.sha256,
        "mime_type": item.mime_type,
        "size_bytes": item.size_bytes,
        "headers": _json_loads(item.headers_json, {}),
        "cookies": _json_loads(item.cookies_json, []),
        "payload": _json_loads(item.payload_json, {}),
        "actor": item.actor,
        "created_at": item.created_at.isoformat(),
    }


def list_capture_artifacts(
    case_key: str | None = None,
    subject_id: int | None = None,
) -> list[dict[str, Any]]:
    return [
        _capture_dict(item)
        for item in db.list_evidence_captures(
            case_key=case_key,
            subject_id=subject_id,
            limit=500,
        )
    ]


def verify_capture(capture_id: str) -> dict[str, Any]:
    item = db.get_evidence_capture(capture_id)
    if not item:
        return {"capture_id": capture_id, "valid": False, "reason": "not_found"}
    path = Path(item.path)
    if not path.exists():
        return {"capture_id": capture_id, "valid": False, "reason": "missing_file"}
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "schema": "socmint.capture_verification.v8_0",
        "capture_id": capture_id,
        "valid": digest == item.sha256,
        "expected_sha256": item.sha256,
        "actual_sha256": digest,
    }


def capture_automation_plan(url: str) -> dict[str, Any]:
    return {
        "schema": "socmint.capture_automation_plan.v8_0",
        "url": url,
        "engine": "playwright",
        "steps": [
            "open_page",
            "wait_network_idle",
            "capture_headers",
            "capture_cookies_metadata",
            "full_page_screenshot",
            "export_pdf",
            "export_mhtml_or_warc",
            "hash_artifacts",
            "record_chain_of_custody",
        ],
        "retry_policy": {"attempts": 3, "backoff": "linear"},
    }


def analyst_workbench_payload(limit: int = 100) -> dict[str, Any]:
    queue = assertion_review_queue(limit=limit)
    connectors = connector_quality_metrics()
    cases = list_cases(limit=limit)
    captures = list_capture_artifacts()[:limit]
    blockers = [
        item
        for item in queue
        if "unreviewed" in item.get("reasons", [])
        or "single_source" in item.get("reasons", [])
    ]
    return {
        "schema": "socmint.analyst_workbench.v8_0",
        "queues": {
            "high_risk": [
                item
                for item in queue
                if item.get("confidence", 0) >= 0.8
                or item.get("confidence", 0) < 0.45
            ],
            "single_source": [
                item for item in queue if "single_source" in item.get("reasons", [])
            ],
            "export_blockers": blockers,
            "sensitive": [
                item
                for item in queue
                if item.get("type") in {"email", "phone", "address", "location"}
            ],
        },
        "cases": cases,
        "captures": captures,
        "connector_trust": connectors,
        "jobs": scan_job_health(),
        "policy": policy_events_payload(),
        "scope": load_scope(),
    }


def policy_events_payload(limit: int = 100) -> dict[str, Any]:
    return {
        "schema": "socmint.policy_events.v8_0",
        "events": [
            {
                "id": event.id,
                "action": event.action,
                "allowed": bool(event.allowed),
                "reasons": _json_loads(event.reasons_json, []),
                "payload": _json_loads(event.payload_json, {}),
                "actor": event.actor,
                "created_at": event.created_at.isoformat(),
            }
            for event in db.list_policy_gate_events(limit=limit)
        ],
    }


def connector_marketplace_payload() -> dict[str, Any]:
    trust = {row.get("connector"): row for row in connector_quality_metrics()}
    return {
        "schema": "socmint.connector_marketplace.v8_0",
        "connectors": [
            {
                "name": name,
                "target_types": spec.target_types,
                "install_status": "registered",
                "trust_badge": (
                    "trusted"
                    if trust.get(name, {}).get("reliability_score", 0) >= 0.75
                    else "needs_review"
                    if name in trust
                    else "unrated"
                ),
                "capability_tags": list(spec.target_types),
                "fixture_runner": "/api/v1/connectors/sdk/validate",
                "trust": trust.get(name, {}),
            }
            for name, spec in sorted(CONNECTORS.items())
        ],
    }


def entity_resolution_lab_payload(subject_id: int) -> dict[str, Any]:
    dossier = ultimate_dossier_payload(subject_id)
    resolution = dossier.get("resolution") or {}
    delta = resolution.get("confidence_delta_inputs") or {}
    return {
        "schema": "socmint.entity_resolution_lab.v8_0",
        "subject_id": subject_id,
        "classification": resolution.get("classification") or resolution.get("label"),
        "confidence": resolution.get("confidence"),
        "explanation": resolution.get("explanation"),
        "confidence_deltas": delta,
        "source_contribution_chart": [
            {"name": key, "value": value} for key, value in sorted(delta.items())
        ],
        "contradictions": dossier.get("contradictions") or [],
        "manual_override": {"enabled": True, "audit_required": True},
    }


def graph_canvas_payload(subject_id: int) -> dict[str, Any]:
    dossier = build_dossier(subject_id)
    return {
        "schema": "socmint.graph_canvas.v8_0",
        "subject_id": subject_id,
        "nodes": dossier.get("seeds", []) + dossier.get("assertions", []),
        "edges": dossier.get("evidence_links", []),
        "controls": {
            "confidence_slider": True,
            "time_slider": True,
            "node_grouping": ["type", "source", "confidence"],
            "evidence_side_panel": True,
            "contradiction_overlays": True,
        },
    }


def build_export_manifest(
    subject_id: int | None = None,
    case_key: str | None = None,
    redacted: bool = True,
    actor: str | None = None,
) -> dict[str, Any]:
    gate = gate_action("export", case_key or str(subject_id or "all"), actor=actor)
    payload = {
        "subject_id": subject_id,
        "case": case_payload(case_key) if case_key else None,
        "dossier": ultimate_dossier_payload(subject_id) if subject_id else None,
        "export_center": export_center_payload(),
        "redacted": redacted,
    }
    stable = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    digest = hashlib.sha256(stable).hexdigest()
    return {
        "schema": "socmint.export_builder_manifest.v8_0",
        "generated_at": utc_now(),
        "subject_id": subject_id,
        "case_key": case_key,
        "redacted": redacted,
        "formats": ["html", "pdf", "json", "csv"],
        "payload_sha256": digest,
        "signed_manifest": hashlib.sha256(f"{digest}:socmint".encode()).hexdigest(),
        "redaction_presets": ["client", "court", "internal"],
        "export_blockers": analyst_workbench_payload().get("queues", {}).get(
            "export_blockers",
            [],
        ),
        "gate": gate,
    }
