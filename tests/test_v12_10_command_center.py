from src.socmint.v12_10_command_center import (
    DossierBuilderV3,
    EvidenceIntegrityEngine,
    AutonomousRuntimeMesh,
    AnalystPropagationEngine,
    StrategicRiskEngine,
    ContinuousMonitoringEngine,
    SOCMINTCommandCenterV121028,
)


def payload():
    return {
        "entities": [{"id": "e1", "name": "Example Person", "type": "person"}],
        "seeds": [{"type": "username", "value": "example"}],
        "connectors": [{"name": "sherlock", "status": "healthy"}],
        "watchlists": [{"target": "example", "active": True}],
        "alerts": [{"id": "a1", "type": "new_hit"}],
        "artifacts": [{"id": "note1", "label": "Analyst note"}],
        "assertions": [
            {"id": "as1", "type": "identity", "claim": "same handle", "confidence": 0.8, "review_status": "approved"},
            {"id": "as2", "type": "identity", "claim": "possible conflict", "confidence": 0.4, "status": "needs_review"},
        ],
        "timeline": [{"id": "t1", "timestamp": "2026-05-24T00:00:00Z", "title": "Created"}],
        "exposures": [{"id": "x1"}],
        "graph": {
            "nodes": [{"id": "e1", "confidence": 0.5}],
            "edges": [{"id": "r1", "confidence": 0.5}],
        },
        "decisions": [{"target_id": "e1", "action": "PROMOTE"}],
    }


def test_dossier_builder_v3_manifest():
    out = DossierBuilderV3().build("case-1", payload())
    assert out["manifest"]["case_id"] == "case-1"
    assert out["manifest"]["integrity_verified"] is True
    assert set(out["exports"].keys()) == {"json", "html", "csv"}


def test_evidence_integrity_note_only():
    out = EvidenceIntegrityEngine().inspect(payload()["artifacts"])
    assert out["note_only"] == 1
    assert out["risk_level"] == "low"


def test_runtime_mesh_jobs():
    out = AutonomousRuntimeMesh().plan(payload())
    assert out["job_count"] >= 3


def test_analyst_propagation_promote():
    out = AnalystPropagationEngine().apply(payload()["graph"], payload()["decisions"])
    assert out["changed_count"] == 1
    assert out["nodes"][0]["review_status"] == "approved"


def test_strategic_risk_score():
    out = StrategicRiskEngine().score(payload())
    assert "risk_score" in out
    assert out["risk_level"] in {"low", "moderate", "high", "critical"}


def test_continuous_monitoring_evolution():
    out = ContinuousMonitoringEngine().evolve(payload())
    assert out["autonomous_case_evolution"] is True


def test_run_all():
    out = SOCMINTCommandCenterV121028().run_all("case-1", payload())
    assert out["version"] == "12.10.28"
    assert "v12.10.23_dossier_builder" in out["stages"]
    assert "v12.10.28_continuous_monitoring" in out["stages"]
