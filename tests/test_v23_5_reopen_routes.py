from src.socmint.dashboard import create_app
from src.socmint.dossier_assembly_routes_v21_0 import register_dossier_assembly_routes_v21_0


def _app(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    app = create_app()
    register_dossier_assembly_routes_v21_0(app)
    return app


def test_v23_5_routes_require_login_and_accept_valid_requests(tmp_path, monkeypatch):
    from src.socmint import case_reopen_routes_v23_5 as routes

    monkeypatch.setattr(routes, "create_reopen_request", lambda *a, **k: {
        "status": "reopen_request_recorded",
        "request_record_id": 85,
    })
    monkeypatch.setattr(routes, "authorize_reopen_request", lambda *a, **k: {
        "status": "reopen_authorization_recorded",
        "authorization_record_id": 86,
    })

    client = _app(tmp_path, monkeypatch).test_client()
    with client.session_transaction() as sess:
        sess["_csrf_token"] = "test-csrf"

    assert client.post(
        "/api/v1/case-closure/case-alpha/reopen-request",
        json={}, headers={"X-CSRF-Token": "test-csrf"}
    ).status_code == 401
    assert client.post(
        "/api/v1/case-closure/case-alpha/reopen-authorization",
        json={}, headers={"X-CSRF-Token": "test-csrf"}
    ).status_code == 401

    with client.session_transaction() as sess:
        sess["user"] = "supervisor"
        sess["_csrf_token"] = "test-csrf"

    requested = client.post(
        "/api/v1/case-closure/case-alpha/reopen-request",
        json={"reason": "New evidence", "confirmed": True},
        headers={"X-CSRF-Token": "test-csrf"},
    )
    reviewed = client.post(
        "/api/v1/case-closure/case-alpha/reopen-authorization",
        json={"decision": "authorize", "confirmed": True},
        headers={"X-CSRF-Token": "test-csrf"},
    )

    assert requested.status_code == 200
    assert requested.get_json()["request_record_id"] == 85
    assert reviewed.status_code == 200
    assert reviewed.get_json()["authorization_record_id"] == 86
