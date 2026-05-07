import pytest

from src.socmint import database as db
from src.socmint.contradictions import contradiction_payload
from src.socmint.contradictions import detect_subject_contradictions
from src.socmint.contradictions import resolve_contradiction
from src.socmint.spine import correlate_subject, create_subject


@pytest.fixture()
def configured_db(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_ARTIFACT_DIR", str(tmp_path / "artifacts"))
    db.configure_database(f"sqlite:///{tmp_path / 'socmint.db'}")
    return db


def _build_conflicting_subject():
    subject_id = create_subject(
        "Conflict Subject",
        [{"type": "username", "value": "exampleuser"}],
    )
    run_id = db.create_spine_connector_run(
        subject_id=subject_id,
        connector_key="test",
        seed_id=None,
        status="completed",
        raw_result={"status": "completed"},
    )

    for value in ["Alice Example", "Bob Example"]:
        db.create_spine_observation(
            subject_id=subject_id,
            run_id=run_id,
            observation_type="profile_display_name",
            normalized_value=value,
            confidence="0.72",
            source_ref=f"run:{run_id}:test",
            evidence_ref="sha256:test",
            payload={"value": value},
        )

    correlate_subject(subject_id)
    return subject_id


def test_detect_single_value_contradiction(configured_db):
    subject_id = _build_conflicting_subject()

    result = detect_subject_contradictions(subject_id)
    payload = contradiction_payload(subject_id)

    assert result["contradiction_ids"]
    assert payload["contradictions"]
    assert payload["contradictions"][0]["type"] == "single_value_conflict"


def test_resolve_contradiction(configured_db):
    subject_id = _build_conflicting_subject()
    result = detect_subject_contradictions(subject_id)
    contradiction_id = result["contradiction_ids"][0]

    updated = resolve_contradiction(
        contradiction_id,
        "resolved",
        actor="tester",
        note="Reviewed.",
    )
    payload = contradiction_payload(subject_id)

    assert updated == contradiction_id
    assert payload["contradictions"][0]["status"] == "resolved"


def test_contradictions_api(tmp_path, monkeypatch):
    from src.socmint.dashboard import create_app

    monkeypatch.setenv(
        "SOCMINT_SECRET_KEY",
        "test-secret-key-for-socmint-spine-32chars-plus",
    )
    monkeypatch.setenv("SOCMINT_ADMIN_USER", "admin")
    monkeypatch.setenv("SOCMINT_ADMIN_PASSWORD", "StrongPass123!")
    monkeypatch.setenv("SOCMINT_AUTO_CREATE_DB", "1")
    monkeypatch.setenv("SOCMINT_ARTIFACT_DIR", str(tmp_path / "artifacts"))

    app = create_app(database_url=f"sqlite:///{tmp_path / 'web.db'}")
    app.config.update(TESTING=True)
    client = app.test_client()
    csrf = "test-csrf-token"

    with client.session_transaction() as sess:
        sess["_csrf_token"] = csrf

    client.post(
        "/login",
        data={
            "username": "admin",
            "password": "StrongPass123!",
            "csrf_token": csrf,
        },
    )

    created = client.post(
        "/api/v1/spine/subjects",
        json={
            "label": "Conflict Web Subject",
            "seeds": [{"type": "username", "value": "exampleuser"}],
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert created.status_code == 201
    subject_id = created.get_json()["subject_id"]

    response = client.post(
        f"/api/v1/spine/subjects/{subject_id}/contradictions/run",
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 202

    payload = client.get(f"/api/v1/spine/subjects/{subject_id}/contradictions")
    assert payload.status_code == 200
    assert "contradictions" in payload.get_json()
