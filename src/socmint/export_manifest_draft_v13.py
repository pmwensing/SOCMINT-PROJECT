from __future__ import annotations

from typing import Any

from .claim_evidence_ledger_v13 import build_claim_evidence_ledger
from .dossier_readiness_routes_v13 import subject_dossier_readiness
from .handoff_status_v13 import build_handoff_status

SCHEMA = "socmint.export_manifest_draft.v13_19"


def manifest_entry(name: str, kind: str, status: str, ref: str, detail: str) -> dict[str, str]:
    return {
        "name": name,
        "kind": kind,
        "status": status,
        "ref": ref,
        "detail": detail,
    }


def build_export_manifest_draft(subject_id: int) -> dict[str, Any]:
    readiness = subject_dossier_readiness(subject_id)
    ledger = build_claim_evidence_ledger(subject_id)
    status = build_handoff_status(subject_id)

    entries = [
        manifest_entry(
            "dossier_readiness",
            "api",
            readiness.get("state", "unknown"),
            f"/api/v1/subjects/{subject_id}/dossier/readiness",
            readiness.get("label", ""),
        ),
        manifest_entry(
            "claim_evidence_ledger",
            "api",
            "available",
            f"/api/v1/subjects/{subject_id}/claim-evidence-ledger",
            f"claims: {(ledger.get('summary') or {}).get('claim_count', 0)}",
        ),
        manifest_entry(
            "subject_status",
            "api",
            status.get("state", "unknown"),
            f"/api/v1/subjects/{subject_id}/handoff-status",
            f"blocks: {status.get('block_count', 0)} warnings: {status.get('warning_count', 0)}",
        ),
        manifest_entry(
            "full_dossier",
            "ui",
            "linked",
            f"/spine/subjects/{subject_id}/dossier",
            "Primary dossier view.",
        ),
        manifest_entry(
            "claim_ledger_ui",
            "ui",
            "linked",
            f"/subjects/{subject_id}/claim-evidence-ledger",
            "Human-readable claim/evidence view.",
        ),
    ]

    return {
        "schema": SCHEMA,
        "subject_id": subject_id,
        "state": status.get("state", "unknown"),
        "entry_count": len(entries),
        "entries": entries,
        "readiness_state": readiness.get("state"),
        "ledger_summary": ledger.get("summary", {}),
        "status_rows": status.get("rows", []),
        "notes": [
            "Draft manifest only; no files are written.",
            "Use this contract before adding ZIP or filesystem export.",
        ],
    }
