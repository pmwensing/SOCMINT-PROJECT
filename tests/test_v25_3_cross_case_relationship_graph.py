from src.socmint.cross_case_relationship_graph_v25_3 import (
    build_cross_case_relationship_graph,
)


def _link(category="entity", match_value="entity-42"):
    return {
        "confirmed_link_id": f"confirmed-{category}-1",
        "confirmed_link_sha256": "f" * 64,
        "registry_record_id": 21,
        "registered_at": "2026-06-16T07:00:00+00:00",
        "registered_by": "registry-manager",
        "category": category,
        "match_value": match_value,
        "display_values": [match_value],
        "case_ids": ["case-alpha", "case-bravo"],
        "source_occurrences": [
            {
                "case_id": "case-alpha",
                "record_id": 1,
                "source_action": "case_entity_observed",
                "field_path": "entity_id",
                "actor": "analyst-a",
                "occurred_at": "2026-06-16T02:00:00+00:00",
                "display_value": match_value,
                "provenance_sha256": "a" * 64,
            },
            {
                "case_id": "case-bravo",
                "record_id": 2,
                "source_action": "case_entity_observed",
                "field_path": "entity_id",
                "actor": "analyst-b",
                "occurred_at": "2026-06-16T03:00:00+00:00",
                "display_value": match_value,
                "provenance_sha256": "b" * 64,
            },
        ],
        "source_occurrences_sha256": "o" * 64,
        "accepted_review_decision_id": f"review-{category}-1",
        "accepted_review_decision_sha256": "d" * 64,
        "accepted_review": {
            "workspace_access_scope": {
                "mode": "restricted",
                "allowed_case_ids": ["case-alpha", "case-bravo"],
            }
        },
    }


def test_v25_3_projects_confirmed_links_into_provenance_graph():
    result = build_cross_case_relationship_graph(
        links=[_link("entity", "entity-42"), _link("identifier", "shared@example.com")],
        allowed_case_ids={"case-alpha", "case-bravo"},
    )

    assert result["status"] == "ready"
    assert result["access_scope"]["mode"] == "restricted"
    assert result["counts"]["confirmed_links"] == 2
    assert result["counts"]["nodes_by_type"]["case"] == 2
    assert result["counts"]["nodes_by_type"]["entity"] == 1
    assert result["counts"]["nodes_by_type"]["identifier"] == 1
    assert result["counts"]["nodes_by_type"]["temporal"] == 2
    assert result["counts"]["edges_by_type"]["case_confirmed_link"] == 4
    assert result["counts"]["edges_by_type"]["case_observed_at"] == 4
    assert result["counts"]["edges_by_type"]["linked_value_observed_at"] == 4
    assert len(result["graph_sha256"]) == 64

    case_node = next(
        node
        for node in result["graph"]["nodes"]
        if node["node_type"] == "case" and node["label"] == "case-alpha"
    )
    assert set(case_node["confirmed_link_ids"]) == {
        "confirmed-entity-1",
        "confirmed-identifier-1",
    }
    assert len(case_node["review_bindings"]) == 2
    assert len(case_node["source_occurrences"]) == 2
    assert all("confirmed_link_id" in item for item in case_node["provenance"])
    assert len(case_node["node_sha256"]) == 64

    edge = next(
        edge
        for edge in result["graph"]["edges"]
        if edge["edge_type"] == "case_confirmed_link"
    )
    assert edge["confirmed_link_id"]
    assert edge["accepted_review_decision_id"]
    assert edge["access_scope"]["mode"] == "restricted"
    assert edge["source_occurrences"]
    assert len(edge["source_occurrences_sha256"]) == 64
    assert len(edge["edge_sha256"]) == 64

    assert result["source_occurrences_preserved"] is True
    assert result["review_bindings_preserved"] is True
    assert result["provenance_preserved"] is True
    assert result["source_records_mutated"] is False
    assert result["graph_record_created"] is False


def test_v25_3_supports_all_confirmed_link_node_categories():
    links = [
        _link("entity", "entity-42"),
        _link("identifier", "shared@example.com"),
        _link("infrastructure", "example.com"),
        _link("evidence", "evidence-9"),
        _link("timeline", "2026-06-16T02:00:00+00:00"),
    ]
    result = build_cross_case_relationship_graph(links=links)
    node_types = {node["node_type"] for node in result["graph"]["nodes"]}
    assert {
        "case",
        "entity",
        "identifier",
        "infrastructure",
        "evidence",
        "temporal",
    }.issubset(node_types)
    assert result["counts"]["confirmed_links"] == 5


def test_v25_3_filters_inaccessible_links_before_projection():
    visible = _link("entity", "entity-visible")
    hidden = _link("identifier", "hidden@example.com")
    hidden["confirmed_link_id"] = "confirmed-hidden"
    hidden["case_ids"] = ["case-alpha", "case-hidden"]
    hidden["source_occurrences"][1] = {
        **hidden["source_occurrences"][1],
        "case_id": "case-hidden",
    }

    result = build_cross_case_relationship_graph(
        links=[visible, hidden],
        allowed_case_ids={"case-alpha", "case-bravo"},
    )
    assert result["counts"]["confirmed_links"] == 1
    assert result["graph"]["confirmed_link_ids"] == ["confirmed-entity-1"]
    assert all(node.get("value") != "case-hidden" for node in result["graph"]["nodes"])
    assert all(
        edge["confirmed_link_id"] != "confirmed-hidden"
        for edge in result["graph"]["edges"]
    )
