from src.socmint import cross_case_link_impact_analysis_v25_4 as service


def _link():
    return {
        "confirmed_link_id": "confirmed-link-1",
        "confirmed_link_sha256": "f" * 64,
        "registry_record_id": 31,
        "accepted_review_decision_id": "review-1",
        "accepted_review_decision_sha256": "d" * 64,
        "source_occurrences_sha256": "o" * 64,
        "case_ids": ["case-alpha", "case-bravo"],
    }


def _graph():
    return {
        "graph_sha256": "g" * 64,
        "graph": {
            "nodes": [
                {"node_id": "case-a", "node_type": "case", "label": "case-alpha", "confirmed_link_ids": ["confirmed-link-1"], "source_occurrences": []},
                {"node_id": "entity-1", "node_type": "entity", "label": "entity-42", "confirmed_link_ids": ["confirmed-link-1"], "source_occurrences": [{"case_id": "case-alpha"}]},
                {"node_id": "evidence-1", "node_type": "evidence", "label": "evidence-9", "confirmed_link_ids": ["confirmed-link-1"], "source_occurrences": [{"case_id": "case-bravo"}]},
                {"node_id": "hidden", "node_type": "entity", "label": "other", "confirmed_link_ids": ["confirmed-link-2"], "source_occurrences": []},
            ],
            "edges": [
                {"edge_id": "edge-1", "confirmed_link_id": "confirmed-link-1"},
                {"edge_id": "edge-2", "confirmed_link_id": "confirmed-link-2"},
            ],
        },
    }


def test_v25_4_calculates_all_affected_operational_surfaces(monkeypatch):
    monkeypatch.setattr(service, "build_case_closure_history", lambda case_id: {
        "current_closure_state": "closed" if case_id == "case-alpha" else "reopened",
        "current_archive_state": "generated",
        "retention_disposition": "retain_until_expiration",
        "reopen_status": "none" if case_id == "case-alpha" else "authorized",
        "unresolved_actions": [],
        "event_count": 5,
        "latest_events": {
            "archive_generation": {
                "timeline_id": 100 if case_id == "case-alpha" else 101,
                "actor": "archivist",
                "occurred_at": "2026-06-16T06:00:00+00:00",
                "details": {"archive_package_id": f"archive-{case_id}"},
            }
        },
    })
    monkeypatch.setattr(service, "_package_records", lambda case_ids: [
        {"case_id": "case-alpha", "record_id": 80, "action": "dossier_final_export_package", "actor": "reviewer", "occurred_at": "2026-06-16T05:00:00+00:00", "details": {"package_id": "pkg-a"}},
        {"case_id": "case-bravo", "record_id": 81, "action": "dossier_delivery_receipt", "actor": "delivery", "occurred_at": "2026-06-16T05:30:00+00:00", "details": {"receipt_id": "receipt-b"}},
    ])
    workload = {
        "entries": [
            {"case_id": "case-alpha", "review_state": "unreviewed", "assigned_reviewer": "alice", "assignment_age_hours": 12.0},
            {"case_id": "case-other", "review_state": "reviewed", "assigned_reviewer": "bob", "assignment_age_hours": 2.0},
        ]
    }

    result = service.build_cross_case_link_impact_analysis(
        "confirmed-link-1",
        links=[_link()],
        graph=_graph(),
        workload=workload,
        allowed_case_ids={"case-alpha", "case-bravo"},
    )

    assert result["status"] == "ready"
    assert result["counts"] == {
        "affected_cases": 2,
        "affected_entities": 2,
        "entities_by_type": {"entity": 1, "evidence": 1},
        "evidence_packages": 2,
        "review_queue_entries": 1,
        "closure_states": 2,
        "archive_records": 2,
        "graph_nodes": 3,
        "graph_edges": 1,
    }
    assert result["impact"]["affected_case_ids"] == ["case-alpha", "case-bravo"]
    assert {node["node_id"] for node in result["impact"]["affected_entities"]} == {"entity-1", "evidence-1"}
    assert result["impact"]["review_queues"][0]["assigned_reviewer"] == "alice"
    assert result["impact"]["review_queues"][0]["supervisor_queue"].endswith("assigned_reviewer=alice")
    assert {item["current_closure_state"] for item in result["impact"]["closure_states"]} == {"closed", "reopened"}
    assert result["confirmed_link_binding"]["registry_record_id"] == 31
    assert result["graph_binding"]["graph_sha256"] == "g" * 64
    assert len(result["impact_sha256"]) == 64
    assert result["confirmed_link_mutated"] is False
    assert result["graph_mutated"] is False
    assert result["source_records_mutated"] is False
    assert result["impact_record_created"] is False


def test_v25_4_blocks_missing_or_inaccessible_confirmed_link():
    missing = service.build_cross_case_link_impact_analysis(
        "missing", links=[], graph={"graph": {"nodes": [], "edges": []}}, workload={"entries": []}
    )
    assert missing["blockers"][0]["key"] == "visible_confirmed_link_required"

    denied = service.build_cross_case_link_impact_analysis(
        "confirmed-link-1",
        links=[_link()],
        graph={"graph": {"nodes": [], "edges": []}},
        workload={"entries": []},
        allowed_case_ids={"case-alpha"},
    )
    assert denied["blockers"][0]["key"] == "confirmed_link_case_access_required"
    assert denied["confirmed_link_mutated"] is False
    assert denied["graph_mutated"] is False


def test_v25_4_impact_hash_is_deterministic(monkeypatch):
    monkeypatch.setattr(service, "build_case_closure_history", lambda case_id: {
        "current_closure_state": "open", "current_archive_state": "not_generated",
        "retention_disposition": None, "reopen_status": "none", "unresolved_actions": [],
        "event_count": 0, "latest_events": {},
    })
    monkeypatch.setattr(service, "_package_records", lambda case_ids: [])
    kwargs = {
        "links": [_link()],
        "graph": _graph(),
        "workload": {"entries": []},
    }
    first = service.build_cross_case_link_impact_analysis("confirmed-link-1", **kwargs)
    second = service.build_cross_case_link_impact_analysis("confirmed-link-1", **kwargs)
    assert first["impact_sha256"] == second["impact_sha256"]
