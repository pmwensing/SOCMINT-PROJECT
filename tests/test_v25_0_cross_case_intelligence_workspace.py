from src.socmint.cross_case_intelligence_workspace_v25_0 import (
    build_cross_case_intelligence_workspace,
)


def _records():
    return [
        {
            "case_id": "case-alpha",
            "record_id": 1,
            "action": "case_entity_observed",
            "actor": "analyst-a",
            "occurred_at": "2026-06-16T02:00:00+00:00",
            "details": {
                "entity_id": "entity-42",
                "username": "SharedHandle",
                "domain": "https://Example.COM/path",
                "evidence_id": "ev-900",
                "observed_at": "2026-06-01T12:00:00Z",
                "blockers": [{"key": "manual_identity_review_required"}],
            },
        },
        {
            "case_id": "case-bravo",
            "record_id": 2,
            "action": "case_entity_observed",
            "actor": "analyst-b",
            "occurred_at": "2026-06-16T03:00:00+00:00",
            "details": {
                "entity_id": "ENTITY-42",
                "handle": "sharedhandle",
                "hostname": "example.com",
                "artifact_id": "ev-900",
                "observed_at": "2026-06-01T12:00:00Z",
                "blockers": [{"key": "manual_identity_review_required"}],
            },
        },
        {
            "case_id": "case-charlie",
            "record_id": 3,
            "action": "case_entity_observed",
            "actor": "analyst-c",
            "occurred_at": "2026-06-16T04:00:00+00:00",
            "details": {"username": "different"},
        },
    ]


def test_v25_0_correlates_shared_values_with_case_provenance():
    result = build_cross_case_intelligence_workspace(records=_records())

    assert result["status"] == "ready"
    assert result["access_scope"]["mode"] == "all_visible_cases"
    assert result["counts"]["visible_cases"] == 3
    assert result["counts"]["entity_correlations"] == 1
    assert result["counts"]["identifier_correlations"] == 1
    assert result["counts"]["infrastructure_correlations"] == 1
    assert result["counts"]["evidence_correlations"] == 1
    assert result["counts"]["timeline_correlations"] == 1

    entity = result["correlations"]["entities"][0]
    assert entity["case_ids"] == ["case-alpha", "case-bravo"]
    assert entity["case_count"] == 2
    assert entity["confirmed_match"] is False
    assert entity["human_review_required"] is True
    assert {item["record_id"] for item in entity["occurrences"]} == {1, 2}
    assert all(len(item["provenance_sha256"]) == 64 for item in entity["occurrences"])

    infrastructure = result["correlations"]["infrastructure"][0]
    assert infrastructure["match_value"] == "example.com"
    assert any(item["pattern"] == "case_entity_observed" for item in result["repeated_patterns"])
    assert any(item["pattern"] == "manual_identity_review_required" for item in result["repeated_patterns"])
    assert result["human_review_required"] is True
    assert result["correlations_are_candidates"] is True
    assert result["source_records_mutated"] is False
    assert result["correlation_record_created"] is False


def test_v25_0_enforces_case_access_scope_before_correlation():
    result = build_cross_case_intelligence_workspace(
        records=_records(),
        allowed_case_ids={"case-alpha", "case-charlie"},
    )

    assert result["access_scope"]["mode"] == "restricted"
    assert result["access_scope"]["allowed_case_ids"] == ["case-alpha", "case-charlie"]
    assert result["access_scope"]["visible_case_ids"] == ["case-alpha", "case-charlie"]
    assert result["counts"]["visible_cases"] == 2
    assert result["counts"]["entity_correlations"] == 0
    assert result["counts"]["identifier_correlations"] == 0
    assert "case-bravo" not in result["case_provenance"]


def test_v25_0_minimum_case_threshold_is_at_least_two():
    result = build_cross_case_intelligence_workspace(
        records=_records(), minimum_case_count=1
    )
    assert result["minimum_case_count"] == 2
