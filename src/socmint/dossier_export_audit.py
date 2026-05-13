from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .dossier_export_store import DEFAULT_EXPORT_ROOT
from .dossier_export_store import export_directory
from .dossier_export_store import safe_slug

DOSSIER_EXPORT_AUDIT_SCHEMA = "socmint.dossier_export_audit.v10_7_0"
AUDIT_FILENAME = "audit.jsonl"
ALLOWED_AUDIT_ACTIONS = {
    "export_created",
    "manifest_read",
    "download_resolved",
    "download_blocked",
    "download_missing",
}


def audit_path(case_id: str, subject_id: str, root: str | Path = DEFAULT_EXPORT_ROOT) -> Path:
    return export_directory(subject_id, case_id, root=root) / AUDIT_FILENAME


def audit_event(
    action: str,
    case_id: str,
    subject_id: str,
    actor: str | None = None,
    detail: dict[str, Any] | None = None,
    root: str | Path = DEFAULT_EXPORT_ROOT,
) -> dict[str, Any]:
    normalized_action = action if action in ALLOWED_AUDIT_ACTIONS else "download_blocked"
    event = {
        "schema": DOSSIER_EXPORT_AUDIT_SCHEMA,
        "timestamp": datetime.now(UTC).isoformat(),
        "action": normalized_action,
        "case_id": case_id,
        "subject_id": subject_id,
        "actor": actor or "system",
        "detail": detail or {},
    }
    path = audit_path(case_id, subject_id, root=root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")
    return event


def read_audit_events(case_id: str, subject_id: str, root: str | Path = DEFAULT_EXPORT_ROOT) -> list[dict[str, Any]]:
    path = audit_path(case_id, subject_id, root=root)
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            events.append(
                {
                    "schema": DOSSIER_EXPORT_AUDIT_SCHEMA,
                    "action": "invalid_audit_line",
                    "case_id": case_id,
                    "subject_id": subject_id,
                    "actor": "system",
                    "detail": {"line": line},
                }
            )
    return events


def audit_summary(case_id: str, subject_id: str, root: str | Path = DEFAULT_EXPORT_ROOT) -> dict[str, Any]:
    events = read_audit_events(case_id, subject_id, root=root)
    counts: dict[str, int] = {}
    for event in events:
        action = str(event.get("action", "unknown"))
        counts[action] = counts.get(action, 0) + 1
    return {
        "schema": DOSSIER_EXPORT_AUDIT_SCHEMA,
        "case_id": case_id,
        "subject_id": subject_id,
        "event_count": len(events),
        "counts": counts,
        "audit_path": str(audit_path(case_id, subject_id, root=root)),
    }


def audit_index(root: str | Path = DEFAULT_EXPORT_ROOT) -> dict[str, Any]:
    root_path = Path(root)
    entries = []
    if root_path.exists():
        for path in sorted(root_path.glob(f"*/*/{AUDIT_FILENAME}")):
            try:
                case_id = path.parents[1].name
                subject_id = path.parent.name
            except IndexError:
                case_id = "unknown"
                subject_id = "unknown"
            events = read_audit_events(subject_id=subject_id, case_id=case_id, root=root_path)
            entries.append(
                {
                    "case_slug": safe_slug(case_id),
                    "subject_slug": safe_slug(subject_id),
                    "audit_path": str(path),
                    "event_count": len(events),
                }
            )
    return {
        "schema": DOSSIER_EXPORT_AUDIT_SCHEMA,
        "status": "ready",
        "entry_count": len(entries),
        "entries": entries,
    }
