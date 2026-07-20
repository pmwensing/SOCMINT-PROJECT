from __future__ import annotations

from src.socmint import database
from src.socmint import entity_candidate_resolution_v36_3 as resolution


def _observation(observation_id: str, case_id: str = "case-a"):
    return {
        "canonical_observation_id": observation_id,
        "case_id": case_id,
        "observation_state": "accepted",
        "canonical_observation_event_sha256": observation_id.ljust(64, "a")[:64],
        "canonical_observation": {"observation_type": "identifier"},
    }


def _assess(monkeypatch, tmp_path, signals, **overrides):
    database.configure_database(f"sqlite:///{tmp_path / 'resolution.db'}")
    observations = {
        "obs-1": _observation("obs-1"),
        "obs-2": _observation("obs-2"),
        "obs-3": _observation("obs-3"),
        "obs-other": _observation("obs-other", "case-other"),
    }
    monkeypatch.setattr(
        resolution,
        "find_canonical_observation",
        lambda observation_id: observations.get(observation_id),
    )
    values = {
        "actor": "admin",
        "case_id": "case-a",
        "entity_a_id": "entity-a",
        "entity_b_id": "entity-b",
        "signals": signals,
        "limitations": [],
        "reason": "Assess candidate identity without merging it.",
        "confirmed": True,
    }
    values.update(overrides)
    return resolution.assess_entity_candidate(**values)


def _signal(signal_type: str, *observation_ids: str):
    return {
        "signal_type": signal_type,
        "observation_ids": list(observation_ids),
        "reason": f"Evidence for {signal_type}.",
    }


def test_v36_3_two_strong_signals_can_recommend_likely_same(monkeypatch, tmp_path):
    result = _assess(
        monkeypatch,
        tmp_path,
        [
            _signal("exact_unique_identifier", "obs-1"),
            _signal("reciprocal_verified_link", "obs-2"),
            _signal("stable_username_reuse", "obs-3"),
        ],
    )
    assert result["status"] == "entity_candidate_assessed"
    assert result["scoring"]["score"] == 58
    assert result["scoring"]["recommendation"] == "possible_same_entity"

    stronger = _assess(
        monkeypatch,
        tmp_path,
        [
            _signal("exact_unique_identifier", "obs-1"),
            _signal("reciprocal_verified_link", "obs-2"),
            _signal("cryptographic_control", "obs-3"),
        ],
        entity_b_id="entity-c",
    )
    assert stronger["scoring"]["score"] == 75
    assert stronger["scoring"]["recommendation"] == "likely_same_entity"
    assert stronger["scoring"]["automatic_merge_allowed"] is False
    assert stronger["identity_merged"] is False
    assert stronger["graph_mutated"] is False


def test_v36_3_weak_only_evidence_is_capped(monkeypatch, tmp_path):
    result = _assess(
        monkeypatch,
        tmp_path,
        [
            _signal("common_name", "obs-1"),
            _signal("avatar_similarity", "obs-2"),
            _signal("tool_probability", "obs-3"),
        ],
    )
    assert result["scoring"]["score"] == 6
    assert result["scoring"]["recommendation"] == "insufficient_evidence"
    assert "weak_only_cap_20" in result["scoring"]["caps"]


def test_v36_3_negative_signal_prevents_merge_recommendation(monkeypatch, tmp_path):
    result = _assess(
        monkeypatch,
        tmp_path,
        [
            _signal("exact_unique_identifier", "obs-1"),
            _signal("reciprocal_verified_link", "obs-2"),
            _signal("distinct_verified_control", "obs-3"),
        ],
    )
    assert result["scoring"]["score"] == 25
    assert result["scoring"]["recommendation"] == "keep_separate"
    assert "negative_signal_cap_69" in result["scoring"]["caps"]


def test_v36_3_requires_accepted_same_case_observations(monkeypatch, tmp_path):
    mismatch = _assess(
        monkeypatch,
        tmp_path,
        [_signal("exact_unique_identifier", "obs-other")],
    )
    assert mismatch["blockers"] == [
        {"key": "entity_resolution_observation_case_mismatch"}
    ]

    monkeypatch.setattr(
        resolution,
        "find_canonical_observation",
        lambda observation_id: {
            **_observation(observation_id),
            "observation_state": "quarantined",
        },
    )
    rejected = resolution.assess_entity_candidate(
        actor="admin",
        case_id="case-a",
        entity_a_id="entity-a",
        entity_b_id="entity-b",
        signals=[_signal("exact_unique_identifier", "obs-1")],
        limitations=[],
        reason="Assess.",
        confirmed=True,
    )
    assert rejected["blockers"] == [
        {"key": "accepted_canonical_observation_required"}
    ]


def test_v36_3_human_decision_does_not_mutate_graph(monkeypatch, tmp_path):
    candidate = _assess(
        monkeypatch,
        tmp_path,
        [
            _signal("exact_unique_identifier", "obs-1"),
            _signal("reciprocal_verified_link", "obs-2"),
            _signal("cryptographic_control", "obs-3"),
        ],
    )
    decision = resolution.record_entity_candidate_decision(
        actor="reviewer",
        candidate_id=candidate["candidate_id"],
        decision="recommend_merge",
        rationale="Three independently bound strong signals support review.",
        confirmed=True,
    )
    assert decision["status"] == "entity_candidate_decision_recorded"
    assert decision["identity_merged"] is False
    assert decision["graph_mutated"] is False
    current = resolution.find_candidate(candidate["candidate_id"])
    assert current is not None
    assert current["decision_recorded"] is True
    assert current["current_decision"]["decision"] == "recommend_merge"


def test_v36_3_blocks_merge_decision_for_non_likely_candidate(monkeypatch, tmp_path):
    candidate = _assess(
        monkeypatch,
        tmp_path,
        [_signal("stable_username_reuse", "obs-1")],
    )
    decision = resolution.record_entity_candidate_decision(
        actor="reviewer",
        candidate_id=candidate["candidate_id"],
        decision="recommend_merge",
        rationale="Attempted overreach.",
        confirmed=True,
    )
    assert decision["blockers"] == [
        {"key": "merge_recommendation_requires_likely_same_entity"}
    ]
