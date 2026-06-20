from pathlib import Path

from src.socmint.dashboard import create_app
from src.socmint.dossier_assembly_routes_v21_0 import (
    register_dossier_assembly_routes_v21_0,
)


def _app(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    monkeypatch.setenv(
        "SOCMINT_SECRET_KEY", "v29-4-route-test-secret-key-with-more-than-32-characters"
    )
    app = create_app()
    register_dossier_assembly_routes_v21_0(app)
    return app


def test_v29_4_routes_require_admin_and_dispatch(tmp_path, monkeypatch):
    from src.socmint import evidence_ingestion_routes_v29_4 as routes

    payload = {
        "status": "ready",
        "artifacts": [],
        "artifact_count": 0,
        "artifact_state_counts": {},
        "accepted_artifacts": [],
        "accepted_artifact_count": 0,
        "quarantined_artifacts": [],
        "quarantined_artifact_count": 0,
        "rejected_artifacts": [],
        "rejected_artifact_count": 0,
        "duplicate_artifacts": [],
        "duplicate_artifact_count": 0,
        "chain_of_custody_incomplete": [],
        "chain_of_custody_incomplete_count": 0,
        "derived_observations": [],
        "derived_observation_count": 0,
        "ingestion_findings": [],
        "ingestion_finding_count": 0,
        "provenance_history": [],
        "provenance_event_count": 0,
    }
    monkeypatch.setattr(
        routes, "actor_is_administrator", lambda actor: actor == "admin"
    )
    monkeypatch.setattr(routes, "build_evidence_ingestion_workspace", lambda: payload)
    monkeypatch.setattr(
        routes,
        "register_artifact",
        lambda **kwargs: {
            "status": "evidence_artifact_registered",
            "artifact_id": "artifact-1",
        },
    )
    monkeypatch.setattr(
        routes,
        "change_artifact_state",
        lambda **kwargs: {
            "status": "evidence_artifact_state_changed",
            "to_state": kwargs["to_state"],
        },
    )
    monkeypatch.setattr(
        routes,
        "derive_observation",
        lambda **kwargs: {
            "status": "evidence_observation_derived",
            "observation_id": "observation-1",
        },
    )
    client = _app(tmp_path, monkeypatch).test_client()
    assert client.get("/api/v1/collection-operations/evidence").status_code == 401
    with client.session_transaction() as sess:
        sess["user"] = "viewer"
    assert client.get("/api/v1/collection-operations/evidence").status_code == 403
    csrf = "v29-4-csrf-token"
    with client.session_transaction() as sess:
        sess["user"] = "admin"
        sess["_csrf_token"] = csrf
    headers = {"X-CSRF-Token": csrf}
    assert client.get("/collection-operations/evidence").status_code == 200
    assert client.get("/api/v1/collection-operations/evidence").status_code == 200
    registered = client.post(
        "/api/v1/collection-operations/evidence",
        json={
            "collection_job_id": "collection-job-1",
            "attempt_number": 1,
            "source_reference": "source://demo",
            "acquired_at": "2026-06-19T12:00:00+00:00",
            "content_sha256": "a" * 64,
            "content_type": "application/json",
            "byte_size": 10,
            "acquisition_method": "adapter",
            "reason": "register",
            "confirmed": True,
        },
        headers=headers,
    )
    state = client.post(
        "/api/v1/collection-operations/evidence/artifact-1/state",
        json={"to_state": "accepted", "reason": "reviewed", "confirmed": True},
        headers=headers,
    )
    observation = client.post(
        "/api/v1/collection-operations/evidence/artifact-1/observations",
        json={
            "observation_type": "profile",
            "normalized_value": {"username": "alice"},
            "confidence": "0.8",
            "derivation_method": "adapter",
            "reason": "derive",
            "confirmed": True,
        },
        headers=headers,
    )
    assert [registered.status_code, state.status_code, observation.status_code] == [
        200,
        200,
        200,
    ]


def test_v29_4_release_note_and_no_migration():
    note = Path("release/V29_4_EVIDENCE_SAFE_INGESTION_PROVENANCE.md").read_text(
        encoding="utf-8"
    )
    for phrase in (
        "Evidence-Safe Ingestion and Provenance",
        "append-only artifact registration",
        "content and acquisition hashes",
        "collection-attempt bindings",
        "duplicate detection",
        "chain-of-custody checks",
        "quarantine and rejection states",
        "observation derivation",
        "immutable provenance history",
        "no raw artifact content",
        "existing results, media, findings, connector outputs, and legacy jobs remain unchanged",
        "no migration",
    ):
        assert phrase in note
    migrations = [
        path
        for directory in (Path("migrations"), Path("alembic"))
        if directory.exists()
        for path in directory.rglob("*v29_4*")
    ]
    assert migrations == []
