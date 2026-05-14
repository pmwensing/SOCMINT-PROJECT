from socmint.dashboard import create_app
from socmint.dossier_finalization_routes_v7_5_1 import register_dossier_finalization_routes


def base_payload():
    return {
        "quality_gate": {"status": "pass", "finding_count": 0},
        "export_enforcement": {"status": "allowed", "allowed": True, "final_export_blocked": False},
        "evidence_manifest": {"status": "pass", "appendix_summary": {"missing_ref_count": 0, "missing_hash_count": 0, "missing_source_count": 0}},
        "identity_confidence": {"status": "pass", "contradiction_count": 0, "low_confidence_count": 0, "needs_review_count": 0},
        "connector_compliance": {"status": "pass", "finding_count": 0},
        "policy_coverage": {"status": "pass", "finding_count": 0},
    }


def app_client():
    app = create_app()
    register_dossier_finalization_routes(app)
    return app.test_client()


def test_json_route_returns_packet():
    client = app_client()
    response = client.post("/api/v1/dossier-builder/v3/intelligence/finalization", json={"dossier": base_payload(), "export_mode": "final"})

    assert response.status_code == 200
    data = response.get_json()
    assert data["schema"] == "socmint.v7_5_1.dossier_finalization"
    assert data["decision"] == "ready"


def test_markdown_route_returns_packet_text():
    client = app_client()
    response = client.post("/api/v1/dossier-builder/v3/intelligence/finalization/markdown", json={"dossier": base_payload(), "export_mode": "final"})

    assert response.status_code == 200
    text = response.get_data(as_text=True)
    assert "# SOCMINT v7.5.1 Dossier Finalization Packet" in text
    assert "Decision: READY" in text


def test_wrapped_request_shape_uses_connectors_and_policy_events():
    payload = base_payload()
    payload.pop("connector_compliance")
    payload.pop("policy_coverage")
    client = app_client()
    response = client.post(
        "/api/v1/dossier-builder/v3/intelligence/finalization",
        json={
            "dossier": payload,
            "connectors": [
                {
                    "name": "manual_source",
                    "version": "1.0",
                    "supported_seed_types": ["name", "url"],
                    "requires_network": False,
                    "requires_api_key": False,
                    "risk_level": "low",
                    "source_method": "analyst_supplied",
                    "rate_limit_policy": {"requests_per_minute": 0},
                    "policy_metadata": {"human_review_required": False, "public_source_only": True},
                    "dry_run_supported": True,
                }
            ],
            "policy_events": [
                {"operation": name, "decision": "allow", "case_id": "case-1"}
                for name in [
                    "dossier_build",
                    "dossier_export",
                    "connector_run",
                    "recursive_run",
                    "artifact_upload",
                    "artifact_download",
                    "retention_run",
                ]
            ],
            "export_mode": "final",
        },
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["component_status"]["connector_compliance"] == "pass"
    assert data["component_status"]["policy_coverage"] == "pass"


def test_raw_dossier_request_shape_works():
    client = app_client()
    response = client.post("/api/v1/dossier-builder/v3/intelligence/finalization", json=base_payload())

    assert response.status_code == 200
    assert response.get_json()["schema"] == "socmint.v7_5_1.dossier_finalization"


def test_route_treats_connectors_as_metadata_only(monkeypatch):
    import socmint.dossier_finalization_v7_5_1 as finalization

    def explode(_connectors):
        raise AssertionError("connector execution must not happen")

    monkeypatch.setattr(finalization, "execute_connector", explode, raising=False)
    client = app_client()
    response = client.post("/api/v1/dossier-builder/v3/intelligence/finalization", json={"dossier": base_payload(), "connectors": []})

    assert response.status_code == 200
