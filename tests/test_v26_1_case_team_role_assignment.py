import datetime as dt

from src.socmint import case_team_role_assignment_v26_1 as service


class _FakeSession:
    def __init__(self):
        self.row = None

    def add(self, row):
        self.row = row

    def commit(self):
        self.row.id = 101
        self.row.created_at = dt.datetime(2026, 6, 16, 14, 0, tzinfo=dt.UTC)

    def refresh(self, row):
        return None

    def close(self):
        return None


def _patch_recording(monkeypatch):
    monkeypatch.setattr(service, "_ensure_storage", lambda: None)
    monkeypatch.setattr(service.database, "Session", _FakeSession)
    monkeypatch.setattr(
        service,
        "_case_state",
        lambda case_id: {
            "portfolio_schema": "socmint.portfolio_operations_dashboard.v24_0",
            "portfolio_version": "v24.0.0",
            "case": {"case_id": case_id, "stage": "active", "status": "operational"},
        },
    )


def test_v26_1_records_append_only_assignment_with_source_binding(monkeypatch):
    _patch_recording(monkeypatch)
    monkeypatch.setattr(
        service,
        "latest_active_assignment",
        lambda *args, **kwargs: {
            "case_team_assignment_id": "case-team-assignment-old",
            "case_team_event_sha256": "a" * 64,
        },
    )

    result = service.assign_case_team_role(
        "case-a",
        user_identity="alice",
        role="lead_analyst",
        assigned_by="supervisor",
        reason="Lead the active investigation.",
        confirmed=True,
        effective_from="2026-06-16T14:00:00+00:00",
        allowed_case_ids={"case-a"},
    )

    assert result["status"] == "case_team_assignment_recorded"
    assert result["user_identity"] == "alice"
    assert result["role"] == "lead_analyst"
    assert result["supersedes_assignment_id"] == "case-team-assignment-old"
    assert result["source_case_state_sha256"]
    assert len(result["case_team_event_sha256"]) == 64
    assert result["source_records_mutated"] is False
    assert result["prior_assignments_mutated"] is False
    assert result["case_access_scope_changed"] is False
    assert result["access_granted_by_assignment"] is False


def test_v26_1_records_revocation_bound_to_active_assignment(monkeypatch):
    _patch_recording(monkeypatch)
    monkeypatch.setattr(
        service,
        "current_case_team",
        lambda case_id: [
            {
                "case_team_assignment_id": "case-team-assignment-1",
                "case_team_event_id": "case-team-event-1",
                "case_team_event_sha256": "b" * 64,
                "action_record_id": 77,
                "user_identity": "alice",
                "role": "reviewer",
                "assignment_status": "active",
            }
        ],
    )

    result = service.revoke_case_team_role(
        "case-a",
        "case-team-assignment-1",
        revoked_by="supervisor",
        reason="Review assignment completed.",
        confirmed=True,
        allowed_case_ids={"case-a"},
    )

    assert result["status"] == "case_team_revocation_recorded"
    assert result["assignment_binding"]["action_record_id"] == 77
    assert result["assignment_binding_sha256"]
    assert result["assignment_status"] == "revoked"
    assert result["assignment_event_mutated"] is False
    assert result["case_access_scope_changed"] is False
    assert result["access_revoked_by_role_event"] is False


def test_v26_1_reducer_and_validation_blockers(monkeypatch):
    monkeypatch.setattr(
        service,
        "case_team_history",
        lambda case_id: [
            {
                "event_type": "assignment",
                "case_team_assignment_id": "a1",
                "case_team_event_sha256": "1" * 64,
                "user_identity": "alice",
                "role": "analyst",
                "recorded_at": "2026-06-16T10:00:00+00:00",
            },
            {
                "event_type": "assignment",
                "case_team_assignment_id": "a2",
                "case_team_event_sha256": "2" * 64,
                "supersedes_assignment_id": "a1",
                "user_identity": "alice",
                "role": "analyst",
                "recorded_at": "2026-06-16T11:00:00+00:00",
            },
            {
                "event_type": "revocation",
                "case_team_assignment_id": "a2",
                "case_team_event_id": "r2",
                "reason": "done",
                "recorded_by": "supervisor",
                "recorded_at": "2026-06-16T12:00:00+00:00",
            },
        ],
    )
    team = {
        item["case_team_assignment_id"]: item
        for item in service.current_case_team("case-a")
    }
    assert team["a1"]["assignment_status"] == "superseded"
    assert team["a2"]["assignment_status"] == "revoked"

    denied = service.assign_case_team_role(
        "case-hidden",
        user_identity="alice",
        role="analyst",
        assigned_by="supervisor",
        reason="test",
        confirmed=True,
        allowed_case_ids={"case-a"},
    )
    invalid_role = service.assign_case_team_role(
        "case-a",
        user_identity="alice",
        role="administrator",
        assigned_by="supervisor",
        reason="test",
        confirmed=True,
        allowed_case_ids={"case-a"},
    )
    assert denied["blockers"][0]["key"] == "case_access_required"
    assert invalid_role["blockers"][0]["key"] == "case_team_role_not_in_catalog"
