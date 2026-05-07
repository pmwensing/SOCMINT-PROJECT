import pytest

from src.socmint import database as db
from src.socmint.identity_graph import build_identity_graph, graph_payload
from src.socmint.spine import create_subject, run_spine_for_subject


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
        "Graph Subject",
        [{"type": "username", "value": "exampleuser"}],
    )
    run_spine_for_subject(subject_id, ["sherlock", "maigret"])
    return subject_id


def test_identity_graph_builds_nodes_and_edges(configured_db, monkeypatch):
    subject_id = _build_subject(monkeypatch)

    graph_id = build_identity_graph(subject_id)
    payload = graph_payload(subject_id)

    assert graph_id
    assert payload["nodes"]
    assert payload["edges"]
    assert any(node["type"] == "username" for node in payload["nodes"])


def test_graph_api_route(tmp_path, monkeypatch):
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
            "label": "Graph Web Subject",
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

    graph = client.get(f"/api/v1/spine/subjects/{subject_id}/graph")
    assert graph.status_code == 200
    assert graph.get_json()["nodes"]
