import re

import pytest

from src.socmint import database as db
from src.socmint.dashboard import create_app


def csrf_token(response):
    match = re.search(rb'name="csrf_token" value="([^"]+)"', response.data)
    assert match
    return match.group(1).decode()


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_SECRET_KEY", "test-secret-key-with-enough-entropy")
    monkeypatch.setenv("SOCMINT_ALLOW_SIGNUP", "true")
    monkeypatch.setenv("SOCMINT_SIGNUP_INVITE_CODE", "test-invite-code")
    monkeypatch.setenv("SOCMINT_AUTO_CREATE_DB", "true")
    monkeypatch.setenv("SOCMINT_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("SOCMINT_ADMIN_USER", raising=False)
    monkeypatch.delenv("SOCMINT_ADMIN_PASSWORD", raising=False)
    app = create_app(f"sqlite:///{tmp_path / 'socmint-test.db'}")
    app.config.update(TESTING=True)
    return app


def signup(client, username="operator", password="StrongPass123!"):
    response = client.get("/signup")
    token = csrf_token(response)
    return client.post(
        "/signup",
        data={
            "username": username,
            "password": password,
            "confirm": password,
            "invite_code": "test-invite-code",
            "csrf_token": token,
        },
    )


def signup_with_invite(
    client, invite_code, username="operator", password="StrongPass123!"
):
    response = client.get("/signup")
    token = csrf_token(response)
    return client.post(
        "/signup",
        data={
            "username": username,
            "password": password,
            "confirm": password,
            "invite_code": invite_code,
            "csrf_token": token,
        },
    )


def login(client, username="operator", password="StrongPass123!"):
    response = client.get("/login")
    token = csrf_token(response)
    return client.post(
        "/login",
        data={
            "username": username,
            "password": password,
            "csrf_token": token,
        },
    )


def test_dashboard_index_redirects_when_unauthenticated(app):
    with app.test_client() as client:
        response = client.get("/")
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/login")


def test_create_app_requires_secret(monkeypatch):
    monkeypatch.delenv("SOCMINT_SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError, match="SOCMINT_SECRET_KEY"):
        create_app()


def test_create_app_rejects_placeholder_secret(monkeypatch):
    monkeypatch.setenv("SOCMINT_SECRET_KEY", "replace-with-a-long-random-secret")
    with pytest.raises(RuntimeError, match="placeholder"):
        create_app()


def test_signup_is_disabled_by_default(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_SECRET_KEY", "test-secret-key-with-enough-entropy")
    monkeypatch.setenv("SOCMINT_AUTO_CREATE_DB", "true")
    monkeypatch.setenv("SOCMINT_DATA_DIR", str(tmp_path))
    app = create_app(f"sqlite:///{tmp_path / 'socmint-default-signup.db'}")
    app.config.update(TESTING=True)

    with app.test_client() as client:
        assert client.get("/signup").status_code == 404


def test_signup_requires_invite_when_enabled(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_SECRET_KEY", "test-secret-key-with-enough-entropy")
    monkeypatch.setenv("SOCMINT_ALLOW_SIGNUP", "true")
    monkeypatch.setenv("SOCMINT_AUTO_CREATE_DB", "true")
    monkeypatch.setenv("SOCMINT_DATA_DIR", str(tmp_path))

    with pytest.raises(RuntimeError, match="SOCMINT_SIGNUP_INVITE_CODE"):
        create_app(f"sqlite:///{tmp_path / 'socmint-open-signup.db'}")


def test_signup_flow_logs_user_in(app):
    with app.test_client() as client:
        response = signup(client)
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/")

        response = client.get("/")
        assert response.status_code == 200


def test_env_admin_user_is_admin(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_SECRET_KEY", "test-secret-key-with-enough-entropy")
    monkeypatch.setenv("SOCMINT_ADMIN_USER", "admin")
    monkeypatch.setenv("SOCMINT_ADMIN_PASSWORD", "StrongAdmin123!")
    monkeypatch.setenv("SOCMINT_AUTO_CREATE_DB", "true")
    monkeypatch.setenv("SOCMINT_DATA_DIR", str(tmp_path))
    create_app(f"sqlite:///{tmp_path / 'socmint-admin.db'}")

    user = db.get_user_by_username("admin")
    assert user.is_admin is True


def test_env_admin_rejects_weak_password(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_SECRET_KEY", "test-secret-key-with-enough-entropy")
    monkeypatch.setenv("SOCMINT_ADMIN_USER", "admin")
    monkeypatch.setenv("SOCMINT_ADMIN_PASSWORD", "weak")
    monkeypatch.setenv("SOCMINT_AUTO_CREATE_DB", "true")
    monkeypatch.setenv("SOCMINT_DATA_DIR", str(tmp_path))

    with pytest.raises(RuntimeError, match="SOCMINT_ADMIN_PASSWORD"):
        create_app(f"sqlite:///{tmp_path / 'socmint-weak-admin.db'}")


def test_self_signup_user_is_not_admin(app):
    with app.test_client() as client:
        signup(client)

    user = db.get_user_by_username("operator")
    assert user.is_admin is False


def test_signup_can_be_disabled(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_SECRET_KEY", "test-secret-key-with-enough-entropy")
    monkeypatch.setenv("SOCMINT_ALLOW_SIGNUP", "false")
    monkeypatch.setenv("SOCMINT_AUTO_CREATE_DB", "true")
    monkeypatch.setenv("SOCMINT_DATA_DIR", str(tmp_path))
    app = create_app(f"sqlite:///{tmp_path / 'socmint-no-signup.db'}")
    app.config.update(TESTING=True)

    with app.test_client() as client:
        assert client.get("/signup").status_code == 404


def test_signup_requires_invite_code(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_SECRET_KEY", "test-secret-key-with-enough-entropy")
    monkeypatch.setenv("SOCMINT_ALLOW_SIGNUP", "true")
    monkeypatch.setenv("SOCMINT_AUTO_CREATE_DB", "true")
    monkeypatch.setenv("SOCMINT_SIGNUP_INVITE_CODE", "invite-code-123")
    monkeypatch.setenv("SOCMINT_DATA_DIR", str(tmp_path))
    app = create_app(f"sqlite:///{tmp_path / 'socmint-invite.db'}")
    app.config.update(TESTING=True)

    with app.test_client() as client:
        response = signup_with_invite(client, "wrong-code")
        assert response.status_code == 200
        assert b"Valid invite code is required" in response.data

        response = signup_with_invite(client, "invite-code-123")
        assert response.status_code == 302


def test_signup_rejects_weak_password(app):
    with app.test_client() as client:
        response = signup(client, password="password")
        assert response.status_code == 200
        assert b"at least 12 characters" in response.data


def test_login_flow_after_signup(app):
    with app.test_client() as client:
        signup(client)
        client.get("/logout")

        response = login(client)
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/")


def test_logout_clears_session(app):
    with app.test_client() as client:
        signup(client)
        response = client.get("/logout")
        assert response.status_code == 302

        response = client.get("/")
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/login")


def test_csrf_required_for_login_post(app):
    with app.test_client() as client:
        response = client.post(
            "/login", data={"username": "operator", "password": "StrongPass123!"}
        )
        assert response.status_code == 400


def test_login_rate_limiting(app):
    with app.test_client() as client:
        for _ in range(5):
            response = login(client, password="WrongPass123!")
            assert response.status_code == 200

        response = login(client, password="WrongPass123!")
        assert response.status_code == 200
        assert b"Too many failed login attempts" in response.data


def test_signup_rate_limiting(app):
    with app.test_client() as client:
        for i in range(3):
            response = signup(client, username=f"operator{i}", password="weak")
            assert response.status_code == 200

        response = signup(client, username="operator4", password="weak")
        assert response.status_code == 200
        assert b"Too many signup attempts" in response.data


def test_security_headers_are_added(app):
    with app.test_client() as client:
        response = client.get("/login")
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["Referrer-Policy"] == "no-referrer"
        assert response.headers["Cross-Origin-Opener-Policy"] == "same-origin"
        assert response.headers["Cross-Origin-Resource-Policy"] == "same-origin"
        assert "default-src 'self'" in response.headers["Content-Security-Policy"]
        assert "'nonce-" in response.headers["Content-Security-Policy"]


def test_healthz_only_allows_localhost(app):
    with app.test_client() as client:
        assert client.get("/healthz").status_code == 200
        assert (
            client.get("/healthz", environ_base={"REMOTE_ADDR": "10.0.0.5"}).status_code
            == 404
        )


def test_admin_can_export_and_delete_dossier(app):
    db.create_user("admin", "StrongAdmin123!", is_admin=True)
    db.save_dossier(
        {
            "target": "operator_1",
            "type": "username",
            "data": {"sherlock": {"found": True}},
        }
    )
    session_db = db.Session()
    target = session_db.query(db.Target).filter_by(value="operator_1").first()
    target_id = target.id
    session_db.close()

    with app.test_client() as client:
        login(client, username="admin", password="StrongAdmin123!")

        response = client.get(f"/target/{target_id}/export")
        assert response.status_code == 200
        assert response.json["target"] == "operator_1"

        detail = client.get(f"/target/{target_id}")
        token = csrf_token(detail)
        response = client.post(
            f"/target/{target_id}/delete",
            data={"csrf_token": token, "confirm_target": "operator_1"},
        )
        assert response.status_code == 302

    assert db.get_dossier("operator_1") is None
    session_db = db.Session()
    actions = [event.action for event in session_db.query(db.AuditLog).all()]
    session_db.close()
    assert "dossier_export" in actions
    assert "dossier_delete" in actions


def test_admin_can_view_audit_log(app):
    db.create_user("admin", "StrongAdmin123!", is_admin=True)
    db.record_audit_event("manual_event", actor="admin", ip_address="127.0.0.1")
    db.record_audit_event("other_event", actor="operator", ip_address="127.0.0.1")

    with app.test_client() as client:
        login(client, username="admin", password="StrongAdmin123!")
        response = client.get("/admin/audit?action=manual_event")

    assert response.status_code == 200
    assert b"manual_event" in response.data
    assert b"other_event" not in response.data


def test_admin_can_manage_users(app):
    db.create_user("admin", "StrongAdmin123!", is_admin=True)

    with app.test_client() as client:
        login(client, username="admin", password="StrongAdmin123!")
        response = client.get("/admin/users")
        token = csrf_token(response)
        response = client.post(
            "/admin/users",
            data={
                "username": "analyst",
                "password": "StrongUser123!",
                "role": "analyst",
                "csrf_token": token,
            },
        )
        assert response.status_code == 302

        user = db.get_user_by_username("analyst")
        response = client.post(
            f"/admin/users/{user.id}",
            data={
                "is_active": "0",
                "is_admin": "0",
                "role": "viewer",
                "csrf_token": token,
            },
        )
        assert response.status_code == 302

    user = db.get_user_by_username("analyst")
    assert user.is_active is False
    assert user.is_admin is False
    assert user.role == "viewer"


def test_inactive_user_cannot_login(app):
    user = db.create_user("disabled", "StrongUser123!", is_admin=False)
    db.update_user(user.id, is_active=False)

    with app.test_client() as client:
        response = login(client, username="disabled", password="StrongUser123!")

    assert response.status_code == 200
    assert b"Invalid username or password" in response.data


def test_user_can_change_own_password(app):
    db.create_user("operator", "StrongPass123!", is_admin=False, role="viewer")

    with app.test_client() as client:
        login(client)
        response = client.get("/account/password")
        token = csrf_token(response)
        response = client.post(
            "/account/password",
            data={
                "current_password": "StrongPass123!",
                "new_password": "NewStrongPass123!",
                "confirm": "NewStrongPass123!",
                "csrf_token": token,
            },
        )
        assert response.status_code == 302
        client.get("/logout")
        response = login(client, password="NewStrongPass123!")

    assert response.status_code == 302


def test_non_admin_cannot_view_audit_log(app):
    with app.test_client() as client:
        signup(client)
        assert client.get("/admin/audit").status_code == 403
        assert client.get("/admin/users").status_code == 403


def test_non_admin_cannot_export_or_delete_dossier(app):
    db.save_dossier({"target": "operator_2", "type": "username"})
    session_db = db.Session()
    target = session_db.query(db.Target).filter_by(value="operator_2").first()
    target_id = target.id
    session_db.close()

    with app.test_client() as client:
        signup(client)
        assert client.get(f"/target/{target_id}/export").status_code == 403


def test_delete_requires_target_confirmation(app):
    db.create_user("admin", "StrongAdmin123!", is_admin=True)
    db.save_dossier({"target": "operator_3", "type": "username"})
    session_db = db.Session()
    target = session_db.query(db.Target).filter_by(value="operator_3").first()
    target_id = target.id
    session_db.close()

    with app.test_client() as client:
        login(client, username="admin", password="StrongAdmin123!")
        detail = client.get(f"/target/{target_id}")
        token = csrf_token(detail)
        response = client.post(
            f"/target/{target_id}/delete",
            data={"csrf_token": token, "confirm_target": "wrong"},
        )

    assert response.status_code == 302
    assert db.get_dossier("operator_3") is not None


def test_admin_can_run_dossier_from_dashboard(app):
    db.create_user("admin", "StrongAdmin123!", is_admin=True)

    with app.test_client() as client:
        login(client, username="admin", password="StrongAdmin123!")
        dashboard = client.get("/")
        token = csrf_token(dashboard)
        response = client.post(
            "/target/run",
            data={
                "target": "operator_run",
                "tools": "",
                "csrf_token": token,
            },
        )

    assert response.status_code == 302
    jobs = db.list_scan_jobs()
    assert jobs[0].target_value == "operator_run"
    assert jobs[0].status == "queued"


def test_analyst_can_queue_dossier_but_viewer_cannot(app):
    db.create_user("analyst", "StrongUser123!", role="analyst")
    db.create_user("viewer", "StrongUser123!", role="viewer")

    with app.test_client() as client:
        login(client, username="analyst", password="StrongUser123!")
        dashboard = client.get("/")
        token = csrf_token(dashboard)
        response = client.post(
            "/target/run",
            data={"target": "operator_analyst", "csrf_token": token},
        )
        assert response.status_code == 302
        client.get("/logout")

        login(client, username="viewer", password="StrongUser123!")
        password_page = client.get("/account/password")
        token = csrf_token(password_page)
        response = client.post(
            "/target/run",
            data={"target": "operator_viewer", "csrf_token": token},
        )

    assert response.status_code == 403
    assert db.list_scan_jobs()[0].target_value == "operator_analyst"
