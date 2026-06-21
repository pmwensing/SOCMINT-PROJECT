from werkzeug.security import generate_password_hash

from src.socmint.user_account_mutations_v28_1 import provision_user, update_user
from src.socmint.user_account_workspace_v28_1 import build_user_account_workspace


def _seed_admin(database):
    session = database.Session()
    try:
        session.add(
            database.User(
                username="admin",
                password_hash=generate_password_hash("admin-test-value"),
                is_admin=True,
                role="admin",
                is_active=True,
            )
        )
        session.commit()
    finally:
        session.close()


def test_v28_1_provision_activate_suspend_and_audit(tmp_path):
    from src.socmint import database

    database.configure_database(f"sqlite:///{tmp_path / 'app.db'}")
    _seed_admin(database)
    created = provision_user(
        actor="admin",
        username="alice",
        role="analyst",
        is_admin=False,
        reason="new analyst",
        confirmed=True,
    )
    assert created["status"] == "user_provisioned"
    assert created["user"]["is_active"] is False
    assert created["credential_returned"] is False
    assert created["credential_hash_returned"] is False
    activated = update_user(
        "alice",
        actor="admin",
        is_active=True,
        reason="onboarding complete",
        confirmed=True,
    )
    assert activated["status"] == "user_updated"
    assert activated["account_event"]["action"] == "administration_user_activated"
    revised = update_user(
        "alice", actor="admin", role="reviewer", reason="role change", confirmed=True
    )
    assert revised["user"]["role"] == "reviewer"
    suspended = update_user(
        "alice", actor="admin", is_active=False, reason="leave", confirmed=True
    )
    assert suspended["account_event"]["action"] == "administration_user_suspended"
    workspace = build_user_account_workspace()
    assert workspace["user_count"] == 2
    assert workspace["suspended_user_count"] == 1
    assert workspace["account_event_count"] == 4
    assert workspace["credentials_visible"] is False
    assert workspace["credential_hashes_visible"] is False
    assert workspace["case_access_scope_changed"] is False


def test_v28_1_preserves_last_active_administrator(tmp_path):
    from src.socmint import database

    database.configure_database(f"sqlite:///{tmp_path / 'guard.db'}")
    _seed_admin(database)
    result = update_user(
        "admin", actor="admin", is_active=False, reason="test", confirmed=True
    )
    assert result["status"] == "blocked"
    assert result["blockers"] == [
        {"key": "last_active_administrator_must_be_preserved"}
    ]
