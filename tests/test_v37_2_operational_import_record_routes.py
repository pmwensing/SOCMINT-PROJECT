from pathlib import Path

from flask import Flask

from src.socmint import operational_import_record_routes_v37_2 as routes


def _app(monkeypatch):
    app = Flask(__name__)
    app.secret_key = "v37-2-route-secret"
    routes.register_operational_import_record_routes_v37_2(app)
    monkeypatch.setattr(routes, "actor_is_administrator", lambda actor: actor == "admin")
    monkeypatch.setattr(
        routes,
        "current_staged_records",
        lambda import_id=None: [
            {
                "staged_record_id": "record-1",
                "initial_state": "accepted",
                "operational_import_id": import_id or "import-a",
            },
            {
                "staged_record_id": "record-2",
                "initial_state": "quarantined",
                "operational_import_id": import_id or "import-a",
            },
        ],
    )
    monkeypatch.setattr(
        routes,
        "current_batches",
        lambda: [{"staged_record_batch_id": "batch-1"}],
    )
    monkeypatch.setattr(
        routes,
        "find_staged_record",
        lambda record_id: {"staged_record_id": record_id} if record_id == "record-1" else None,
    )
    monkeypatch.setattr(
        routes,
        "find_batch",
        lambda batch_id: {"staged_record_batch_id": batch_id} if batch_id == "batch-1" else None,
    )
    monkeypatch.setattr(
        routes,
        "stage_import_records",
        lambda **kwargs: {
            "status": "import_records_staged",
            "staged_record_batch_id": "batch-1",
            "observation_created": False,
        },
    )
    return app


def _login(client, user):
    with client.session_transaction() as state:
        state["user"] = user


def test_v37_2_routes_require_administrator(monkeypatch):
    client = _app(monkeypatch).test_client()
    path = "/api/v1/operational-import-records"
    assert client.get(path).status_code == 401
    _login(client, "viewer")
    assert client.get(path).status_code == 403
    _login(client, "admin")
    payload = client.get(path).get_json()
    assert payload["count"] == 2
    assert payload["observation_created"] is False
    assert payload["automatic_promotion"] is False


def test_v37_2_stage_filter_and_detail_routes(monkeypatch):
    client = _app(monkeypatch).test_client()
    _login(client, "admin")
    created = client.post(
        "/api/v1/operational-imports/import-a/records",
        json={
            "records": [{"source_record_id": "record-1"}],
            "adapter_diagnostics": {},
            "reason": "Stage.",
            "confirmed": True,
        },
    )
    assert created.status_code == 200
    assert created.get_json()["staged_record_batch_id"] == "batch-1"
    filtered = client.get(
        "/api/v1/operational-import-records?import_id=import-a&state=quarantined"
    )
    assert filtered.status_code == 200
    assert filtered.get_json()["count"] == 1
    assert client.get("/api/v1/operational-import-records/record-1").status_code == 200
    assert client.get("/api/v1/operational-import-records/missing").status_code == 404
    assert client.get("/api/v1/operational-import-batches").status_code == 200
    assert client.get("/api/v1/operational-import-batches/batch-1").status_code == 200


def test_v37_2_is_registered_without_collection_or_promotion_routes():
    root = Path(__file__).resolve().parents[1]
    chain = (root / "src/socmint/analytic_review_routes_v30_0.py").read_text(
        encoding="utf-8"
    )
    route_source = (
        root / "src/socmint/operational_import_record_routes_v37_2.py"
    ).read_text(encoding="utf-8")
    service_source = (
        root / "src/socmint/operational_import_records_v37_2.py"
    ).read_text(encoding="utf-8")
    assert "register_operational_import_record_routes_v37_2" in chain
    assert "register_operational_import_record_routes_v37_2(app)" in chain
    assert "/collect" not in route_source
    assert "/promote" not in route_source
    assert "observation_created" in service_source
    assert "connector_execution_performed" in service_source
