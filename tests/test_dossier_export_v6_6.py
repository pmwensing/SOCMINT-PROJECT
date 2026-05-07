import json
from pathlib import Path

import pytest

from src.socmint import database as db
from src.socmint.dossier_export import export_dossier
from src.socmint.spine import create_subject, run_spine_for_subject


@pytest.fixture()
def configured_db(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_ARTIFACT_DIR", str(tmp_path / "artifacts"))
    monkeypatch.setenv("SOCMINT_EXPORT_DIR", str(tmp_path / "exports"))
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
        "Export Subject",
        [{"type": "username", "value": "exampleuser"}],
    )
    run_spine_for_subject(subject_id, ["sherlock"])
    return subject_id


def test_export_json_html_pdf(configured_db, monkeypatch):
    subject_id = _build_subject(monkeypatch)

    result = export_dossier(subject_id)

    assert result["export_id"]
    assert len(result["files"]) == 3
    paths = [Path(item["path"]) for item in result["files"]]
    assert all(path.exists() for path in paths)
    assert {path.suffix for path in paths} == {".json", ".html", ".pdf"}

    json_path = next(path for path in paths if path.suffix == ".json")
    payload = json.loads(json_path.read_text())
    assert payload["dossier"]["subject"]["id"] == subject_id


def test_export_api(tmp_path, monkeypatch):
    from src.socmint.dashboard import create_app

    monkeypatch.setenv(
        "SOCMINT_SECRET_KEY",
        "test-secret-key-for-socmint-spine-32chars-plus",
    )
    monkeypatch.setenv("SOCMINT_ADMIN_USER", "admin")
    monkeypatch.setenv("SOCMINT_ADMIN_PASSWORD", "StrongPass123!")
    monkeypatch.setenv("SOCMINT_AUTO_CREATE_DB", "1")
    monkeypatch.setenv("SOCMINT_ARTIFACT_DIR", str(tmp_path / "artifacts"))
    monkeypatch.setenv("SOCMINT_EXPORT_DIR", str(tmp_path / "exports"))

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
            "label": "Export Web Subject",
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

    export = client.post(
        f"/api/v1/spine/subjects/{subject_id}/exports/run",
        json={"formats": ["json", "html", "pdf"]},
        headers={"X-CSRF-Token": csrf},
    )
    assert export.status_code == 202
    assert len(export.get_json()["files"]) == 3

    listing = client.get(f"/api/v1/spine/subjects/{subject_id}/exports")
    assert listing.status_code == 200
    assert listing.get_json()["exports"]
