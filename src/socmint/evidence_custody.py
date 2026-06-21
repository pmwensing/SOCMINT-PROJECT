from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .evidence_intake import evidence_root
from .evidence_intake import list_evidence
from .evidence_intake import safe_evidence_path
from .evidence_intake import sha256_file


VALID_CUSTODY_ACTIONS = {
    "intake",
    "verify",
    "download",
    "link",
    "unlink",
    "export_attach",
    "note",
    "manual_review",
    "capture",
}


@dataclass
class CustodyEvent:
    event_id: str
    evidence_id: str
    action: str
    actor: str | None
    created_at: str
    sha256: str | None = None
    status: str | None = None
    note: str | None = None
    details: dict[str, Any] | None = None


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def custody_ledger_path() -> Path:
    evidence_root().mkdir(parents=True, exist_ok=True)
    return evidence_root() / "CHAIN-OF-CUSTODY.json"


def verification_report_root() -> Path:
    root = evidence_root() / "verification_reports"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _load_events() -> list[dict[str, Any]]:
    path = custody_ledger_path()

    if not path.exists():
        return []

    try:
        payload = json.loads(path.read_text(errors="replace"))
    except json.JSONDecodeError:
        return []

    if isinstance(payload, dict):
        return list(payload.get("events") or [])

    if isinstance(payload, list):
        return payload

    return []


def _write_events(events: list[dict[str, Any]]) -> None:
    payload = {
        "schema": "socmint.chain_of_custody.v7_4_2",
        "generated_at": utc_now(),
        "count": len(events),
        "events": events,
    }
    custody_ledger_path().write_text(json.dumps(payload, indent=2, sort_keys=True))


def _make_event_id(evidence_id: str, action: str) -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")
    safe_id = evidence_id.replace("/", "_").replace(":", "_")
    return f"{stamp}-{safe_id[:16]}-{action}"


