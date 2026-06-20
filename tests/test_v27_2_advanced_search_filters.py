from src.socmint.advanced_search_filters_v27_2 import build_advanced_search_filters


def _payload():
    return {
        "access_scope": {
            "mode": "restricted",
            "allowed_case_ids": ["case-a", "case-b"],
        },
        "results": [
            {
                "result_id": "r1",
                "record_type": "case",
                "case_id": "case-a",
                "score": 10.0,
                "actor": "alice",
                "status": "active",
                "source_action": "portfolio_case",
                "occurred_at": "2026-06-10T10:00:00+00:00",
                "matched_terms": ["alpha"],
                "preview": {
                    "fields": [
                        {"field": "stage", "value": "review", "matched": False},
                        {"field": "priority", "value": "high", "matched": False},
                    ]
                },
                "links": {"primary": "/case-a", "case": "/case-a"},
            },
            {
                "result_id": "r2",
                "record_type": "finding",
                "case_id": "case-b",
                "score": 30.0,
                "actor": "bob",
                "status": "open",
                "source_action": "case_finding_recorded",
                "occurred_at": "2026-06-15T12:00:00+00:00",
                "matched_terms": ["reuse"],
                "preview": {
                    "fields": [
                        {"field": "confidence", "value": "high", "matched": False},
                        {"field": "priority", "value": "urgent", "matched": False},
                        {
                            "field": "finding",
                            "value": "Repeated account reuse",
                            "matched": True,
                        },
                    ]
                },
                "links": {"primary": "/case-b", "case": "/case-b"},
            },
            {
                "result_id": "r3",
                "record_type": "evidence",
                "case_id": "case-b",
                "score": 20.0,
                "actor": "bob",
                "status": "verified",
                "source_action": "case_evidence_promoted",
                "occurred_at": "2026-06-12T09:00:00+00:00",
                "matched_terms": ["email"],
                "preview": {
                    "fields": [
                        {"field": "confidence", "value": "medium", "matched": False},
                        {
                            "field": "description",
                            "value": "Email message",
                            "matched": True,
                        },
                    ]
                },
                "links": {"primary": "/case-b", "case": "/case-b"},
            },
        ],
    }


def test_v27_2_advanced_filters_facets_dates_terms_and_hashes():
    result = build_advanced_search_filters(
        "",
        stages=["review"],
        priorities=["high"],
        date_from="2026-06-01",
        date_to="2026-06-11",
        include_terms=["alpha"],
        sort="newest",
        base_payload=_payload(),
    )
    assert result["status"] == "ready"
    assert result["candidate_count"] == 3
    assert result["result_count"] == 1
    assert result["results"][0]["result_id"] == "r1"
    assert result["facets"]["record_type"] == {"case": 1, "evidence": 1, "finding": 1}
    assert result["filtered_facets"]["priority"] == {"high": 1}
    assert result["excluded_counts"]["stage"] == 2
    assert len(result["filter_sha256"]) == 64
    assert len(result["result_set_sha256"]) == 64
    assert result["read_only"] is True
    assert result["source_records_mutated"] is False
    assert result["filter_record_created"] is False


def test_v27_2_exact_exclusion_and_sort_modes():
    result = build_advanced_search_filters(
        "",
        confidences=["high"],
        exclude_terms=["email"],
        exact_fields={"case_id": "case-b"},
        sort="oldest",
        base_payload=_payload(),
    )
    assert result["result_count"] == 1
    assert result["results"][0]["result_id"] == "r2"
    assert result["active_filters"]["exact_fields"] == {"case_id": "case-b"}
    assert result["relevance_is_not_confidence"] is True
