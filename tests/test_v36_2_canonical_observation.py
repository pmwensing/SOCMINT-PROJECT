from __future__ import annotations

from src.socmint import canonical_observation_v36_2 as canonical
from src.socmint import database


def _source():
    return {
        "source_id": "source-record-1",
        "case_id": "case-a",
        "source_event_sha256": "a" * 64,
        "capture_sha256": "b" * 64,
        "capture": {
            "capture_artifact_id": "evidence-artifact-1",
            "content_sha256": "c" * 64,
            "artifact_binding": {
                "collection_job_id": "collection-job-1",
            },
        },
    }


def _observation():
    return {
        "event_type": "observation_derived",
        "observation_id": "evidence-observation-1",
        "artifact_id": "evidence-artifact-1",
        "observation_sha256": "d" * 64,
        "artifact_event_sha256": "e" * 64,
        "artifact_binding": {
            "collection_job_id": "collection-job-1",
        },
        "observation": {
            "observation_type": "email",
            "normalized_value": "analyst@example.test",
            "confidence": "0.8",
            "derivation_method": "json_path",
        },
    }


def _register(monkeypatch, tmp_path, **overrides):
    database.configure_database(f"sqlite:///{tmp_path / 'canonical.db'}")
    source = overrides.pop("source", _source())
    observation = overrides.pop("observation", _observation())
    monkeypatch.setattr(canonical, "find_source", lambda source_id: source)
    monkeypatch.setattr(canonical, "observations", lambda: [observation])
    values = {
        "actor": "admin",
        "case_id": "case-a",
        "source_id": "source-record-1",
        "source_observation_id": "evidence-observation-1",
        "tool_run_id": "collection-job-1",
        "artifact_id": "evidence-artifact-1",
        "observation_type": "email_address",
        "raw_value": "Analyst@Example.Test",
        "normalized_value": "analyst@example.test",
        "observed_at": "2026-07-20T03:00:00+00:00",
        "valid_time_start": None,
        "valid_time_end": None,
        "extraction_method": "json_path:$.contact.email",
        "extraction_confidence": 0.92,
        "context": {"field": "contact.email", "language": "en"},
        "parent_observation_id": None,
        "adapter_format": "json",
        "adapter_name": "profile-json-adapter",
        "adapter_version": "1.0.0",
        "quarantine_reasons": [],
        "reason": "Normalize accepted observation.",
        "confirmed": True,
    }
    values.update(overrides)
    return canonical.register_canonical_observation(**values)


def test_v36_2_registers_accepted_envelope_without_assigning_identity(
    monkeypatch,
    tmp_path,
):
    result = _register(monkeypatch, tmp_path)
    assert result["status"] == "canonical_observation_registered"
    assert result["initial_state"] == "accepted"
    assert result["canonical_observation_id"].startswith(
        "canonical-observation-"
    )
    assert result["source_binding"]["source_id"] == "source-record-1"
    assert result["authoritative_observation_binding"][
        "source_observation_id"
    ] == "evidence-observation-1"
    assert result["canonical_observation"]["normalized_value"] == (
        "analyst@example.test"
    )
    assert result["truth_assigned"] is False
    assert result["identity_assigned"] is False
    assert result["source_observation_mutated"] is False
    assert result["claim_created"] is False
    assert canonical.find_canonical_observation(
        result["canonical_observation_id"]
    )["observation_state"] == "accepted"


def test_v36_2_quarantines_low_confidence_and_preserves_review_history(
    monkeypatch,
    tmp_path,
):
    registered = _register(
        monkeypatch,
        tmp_path,
        extraction_confidence=0.35,
        quarantine_reasons=["parser_schema_drift"],
    )
    assert registered["initial_state"] == "quarantined"
    assert registered["validation_findings"] == [
        "low_extraction_confidence",
        "parser_schema_drift",
    ]
    changed = canonical.change_canonical_observation_state(
        actor="reviewer",
        canonical_observation_id=registered["canonical_observation_id"],
        to_state="accepted",
        reason="Manually checked against the preserved capture.",
        confirmed=True,
    )
    assert changed["status"] == "canonical_observation_state_changed"
    current = canonical.find_canonical_observation(
        registered["canonical_observation_id"]
    )
    assert current["observation_state"] == "accepted"
    assert len(current["state_history"]) == 1
    assert current["source_observation_mutated"] is False


def test_v36_2_blocks_source_artifact_run_and_case_mismatches(
    monkeypatch,
    tmp_path,
):
    case_result = _register(
        monkeypatch,
        tmp_path,
        source={**_source(), "case_id": "case-other"},
    )
    assert case_result["blockers"] == [
        {"key": "observation_source_case_mismatch"}
    ]

    artifact_result = _register(
        monkeypatch,
        tmp_path,
        artifact_id="evidence-artifact-other",
    )
    assert artifact_result["blockers"] == [
        {"key": "observation_source_artifact_mismatch"}
    ]

    run_result = _register(
        monkeypatch,
        tmp_path,
        tool_run_id="collection-job-other",
    )
    assert run_result["blockers"] == [
        {"key": "observation_source_tool_run_mismatch"}
    ]


def test_v36_2_blocks_invalid_time_range_and_adapter(monkeypatch, tmp_path):
    time_result = _register(
        monkeypatch,
        tmp_path,
        valid_time_start="2026-07-20T04:00:00+00:00",
        valid_time_end="2026-07-20T03:00:00+00:00",
    )
    assert time_result["blockers"] == [{"key": "valid_time_range_invalid"}]

    adapter_result = _register(
        monkeypatch,
        tmp_path,
        adapter_format="html",
    )
    assert adapter_result["blockers"] == [{"key": "adapter_format_invalid"}]


def test_v36_2_parent_envelope_must_exist_in_same_case(monkeypatch, tmp_path):
    parent = _register(monkeypatch, tmp_path)
    child = _register(
        monkeypatch,
        tmp_path,
        normalized_value="second@example.test",
        raw_value="Second@Example.Test",
        parent_observation_id=parent["canonical_observation_id"],
    )
    assert child["status"] == "canonical_observation_registered"
    assert child["parent_binding_sha256"] == parent[
        "canonical_observation_event_sha256"
    ]


def test_v36_2_accepted_and_rejected_states_are_terminal(monkeypatch, tmp_path):
    accepted = _register(monkeypatch, tmp_path)
    blocked = canonical.change_canonical_observation_state(
        actor="reviewer",
        canonical_observation_id=accepted["canonical_observation_id"],
        to_state="rejected",
        reason="Attempt invalid transition.",
        confirmed=True,
    )
    assert blocked["blockers"] == [
        {"key": "canonical_observation_state_transition_invalid"}
    ]
