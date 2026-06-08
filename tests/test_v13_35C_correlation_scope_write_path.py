from src.socmint.correlation_scope_write_path_v13_35 import (
    SCOPE_ID,
    assign_seed_scope,
    backfill_record_scope,
    backfill_records,
    inherit_scope,
    record_scope_fields,
    scoped_promotion_decision,
    write_path_status,
)


def test_v13_35c_seed_creation_assigns_scope():
    result = assign_seed_scope(
        subject_id="subject-1",
        seed_id="seed-1",
        seed_type="username",
        seed_value="alexsmith",
    )

    assert result.correlation_scope_id.startswith("cs_")
    assert result.correlation_scope_state == "root_seed"
    assert result.correlation_scope_reason == "assigned_at_seed_creation"


def test_v13_35c_connector_child_inherits_parent_scope():
    parent = assign_seed_scope(
        subject_id="subject-1",
        seed_id="seed-1",
        seed_type="username",
        seed_value="alexsmith",
    )
    child = inherit_scope(
        parent_scope_id=parent.correlation_scope_id,
        subject_id="subject-1",
        seed_id="seed-1",
        connector_run_id="run-1",
        target_type="profile_url",
        target_value="https://social.example/alex",
    )

    assert child.correlation_scope_id == parent.correlation_scope_id
    assert child.correlation_scope_reason == "inherited_from_parent_scope"


def test_v13_35c_record_scope_fields_are_added_without_mutating_original():
    record = {"finding_type": "email", "value": "alex@example.test"}
    result = assign_seed_scope(
        subject_id="subject-1",
        seed_id="seed-1",
        seed_type="email",
        seed_value="alex@example.test",
    )

    updated = record_scope_fields(record, result)

    assert SCOPE_ID not in record
    assert updated[SCOPE_ID] == result.correlation_scope_id
    assert updated["correlation_scope_state"] == "root_seed"


def test_v13_35c_backfill_is_idempotent_and_preserves_scope():
    record = {
        "subject_id": "subject-1",
        "seed_id": "seed-1",
        "connector_run_id": "run-1",
        "finding_type": "username",
        "value": "alexsmith",
    }

    first = backfill_record_scope(record)
    second = backfill_record_scope(first)

    assert first[SCOPE_ID] == second[SCOPE_ID]
    assert second["correlation_scope_reason"] in {
        "derived_legacy_scope_per_subject_seed_run_target",
        "existing_scope_preserved",
    }


def test_v13_35c_two_initial_searches_stay_separate():
    first = backfill_record_scope(
        {
            "subject_id": "subject-1",
            "seed_id": "seed-1",
            "connector_run_id": "run-1",
            "finding_type": "username",
            "value": "alexsmith",
        }
    )
    second = backfill_record_scope(
        {
            "subject_id": "subject-1",
            "seed_id": "seed-2",
            "connector_run_id": "run-2",
            "finding_type": "username",
            "value": "alexsmith",
        }
    )

    assert first[SCOPE_ID] != second[SCOPE_ID]


def test_v13_35c_cross_scope_ambiguous_profile_quarantines():
    parent = backfill_record_scope(
        {
            "subject_id": "subject-1",
            "seed_id": "seed-1",
            "connector_run_id": "run-1",
            "target_type": "name",
            "target_value": "Alex Smith",
        }
    )
    finding = backfill_record_scope(
        {
            "subject_id": "subject-1",
            "seed_id": "seed-2",
            "connector_run_id": "run-2",
            "finding_type": "profile_url",
            "value": "https://social.example/alex-smith",
        }
    )

    decision = scoped_promotion_decision(finding_record=finding, parent_record=parent)

    assert decision["state"] == "quarantine"
    assert decision["reason"] == "ambiguous_cross_scope_profile"


def test_v13_35c_analyst_merge_is_explicit():
    parent = {SCOPE_ID: "cs_parent", "target_type": "name", "target_value": "Alex Smith"}
    finding = {SCOPE_ID: "cs_finding", "finding_type": "profile_url", "value": "https://social.example/alex-smith"}

    without_merge = scoped_promotion_decision(finding_record=finding, parent_record=parent)
    with_merge = scoped_promotion_decision(
        finding_record=finding,
        parent_record=parent,
        analyst_merged_scope=True,
    )

    assert without_merge["state"] == "quarantine"
    assert with_merge["state"] == "allow"
    assert with_merge["reason"] == "analyst_merged_scope"


def test_v13_35c_backfill_records_batch():
    records = [
        {"subject_id": "s1", "seed_id": "a", "connector_run_id": "r1", "finding_type": "email", "value": "a@example.test"},
        {"subject_id": "s1", "seed_id": "b", "connector_run_id": "r2", "finding_type": "email", "value": "a@example.test"},
    ]

    filled = backfill_records(records)

    assert len(filled) == 2
    assert filled[0][SCOPE_ID] != filled[1][SCOPE_ID]


def test_v13_35c_status_declares_non_goals():
    status = write_path_status()

    assert status["schema"] == "socmint.correlation_scope_write_path.v13_35C"
    assert "no_new_connectors" in status["non_goals"]
    assert "no_final_v13_35_tag" in status["non_goals"]
