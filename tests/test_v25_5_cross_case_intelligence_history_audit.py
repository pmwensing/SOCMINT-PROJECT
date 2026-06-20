import datetime as dt
from src.socmint import cross_case_intelligence_history_audit_v25_5 as service


def _patch(monkeypatch):
    monkeypatch.setattr(
        service,
        "_persisted_events",
        lambda allowed: [
            {
                "history_event_id": "audit-1",
                "event_type": "analyst_decision",
                "occurred_at": "2026-06-16T06:00:00+00:00",
                "actor": "reviewer-one",
                "correlation_id": "correlation-1",
                "confirmed_link_id": None,
                "case_ids": ["case-alpha", "case-bravo"],
                "source_action": service.REVIEW_ACTION,
                "source_record_id": 1,
                "source_binding": {"record_id": 1},
                "source_binding_sha256": "a" * 64,
                "access_scope": {"mode": "restricted"},
                "details": {"decision": "accept"},
                "synthetic_checkpoint": False,
            },
            {
                "history_event_id": "audit-2",
                "event_type": "confirmed_link_registration",
                "occurred_at": "2026-06-16T07:00:00+00:00",
                "actor": "registry-manager",
                "correlation_id": "correlation-1",
                "confirmed_link_id": "link-1",
                "case_ids": ["case-alpha", "case-bravo"],
                "source_action": service.CONFIRMED_LINK_ACTION,
                "source_record_id": 2,
                "source_binding": {"record_id": 2},
                "source_binding_sha256": "b" * 64,
                "access_scope": {"mode": "restricted"},
                "details": {"confirmed_link_id": "link-1"},
                "synthetic_checkpoint": False,
            },
        ],
    )
    monkeypatch.setattr(
        service,
        "build_cross_case_intelligence_workspace",
        lambda **kwargs: {
            "schema": "socmint.cross_case_intelligence_workspace.v25_0",
            "version": "v25.0.0",
            "status": "ready",
            "minimum_case_count": 2,
            "counts": {"visible_cases": 2, "entity_correlations": 1},
            "access_scope": {
                "mode": "restricted",
                "visible_case_ids": ["case-alpha", "case-bravo"],
            },
        },
    )
    monkeypatch.setattr(
        service,
        "build_confirmed_link_registry_workspace",
        lambda **kwargs: {
            "confirmed_link_count": 1,
            "confirmed_links": [{"confirmed_link_id": "link-1"}],
            "accepted_pending_count": 0,
            "review_disposition_counts": {"accept": 1},
            "review_histories": {"correlation-1": [{"decision": "accept"}]},
        },
    )
    monkeypatch.setattr(
        service,
        "build_cross_case_relationship_graph",
        lambda **kwargs: {
            "schema": "socmint.cross_case_relationship_graph.v25_3",
            "version": "v25.3.0",
            "status": "ready",
            "graph_sha256": "g" * 64,
            "counts": {"confirmed_links": 1, "nodes": 4, "edges": 3},
            "access_scope": {
                "mode": "restricted",
                "allowed_case_ids": ["case-alpha", "case-bravo"],
            },
        },
    )
    monkeypatch.setattr(
        service,
        "build_cross_case_link_impact_analysis",
        lambda link_id, **kwargs: {
            "schema": "socmint.cross_case_link_impact_analysis.v25_4",
            "version": "v25.4.0",
            "status": "ready",
            "impact_sha256": "i" * 64,
            "impact": {
                "confirmed_link_id": link_id,
                "affected_case_ids": ["case-alpha", "case-bravo"],
            },
            "access_scope": {
                "mode": "restricted",
                "allowed_case_ids": ["case-alpha", "case-bravo"],
            },
        },
    )


def test_v25_5_consolidates_history(monkeypatch):
    _patch(monkeypatch)
    result = service.build_cross_case_intelligence_history_audit(
        allowed_case_ids={"case-alpha", "case-bravo"},
        now=dt.datetime(2026, 6, 16, 8, 0, tzinfo=dt.UTC),
    )
    assert result["event_count"] == 5
    assert result["event_type_counts"] == {
        "analyst_decision": 1,
        "candidate_discovery": 1,
        "confirmed_link_registration": 1,
        "graph_projection": 1,
        "impact_analysis": 1,
    }
    assert result["actor_counts"] == {
        "registry-manager": 1,
        "reviewer-one": 1,
        "system": 3,
    }
    assert result["correlation_count"] == 1
    assert result["confirmed_link_count"] == 1
    assert result["case_count"] == 2
    assert result["source_bound_event_count"] == 5
    assert result["history"][0]["history_event_id"] == "audit-1"
    assert len(result["current_cross_case_intelligence_state_sha256"]) == 64
    assert result["source_records_mutated"] is False
    assert result["history_record_created"] is False


def test_v25_5_checkpoint_and_visibility_helpers():
    source = {"schema": "x", "version": "1", "status": "ready", "value": 3}
    first = service._checkpoint(
        "candidate_discovery", "2026-06-16T08:00:00+00:00", source
    )
    second = service._checkpoint(
        "candidate_discovery", "2026-06-16T08:00:00+00:00", source
    )
    assert first["history_event_id"] == second["history_event_id"]
    review = {"candidate_snapshot": {"case_ids": ["case-alpha", "case-bravo"]}}
    link = {"case_ids": ["case-alpha", "case-bravo"]}
    assert service._review_visible(review, {"case-alpha", "case-bravo"})
    assert not service._review_visible(review, {"case-alpha"})
    assert service._link_visible(link, {"case-alpha", "case-bravo"})
    assert not service._link_visible(link, {"case-alpha"})
