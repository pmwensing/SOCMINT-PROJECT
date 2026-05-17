#!/usr/bin/env bash
set -euo pipefail

ROOT="${SOCMINT_ROOT:-$(pwd)}"
cd "$ROOT"

docker compose exec -T app python - <<'PY'
from __future__ import annotations

import json
import shutil
from pathlib import Path

from src.socmint import database as db

PREFIXES = ("v11-smoke-", "v11.2-smoke-", "v11.3-smoke-")
ARTIFACT_DIRS = [
    Path("var/socmint/v11_2_smoke_artifacts"),
    Path("var/socmint/v11_3_smoke_artifacts"),
]


def is_smoke(value: str | None) -> bool:
    return bool(value) and any(value.startswith(prefix) for prefix in PREFIXES)


def delete_query(session, query, label: str, summary: dict) -> None:
    summary[label] = query.delete(synchronize_session=False)


db.ensure_configured()
session = db.Session()
summary = {
    "schema": "socmint.v11_3.clean_v11_smoke_data",
    "subjects_deleted": 0,
    "seeds_deleted": 0,
    "connector_runs_deleted": 0,
    "raw_artifacts_deleted": 0,
    "observations_deleted": 0,
    "assertions_deleted": 0,
    "validation_events_deleted": 0,
    "account_discoveries_deleted": 0,
    "dossier_files_deleted": 0,
    "artifact_dirs_deleted": [],
    "subject_ids": [],
}

try:
    subjects = [s for s in session.query(db.SpineSubject).all() if is_smoke(s.label)]
    subject_ids = [s.id for s in subjects]
    summary["subject_ids"] = subject_ids

    if subject_ids:
        assertion_ids = [
            item.id
            for item in session.query(db.SpineDossierAssertion)
            .filter(db.SpineDossierAssertion.subject_id.in_(subject_ids))
            .all()
        ]
        run_ids = [
            item.id
            for item in session.query(db.SpineConnectorRun)
            .filter(db.SpineConnectorRun.subject_id.in_(subject_ids))
            .all()
        ]
        if assertion_ids:
            delete_query(
                session,
                session.query(db.SpineValidationEvent).filter(
                    db.SpineValidationEvent.assertion_id.in_(assertion_ids)
                ),
                "validation_events_deleted",
                summary,
            )
        delete_query(session, session.query(db.AccountDiscovery).filter(db.AccountDiscovery.subject_id.in_(subject_ids)), "account_discoveries_deleted", summary)
        delete_query(session, session.query(db.SpineDossierAssertion).filter(db.SpineDossierAssertion.subject_id.in_(subject_ids)), "assertions_deleted", summary)
        delete_query(session, session.query(db.SpineObservation).filter(db.SpineObservation.subject_id.in_(subject_ids)), "observations_deleted", summary)
        if run_ids:
            delete_query(session, session.query(db.SpineRawArtifact).filter(db.SpineRawArtifact.run_id.in_(run_ids)), "raw_artifacts_deleted", summary)
        delete_query(session, session.query(db.SpineConnectorRun).filter(db.SpineConnectorRun.subject_id.in_(subject_ids)), "connector_runs_deleted", summary)
        delete_query(session, session.query(db.SpineSeed).filter(db.SpineSeed.subject_id.in_(subject_ids)), "seeds_deleted", summary)
        delete_query(session, session.query(db.SpineSubject).filter(db.SpineSubject.id.in_(subject_ids)), "subjects_deleted", summary)

    session.commit()
finally:
    session.close()

root = Path("var/socmint/dossiers")
if root.exists():
    for path in root.glob("subject-*-full-entity-dossier-v2-*"):
        try:
            text = path.read_text(errors="ignore") if path.suffix in {".json", ".md", ".html"} or path.name.endswith("-EXPORT.json") else ""
            if any(prefix in text for prefix in PREFIXES):
                path.unlink()
                summary["dossier_files_deleted"] += 1
        except Exception:
            pass

for artifact_dir in ARTIFACT_DIRS:
    if artifact_dir.exists():
        shutil.rmtree(artifact_dir)
        summary["artifact_dirs_deleted"].append(str(artifact_dir))

print(json.dumps(summary, indent=2, sort_keys=True))
print("PASS clean v11 smoke data")
PY
