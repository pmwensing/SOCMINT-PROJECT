from src.socmint.correlation_scope_enforcement_v13_35 import (
    derive_correlation_scope_id,
    deterministic_same_target,
    promotion_scope_decision,
    should_promote,
    should_quarantine,
)


def test_v13_35b_scope_ids_are_deterministic_and_seed_isolated():
    left = derive_correlation_scope_id(
        subject_id=4,
        seed_id=1,
        connector_run_id=10,
        target_type="username",
        target_value="ExampleUser",
    )
    repeat = derive_correlation_scope_id(
        subject_id=4,
        seed_id=1,
        connector_run_id=10,
        target_type="username",
        target_value="exampleuser",
    )
    other_seed = derive_correlation_scope_id(
        subject_id=4,
        seed_id=2,
        connector_run_id=10,
        target_type="username",
        target_value="exampleuser",
    )

    assert left == repeat
    assert left != other_seed
    assert left.startswith("cs_")


def test_v13_35b_same_scope_allows_promotion():
    decision = promotion_scope_decision(
        finding_scope_id="cs_same",
        parent_scope_id="cs_same",
        finding_type="profile_url",
        finding_value="https://example.test/a",
        parent_type="profile_url",
        parent_value="https://example.test/a",
    )
    assert should_promote(decision) is True
    assert decision["reason"] == "same_correlation_scope"


def test_v13_35b_ambiguous_cross_scope_profile_quarantines():
    decision = promotion_scope_decision(
        finding_scope_id="cs_found",
        parent_scope_id="cs_parent",
        finding_type="profile_url",
        finding_value="https://social.example/alex-smith",
        parent_type="name",
        parent_value="Alex Smith",
    )
    assert should_quarantine(decision) is True
    assert decision["reason"] == "ambiguous_cross_scope_profile"


def test_v13_35b_deterministic_same_target_allows_cross_scope():
    decision = promotion_scope_decision(
        finding_scope_id="cs_run_1",
        parent_scope_id="cs_run_2",
        finding_type="email",
        finding_value="ALEX@example.test",
        parent_type="email",
        parent_value="alex@example.test",
    )
    assert should_promote(decision) is True
    assert decision["reason"] == "deterministic_same_target"


def test_v13_35b_similar_people_do_not_false_merge():
    first = promotion_scope_decision(
        finding_scope_id="cs_alex_1",
        parent_scope_id="cs_alex_2",
        finding_type="profile_url",
        finding_value="https://social.example/alex-smith-kingston",
        parent_type="name",
        parent_value="Alex Smith",
    )
    second = promotion_scope_decision(
        finding_scope_id="cs_alex_3",
        parent_scope_id="cs_alex_4",
        finding_type="profile_url",
        finding_value="https://social.example/alex-smyth-kingston",
        parent_type="name",
        parent_value="Alex Smyth",
    )
    assert first["state"] == "quarantine"
    assert second["state"] == "quarantine"


def test_v13_35b_deterministic_same_target_requires_same_type():
    result = deterministic_same_target(
        left_type="username",
        left_value="alexsmith",
        right_type="name",
        right_value="Alex Smith",
    )
    assert result["same_target"] is False
