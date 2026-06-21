from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from . import database as db

SMOKE_PREFIXES = ("v11-smoke-", "v11.2-smoke-", "v11.3-smoke-", "v11.4-smoke-")
SMOKE_ARTIFACT_DIRS = (
    Path("var/socmint/v11_2_smoke_artifacts"),
    Path("var/socmint/v11_3_smoke_artifacts"),
    Path("var/socmint/v11_4_smoke_artifacts"),
)


def is_smoke_label(value: str | None) -> bool:
    return bool(value) and any(
        str(value).startswith(prefix) for prefix in SMOKE_PREFIXES
    )


def _json(raw: str | None, fallback: Any) -> Any:
    if not raw:
        return fallback
    try:
        return json.loads(raw)
    except Exception:
        return fallback


def _dossier_file_hits() -> list[dict[str, Any]]:
    root = Path("var/socmint/dossiers")
    hits: list[dict[str, Any]] = []
    if not root.exists():
        return hits
    for path in root.glob("subject-*-full-entity-dossier-v2-*"):
        matched = False
        try:
            if path.suffix in {".json", ".md", ".html"} or path.name.endswith(
                "-EXPORT.json"
            ):
                text = path.read_text(errors="ignore")
                matched = any(prefix in text for prefix in SMOKE_PREFIXES)
        except Exception:
            matched = False
        if matched:
            hits.append(
                {
                    "path": str(path),
                    "name": path.name,
                    "size_bytes": path.stat().st_size,
                }
            )
    return hits


def collect_test_data_summary() -> dict[str, Any]:
    db.ensure_configured()
    session = db.Session()
    try:
        smoke_subjects = [
            s for s in session.query(db.SpineSubject).all() if is_smoke_label(s.label)
        ]
        subject_ids = [s.id for s in smoke_subjects]
        run_ids: list[int] = []
        assertion_ids: list[int] = []
        if subject_ids:
            run_ids = [
                r.id
                for r in session.query(db.SpineConnectorRun)
                .filter(db.SpineConnectorRun.subject_id.in_(subject_ids))
                .all()
            ]
            assertion_ids = [
                a.id
                for a in session.query(db.SpineDossierAssertion)
                .filter(db.SpineDossierAssertion.subject_id.in_(subject_ids))
                .all()
            ]
            seed_count = (
                session.query(db.SpineSeed)
                .filter(db.SpineSeed.subject_id.in_(subject_ids))
                .count()
            )
            observation_count = (
                session.query(db.SpineObservation)
                .filter(db.SpineObservation.subject_id.in_(subject_ids))
                .count()
            )
            assertion_count = len(assertion_ids)
            discovery_count = (
                session.query(db.AccountDiscovery)
                .filter(db.AccountDiscovery.subject_id.in_(subject_ids))
                .count()
            )
            run_count = len(run_ids)
        else:
            seed_count = observation_count = assertion_count = discovery_count = (
                run_count
            ) = 0

        artifact_count = 0
        if run_ids:
            artifact_count = (
                session.query(db.SpineRawArtifact)
                .filter(db.SpineRawArtifact.run_id.in_(run_ids))
                .count()
            )
        validation_event_count = 0
        if assertion_ids:
            validation_event_count = (
                session.query(db.SpineValidationEvent)
                .filter(db.SpineValidationEvent.assertion_id.in_(assertion_ids))
                .count()
            )

        dossier_files = _dossier_file_hits()
        artifact_dirs = [str(path) for path in SMOKE_ARTIFACT_DIRS if path.exists()]
        cleanup_available = bool(subject_ids or dossier_files or artifact_dirs)
        return {
            "schema": "socmint.test_data_controls.v11_4",
            "namespace_prefixes": list(SMOKE_PREFIXES),
            "cleanup_available": cleanup_available,
            "status": "needs_cleanup" if cleanup_available else "clean",
            "counts": {
                "subjects": len(subject_ids),
                "seeds": seed_count,
                "connector_runs": run_count,
                "raw_artifacts": artifact_count,
                "observations": observation_count,
                "assertions": assertion_count,
                "validation_events": validation_event_count,
                "account_discoveries": discovery_count,
                "dossier_files": len(dossier_files),
                "artifact_dirs": len(artifact_dirs),
            },
            "subjects": [
                {
                    "id": s.id,
                    "label": s.label,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                    "is_test_data": True,
                }
                for s in smoke_subjects
            ],
            "dossier_files": dossier_files,
            "artifact_dirs": artifact_dirs,
        }
    finally:
        session.close()


def clean_test_data(actor: str | None = None) -> dict[str, Any]:
    db.ensure_configured()
    session = db.Session()
    summary = {
        "schema": "socmint.test_data_cleanup.v11_4",
        "actor": actor,
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
        smoke_subjects = [
            s for s in session.query(db.SpineSubject).all() if is_smoke_label(s.label)
        ]
        subject_ids = [s.id for s in smoke_subjects]
        summary["subject_ids"] = subject_ids
        if subject_ids:
            assertion_ids = [
                a.id
                for a in session.query(db.SpineDossierAssertion)
                .filter(db.SpineDossierAssertion.subject_id.in_(subject_ids))
                .all()
            ]
            run_ids = [
                r.id
                for r in session.query(db.SpineConnectorRun)
                .filter(db.SpineConnectorRun.subject_id.in_(subject_ids))
                .all()
            ]
            if assertion_ids:
                summary["validation_events_deleted"] = (
                    session.query(db.SpineValidationEvent)
                    .filter(db.SpineValidationEvent.assertion_id.in_(assertion_ids))
                    .delete(synchronize_session=False)
                )
            summary["account_discoveries_deleted"] = (
                session.query(db.AccountDiscovery)
                .filter(db.AccountDiscovery.subject_id.in_(subject_ids))
                .delete(synchronize_session=False)
            )
            summary["assertions_deleted"] = (
                session.query(db.SpineDossierAssertion)
                .filter(db.SpineDossierAssertion.subject_id.in_(subject_ids))
                .delete(synchronize_session=False)
            )
            summary["observations_deleted"] = (
                session.query(db.SpineObservation)
                .filter(db.SpineObservation.subject_id.in_(subject_ids))
                .delete(synchronize_session=False)
            )
            if run_ids:
                summary["raw_artifacts_deleted"] = (
                    session.query(db.SpineRawArtifact)
                    .filter(db.SpineRawArtifact.run_id.in_(run_ids))
                    .delete(synchronize_session=False)
                )
            summary["connector_runs_deleted"] = (
                session.query(db.SpineConnectorRun)
                .filter(db.SpineConnectorRun.subject_id.in_(subject_ids))
                .delete(synchronize_session=False)
            )
            summary["seeds_deleted"] = (
                session.query(db.SpineSeed)
                .filter(db.SpineSeed.subject_id.in_(subject_ids))
                .delete(synchronize_session=False)
            )
            summary["subjects_deleted"] = (
                session.query(db.SpineSubject)
                .filter(db.SpineSubject.id.in_(subject_ids))
                .delete(synchronize_session=False)
            )
        session.commit()
    finally:
        session.close()

    for item in _dossier_file_hits():
        try:
            Path(item["path"]).unlink()
            summary["dossier_files_deleted"] += 1
        except Exception:
            pass
    for artifact_dir in SMOKE_ARTIFACT_DIRS:
        if artifact_dir.exists():
            shutil.rmtree(artifact_dir)
            summary["artifact_dirs_deleted"].append(str(artifact_dir))
    summary["status"] = "cleaned"
    summary["post_summary"] = collect_test_data_summary()
    return summary


test_data_summary = collect_test_data_summary
test_data_summary.__test__ = False
