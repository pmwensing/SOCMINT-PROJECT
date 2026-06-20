from pathlib import Path

from src.socmint.dashboard import create_app
from src.socmint.dossier_assembly_routes_v21_0 import (
    register_dossier_assembly_routes_v21_0,
)


def _app(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    monkeypatch.setenv(
        "SOCMINT_SECRET_KEY", "v28-5-route-test-secret-key-with-more-than-32-characters"
    )
    app = create_app()
    register_dossier_assembly_routes_v21_0(app)
    return app


def test_v28_5_routes_require_admin_and_dispatch(tmp_path, monkeypatch):
    from src.socmint import connector_administration_routes_v28_5 as routes

    payload = {
        "schema": "socmint.connector_integration_administration.v28_5",
        "version": "v28.5.0",
        "status": "ready",
        "connector_summaries": [],
        "connector_count": 0,
        "active_connector_count": 0,
        "disabled_connector_count": 0,
        "auth_readiness_counts": {},
        "connector_health": {},
        "administration_findings": [],
        "administration_finding_count": 0,
        "connector_history": [],
        "connector_event_count": 0,
    }
    monkeypatch.setattr(
        routes, "actor_is_administrator", lambda actor: actor == "admin"
    )
    monkeypatch.setattr(
        routes, "build_connector_administration_workspace", lambda: payload
    )
    monkeypatch.setattr(
        routes,
        "register_connector",
        lambda **kwargs: {
            "status": "connector_registered",
            "connector_id": "connector-1",
        },
    )
    monkeypatch.setattr(
        routes,
        "revise_connector",
        lambda *args, **kwargs: {
            "status": "connector_revised",
            "connector_id": "connector-2",
        },
    )
    monkeypatch.setattr(
        routes,
        "set_connector_enabled",
        lambda *args, **kwargs: {"status": "connector_state_updated"},
    )
    monkeypatch.setattr(
        routes,
        "update_auth_readiness",
        lambda *args, **kwargs: {"status": "connector_auth_readiness_updated"},
    )
    client = _app(tmp_path, monkeypatch).test_client()
    assert client.get("/api/v1/administration/connectors").status_code == 401
    with client.session_transaction() as sess:
        sess["user"] = "viewer"
    assert client.get("/api/v1/administration/connectors").status_code == 403
    csrf = "v28-5-csrf-token"
    with client.session_transaction() as sess:
        sess["user"] = "admin"
        sess["_csrf_token"] = csrf
    headers = {"X-CSRF-Token": csrf}
    assert client.get("/administration/connectors").status_code == 200
    assert (
        client.post(
            "/api/v1/administration/connectors",
            json={
                "name": "Example",
                "connector_type": "api",
                "reason": "register",
                "confirmed": True,
            },
            headers=headers,
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/v1/administration/connectors/connector-1/revise",
            json={
                "name": "Example 2",
                "connector_type": "api",
                "reason": "revise",
                "confirmed": True,
            },
            headers=headers,
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/v1/administration/connectors/connector-1/enable",
            json={"reason": "enable", "confirmed": True},
            headers=headers,
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/v1/administration/connectors/connector-1/disable",
            json={"reason": "disable", "confirmed": True},
            headers=headers,
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/v1/administration/connectors/connector-1/auth-readiness",
            json={"auth_readiness": "configured", "reason": "ready", "confirmed": True},
            headers=headers,
        ).status_code
        == 200
    )


def test_v28_5_release_note_and_no_migration():
    note = Path("release/V28_5_CONNECTOR_INTEGRATION_ADMINISTRATION.md").read_text(
        encoding="utf-8"
    )
    for phrase in (
        "Connector and Integration Administration",
        "connector registration",
        "authorization scopes",
        "authentication readiness",
        "enable and disable state",
        "rate-limit policy",
        "health summaries",
        "immutable connector history",
        "administrator required",
        "explicit confirmation",
        "administrative reason",
        "sensitive values are excluded",
        "no connector execution",
        "no migration",
    ):
        assert phrase in note
    migrations = [
        path
        for directory in (Path("migrations"), Path("alembic"))
        if directory.exists()
        for path in directory.rglob("*v28_5*")
    ]
    assert migrations == []
