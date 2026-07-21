from src.socmint import dossier_export_readiness_v37_7 as service


SNAPSHOT = {
    "dossier_synthesis_snapshot_id": "snapshot-1",
    "dossier_synthesis_snapshot_sha256": "a" * 64,
    "integrity_manifest_sha256": "b" * 64,
    "case_id": "case-a",
    "entity_id": "entity-a",
}
READY_WORKFLOW = {
    "summary": {"finding_count": 0},
    "findings": [],
}
READY_CHRONOLOGY = {
    "summary": {"entry_count": 1},
    "entries": [{"entry_id": "entry-1"}],
}


def _configure(monkeypatch, *, snapshot=SNAPSHOT, workflow=READY_WORKFLOW, chronology=READY_CHRONOLOGY):
    monkeypatch.setattr(service, "find_snapshot", lambda snapshot_id: snapshot)
    monkeypatch.setattr(service, "build_guided_analyst_workflow", lambda: workflow)
    monkeypatch.setattr(
        service,
        "build_relationship_chronology",
        lambda **kwargs: chronology,
    )
    monkeypatch.setattr(
        service,
        "_record",
        lambda actor, readiness_id, event, ip_address: {
            **event,
            "actor": actor,
            "audit_record_id": 1,
            "recorded_at": "2026-07-20T01:30:00+00:00",
        },
    )


def _assess(monkeypatch, **config):
    _configure(monkeypatch, **config)
    return service.assess_dossier_export_readiness(
        actor="admin",
        snapshot_id="snapshot-1",
        redaction_review_id="redaction-1",
        scope_review_id="scope-1",
        quality_gate_reference="quality-1",
        approval_reference="approval-1",
        manifest_reference="manifest-1",
        chronology_reviewed=True,
        unresolved_exceptions=[],
        reason="Assess readiness without exporting.",
        confirmed=True,
    )


def test_v37_7_records_ready_projection_without_export(monkeypatch):
    result = _assess(monkeypatch)
    assert result["status"] == "dossier_export_readiness_recorded"
    assert result["readiness_status"] == "ready"
    assert result["readiness_blockers"] == []
    assert result["bindings"]["snapshot_id"] == "snapshot-1"
    assert result["bindings"]["redaction_review_id"] == "redaction-1"
    assert result["bindings"]["chronology_summary"] == {"entry_count": 1}
    assert result["export_created"] is False
    assert result["published"] is False
    assert result["dossier_mutated"] is False
    assert result["existing_export_services_remain_authoritative"] is True
    assert result["next_action"] == "submit_to_existing_export_approval_gate"


def test_v37_7_records_not_ready_when_integrity_or_conflicts_remain(monkeypatch):
    workflow = {
        "summary": {"finding_count": 2},
        "findings": [
            {
                "key": "quarantined_import_records",
                "severity": "integrity_alert",
                "count": 1,
            },
            {
                "key": "alternative_ranking_tied",
                "severity": "attention",
                "count": 1,
            },
        ],
    }
    result = _assess(monkeypatch, workflow=workflow)
    assert result["readiness_status"] == "not_ready"
    assert result["readiness_blockers"] == [
        "workflow_integrity_findings_unresolved",
        "claim_conflicts_or_ranking_ties_unresolved",
    ]
    assert result["unresolved_conflict_count"] == 1
    assert result["next_action"] == "resolve_readiness_blockers"
    assert result["export_created"] is False


def test_v37_7_requires_nonempty_reviewed_chronology(monkeypatch):
    result = _assess(monkeypatch, chronology={"summary": {}, "entries": []})
    assert result["readiness_status"] == "not_ready"
    assert result["readiness_blockers"] == ["reviewed_chronology_empty"]


def test_v37_7_declared_exceptions_keep_projection_not_ready(monkeypatch):
    _configure(monkeypatch)
    result = service.assess_dossier_export_readiness(
        actor="admin",
        snapshot_id="snapshot-1",
        redaction_review_id="redaction-1",
        scope_review_id="scope-1",
        quality_gate_reference="quality-1",
        approval_reference="approval-1",
        manifest_reference="manifest-1",
        chronology_reviewed=True,
        unresolved_exceptions=["synthetic_exception"],
        reason="Assess.",
        confirmed=True,
    )
    assert result["readiness_status"] == "not_ready"
    assert result["readiness_blockers"] == ["declared_unresolved_exceptions"]


def test_v37_7_blocks_missing_snapshot_references_and_confirmation(monkeypatch):
    _configure(monkeypatch, snapshot=None)
    result = service.assess_dossier_export_readiness(
        actor="admin",
        snapshot_id="snapshot-1",
        redaction_review_id="redaction-1",
        scope_review_id="scope-1",
        quality_gate_reference="quality-1",
        approval_reference="approval-1",
        manifest_reference="manifest-1",
        chronology_reviewed=True,
        unresolved_exceptions=[],
        reason="Assess.",
        confirmed=True,
    )
    assert result["blockers"] == [{"key": "dossier_synthesis_snapshot_required"}]

    _configure(monkeypatch)
    result = service.assess_dossier_export_readiness(
        actor="admin",
        snapshot_id="snapshot-1",
        redaction_review_id="",
        scope_review_id="scope-1",
        quality_gate_reference="quality-1",
        approval_reference="approval-1",
        manifest_reference="manifest-1",
        chronology_reviewed=True,
        unresolved_exceptions=[],
        reason="Assess.",
        confirmed=True,
    )
    assert result["blockers"] == [
        {"key": "redaction_scope_quality_approval_and_manifest_references_required"}
    ]

    result = service.assess_dossier_export_readiness(
        actor="admin",
        snapshot_id="snapshot-1",
        redaction_review_id="redaction-1",
        scope_review_id="scope-1",
        quality_gate_reference="quality-1",
        approval_reference="approval-1",
        manifest_reference="manifest-1",
        chronology_reviewed=True,
        unresolved_exceptions=[],
        reason="Assess.",
        confirmed=False,
    )
    assert result["blockers"] == [
        {"key": "explicit_export_readiness_confirmation_required"}
    ]
