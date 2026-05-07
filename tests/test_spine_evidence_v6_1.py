import pytest

from src.socmint import database as db
from src.socmint.evidence import connector_quality_metrics, get_assertion_evidence
from src.socmint.spine import build_dossier, create_subject, run_spine_for_subject


@pytest.fixture()
def configured_db(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_ARTIFACT_DIR", str(tmp_path / "artifacts"))
    db.configure_database(f"sqlite:///{tmp_path / 'socmint.db'}")
    return db


def _build_subject(monkeypatch):
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

    monkeypatch.setattr("src.socmint.spine.execute_connector", fake_execute_connector)
    subject_id = create_subject(
        "Evidence Subject",
        [{"type": "username", "value": "exampleuser"}],
    )
    run_spine_for_subject(subject_id, ["sherlock", "maigret"])
    return subject_id


def test_assertion_evidence_detail(configured_db, monkeypatch):
    subject_id = _build_subject(monkeypatch)
    dossier = build_dossier(subject_id)
    assertion_id = dossier["assertions"][0]["id"]

    evidence = get_assertion_evidence(assertion_id)

    assert evidence["assertion"]["id"] == assertion_id
    assert evidence["observations"]
    assert evidence["connector_runs"]
    assert evidence["raw_artifacts"]
    assert evidence["confidence_explanation"]["factors"]


def test_connector_quality_metrics(configured_db, monkeypatch):
    _build_subject(monkeypatch)

    metrics = connector_quality_metrics()
    names = {item["connector"] for item in metrics}

    assert {"sherlock", "maigret"}.issubset(names)
    assert all("average_confidence" in item for item in metrics)
    assert all("evidence_coverage" in item for item in metrics)


def test_evidence_dashboard_api(tmp_path, monkeypatch):
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
            "label": "Evidence Web Subject",
            "seeds": [{"type": "username", "value": "exampleuser"}],
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert created.status_code == 201
    subject_id = created.get_json()["subject_id"]

    run = client.post(
        f"/api/v1/spine/subjects/{subject_id}/run",
        json={"connectors": ["sherlock"]},
        headers={"X-CSRF-Token": csrf},
    )
    assert run.status_code == 202

    dossier = client.get(f"/api/v1/spine/subjects/{subject_id}/dossier")
    assertion_id = dossier.get_json()["assertions"][0]["id"]

    evidence = client.get(f"/api/v1/spine/assertions/{assertion_id}")
    assert evidence.status_code == 200
    assert evidence.get_json()["observations"]

    quality = client.get("/api/v1/spine/connectors/quality")
    assert quality.status_code == 200
    assert quality.get_json()["connectors"]
