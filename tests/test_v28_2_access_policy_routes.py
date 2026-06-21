from pathlib import Path

from src.socmint.dashboard import create_app
from src.socmint.dossier_assembly_routes_v21_0 import (
    register_dossier_assembly_routes_v21_0,
)


def _app(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    monkeypatch.setenv(
        "SOCMINT_SECRET_KEY", "v28-2-route-test-secret-key-with-more-than-32-characters"
    )
    app = create_app()
    register_dossier_assembly_routes_v21_0(app)
    return app


def test_v28_2_routes_require_admin_csrf_and_dispatch(tmp_path, monkeypatch):
    from src.socmint import access_policy_routes_v28_2 as routes
    from src.socmint import access_policy_write_routes_v28_2 as writes

    payload = {
        "schema": "socmint.role_permission_access_policy.v28_2",
        "version": "v28.2.0",
        "status": "ready",
        "permission_catalog": [],
        "roles": [],
        "active_roles": [],
        "role_count": 0,
        "active_role_count": 0,
        "permission_matrix": [],
        "access_rules": [],
        "active_access_rules": [],
        "access_rule_count": 0,
        "active_access_rule_count": 0,
        "explicit_deny_rule_count": 0,
        "least_privilege_findings": [],
        "least_privilege_finding_count": 0,
        "access_policy_history": [],
        "access_policy_event_count": 0,
        "explicit_deny_overrides_allow": True,
        "access_views_grant_access": False,
        "case_access_scope_changed_by_view": False,
    }
    monkeypatch.setattr(
        routes, "actor_is_administrator", lambda actor: actor == "admin"
    )
    monkeypatch.setattr(
        writes, "actor_is_administrator", lambda actor: actor == "admin"
    )
    monkeypatch.setattr(routes, "build_access_policy_workspace", lambda: payload)
    monkeypatch.setattr(
        routes,
        "evaluate_effective_access",
        lambda username, case_id: {
            "status": "ready",
            "username": username,
            "case_id": case_id,
            "effective_permissions": ["case.read"],
            "deny_overrides_allow": True,
        },
    )
    monkeypatch.setattr(
        writes,
        "define_role",
        lambda **kwargs: {"status": "role_defined", "role_id": "role-1"},
    )
    monkeypatch.setattr(
        writes,
        "revise_role",
        lambda *args, **kwargs: {"status": "role_revised", "role_id": "role-2"},
    )
    monkeypatch.setattr(
        writes,
        "create_case_access_rule",
        lambda **kwargs: {
            "status": "case_access_rule_created",
            "access_rule_id": "rule-1",
        },
    )
    monkeypatch.setattr(
        writes,
        "revoke_case_access_rule",
        lambda *args, **kwargs: {"status": "case_access_rule_revoked"},
    )
    client = _app(tmp_path, monkeypatch).test_client()
    assert client.get("/api/v1/administration/access-policy").status_code == 401
    with client.session_transaction() as sess:
        sess["user"] = "viewer"
    assert client.get("/api/v1/administration/access-policy").status_code == 403
    csrf = "v28-2-csrf-token"
    with client.session_transaction() as sess:
        sess["user"] = "admin"
        sess["_csrf_token"] = csrf
    headers = {"X-CSRF-Token": csrf}
    assert client.get("/administration/access-policy").status_code == 200
    assert (
        client.get(
            "/api/v1/administration/access-policy/evaluate?username=alice&case_id=case-a"
        ).status_code
        == 200
    )
    defined = client.post(
        "/api/v1/administration/access-policy/roles",
        json={
            "name": "analyst",
            "permissions": ["case.read"],
            "inherits_role_ids": [],
            "reason": "define",
            "confirmed": True,
        },
        headers=headers,
    )
    revised = client.post(
        "/api/v1/administration/access-policy/roles/role-1/revise",
        json={
            "name": "analyst",
            "permissions": ["case.read", "evidence.read"],
            "inherits_role_ids": [],
            "reason": "revise",
            "confirmed": True,
        },
        headers=headers,
    )
    granted = client.post(
        "/api/v1/administration/access-policy/case-rules",
        json={
            "subject_type": "user",
            "subject_id": "alice",
            "case_id": "case-a",
            "permissions": ["case.read"],
            "effect": "allow",
            "reason": "grant",
            "confirmed": True,
        },
        headers=headers,
    )
    revoked = client.post(
        "/api/v1/administration/access-policy/case-rules/rule-1/revoke",
        json={"reason": "remove", "confirmed": True},
        headers=headers,
    )
    assert [
        defined.status_code,
        revised.status_code,
        granted.status_code,
        revoked.status_code,
    ] == [200, 200, 200, 200]


def test_v28_2_release_note_and_no_migration():
    note = Path("release/V28_2_ROLE_PERMISSION_ACCESS_POLICY_MANAGEMENT.md").read_text(
        encoding="utf-8"
    )
    for phrase in (
        "Role, Permission, and Access Policy Management",
        "controlled role definitions",
        "permission matrices",
        "inherited permissions",
        "explicit deny rules",
        "case-level access grants",
        "least-privilege checks",
        "immutable access-policy history",
        "explicit deny overrides allow",
        "administrator required",
        "explicit confirmation",
        "administrative reason",
        "access views do not grant access",
        "no migration",
    ):
        assert phrase in note
    migrations = [
        path
        for directory in (Path("migrations"), Path("alembic"))
        if directory.exists()
        for path in directory.rglob("*v28_2*")
    ]
    assert migrations == []
