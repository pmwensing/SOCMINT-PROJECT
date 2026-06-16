import datetime as dt

from src.socmint import cross_case_intelligence_metrics_v25_6 as service


def _candidate_workspace():
    return {
        "counts": {"visible_cases": 4, "source_records": 12, "repeated_patterns": 2},
        "correlations": {
            "entities": [{"correlation_id": "c1", "case_ids": ["a", "b"], "occurrence_count": 4}],
            "identifiers": [{"correlation_id": "c2", "case_ids": ["b", "c"], "occurrence_count": 2}],
            "infrastructure": [{"correlation_id": "c3", "case_ids": ["a", "d"], "occurrence_count": 2}],
            "evidence": [],
            "timelines": [],
        },
    }


def _registry_workspace():
    return {
        "review_histories": {
            "c1": [
                {"decision": "defer", "reviewer": "alice", "recorded_at": "2026-06-14T10:00:00+00:00"},
                {"decision": "accept", "reviewer": "alice", "recorded_at": "2026-06-15T10:00:00+00:00"},
            ],
            "c2": [{"decision": "reject", "reviewer": "bob", "recorded_at": "2026-06-15T11:00:00+00:00"}],
        },
        "confirmed_links": [
            {"confirmed_link_id": "l1", "case_ids": ["a", "b"], "source_occurrence_count": 4}
        ],
    }


def _graph():
    return {
        "graph_sha256": "g" * 64,
        "graph": {
            "nodes": [{"node_id": f"n{i}"} for i in range(4)],
            "edges": [
                {"source": "n0", "target": "n1"},
                {"source": "n1", "target": "n2"},
                {"source": "n2", "target": "n3"},
            ],
        },
    }


def test_v25_6_calculates_metrics_and_confidence(monkeypatch):
    monkeypatch.setattr(service, "build_cross_case_link_impact_analysis", lambda link_id, **kwargs: {
        "status": "ready",
        "impact_sha256": "i" * 64,
        "counts": {
            "affected_cases": 2,
            "affected_entities": 1,
            "evidence_packages": 1,
            "review_queue_entries": 1,
            "closure_states": 2,
            "archive_records": 1,
        },
    })
    result = service.build_cross_case_intelligence_metrics(
        candidate_workspace=_candidate_workspace(),
        registry_workspace=_registry_workspace(),
        graph_payload=_graph(),
        allowed_case_ids={"a", "b", "c", "d"},
        now=dt.datetime(2026, 6, 16, 9, 0, tzinfo=dt.UTC),
    )
    metrics = result["metrics"]
    assert metrics["candidate_volume"]["total"] == 3
    assert metrics["review_dispositions"]["total_reviews"] == 3
    assert metrics["review_dispositions"]["all_decisions"] == {"accept": 1, "defer": 1, "reject": 1}
    assert metrics["review_dispositions"]["review_coverage_percent"] == 66.67
    assert metrics["confirmation_conversion"]["candidate_to_confirmed_percent"] == 33.33
    assert metrics["confirmation_conversion"]["accepted_to_registered_percent"] == 100.0
    assert metrics["graph_density"]["nodes"] == 4
    assert metrics["graph_density"]["edges"] == 3
    assert metrics["graph_density"]["density_percent"] == 50.0
    assert metrics["cross_case_reach"]["confirmed_case_reach_percent"] == 50.0
    assert metrics["source_occurrence_coverage"]["coverage_percent"] == 50.0
    assert metrics["impact_breadth"]["average_breadth_score"] == 8.0
    assert metrics["analyst_throughput"]["analyst_count"] == 2
    assert metrics["analyst_throughput"]["analysts"][0]["analyst"] == "alice"
    assert metrics["confidence_indicators"]["interpretation"] == "operational_indicator_not_probability_or_factual_certainty"
    assert len(result["metrics_sha256"]) == 64
    assert result["confidence_is_not_probability"] is True
    assert result["source_records_mutated"] is False
    assert result["metrics_record_created"] is False


def test_v25_6_handles_empty_workspace_without_division_errors(monkeypatch):
    result = service.build_cross_case_intelligence_metrics(
        candidate_workspace={"counts": {}, "correlations": {}},
        registry_workspace={"review_histories": {}, "confirmed_links": []},
        graph_payload={"graph": {"nodes": [], "edges": []}},
        now=dt.datetime(2026, 6, 16, tzinfo=dt.UTC),
    )
    metrics = result["metrics"]
    assert metrics["candidate_volume"]["total"] == 0
    assert metrics["confirmation_conversion"]["candidate_to_confirmed_percent"] == 0.0
    assert metrics["graph_density"]["density_percent"] == 0.0
    assert metrics["confidence_indicators"]["score"] == 0.0
    assert metrics["confidence_indicators"]["band"] == "limited"


def test_v25_6_metrics_hash_is_deterministic(monkeypatch):
    monkeypatch.setattr(service, "build_cross_case_link_impact_analysis", lambda *args, **kwargs: {"status": "blocked"})
    kwargs = {
        "candidate_workspace": _candidate_workspace(),
        "registry_workspace": _registry_workspace(),
        "graph_payload": _graph(),
        "now": dt.datetime(2026, 6, 16, tzinfo=dt.UTC),
    }
    first = service.build_cross_case_intelligence_metrics(**kwargs)
    second = service.build_cross_case_intelligence_metrics(**kwargs)
    assert first["metrics_sha256"] == second["metrics_sha256"]
