from pathlib import Path

import pytest

from src.socmint import database as db
from src.socmint.enrichment import enrich_subject_media_profiles
from src.socmint.enrichment import media_profile_payload
from src.socmint.media_profile import enrich_media_path
from src.socmint.media_profile import enrich_profile_url
from src.socmint.spine import create_subject, run_spine_for_subject


@pytest.fixture()
def configured_db(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_ARTIFACT_DIR", str(tmp_path / "artifacts"))
    db.configure_database(f"sqlite:///{tmp_path / 'socmint.db'}")
    return db


def test_profile_url_enrichment_creates_findings(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_ARTIFACT_DIR", str(tmp_path / "artifacts"))

    result = enrich_profile_url(
        "https://example.com/exampleuser",
        {"title": "Example User", "description": "Profile bio"},
    )

    assert result["status"] == "completed"
    assert result["artifact"]["sha256"]
    assert any(item["type"] == "profile_display_name" for item in result["findings"])


def test_media_path_enrichment_hashes_file(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_ARTIFACT_DIR", str(tmp_path / "artifacts"))
    sample = Path(tmp_path / "sample.jpg")
    sample.write_bytes(b"fake image bytes")

    result = enrich_media_path(str(sample), source_url="https://example.com/a.jpg")

    assert result["status"] == "completed"
    assert result["media"]["sha256"]
    assert result["findings"][0]["type"] == "media_asset"


def test_subject_media_profile_enrichment(configured_db, monkeypatch):
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
        "Media Subject",
        [{"type": "username", "value": "exampleuser"}],
    )
    run_spine_for_subject(subject_id, ["sherlock"])

    result = enrich_subject_media_profiles(subject_id)
    payload = media_profile_payload(subject_id)

    assert result["enrichment_ids"]
    assert payload["enrichments"]


def test_media_profile_api(tmp_path, monkeypatch):
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
            "label": "Media Web Subject",
            "seeds": [{"type": "url", "value": "https://example.com/profile"}],
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert created.status_code == 201
    subject_id = created.get_json()["subject_id"]

    run = client.post(
        f"/api/v1/spine/subjects/{subject_id}/run",
        json={"connectors": ["archivebox"]},
        headers={"X-CSRF-Token": csrf},
    )
    assert run.status_code == 202

    enrich = client.post(
        f"/api/v1/spine/subjects/{subject_id}/media-profiles/run",
        headers={"X-CSRF-Token": csrf},
    )
    assert enrich.status_code == 202

    payload = client.get(f"/api/v1/spine/subjects/{subject_id}/media-profiles")
    assert payload.status_code == 200
    assert payload.get_json()["enrichments"]
