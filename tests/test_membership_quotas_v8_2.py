from src.socmint import database as db
from src.socmint.membership import assign_membership
from src.socmint.membership import ensure_default_membership
from src.socmint.membership import evaluate_gate
from src.socmint.membership import list_memberships
from src.socmint.membership import record_usage
from src.socmint.membership import set_quota_override


def test_free_membership_is_created_and_blocks_paid_exports(tmp_path):
    db.configure_database(f"sqlite:///{tmp_path / 'socmint.db'}")
    db.create_user("freeuser", "StrongPass123!", role="viewer")

    summary = ensure_default_membership("freeuser", actor="test")
    gate = evaluate_gate("freeuser", "signed_export")

    assert summary["schema"] == "socmint.membership.v8_2_0"
    assert summary["plan"] == "free"
    assert summary["usage"]["signed_exports_per_month"]["limit"] == 0
    assert gate["allowed"] is False
    assert gate["upgrade_required"] is True


def test_paid_plan_unlocks_and_records_usage(tmp_path):
    db.configure_database(f"sqlite:///{tmp_path / 'socmint.db'}")
    db.create_user("analyst", "StrongPass123!", role="analyst")

    assign_membership("analyst", "weekly", actor="admin")
    gate = evaluate_gate("analyst", "signed_export", consume=True)
    summary = ensure_default_membership("analyst")

    assert gate["allowed"] is True
    assert gate["used"] == 1
    assert summary["plan"] == "weekly"
    assert summary["usage"]["signed_exports_per_month"]["used"] == 1
    assert summary["usage"]["signed_exports_per_month"]["remaining"] == 2


def test_quota_override_expands_free_connector_runs(tmp_path):
    db.configure_database(f"sqlite:///{tmp_path / 'socmint.db'}")
    db.create_user("operator", "StrongPass123!", role="analyst")
    ensure_default_membership("operator")
    set_quota_override(
        "operator",
        "connector_runs_per_day",
        12,
        actor="admin",
        reason="case-specific authorization",
    )

    for _ in range(11):
        record_usage("operator", "connector_run", "connector_runs_per_day")

    allowed = evaluate_gate("operator", "connector_run")
    blocked = evaluate_gate("operator", "connector_run", amount=2)

    assert allowed["allowed"] is True
    assert allowed["limit"] == 12
    assert allowed["used"] == 11
    assert blocked["allowed"] is False


def test_list_memberships_reports_unassigned_users_as_free(tmp_path):
    db.configure_database(f"sqlite:///{tmp_path / 'socmint.db'}")
    db.create_user("newuser", "StrongPass123!", role="viewer")

    payload = list_memberships()
    row = next(item for item in payload["memberships"] if item["username"] == "newuser")

    assert payload["schema"] == "socmint.membership.v8_2_0"
    assert row["plan_key"] == "free"
