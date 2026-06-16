from src.socmint import database
from src.socmint import cross_case_correlation_review_v25_1 as service


def _candidate():
    return {
        "correlation_id": "cross-case-entity-abc",
        "category": "entity",
        "match_value": "entity-42",
        "display_values": ["entity-42", "ENTITY-42"],
        "case_ids": ["case-alpha", "case-bravo"],
        "case_count": 2,
        "occurrence_count": 2,
        "occurrences": [
            {
                "case_id": "case-alpha",
                "record_id": 1,
                "source_action": "case_entity_observed",
                "actor": "analyst-a",
                "occurred_at": "2026-06-16T02:00:00+00:00",
                "field_path": "entity_id",
                "display_value": "entity-42",
                "provenance_sha256": "a" * 64,
            },
            {
                "case_id": "case-bravo",
                "record_id": 2,
                "source_action": "case_entity_observed",
                "actor": "analyst-b",
                "occurred_at": "2026-06-16T03:00:00+00:00",
                "field_path": "entity_id",
                "display_value": "ENTITY-42",
                "provenance_sha256": "b" * 64,
            },
        ],
        "human_review_required": True,
        "confirmed_match": False,
    }


def _setup(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'app.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    database.configure_database(url)
    workspace = {
        "access_scope": {
            "mode": "restricted",
            "allowed_case_ids": ["case-alpha", "case-bravo"],
            "visible_case_ids": ["case-alpha", "case-bravo"],
        },
        "minimum_case_count": 2,
    }
    monkeypatch.setattr(
        service,
        "_candidate_from_workspace",
        lambda *args, **kwargs: (_candidate(), workspace),
    )


def test_v25_1_records_accept_reject_defer_with_immutable_history(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    decisions = []
    for value in ("accept", "reject", "defer"):
        result = service.review_correlation_candidate(
            "cross-case-entity-abc",
            category="entity",
            decision=value,
            reason=f"Reason for {value}.",
            reviewer="reviewer-one",
            confirmed=True,
            allowed_case_ids={"case-alpha", "case-bravo"},
        )
        decisions.append(result)
        assert result["status"] == "correlation_review_recorded"
        assert result["decision"] == value
        assert result["reviewer"] == "reviewer-one"
        assert result["candidate_snapshot"]["occurrence_count"] == 2
        assert result["source_occurrence_count"] == 2
        assert result["source_occurrences_preserved"] is True
        assert result["source_records_mutated"] is False
        assert result["candidate_mutated"] is False
        assert result["case_provenance_mutated"] is False
        assert len(result["candidate_sha256"]) == 64
        assert len(result["review_decision_sha256"]) == 64

    history = service.correlation_review_history("cross-case-entity-abc")
    assert [item["decision"] for item in history] == ["accept", "reject", "defer"]
    assert [item["action_record_id"] for item in history] == [
        decisions[0]["action_record_id"],
        decisions[1]["action_record_id"],
        decisions[2]["action_record_id"],
    ]
    assert service.latest_correlation_review("cross-case-entity-abc")["decision"] == "defer"


def test_v25_1_split_requires_complete_non_overlapping_occurrence_groups(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    result = service.review_correlation_candidate(
        "cross-case-entity-abc",
        category="entity",
        decision="split",
        reason="The occurrences represent two distinct entities.",
        reviewer="reviewer-two",
        confirmed=True,
        split_groups=[
            {
                "group_id": "group-a",
                "label": "Alpha entity",
                "occurrence_provenance_sha256": ["a" * 64],
            },
            {
                "group_id": "group-b",
                "label": "Bravo entity",
                "occurrence_provenance_sha256": ["b" * 64],
            },
        ],
    )
    assert result["status"] == "correlation_review_recorded"
    assert result["decision"] == "split"
    assert len(result["split_groups"]) == 2
    assert result["split_groups"][0]["occurrence_provenance_sha256"] == ["a" * 64]
    assert result["split_groups"][1]["occurrence_provenance_sha256"] == ["b" * 64]

    invalid = service.review_correlation_candidate(
        "cross-case-entity-abc",
        category="entity",
        decision="split",
        reason="Incomplete split.",
        reviewer="reviewer-two",
        confirmed=True,
        split_groups=[
            {
                "group_id": "group-a",
                "occurrence_provenance_sha256": ["a" * 64],
            },
            {
                "group_id": "group-b",
                "occurrence_provenance_sha256": ["a" * 64],
            },
        ],
    )
    assert invalid["blockers"][0]["key"] == "valid_complete_split_groups_required"


def test_v25_1_enforces_confirmation_reason_reviewer_decision_and_visibility(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    base = {
        "correlation_id": "cross-case-entity-abc",
        "category": "entity",
        "decision": "accept",
        "reason": "Supported by matching occurrences.",
        "reviewer": "reviewer-one",
        "confirmed": True,
    }
    variants = [
        ({"confirmed": False}, "explicit_correlation_review_confirmation_required"),
        ({"decision": "merge"}, "correlation_review_decision_invalid"),
        ({"reviewer": ""}, "correlation_reviewer_identity_required"),
        ({"reason": ""}, "correlation_review_reason_required"),
    ]
    for changes, expected in variants:
        payload = {**base, **changes}
        correlation_id = payload.pop("correlation_id")
        result = service.review_correlation_candidate(correlation_id, **payload)
        assert result["blockers"][0]["key"] == expected

    monkeypatch.setattr(
        service,
        "_candidate_from_workspace",
        lambda *args, **kwargs: (None, {"access_scope": {"mode": "restricted"}}),
    )
    result = service.review_correlation_candidate(**base)
    assert result["blockers"][0]["key"] == "visible_correlation_candidate_required"
