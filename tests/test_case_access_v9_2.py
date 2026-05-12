from src.socmint import database as db
from src.socmint.case_access import add_team_member
from src.socmint.case_access import assign_case
from src.socmint.case_access import case_access_decision
from src.socmint.case_access import case_access_summary
from src.socmint.case_access import team_access_summary
from src.socmint.case_access import user_case_access


def test_case_assignment_allows_required_access(tmp_path):
    db.configure_database(f"sqlite:///{tmp_path / 'socmint.db'}")
    db.create_user("analyst", "StrongPass123!", role="analyst")

    assign_case(101, "analyst", access_level="analyst", actor="admin")
    view = case_access_decision("analyst", 101, required="view")
    run = case_access_decision("analyst", 101, required="run")
    export = case_access_decision("analyst", 101, required="export")

    assert view["allowed"] is True
    assert run["allowed"] is True
    assert export["allowed"] is False
    assert export["required_level"] == "manager"


def test_admin_bypasses_case_assignment(tmp_path):
    db.configure_database(f"sqlite:///{tmp_path / 'socmint.db'}")
    db.create_user("admin", "StrongPass123!", role="admin")

    decision = case_access_decision("admin", 999, required="export")

    assert decision["allowed"] is True
    assert decision["access_level"] == "admin"


def test_team_and_case_summaries(tmp_path):
    db.configure_database(f"sqlite:///{tmp_path / 'socmint.db'}")
    db.create_user("viewer", "StrongPass123!", role="viewer")

    add_team_member("team-a", "viewer", role="member", actor="admin")
    assign_case(202, "viewer", access_level="viewer", actor="admin")

    team = team_access_summary("team-a")
    case = case_access_summary(202)
    user = user_case_access("viewer")

    assert team["schema"] == "socmint.case_access.v9_2_0"
    assert team["member_count"] == 1
    assert case["assignment_count"] == 1
    assert user["case_count"] == 1
    assert user["cases"][0]["case_id"] == 202


def test_unassigned_user_is_denied(tmp_path):
    db.configure_database(f"sqlite:///{tmp_path / 'socmint.db'}")
    db.create_user("viewer", "StrongPass123!", role="viewer")

    decision = case_access_decision("viewer", 303, required="view")

    assert decision["allowed"] is False
    assert decision["reason"] == "insufficient_case_access"
    assert decision["access_level"] == "none"
