from src.socmint.access_policy_events_v28_2 import create_case_access_rule, define_role, revise_role, revoke_case_access_rule
from src.socmint.access_policy_workspace_v28_2 import build_access_policy_workspace, evaluate_effective_access, resolve_role_permissions


def test_v28_2_roles_inheritance_denies_and_history(tmp_path, monkeypatch):
    from src.socmint import database
    from src.socmint import access_policy_workspace_v28_2 as workspace
    database.configure_database(f"sqlite:///{tmp_path / 'app.db'}")
    base = define_role(actor="admin", name="analyst", permissions=["case.read","evidence.read"], inherits_role_ids=[], description="base", reason="define", confirmed=True)
    assert base["status"] == "role_defined"
    reviewer = define_role(actor="admin", name="reviewer", permissions=["review.request"], inherits_role_ids=[base["role_id"]], description="review", reason="define", confirmed=True)
    assert reviewer["status"] == "role_defined"
    resolution = resolve_role_permissions(reviewer["role_id"])
    assert resolution["effective_permissions"] == ["case.read","evidence.read","review.request"]
    revised = revise_role(reviewer["role_id"], actor="admin", name="reviewer", permissions=["review.request","review.decide"], inherits_role_ids=[base["role_id"]], description="updated", reason="revise", confirmed=True)
    assert revised["status"] == "role_revised"
    allow = create_case_access_rule(actor="admin", subject_type="user", subject_id="alice", case_id="case-a", permissions=["case.write"], effect="allow", reason="grant", confirmed=True)
    deny = create_case_access_rule(actor="admin", subject_type="user", subject_id="alice", case_id="case-a", permissions=["case.write"], effect="deny", reason="deny", confirmed=True)
    assert allow["status"] == deny["status"] == "case_access_rule_created"
    monkeypatch.setattr(workspace, "_users", lambda: [{"username":"alice","role":"analyst","is_admin":False,"is_active":True}])
    effective = evaluate_effective_access("alice", "case-a")
    assert "case.read" in effective["effective_permissions"]
    assert "case.write" not in effective["effective_permissions"]
    assert effective["explicit_denies"] == ["case.write"]
    assert effective["deny_overrides_allow"] is True
    revoked = revoke_case_access_rule(allow["access_rule_id"], actor="admin", reason="remove", confirmed=True)
    assert revoked["status"] == "case_access_rule_revoked"
    result = build_access_policy_workspace()
    assert result["active_role_count"] == 2
    assert result["explicit_deny_rule_count"] == 1
    assert result["access_policy_event_count"] == 6
    assert result["access_views_grant_access"] is False


def test_v28_2_rejects_invalid_permission_and_self_inheritance(tmp_path):
    from src.socmint import database
    database.configure_database(f"sqlite:///{tmp_path / 'blocked.db'}")
    bad = define_role(actor="admin", name="bad", permissions=["unknown.permission"], inherits_role_ids=[], description="", reason="bad", confirmed=True)
    assert bad["status"] == "blocked"
    role = define_role(actor="admin", name="viewer", permissions=["case.read"], inherits_role_ids=[], description="", reason="ok", confirmed=True)
    revised = revise_role(role["role_id"], actor="admin", name="viewer", permissions=["case.read"], inherits_role_ids=[role["role_id"]], description="", reason="bad", confirmed=True)
    assert revised["status"] == "blocked"
