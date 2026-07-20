from src.socmint import relationship_chronology_workflow_v37_6 as workflow


def _configure(monkeypatch):
    monkeypatch.setattr(
        workflow,
        "current_promotions",
        lambda: [
            {
                "promotion_id": "promotion-1",
                "case_id": "case-a",
                "staged_record_id": "record-1",
                "binding_sha256": "a" * 64,
                "relocation_context_only": True,
                "issue_claim_support_allowed": False,
            }
        ],
    )
    monkeypatch.setattr(
        workflow,
        "find_staged_record_projection",
        lambda record_id: {
            "staged_record_id": record_id,
            "operational_import_id": "import-1",
            "observed_at": "2026-07-20T01:00:00+00:00",
        },
    )
    monkeypatch.setattr(
        workflow,
        "find_import",
        lambda import_id: {
            "envelope": {
                "case_id": "case-a",
                "exported_at": "2026-07-20T01:01:00+00:00",
                "imported_at": "2026-07-20T01:02:00+00:00",
            }
        },
    )
    monkeypatch.setattr(
        workflow,
        "current_relationship_assessments",
        lambda: [
            {
                "relationship_timeline_assessment_id": "relationship-1",
                "relationship_timeline_assessment_sha256": "b" * 64,
                "case_id": "case-a",
                "subject_entity_id": "entity-a",
                "object_entity_id": "entity-b",
                "relationship_type": "communication",
                "inference_class": "supported_inference",
                "inference_warning": "Supported inference; not direct proof.",
                "limitations": ["Synthetic fixture."],
                "times": {
                    "event_time": "2026-07-20T02:00:00+00:00",
                    "report_time": "2026-07-20T02:01:00+00:00",
                    "capture_time": "2026-07-20T02:02:00+00:00",
                    "valid_from": "2026-07-20T02:00:00+00:00",
                    "valid_to": None,
                },
            },
            {
                "relationship_timeline_assessment_id": "relationship-2",
                "relationship_timeline_assessment_sha256": "c" * 64,
                "case_id": "case-a",
                "subject_entity_id": "entity-a",
                "object_entity_id": "entity-c",
                "relationship_type": "co_occurrence",
                "inference_class": "co_occurrence_only",
                "inference_warning": "Co-occurrence is not a relationship.",
                "limitations": [],
                "times": {
                    "event_time": "2026-07-20T03:00:00+00:00",
                    "report_time": None,
                    "capture_time": "2026-07-20T03:01:00+00:00",
                    "valid_from": None,
                    "valid_to": None,
                },
            },
        ],
    )


def test_v37_6_builds_time_separated_chronology(monkeypatch):
    _configure(monkeypatch)
    result = workflow.build_relationship_chronology(case_id="case-a")
    assert result["schema"] == "socmint.relationship_chronology_workflow.v37_6"
    assert [item["entry_id"] for item in result["entries"]] == [
        "promotion-1",
        "relationship-1",
        "relationship-2",
    ]
    assert result["summary"] == {
        "entry_count": 3,
        "promoted_observation_count": 1,
        "relationship_assessment_count": 2,
        "supported_inference_count": 1,
        "co_occurrence_only_count": 1,
        "relocation_context_count": 1,
    }
    relationship = result["entries"][1]
    assert relationship["event_time"] != relationship["report_time"]
    assert relationship["capture_time"] != relationship["event_time"]
    assert relationship["inference_warning"]
    assert result["controls"]["co_occurrence_promoted_to_relationship"] is False
    assert result["controls"]["causation_assigned"] is False


def test_v37_6_entity_filter_preserves_only_matching_relationships(monkeypatch):
    _configure(monkeypatch)
    result = workflow.build_relationship_chronology(
        case_id="case-a",
        entity_id="entity-b",
    )
    assert [item["entry_id"] for item in result["entries"]] == ["relationship-1"]
    assert result["summary"]["promoted_observation_count"] == 0


def test_v37_6_relocation_observation_stays_out_of_issue_support(monkeypatch):
    _configure(monkeypatch)
    result = workflow.build_relationship_chronology(case_id="case-a")
    relocation = result["entries"][0]
    assert relocation["relocation_context_only"] is True
    assert relocation["issue_claim_support_allowed"] is False
    assert "not a truth assignment" in relocation["limitations"][0]
