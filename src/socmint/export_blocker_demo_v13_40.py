from __future__ import annotations

from pathlib import Path
from typing import Any

from .dossier_export_store import DEFAULT_EXPORT_ROOT
from .dossier_export_store import persist_export_pack

EXPORT_BLOCKER_DEMO_SCHEMA = "socmint.export_blocker_demo.v13_40"
ALLOWED_CASE_ID = "case-export-ok-v13-40"
ALLOWED_SUBJECT_ID = "subject-export-ok-v13-40"
DENIED_CASE_ID = "case-export-held-v13-40"
DENIED_SUBJECT_ID = "subject-export-held-v13-40"


def _subject(subject_id: str, case_id: str, name: str) -> dict[str, Any]:
    return {
        "subject_id": subject_id,
        "display_name": name,
        "case_id": case_id,
        "aliases": [name.lower().replace(" ", "-")],
    }


def _evidence(prefix: str) -> list[dict[str, Any]]:
    return [
        {
            "evidence_id": f"{prefix}-profile",
            "label": "profile artifact",
            "source": "public_profile",
            "confidence": 0.96,
            "artifact_id": f"{prefix}-profile-artifact",
        },
        {
            "evidence_id": f"{prefix}-registry",
            "label": "registry artifact",
            "source": "public_registry",
            "confidence": 0.92,
            "artifact_id": f"{prefix}-registry-artifact",
        },
    ]


def create_export_blocker_demo(root: str | Path = DEFAULT_EXPORT_ROOT) -> dict[str, Any]:
    allowed = persist_export_pack(
        _subject(ALLOWED_SUBJECT_ID, ALLOWED_CASE_ID, "V13.40 Allowed Export"),
        _evidence("v13-40-allowed"),
        analyst_reviewed=True,
        root=root,
        audit=True,
        expected_subject_id=ALLOWED_SUBJECT_ID,
        expected_case_id=ALLOWED_CASE_ID,
    )
    denied = persist_export_pack(
        _subject(DENIED_SUBJECT_ID, DENIED_CASE_ID, "V13.40 Denied Export"),
        _evidence("v13-40-denied"),
        analyst_reviewed=True,
        root=root,
        audit=False,
        expected_subject_id=DENIED_SUBJECT_ID,
        expected_case_id=DENIED_CASE_ID,
    )
    return {
        "schema": EXPORT_BLOCKER_DEMO_SCHEMA,
        "allowed": {
            "case_id": ALLOWED_CASE_ID,
            "subject_id": ALLOWED_SUBJECT_ID,
            "manifest_path": allowed["manifest_path"],
            "ui_path": f"/dossier/export-blockers?case_id={ALLOWED_CASE_ID}&subject_id={ALLOWED_SUBJECT_ID}",
        },
        "denied": {
            "case_id": DENIED_CASE_ID,
            "subject_id": DENIED_SUBJECT_ID,
            "manifest_path": denied["manifest_path"],
            "ui_path": f"/dossier/export-blockers?case_id={DENIED_CASE_ID}&subject_id={DENIED_SUBJECT_ID}",
            "expected_blocker": "audit_coverage",
        },
    }
