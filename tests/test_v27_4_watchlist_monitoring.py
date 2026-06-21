from datetime import datetime, timezone

from src.socmint.watchlist_monitoring_events_v27_4 import (
    create_watchlist,
    current_watchlists,
    set_watchlist_status,
)
from src.socmint.watchlist_monitoring_workspace_v27_4 import (
    build_watchlist_workspace,
    run_watchlist_monitoring,
)


def test_v27_4_create_pause_resume_and_due_projection(tmp_path, monkeypatch):
    from src.socmint import database
    from src.socmint import watchlist_monitoring_events_v27_4 as events

    database.configure_database(f"sqlite:///{tmp_path / 'app.db'}")
    view = {
        "saved_view_id": "view-1",
        "saved_view_event_id": "event-1",
        "saved_view_event_sha256": "a" * 64,
        "definition_sha256": "b" * 64,
        "view_status": "active",
    }
    monkeypatch.setattr(events, "find_view", lambda view_id, user: view)
    created = create_watchlist(
        name="Daily findings",
        owner="alice",
        saved_view_id="view-1",
        cadence="daily",
        notification_rule="new_results",
        confirmed=True,
    )
    assert created["status"] == "watchlist_created"
    paused = set_watchlist_status(
        created["watchlist_id"],
        actor="alice",
        status="paused",
        reason="maintenance",
        confirmed=True,
    )
    assert paused["status"] == "watchlist_paused"
    resumed = set_watchlist_status(
        created["watchlist_id"],
        actor="alice",
        status="active",
        reason="resume",
        confirmed=True,
    )
    assert resumed["status"] == "watchlist_resumed"
    assert current_watchlists()[0]["watchlist_status"] == "active"
    workspace = build_watchlist_workspace(
        "alice", now=datetime(2030, 1, 1, tzinfo=timezone.utc)
    )
    assert workspace["watchlist_count"] == 1
    assert workspace["due_watchlist_count"] == 1
    assert workspace["source_records_mutated"] is False


def test_v27_4_monitoring_detects_changes_and_current_scope(tmp_path, monkeypatch):
    from src.socmint import database
    from src.socmint import watchlist_monitoring_workspace_v27_4 as workspace

    database.configure_database(f"sqlite:///{tmp_path / 'run.db'}")
    watchlist = {
        "watchlist_id": "watch-1",
        "watchlist_status": "active",
        "notification_rule": "any_change",
        "watchlist_event_id": "we-1",
        "watchlist_event_sha256": "c" * 64,
        "saved_view_binding": {
            "saved_view_id": "view-1",
            "definition_sha256": "d" * 64,
        },
    }
    monkeypatch.setattr(
        workspace, "find_watchlist", lambda watchlist_id, user: watchlist
    )
    monkeypatch.setattr(
        workspace,
        "_previous_run",
        lambda watchlist_id: {
            "monitoring_run_sequence": 1,
            "result_ids": ["r1"],
            "result_set_sha256": "e" * 64,
        },
    )
    captured = {}

    def execute(view_id, **kwargs):
        captured.update(kwargs)
        return {
            "status": "saved_view_executed",
            "execution": {
                "results": [{"result_id": "r1"}, {"result_id": "r2"}],
                "access_scope": {"allowed_case_ids": ["case-a"]},
            },
        }

    monkeypatch.setattr(workspace, "run_saved_view", execute)
    result = run_watchlist_monitoring(
        "watch-1", user_identity="alice", allowed_case_ids={"case-a"}, limit=25
    )
    assert result["status"] == "watchlist_monitoring_completed"
    assert result["added_result_ids"] == ["r2"]
    assert result["removed_result_ids"] == []
    assert result["notification_triggered"] is True
    assert captured["allowed_case_ids"] == {"case-a"}
    assert result["watchlist_grants_access"] is False
    assert result["case_access_scope_changed"] is False
