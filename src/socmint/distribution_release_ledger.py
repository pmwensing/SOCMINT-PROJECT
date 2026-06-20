from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .distribution_export_verification import verify_distribution_export
from .dossier_export_store import safe_slug

DISTRIBUTION_RELEASE_LEDGER_SCHEMA = "socmint.distribution_release_ledger.v10_17_0"
DISTRIBUTION_RELEASE_LEDGER_ROOT = Path("exports") / "distribution_release_ledger"


def _ledger_dir(
    case_id: str, root: str | Path = DISTRIBUTION_RELEASE_LEDGER_ROOT
) -> Path:
    path = Path(root) / safe_slug(case_id, "case")
    path.mkdir(parents=True, exist_ok=True)
    return path


def release_ledger_path(
    case_id: str, root: str | Path = DISTRIBUTION_RELEASE_LEDGER_ROOT
) -> Path:
    return _ledger_dir(case_id, root=root) / "release_ledger.jsonl"


def release_seal_path(
    case_id: str, subject_id: str, root: str | Path = DISTRIBUTION_RELEASE_LEDGER_ROOT
) -> Path:
    return (
        _ledger_dir(case_id, root=root)
        / f"{safe_slug(subject_id, 'subject')}.seal.json"
    )


def _seal_id(payload: dict[str, Any]) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()[:32]


def load_release_ledger(
    case_id: str, root: str | Path = DISTRIBUTION_RELEASE_LEDGER_ROOT
) -> list[dict[str, Any]]:
    path = release_ledger_path(case_id, root=root)
    if not path.exists():
        return []
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            entries.append(json.loads(line))
    return entries


def latest_release_seal(
    case_id: str, subject_id: str, root: str | Path = DISTRIBUTION_RELEASE_LEDGER_ROOT
) -> dict[str, Any] | None:
    path = release_seal_path(case_id, subject_id, root=root)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def create_distribution_release_seal(
    case_id: str,
    subject_id: str,
    actor: str | None = None,
    note: str | None = None,
    root: str | Path = DISTRIBUTION_RELEASE_LEDGER_ROOT,
) -> dict[str, Any]:
    verification = verify_distribution_export(case_id=case_id, subject_id=subject_id)
    if not verification.get("verified"):
        raise ValueError("Cannot seal distribution export until verification passes.")
    manifest = verification.get("manifest", {})
    base = {
        "schema": DISTRIBUTION_RELEASE_LEDGER_SCHEMA,
        "case_id": case_id,
        "subject_id": subject_id,
        "actor": actor or "system",
        "note": note or "",
        "created_at": datetime.now(UTC).isoformat(),
        "release_state": "released",
        "verification_status": verification.get("status"),
        "zip_path": manifest.get("zip_path"),
        "zip_sha256": manifest.get("zip_sha256"),
        "zip_size_bytes": manifest.get("zip_size_bytes"),
        "manifest_path": manifest.get("manifest_path"),
        "file_count": manifest.get("file_count"),
        "verification_blockers": verification.get("blockers", []),
    }
    base["seal_id"] = _seal_id(base)
    seal_path = release_seal_path(case_id, subject_id, root=root)
    seal_path.write_text(
        json.dumps(base, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    ledger_path = release_ledger_path(case_id, root=root)
    with ledger_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(base, sort_keys=True) + "\n")
    return base


def release_state(
    case_id: str, subject_id: str, root: str | Path = DISTRIBUTION_RELEASE_LEDGER_ROOT
) -> dict[str, Any]:
    seal = latest_release_seal(case_id, subject_id, root=root)
    if seal:
        return {
            "schema": DISTRIBUTION_RELEASE_LEDGER_SCHEMA,
            "case_id": case_id,
            "subject_id": subject_id,
            "release_state": "released",
            "sealed": True,
            "seal": seal,
        }
    verification = verify_distribution_export(case_id=case_id, subject_id=subject_id)
    return {
        "schema": DISTRIBUTION_RELEASE_LEDGER_SCHEMA,
        "case_id": case_id,
        "subject_id": subject_id,
        "release_state": "ready_to_seal" if verification.get("verified") else "held",
        "sealed": False,
        "verification": verification,
    }


def release_ledger_summary(
    case_id: str, root: str | Path = DISTRIBUTION_RELEASE_LEDGER_ROOT
) -> dict[str, Any]:
    entries = load_release_ledger(case_id, root=root)
    return {
        "schema": DISTRIBUTION_RELEASE_LEDGER_SCHEMA,
        "case_id": case_id,
        "release_count": len(entries),
        "released_subjects": [entry.get("subject_id") for entry in entries],
        "entries": entries,
    }


def release_seal_markdown(
    case_id: str, subject_id: str, root: str | Path = DISTRIBUTION_RELEASE_LEDGER_ROOT
) -> str:
    state = release_state(case_id, subject_id, root=root)
    seal = state.get("seal") or {}
    lines = [
        f"# Distribution Release Seal — {case_id} / {subject_id}",
        "",
        f"Release state: {state.get('release_state')}",
        f"Sealed: {state.get('sealed')}",
        f"Seal ID: {seal.get('seal_id', 'none')}",
        f"ZIP SHA-256: {seal.get('zip_sha256', 'none')}",
        f"Actor: {seal.get('actor', 'none')}",
        f"Created at: {seal.get('created_at', 'none')}",
    ]
    return "\n".join(lines) + "\n"
