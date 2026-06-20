from src.socmint.core_record_search_v27_1 import build_core_record_search


def _records():
    return [
        {
            "record_id": 1,
            "case_id": "case-a",
            "action": "portfolio_case",
            "actor": "alice",
            "occurred_at": "2026-06-17T01:00:00+00:00",
            "details": {
                "title": "Alpha Investigation",
                "stage": "active",
                "status": "operational",
            },
        },
        {
            "record_id": 2,
            "case_id": "case-a",
            "action": "case_entity_observed",
            "actor": "alice",
            "occurred_at": "2026-06-17T02:00:00+00:00",
            "details": {
                "entity_id": "entity-42",
                "entity_type": "person",
                "name": "Example Person",
                "aliases": ["E. Person"],
            },
        },
        {
            "record_id": 3,
            "case_id": "case-b",
            "action": "case_evidence_promoted",
            "actor": "bob",
            "occurred_at": "2026-06-17T03:00:00+00:00",
            "details": {
                "evidence_id": "ev-7",
                "title": "Email Evidence",
                "description": "Message from example@example.test",
                "status": "verified",
            },
        },
        {
            "record_id": 4,
            "case_id": "case-b",
            "action": "case_finding_recorded",
            "actor": "bob",
            "occurred_at": "2026-06-17T04:00:00+00:00",
            "details": {
                "finding_id": "finding-9",
                "finding": "Repeated account reuse",
                "category": "identity",
                "status": "open",
                "confidence": "high",
            },
        },
        {
            "record_id": 5,
            "case_id": "case-hidden",
            "action": "case_entity_observed",
            "actor": "eve",
            "occurred_at": "2026-06-17T05:00:00+00:00",
            "details": {"entity_id": "hidden-1", "name": "Hidden Person"},
        },
    ]


def test_v27_1_field_matching_facets_previews_and_scope():
    result = build_core_record_search(
        "example", allowed_case_ids={"case-a", "case-b"}, records=_records()
    )
    assert result["status"] == "ready"
    assert result["result_count"] == 2
    assert result["visible_case_ids"] == ["case-a", "case-b"]
    assert result["facets"]["record_type"]["entity"] == 1
    assert result["facets"]["record_type"]["evidence"] == 1
    assert all(item["field_matches"] for item in result["results"])
    assert all(
        item["preview"]["matched_field_count"] >= 1 for item in result["results"]
    )
    assert all(item["source_binding_sha256"] for item in result["results"])
    assert all(item["case_id"] != "case-hidden" for item in result["results"])
    assert result["relevance_is_not_confidence"] is True
    assert result["source_records_mutated"] is False
    assert result["search_record_created"] is False


def test_v27_1_exact_field_and_facet_filters():
    result = build_core_record_search(
        "entity-42",
        record_types=["entity"],
        case_ids=["case-a"],
        actors=["alice"],
        statuses=["unspecified"],
        allowed_case_ids={"case-a", "case-b"},
        records=_records(),
    )
    assert result["result_count"] == 1
    item = result["results"][0]
    assert item["record_type"] == "entity"
    assert item["score"] >= 180
    assert item["field_matches"][0]["field"] == "entity_id"
    assert item["field_matches"][0]["exact"] is True
    assert result["applied_filters"]["record_types"] == ["entity"]