def record_custody_event(
    evidence_id: str,
    action: str,
    actor: str | None = None,
    sha256: str | None = None,
    status: str | None = None,
    note: str | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if action not in VALID_CUSTODY_ACTIONS:
        raise ValueError(f"Invalid custody action: {action}")

    if not evidence_id:
        raise ValueError("evidence_id required")

    event = CustodyEvent(
        event_id=_make_event_id(evidence_id, action),
        evidence_id=evidence_id,
        action=action,
        actor=actor,
        created_at=utc_now(),
        sha256=sha256,
        status=status,
        note=note,
        details=details or {},
    )

    events = _load_events()
    events.append(asdict(event))
    _write_events(events)

    return asdict(event)


def list_custody_events(
    evidence_id: str | None = None,
    action: str | None = None,
) -> list[dict[str, Any]]:
    events = _load_events()

    if evidence_id:
        events = [event for event in events if event.get("evidence_id") == evidence_id]

    if action:
        events = [event for event in events if event.get("action") == action]

    return events


def custody_payload(
    evidence_id: str | None = None,
    action: str | None = None,
) -> dict[str, Any]:
    events = list_custody_events(evidence_id=evidence_id, action=action)
    evidence = list_evidence()

    return {
        "schema": "socmint.chain_of_custody_payload.v7_4_2",
        "generated_at": utc_now(),
        "event_count": len(events),
        "evidence_count": len(evidence),
        "events": events,
        "evidence": evidence,
        "actions": sorted(VALID_CUSTODY_ACTIONS),
    }


def verify_evidence_item(item: dict[str, Any]) -> dict[str, Any]:
    stored_name = str(item.get("stored_name") or "")
    expected_sha = str(item.get("sha256") or "")
    evidence_id = str(item.get("evidence_id") or expected_sha[:16])

    try:
        path = safe_evidence_path(stored_name)
    except (FileNotFoundError, ValueError) as exc:
        return {
            "evidence_id": evidence_id,
            "stored_name": stored_name,
            "original_name": item.get("original_name"),
            "expected_sha256": expected_sha,
            "current_sha256": None,
            "verified": False,
            "status": "missing",
            "error": str(exc),
        }

    current_sha = sha256_file(path)
    verified = bool(expected_sha and current_sha == expected_sha)

    return {
        "evidence_id": evidence_id,
        "stored_name": stored_name,
        "original_name": item.get("original_name"),
        "expected_sha256": expected_sha,
        "current_sha256": current_sha,
        "verified": verified,
        "status": "ok" if verified else "hash_mismatch",
        "size_bytes": path.stat().st_size,
        "path": str(path),
    }


def verify_all_evidence(
    case_id: str | None = None,
    subject_id: int | None = None,
    actor: str | None = None,
    write_report: bool = True,
) -> dict[str, Any]:
    evidence_items = list_evidence(case_id=case_id, subject_id=subject_id)

    results = []
    for item in evidence_items:
        result = verify_evidence_item(item)
        results.append(result)
        record_custody_event(
            evidence_id=str(result.get("evidence_id")),
            action="verify",
            actor=actor,
            sha256=result.get("current_sha256"),
            status=result.get("status"),
            note="hash verification",
            details={
                "expected_sha256": result.get("expected_sha256"),
                "verified": result.get("verified"),
                "stored_name": result.get("stored_name"),
            },
        )

    verified_count = sum(1 for item in results if item.get("verified"))
    failed_count = len(results) - verified_count

    payload = {
        "schema": "socmint.hash_verification_report.v7_4_2",
        "generated_at": utc_now(),
        "case_id": case_id,
        "subject_id": subject_id,
        "checked_count": len(results),
        "verified_count": verified_count,
        "failed_count": failed_count,
        "results": results,
    }

    if write_report:
        stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        report_path = verification_report_root() / f"HASH-VERIFY-{stamp}.json"
        report_path.write_text(json.dumps(payload, indent=2, sort_keys=True))
        payload["report_path"] = str(report_path)

        md_path = verification_report_root() / f"HASH-VERIFY-{stamp}.md"
        md_path.write_text(render_verification_markdown(payload))
        payload["markdown_path"] = str(md_path)

    return payload


def render_verification_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Evidence Hash Verification Report",
        "",
        f"- Generated: `{payload.get('generated_at')}`",
        f"- Case ID: `{payload.get('case_id')}`",
        f"- Subject ID: `{payload.get('subject_id')}`",
        f"- Checked: `{payload.get('checked_count')}`",
        f"- Verified: `{payload.get('verified_count')}`",
        f"- Failed: `{payload.get('failed_count')}`",
        "",
        "## Results",
        "",
    ]

    for item in payload.get("results") or []:
        lines.extend(
            [
                f"### {item.get('original_name') or item.get('stored_name')}",
                "",
                f"- Evidence ID: `{item.get('evidence_id')}`",
                f"- Status: `{item.get('status')}`",
                f"- Verified: `{item.get('verified')}`",
                f"- Expected SHA-256: `{item.get('expected_sha256')}`",
                f"- Current SHA-256: `{item.get('current_sha256')}`",
                f"- Stored name: `{item.get('stored_name')}`",
                "",
            ]
        )

    return "\n".join(lines).rstrip() + "\n"


def chain_of_custody_report(
    evidence_id: str | None = None,
    write_report: bool = True,
) -> dict[str, Any]:
    payload = custody_payload(evidence_id=evidence_id)

    if write_report:
        stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        name = f"CHAIN-OF-CUSTODY-{stamp}"
        if evidence_id:
            safe_id = evidence_id.replace("/", "_").replace(":", "_")
            name = f"CHAIN-OF-CUSTODY-{safe_id}-{stamp}"

        report_path = verification_report_root() / f"{name}.json"
        report_path.write_text(json.dumps(payload, indent=2, sort_keys=True))
        payload["report_path"] = str(report_path)

        md_path = verification_report_root() / f"{name}.md"
        md_path.write_text(render_custody_markdown(payload))
        payload["markdown_path"] = str(md_path)

    return payload


def render_custody_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Chain-of-Custody Ledger",
        "",
        f"- Generated: `{payload.get('generated_at')}`",
        f"- Evidence count: `{payload.get('evidence_count')}`",
        f"- Event count: `{payload.get('event_count')}`",
        "",
        "## Events",
        "",
    ]

    for event in payload.get("events") or []:
        lines.extend(
            [
                f"### {event.get('event_id')}",
                "",
                f"- Evidence ID: `{event.get('evidence_id')}`",
                f"- Action: `{event.get('action')}`",
                f"- Actor: `{event.get('actor')}`",
                f"- Time: `{event.get('created_at')}`",
                f"- SHA-256: `{event.get('sha256')}`",
                f"- Status: `{event.get('status')}`",
                f"- Note: {event.get('note') or ''}",
                "",
            ]
        )

    return "\n".join(lines).rstrip() + "\n"
