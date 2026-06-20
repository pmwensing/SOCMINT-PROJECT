from flask import Flask

from src.socmint.analytic_conflict_routes_v30_3 import register_analytic_conflict_routes_v30_3


def test_v30_3_routes_require_admin_and_record(monkeypatch):
    app = Flask(__name__)
    app.secret_key = "test-secret"
    monkeypatch.setattr("src.socmint.analytic_conflict_routes_v30_3.actor_is_administrator", lambda actor: actor == "admin")
    monkeypatch.setattr("src.socmint.analytic_conflict_routes_v30_3.current_conflicts", lambda: [])
    monkeypatch.setattr("src.socmint.analytic_conflict_routes_v30_3.record_conflict", lambda **kwargs: {"status":"analytic_conflict_recorded","conflict_id":"conflict-1"})
    register_analytic_conflict_routes_v30_3(app)
    client = app.test_client()

    assert client.get("/api/v1/analytic-review/conflicts").status_code == 401
    with client.session_transaction() as session:
        session["user"] = "viewer"
    assert client.get("/api/v1/analytic-review/conflicts").status_code == 403

    with client.session_transaction() as session:
        session["user"] = "admin"
    response = client.post("/api/v1/analytic-review/conflicts", json={"confirmed": True})
    assert response.status_code == 200
    assert response.get_json()["conflict_id"] == "conflict-1"
