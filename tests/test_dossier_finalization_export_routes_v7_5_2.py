from __future__ import annotations

import io
import zipfile

from socmint.dashboard import create_app
from socmint.dossier_finalization_export_routes_v7_5_2 import register_dossier_finalization_export_routes

CSRF_TOKEN = "test-csrf-token"
CSRF_HEADERS = {"X-CSRF-Token": CSRF_TOKEN}
REQUIRED_FILES = {
    "README.md",
    "finalization_packet.json",
    "finalization_packet.md",
    "finalization_summary.json",
    "manifest.json",
}


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
    register_dossier_finalization_export_routes(app)
    client = app.test_client()
    with client.session_transaction() as session:
        session["_csrf_token"] = CSRF_TOKEN
    return client


def post_json(client, path, payload):
    return client.post(path, json=payload, headers=CSRF_HEADERS)


def test_json_route_returns_export_packet_metadata():
    client = app_client()
    response = post_json(client, "/api/v1/dossier-builder/v3/intelligence/finalization/export", {"dossier": base_payload(), "export_mode": "final"})

    assert response.status_code == 200
    data = response.get_json()
    assert data["schema"] == "socmint.v7_5_2.dossier_finalization_export_packet"
    assert data["decision"] == "ready"
    assert data["manifest"]["file_count"] == len(data["files"])


def test_zip_route_returns_application_zip():
    client = app_client()
    response = post_json(client, "/api/v1/dossier-builder/v3/intelligence/finalization/export.zip", {"dossier": base_payload(), "package_name": "Case Export"})

    assert response.status_code == 200
    assert response.mimetype == "application/zip"
    assert "case-export.zip" in response.headers["Content-Disposition"]


def test_zip_route_contains_required_files():
    client = app_client()
    response = post_json(client, "/api/v1/dossier-builder/v3/intelligence/finalization/export.zip", {"dossier": base_payload()})

    with zipfile.ZipFile(io.BytesIO(response.get_data())) as archive:
        assert set(archive.namelist()) == REQUIRED_FILES


def test_wrapped_request_shape_works():
    payload = base_payload()
    payload.pop("connector_compliance")
    payload.pop("policy_coverage")
    client = app_client()
    response = post_json(
        client,
        "/api/v1/dossier-builder/v3/intelligence/finalization/export",
        {
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
            "package_name": "Wrapped Packet",
        },
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["package_name"] == "wrapped-packet"
    assert data["finalization"]["component_status"]["connector_compliance"] == "pass"
    assert data["finalization"]["component_status"]["policy_coverage"] == "pass"


def test_raw_dossier_request_shape_works():
    client = app_client()
    response = post_json(client, "/api/v1/dossier-builder/v3/intelligence/finalization/export", base_payload())

    assert response.status_code == 200
    assert response.get_json()["schema"] == "socmint.v7_5_2.dossier_finalization_export_packet"


def test_connector_input_is_metadata_only(monkeypatch):
    import socmint.dossier_finalization_export_v7_5_2 as export_module

    def explode(_connectors):
        raise AssertionError("connector execution must not happen")

    monkeypatch.setattr(export_module, "execute_connector", explode, raising=False)
    client = app_client()
    response = post_json(client, "/api/v1/dossier-builder/v3/intelligence/finalization/export", {"dossier": base_payload(), "connectors": []})

    assert response.status_code == 200
