from src.socmint import guided_analyst_workflow_v37_5 as workflow


def _configure(monkeypatch):
    monkeypatch.setattr(workflow, "current_imports", lambda: [{"operational_import_id": "import-1"}])
    monkeypatch.setattr(
        workflow,
        "current_staged_record_projections",
        lambda: [
            {"staged_record_id": "record-1", "initial_state": "accepted"},
            {"staged_record_id": "record-2", "initial_state": "quarantined"},
            {"staged_record_id": "record-3", "initial_state": "duplicate"},
        ],
    )
    monkeypatch.setattr(
        workflow,
        "current_scope_assessments",
        lambda: [
            {"staged_record_id": "record-1", "scope_status": "in_scope"},
            {
                "staged_record_id": "record-2",
                "scope_status": "candidate_review_required",
                "candidate_review_required": True,
            },
        ],
    )
    monkeypatch.setattr(
        workflow,
        "current_review_decisions",
        lambda: [
            {
                "staged_record_id": "record-1",
                "decision": "accepted",
                "observation_promotion_allowed": True,
            }
        ],
    )
    monkeypatch.setattr(
        workflow,
        "current_promotions",
        lambda: [
            {
                "staged_record_id": "relocation-record",
                "relocation_context_only": True,
            }
        ],
    )
    monkeypatch.setattr(
        workflow,
        "build_entity_accuracy_workspace",
        lambda: {
            "summary": {
                "entity_candidate_count": 2,
                "claim_verification_count": 3,
                "relationship_timeline_count": 1,
                "dossier_snapshot_count": 1,
            },
            "findings": [
                {
                    "key": "alternative_ranking_tied",
                    "severity": "attention",
                    "count": 1,
                    "message": "Tie retained.",
                    "next_action": "Review alternatives.",
                }
            ],
        },
    )


def test_v37_5_builds_integrated_read_only_workflow(monkeypatch):
    _configure(monkeypatch)
    result = workflow.build_guided_analyst_workflow()
    assert result["schema"] == "socmint.guided_analyst_workflow.v37_5"
    assert result["read_only"] is True
    assert result["summary"] == {
        "import_count": 1,
        "staged_record_count": 3,
        "scope_assessment_count": 2,
        "review_decision_count": 1,
        "observation_promotion_count": 1,
        "entity_candidate_count": 2,
        "claim_verification_count": 3,
        "relationship_timeline_count": 1,
        "dossier_snapshot_count": 1,
        "finding_count": 8,
    }
    assert result["controls"]["write_actions_exposed_by_workflow"] == []
    assert result["controls"]["automatic_entity_merge"] is False
    assert result["controls"]["automatic_claim_approval"] is False
    assert result["controls"]["automatic_export"] is False


def test_v37_5_surfaces_expected_findings(monkeypatch):
    _configure(monkeypatch)
    result = workflow.build_guided_analyst_workflow()
    findings = {item["key"]: item for item in result["findings"]}
    assert set(findings) == {
        "import_records_waiting_scope_assessment",
        "import_records_waiting_human_review",
        "quarantined_import_records",
        "duplicate_import_records",
        "candidate_entities_waiting_resolution",
        "accepted_records_waiting_observation_promotion",
        "relocation_context_separated_from_issue_support",
        "alternative_ranking_tied",
    }
    assert findings["quarantined_import_records"]["severity"] == "integrity_alert"
    assert findings["duplicate_import_records"]["severity"] == "integrity_alert"
    assert findings["alternative_ranking_tied"]["source_workspace"] == "entity_accuracy_v36_8"


def test_v37_5_empty_workflow_is_safe(monkeypatch):
    monkeypatch.setattr(workflow, "current_imports", lambda: [])
    monkeypatch.setattr(workflow, "current_staged_record_projections", lambda: [])
    monkeypatch.setattr(workflow, "current_scope_assessments", lambda: [])
    monkeypatch.setattr(workflow, "current_review_decisions", lambda: [])
    monkeypatch.setattr(workflow, "current_promotions", lambda: [])
    monkeypatch.setattr(workflow, "build_entity_accuracy_workspace", lambda: {"summary": {}, "findings": []})
    result = workflow.build_guided_analyst_workflow()
    assert result["status"] == "ready"
    assert result["summary"]["finding_count"] == 0
    assert result["findings"] == []
