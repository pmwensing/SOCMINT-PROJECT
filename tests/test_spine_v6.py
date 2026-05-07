import pytest

from src.socmint import database as db
from src.socmint.seeds import normalize_seed
from src.socmint.spine import build_dossier, create_subject, run_spine_for_subject


@pytest.fixture()
def configured_db(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_ARTIFACT_DIR", str(tmp_path / "artifacts"))
    db.configure_database(f"sqlite:///{tmp_path / 'socmint.db'}")
    return db


def test_normalize_seed_email():
    seed = normalize_seed(" Alice.Example+tag@Example.com ")
    assert seed.seed_type == "email"
    assert seed.normalized_value == "alice.example+tag@example.com"
    assert len(seed.pii_hash) == 64


def test_spine_creates_dossier_from_username(configured_db, monkeypatch):
    def fake_execute_connector(connector_key, seed):
        return {
            "connector": connector_key,
            "status": "dry_run",
            "findings": [
                {
                    "type": "account_presence",
                    "value": f"https://example.com/{seed.normalized_value}",
                    "source": connector_key,
                    "confidence": 0.61,
                }
            ],
        }

    monkeypatch.setattr(
        "src.socmint.spine.execute_connector",
        fake_execute_connector,
    )

    subject_id = create_subject(
        "Test Subject",
        [{"type": "username", "value": "exampleuser"}],
    )
    result = run_spine_for_subject(subject_id, ["sherlock", "maigret"])
    dossier = build_dossier(subject_id)

    assert result["run_ids"]
    assert dossier["summary"]["connector_runs"] == 2
    assert dossier["summary"]["assertions"] >= 1


def test_spine_dashboard_api(tmp_path, monkeypatch):
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

    login = client.post(
        "/login",
        data={
            "username": "admin",
            "password": "StrongPass123!",
            "csrf_token": csrf,
        },
    )
    assert login.status_code in {200, 302}

    response = client.post(
        "/api/v1/spine/subjects",
        json={
            "label": "Web Subject",
            "seeds": [{"type": "username", "value": "exampleuser"}],
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 201
    subject_id = response.get_json()["subject_id"]

    run = client.post(
        f"/api/v1/spine/subjects/{subject_id}/run",
        json={"connectors": ["sherlock"]},
        headers={"X-CSRF-Token": csrf},
    )
    assert run.status_code == 202

    dossier = client.get(f"/api/v1/spine/subjects/{subject_id}/dossier")
    assert dossier.status_code == 200
    assert dossier.get_json()["subject"]["id"] == subject_id
