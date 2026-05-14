from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .dossier_certification_index import certification_index_entry

DISTRIBUTION_ACTION_SCHEMA = "socmint.distribution_actions.v10_14_0"
DISTRIBUTION_ACTIONS_ROOT = Path("exports") / "distribution_actions"
ALLOWED_DISTRIBUTION_ACTIONS = {"approve", "hold", "reject", "mark_reviewed"}


def _safe_component(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in value)[:128]


def distribution_action_log_path(case_id: str, subject_id: str, root: str | Path = DISTRIBUTION_ACTIONS_ROOT) -> Path:
    base = Path(root) / _safe_component(case_id)
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{_safe_component(subject_id)}.jsonl"


def distribution_action_summary_path(case_id: str, subject_id: str, root: str | Path = DISTRIBUTION_ACTIONS_ROOT) -> Path:
    base = Path(root) / _safe_component(case_id)
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{_safe_component(subject_id)}.summary.json"


def _event_id(payload: dict[str, Any]) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()[:24]


def load_distribution_actions(case_id: str, subject_id: str, root: str | Path = DISTRIBUTION_ACTIONS_ROOT) -> list[dict[str, Any]]:
    path = distribution_action_log_path(case_id, subject_id, root=root)
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        events.append(json.loads(line))
    return events


def latest_distribution_action(case_id: str, subject_id: str, root: str | Path = DISTRIBUTION_ACTIONS_ROOT) -> dict[str, Any] | None:
    events = load_distribution_actions(case_id, subject_id, root=root)
    return events[-1] if events else None


def record_distribution_action(
    case_id: str,
    subject_id: str,
    action: str,
    actor: str | None = None,
    note: str | None = None,
    root: str | Path = DISTRIBUTION_ACTIONS_ROOT,
) -> dict[str, Any]:
    if action not in ALLOWED_DISTRIBUTION_ACTIONS:
        raise ValueError(f"Unsupported distribution action: {action}")

    entry = certification_index_entry(case_id=case_id, subject_id=subject_id)
    safe_to_distribute = bool(entry.get("safe_to_distribute"))
    blockers = list(entry.get("blockers", []))
    if action == "approve" and not safe_to_distribute:
        raise ValueError("Cannot approve distribution while certification blockers remain.")

    base_event = {
        "schema": DISTRIBUTION_ACTION_SCHEMA,
        "case_id": case_id,
        "subject_id": subject_id,
        "action": action,
        "actor": actor or "system",
        "note": note or "",
        "created_at": datetime.now(UTC).isoformat(),
        "safe_to_distribute": safe_to_distribute,
        "certified": bool(entry.get("certified")),
        "verification_status": entry.get("verification_status"),
        "gate_decision": entry.get("gate_decision"),
        "blockers": blockers,
        "recommended_bundle": entry.get("recommended_bundle"),
    }
    base_event["event_id"] = _event_id(base_event)

    path = distribution_action_log_path(case_id, subject_id, root=root)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(base_event, sort_keys=True) + "\n")

    summary = distribution_action_summary(case_id, subject_id, root=root)
    distribution_action_summary_path(case_id, subject_id, root=root).write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    return base_event


def distribution_action_summary(case_id: str, subject_id: str, root: str | Path = DISTRIBUTION_ACTIONS_ROOT) -> dict[str, Any]:
    events = load_distribution_actions(case_id, subject_id, root=root)
    latest = events[-1] if events else None
    return {
        "schema": DISTRIBUTION_ACTION_SCHEMA,
        "case_id": case_id,
        "subject_id": subject_id,
        "event_count": len(events),
        "latest_action": latest,
        "approved": bool(latest and latest.get("action") == "approve"),
        "held": bool(latest and latest.get("action") == "hold"),
        "rejected": bool(latest and latest.get("action") == "reject"),
        "reviewed": any(event.get("action") == "mark_reviewed" for event in events),
        "events": events,
    }


def distribution_action_packet(case_id: str, subject_id: str, root: str | Path = DISTRIBUTION_ACTIONS_ROOT) -> dict[str, Any]:
    entry = certification_index_entry(case_id=case_id, subject_id=subject_id)
    actions = distribution_action_summary(case_id, subject_id, root=root)
    return {
        "schema": DISTRIBUTION_ACTION_SCHEMA,
        "case_id": case_id,
        "subject_id": subject_id,
        "certification": entry,
        "actions": actions,
        "distribution_ready": bool(entry.get("safe_to_distribute")) and actions.get("approved") is True,
        "recommended_bundle": entry.get("recommended_bundle") if actions.get("approved") else None,
    }


def distribution_action_markdown(case_id: str, subject_id: str, root: str | Path = DISTRIBUTION_ACTIONS_ROOT) -> str:
    packet = distribution_action_packet(case_id, subject_id, root=root)
    certification = packet["certification"]
    actions = packet["actions"]
    lines = [
        f"# Distribution Action Packet — {case_id} / {subject_id}",
        "",
        f"Certified: {certification.get('certified')}",
        f"Safe to distribute: {certification.get('safe_to_distribute')}",
        f"Operator approved: {actions.get('approved')}",
        f"Distribution ready: {packet.get('distribution_ready')}",
        f"Recommended bundle: {packet.get('recommended_bundle') or 'hold'}",
        "",
        "## Actions",
    ]
    for event in actions.get("events", []):
        lines.append(f"- {event.get('created_at')} — {event.get('actor')} — {event.get('action')} — {event.get('note')}")
    if not actions.get("events"):
        lines.append("- No operator actions recorded.")
    return "\n".join(lines) + "\n"
