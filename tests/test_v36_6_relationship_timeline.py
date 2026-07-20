from __future__ import annotations

from src.socmint import database
from src.socmint import relationship_timeline_v36_6 as timeline


def _configure(monkeypatch, tmp_path):
    database.configure_database(f"sqlite:///{tmp_path / 'timeline.db'}")
    monkeypatch.setattr(
        timeline,
        "find_claim",
        lambda claim_id: {
            "claim_id": claim_id,
            "claim_state": "proposed",
            "case_id": "case-a",
            "claim_event_sha256": "a" * 64,
        },
    )
    monkeypatch.setattr(
        timeline,
        "find_verification",
        lambda claim_id: {
            "claim_id": claim_id,
            "claim_verification_assessment_sha256": "b" * 64,
        },
    )
    monkeypatch.setattr(
        timeline,
        "find_source",
        lambda source_id: {
            "source_id": source_id,
            "case_id": "case-a",
            "source_event_sha256": "c" * 64,
            "capture_sha256": "d" * 64,
        },
    )
    monkeypatch.setattr(
        timeline,
        "find_canonical_observation",
        lambda observation_id: {
            "canonical_observation_id": observation_id,
            "case_id": "case-a",
            "observation_state": "accepted",
            "canonical_observation_event_sha256": "e" * 64,
        },
    )


def _assess(**overrides):
    values = {
        "actor": "admin",
        "claim_id": "claim-1",
        "relationship_type": "person_to_organization",
        "subject_entity_id": "person-1",
        "object_entity_id": "org-1",
        "source_ids": ["source-1"],
        "observation_ids": ["observation-1"],
        "event_time": "2026-07-01T10:00:00+00:00",
        "report_time": "2026-07-02T10:00:00+00:00",
        "capture_time": "2026-07-03T10:00:00+00:00",
        "valid_from": "2026-07-01T10:00:00+00:00",
        "valid_to": None,
        "inference_class": "direct_evidence",
        "inference_warning": "Evidence supports the relationship but not causation.",
        "limitations": [],
        "reason": "Create source-grounded relationship timeline assessment.",
        "confirmed": True,
    }
    values.update(overrides)
    return timeline.assess_relationship_timeline(**values)


def test_v36_6_records_source_grounded_relationship(monkeypatch, tmp_path):
    _configure(monkeypatch, tmp_path)
    result = _assess()
    assert result["status"] == "relationship_timeline_assessed"
    assert result["relationship_type"] == "person_to_organization"
    assert result["times"]["event_time"] == "2026-07-01T10:00:00+00:00"
    assert result["relationship_asserted_as_truth"] is False
    assert result["causation_assigned"] is False
    assert result["graph_mutated"] is False
    assert timeline.timeline_for_entity("person-1")[0][
        "relationship_timeline_assessment_id"
    ] == result["relationship_timeline_assessment_id"]


def test_v36_6_cooccurrence_cannot_be_promoted_to_relationship(
    monkeypatch,
    tmp_path,
):
    _configure(monkeypatch, tmp_path)
    blocked = _assess(
        relationship_type="co_occurrence",
        inference_class="supported_inference",
    )
    assert blocked["blockers"] == [
        {"key": "co_occurrence_must_remain_co_occurrence_only"}
    ]

    accepted = _assess(
        relationship_type="co_occurrence",
        inference_class="co_occurrence_only",
    )
    assert accepted["status"] == "relationship_timeline_assessed"
    assert accepted["causation_assigned"] is False


def test_v36_6_rejects_invalid_time_order(monkeypatch, tmp_path):
    _configure(monkeypatch, tmp_path)
    report = _assess(report_time="2026-06-30T10:00:00+00:00")
    assert report["blockers"] == [{"key": "report_time_precedes_event_time"}]
    capture = _assess(capture_time="2026-06-30T10:00:00+00:00")
    assert capture["blockers"] == [{"key": "capture_time_precedes_event_time"}]
    validity = _assess(
        valid_from="2026-07-05T10:00:00+00:00",
        valid_to="2026-07-04T10:00:00+00:00",
    )
    assert validity["blockers"] == [
        {"key": "relationship_validity_range_invalid"}
    ]


def test_v36_6_requires_verified_claim_and_accepted_observation(
    monkeypatch,
    tmp_path,
):
    _configure(monkeypatch, tmp_path)
    monkeypatch.setattr(timeline, "find_verification", lambda claim_id: None)
    missing = _assess()
    assert missing["blockers"] == [{"key": "claim_verification_required"}]

    _configure(monkeypatch, tmp_path)
    monkeypatch.setattr(
        timeline,
        "find_canonical_observation",
        lambda observation_id: {
            "canonical_observation_id": observation_id,
            "case_id": "case-a",
            "observation_state": "quarantined",
        },
    )
    observation = _assess()
    assert observation["blockers"] == [
        {"key": "accepted_canonical_observation_required"}
    ]


def test_v36_6_duplicate_assessment_is_blocked(monkeypatch, tmp_path):
    _configure(monkeypatch, tmp_path)
    first = _assess()
    second = _assess()
    assert first["status"] == "relationship_timeline_assessed"
    assert second["blockers"] == [
        {"key": "relationship_timeline_assessment_already_exists"}
    ]
