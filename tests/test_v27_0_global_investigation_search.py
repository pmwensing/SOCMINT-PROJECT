from src.socmint.global_investigation_search_v27_0 import (
    build_global_investigation_search,
)


def _records():
    return [
        {
            "record_id": 1,
            "case_id": "case-a",
            "action": "case_entity_observed",
            "actor": "alice",
            "occurred_at": "2026-06-17T01:00:00+00:00",
            "details": {
                "entity_id": "entity-42",
                "name": "Example Person",
                "status": "active",
            },
        },
        {
            "record_id": 2,
            "case_id": "case-b",
            "action": "case_evidence_promoted",
            "actor": "bob",
            "occurred_at": "2026-06-17T02:00:00+00:00",
            "details": {
                "title": "Email evidence",
                "description": "example@example.test",
            },
        },
        {
            "record_id": 3,
            "case_id": "case-hidden",
            "action": "case_finding_recorded",
            "actor": "eve",
            "occurred_at": "2026-06-17T03:00:00+00:00",
            "details": {"finding": "Hidden finding"},
        },
    ]


def test_v27_0_search_normalizes_ranks_and_filters_scope():
    result = build_global_investigation_search(
        "example", allowed_case_ids={"case-a", "case-b"}, records=_records()
    )
    assert result["status"] == "ready"
    assert result["result_count"] == 2
    assert result["visible_case_ids"] == ["case-a", "case-b"]
    assert all(item["source_binding_sha256"] for item in result["results"])
    assert all(item["case_id"] != "case-hidden" for item in result["results"])
    assert result["results"][0]["score"] >= result["results"][1]["score"]
    assert result["read_only"] is True
    assert result["source_records_mutated"] is False
    assert result["search_record_created"] is False
    assert result["case_access_scope_changed"] is False


def test_v27_0_type_filter_and_exact_case_match():
    result = build_global_investigation_search(
        "case-a",
        result_types=["entity"],
        allowed_case_ids={"case-a", "case-b"},
        records=_records(),
    )
    assert result["result_count"] == 1
    assert result["results"][0]["case_id"] == "case-a"
    assert result["results"][0]["result_type"] == "entity"
    assert result["results"][0]["score"] >= 100
