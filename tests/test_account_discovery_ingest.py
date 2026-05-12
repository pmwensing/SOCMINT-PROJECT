import pytest

from src.socmint import database as db
from src.socmint.account_discovery import account_discovery_queue
from src.socmint.account_discovery import ingest_account_discoveries
from src.socmint.account_discovery import review_account_discovery
from src.socmint.dashboard import create_app
from src.socmint.seeds import normalize_seed
from src.socmint.spine import create_subject


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_SECRET_KEY", "test-secret-key-with-enough-entropy")
    monkeypatch.setenv("SOCMINT_AUTO_CREATE_DB", "true")
    monkeypatch.setenv("SOCMINT_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("SOCMINT_ADMIN_USER", raising=False)
    monkeypatch.delenv("SOCMINT_ADMIN_PASSWORD", raising=False)
    app = create_app(f"sqlite:///{tmp_path / 'socmint-account-discovery.db'}")
    app.config.update(TESTING=True)
    return app


def authorize(client):
    with client.session_transaction() as session:
        session["user"] = "tester"
        session["role"] = "analyst"
        session["is_admin"] = True
        session["_csrf_token"] = "test-csrf-token"


def csrf_headers() -> dict[str, str]:
    return {"X-CSRF-Token": "test-csrf-token"}


def _subject_with_profile_observation() -> int:
    subject_id = create_subject(
        "Discovery Subject",
        [{"type": "username", "value": "discovery_user"}],
    )
    seed = db.list_spine_seeds(subject_id)[0]
    run_id = db.create_spine_connector_run(
        subject_id,
        "sherlock",
        seed.id,
        "completed",
        {"status": "completed"},
    )
    observation_id = db.create_spine_observation(
        subject_id,
        run_id,
        "profile_url",
        "https://social.example/discovery_user",
        "0.82",
        f"run:{run_id}:sherlock",
        "sha256:test-artifact",
        {
            "payload": {
                "type": "profile_url",
                "value": "https://social.example/discovery_user",
                "context": {"platform_hint": "social.example"},
            }
        },
    )
    db.upsert_spine_assertion(
        subject_id,
        "profile_url",
        "https://social.example/discovery_user",
        "0.82",
        "unreviewed",
        {
            "supporting_observation_ids": [observation_id],
            "source_refs": [f"run:{run_id}:sherlock"],
            "evidence_refs": ["sha256:test-artifact"],
        },
    )
    return subject_id


def test_account_discovery_ingest_captures_and_promotes(app):
    subject_id = _subject_with_profile_observation()

    result = ingest_account_discoveries(
        subject_id,
        actor="tester",
        capture_profiles=True,
    )
    queued = account_discovery_queue(subject_id)
    discovery = queued["discoveries"][0]
    reviewed = review_account_discovery(
        discovery["id"],
        "confirmed",
        actor="tester",
        promote=True,
    )

    seeds = db.list_spine_seeds(subject_id)

    assert result["discovery_count"] == 1
    assert discovery["profile_url"] == "https://social.example/discovery_user"
    assert discovery["capture_ids"]
    assert reviewed["promoted_seed_id"]
    assert any(seed.seed_type == "url" for seed in seeds)


def test_account_discovery_routes(app):
    subject_id = _subject_with_profile_observation()

    with app.test_client() as client:
        authorize(client)
        ingest = client.post(
            f"/api/v1/spine/subjects/{subject_id}/account-discovery/ingest",
            json={"capture_profiles": False},
            headers=csrf_headers(),
        )
        queue = client.get(
            f"/api/v1/spine/subjects/{subject_id}/account-discovery"
        )
        discovery_id = queue.get_json()["discoveries"][0]["id"]
        review = client.post(
            f"/api/v1/spine/account-discovery/{discovery_id}/review",
            json={"action": "confirmed", "promote": True},
            headers=csrf_headers(),
        )
        page = client.get(
            f"/spine/subjects/{subject_id}/account-discovery"
        )

    assert ingest.status_code == 201
    assert queue.status_code == 200
    assert review.status_code == 200
    assert review.get_json()["promoted_seed_id"]
    assert page.status_code == 200


def test_account_discovery_metadata_and_seed_normalization(app):
    assert db.AccountDiscovery.__tablename__ in db.Base.metadata.tables
    normalized = normalize_seed("https://social.example/discovery_user", "url")
    assert normalized.seed_type == "url"
