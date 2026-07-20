from pathlib import Path

from flask import Flask

from src.socmint import operational_import_routes_v37_1 as routes


def _app(monkeypatch):
    app = Flask(__name__)
    app.secret_key = "v37-1-route-secret"
    routes.register_operational_import_routes_v37_1(app)
    monkeypatch.setattr(
        routes,
        "actor_is_administrator",
        lambda actor: actor == "admin",
    )
    monkeypatch.setattr(
        routes,
        "current_imports",
        lambda: [
            {
                "operational_import_id": "import-1",
                "envelope": {"case_id": "case-a"},
            },
            {
                "operational_import_id": "import-2",
                "envelope": {"case_id": "case-b"},
            },
        ],
    )
    monkeypatch.setattr(
        routes,
        "find_import",
        lambda import_id: (
            {"operational_import_id": import_id}
            if import_id == "import-1"
            else None
        ),
    )
    monkeypatch.setattr(
        routes,
        "register_import_envelope",
        lambda **kwargs: {
            "status": "operational_import_registered",
            "operational_import_id": "import-1",
            "connector_execution_performed": False,
            "hidden_collection_performed": False,
        },
    )
    return app


def _login(client, user):
    with client.session_transaction() as state:
        state["user"] = user


def test_v37_1_routes_require_administrator(monkeypatch):
    client = _app(monkeypatch).test_client()
    path = "/api/v1/operational-imports"
    assert client.get(path).status_code == 401
    _login(client, "viewer")
    assert client.get(path).status_code == 403
    _login(client, "admin")
    response = client.get(path)
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["count"] == 2
    assert payload["connector_execution_performed"] is False
    assert payload["hidden_collection_performed"] is False


def test_v37_1_create_filter_and_detail_routes(monkeypatch):
    client = _app(monkeypatch).test_client()
    _login(client, "admin")
    created = client.post(
        "/api/v1/operational-imports",
        json={
            "case_id": "case-a",
            "purpose": "Synthetic test import.",
            "artifact_id": "artifact-a",
            "content_sha256": "a" * 64,
            "original_filename": "fixture.json",
            "media_type": "application/json",
            "export_format": "json",
            "tool_name": "FixtureTool",
            "tool_version": "1",
            "adapter_name": "fixture-json",
            "adapter_version": "1",
            "exported_at": "2026-07-20T01:00:00Z",
            "imported_at": "2026-07-20T01:01:00Z",
            "declared_record_count": 1,
            "source_references": [],
            "collection_context": {"synthetic": True},
            "reason": "Test.",
            "confirmed": True,
        },
    )
    assert created.status_code == 200
    assert created.get_json()["operational_import_id"] == "import-1"
    filtered = client.get("/api/v1/operational-imports?case_id=case-a")
    assert filtered.status_code == 200
    assert filtered.get_json()["count"] == 1
    assert client.get("/api/v1/operational-imports/import-1").status_code == 200
    assert client.get("/api/v1/operational-imports/missing").status_code == 404


def test_v37_1_is_registered_through_analytic_review_chain():
    root = Path(__file__).resolve().parents[1]
    chain = (root / "src/socmint/analytic_review_routes_v30_0.py").read_text(
        encoding="utf-8"
    )
    route_source = (
        root / "src/socmint/operational_import_routes_v37_1.py"
    ).read_text(encoding="utf-8")
    service_source = (
        root / "src/socmint/operational_import_v37_1.py"
    ).read_text(encoding="utf-8")
    assert "register_operational_import_routes_v37_1" in chain
    assert "register_operational_import_routes_v37_1(app)" in chain
    assert "/collect" not in route_source
    assert "/execute" not in route_source
    assert "connector_execution_performed" in service_source
    assert "raw_payload_recorded" in service_source
