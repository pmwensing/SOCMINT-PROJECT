from src.socmint import collaboration_note_events_v26_2 as events
from src.socmint import collaboration_notes_workspace_v26_2 as workspace


def _patch(monkeypatch):
    counter = {"value": 0}
    monkeypatch.setattr(
        events,
        "case_state",
        lambda case_id: {"case": {"case_id": case_id, "stage": "active"}},
    )

    def record(case_id, actor, action, event, ip_address):
        counter["value"] += 1
        return counter["value"], f"2026-06-16T1{counter['value']}:00:00+00:00"

    monkeypatch.setattr(events, "_record", record)


def test_v26_2_note_mentions_correction_and_acknowledgement(monkeypatch):
    _patch(monkeypatch)
    note = events.create_note(
        "case-a",
        author="paul",
        body="Review the evidence package.",
        target_type="evidence",
        target_id="package-1",
        mentioned_users=["alice", "alice", "paul"],
        visibility="case_team",
        priority="high",
        acknowledgement_required=True,
        confirmed=True,
        allowed_case_ids={"case-a"},
    )
    assert note["status"] == "collaboration_note_recorded"
    assert note["mentioned_users"] == ["alice"]
    assert note["mention_count"] == 1
    assert note["mention_events"][0]["mentioned_user"] == "alice"
    assert note["mention_events"][0]["access_granted_by_mention"] is False
    assert len(note["collaboration_note_sha256"]) == 64
    assert note["source_records_mutated"] is False
    assert note["prior_notes_mutated"] is False

    previous = {**note, "note_status": "active"}
    correction = events.correct_note(
        "case-a",
        note["collaboration_note_id"],
        author="paul",
        body="Review the corrected evidence package.",
        reason="Clarified package reference.",
        previous_note=previous,
        confirmed=True,
        allowed_case_ids={"case-a"},
    )
    assert correction["status"] == "collaboration_note_correction_recorded"
    assert correction["supersedes_note_id"] == note["collaboration_note_id"]
    assert (
        correction["previous_note_binding"]["action_record_id"]
        == note["action_record_id"]
    )
    assert correction["superseded_note_mutated"] is False

    ack = events.acknowledge_note(
        "case-a",
        correction["collaboration_note_id"],
        acknowledged_by="alice",
        response="Acknowledged.",
        note={**correction, "note_status": "active"},
        confirmed=True,
        allowed_case_ids={"case-a"},
    )
    assert ack["status"] == "collaboration_note_acknowledged"
    assert (
        ack["note_binding"]["collaboration_note_id"]
        == correction["collaboration_note_id"]
    )
    assert ack["note_event_mutated"] is False


def test_v26_2_projection_marks_superseded_unread_and_ack_required(monkeypatch):
    monkeypatch.setattr(
        workspace,
        "history",
        lambda case_id: [
            {
                "event_type": "note",
                "collaboration_note_id": "n1",
                "collaboration_note_sha256": "1" * 64,
                "author": "paul",
                "body": "old",
                "mentioned_users": ["alice"],
                "acknowledgement_required": True,
                "recorded_at": "2026-06-16T10:00:00+00:00",
            },
            {
                "event_type": "correction",
                "collaboration_note_id": "n2",
                "collaboration_note_sha256": "2" * 64,
                "supersedes_note_id": "n1",
                "author": "paul",
                "body": "new",
                "mentioned_users": ["alice"],
                "acknowledgement_required": True,
                "recorded_at": "2026-06-16T11:00:00+00:00",
            },
            {
                "event_type": "acknowledgement",
                "collaboration_note_id": "n2",
                "acknowledged_by": "bob",
                "recorded_at": "2026-06-16T12:00:00+00:00",
            },
        ],
    )
    result = workspace.build_collaboration_notes_workspace(
        "case-a", user_identity="alice"
    )
    notes = {item["collaboration_note_id"]: item for item in result["notes"]}
    assert notes["n1"]["note_status"] == "superseded"
    assert notes["n2"]["note_status"] == "active"
    assert result["unread_mention_count"] == 1
    assert result["acknowledgement_required_count"] == 1
    assert result["status"] == "attention_required"
    assert result["access_granted_by_mention"] is False


def test_v26_2_validation_and_access_blockers(monkeypatch):
    _patch(monkeypatch)
    denied = events.create_note(
        "case-hidden",
        author="paul",
        body="x",
        target_type="case",
        target_id=None,
        mentioned_users=[],
        visibility="case_team",
        priority="normal",
        confirmed=True,
        allowed_case_ids={"case-a"},
    )
    invalid = events.create_note(
        "case-a",
        author="paul",
        body="x",
        target_type="unknown",
        target_id=None,
        mentioned_users=[],
        visibility="case_team",
        priority="normal",
        confirmed=True,
        allowed_case_ids={"case-a"},
    )
    assert denied["blockers"][0]["key"] == "case_access_required"
    assert invalid["blockers"][0]["key"] == "collaboration_note_target_not_in_catalog"
