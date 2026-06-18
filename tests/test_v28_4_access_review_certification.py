from src.socmint.access_review_events_v28_4 import assign_review, close_review, create_review, decide_review
from src.socmint.access_review_workspace_v28_4 import build_access_review_workspace


def test_v28_4_review_assignment_decisions_remediation_and_closure(tmp_path, monkeypatch):
    from src.socmint import database
    from src.socmint import access_review_workspace_v28_4 as workspace
    database.configure_database(f"sqlite:///{tmp_path / 'app.db'}")
    created = create_review(actor="admin", name="Quarterly Review", scope={"users":["alice"],"case_ids":["case-a"]}, due_at="2026-07-01T00:00:00+00:00", reason="quarterly", confirmed=True)
    assert created["status"] == "access_review_created"
    assigned = assign_review(created["review_id"], actor="admin", reviewer_username="reviewer", subject_type="user", subject_id="alice", case_id="case-a", reason="assign", confirmed=True)
    assert assigned["status"] == "access_review_assigned"
    decided = decide_review(created["review_id"], actor="admin", assignment_id=assigned["review_assignment_id"], decision="reduce", retained_permissions=["case.read"], reason="least privilege", confirmed=True)
    assert decided["status"] == "access_review_decided"
    assert decided["remediation_required"] is True
    closed = close_review(created["review_id"], actor="admin", reason="complete", confirmed=True)
    assert closed["status"] == "access_review_closed"
    monkeypatch.setattr(workspace, "current_access_rules", lambda: [])
    monkeypatch.setattr(workspace, "current_roles", lambda: [])
    result = build_access_review_workspace()
    assert result["review_count"] == 1
    assert result["closed_review_count"] == 1
    assert result["pending_assignment_count"] == 0
    assert result["decision_counts"] == {"reduce":1}
    assert result["remediation_queue_count"] == 1
    assert result["review_decisions_mutate_access_policy"] is False
    assert result["remediation_requires_separate_policy_action"] is True
    assert result["access_review_event_count"] == 4


def test_v28_4_blocks_duplicate_decision_and_unresolved_closure(tmp_path):
    from src.socmint import database
    database.configure_database(f"sqlite:///{tmp_path / 'blocked.db'}")
    review = create_review(actor="admin", name="Review", scope={"roles":["role-1"]}, due_at="", reason="create", confirmed=True)
    assignment = assign_review(review["review_id"], actor="admin", reviewer_username="reviewer", subject_type="role", subject_id="role-1", case_id="", reason="assign", confirmed=True)
    unresolved = close_review(review["review_id"], actor="admin", reason="early", confirmed=True)
    assert unresolved["status"] == "blocked"
    first = decide_review(review["review_id"], actor="admin", assignment_id=assignment["review_assignment_id"], decision="certify", retained_permissions=[], reason="valid", confirmed=True)
    assert first["status"] == "access_review_decided"
    duplicate = decide_review(review["review_id"], actor="admin", assignment_id=assignment["review_assignment_id"], decision="revoke", retained_permissions=[], reason="change", confirmed=True)
    assert duplicate["status"] == "blocked"
