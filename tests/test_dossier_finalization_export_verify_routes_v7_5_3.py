from __future__ import annotations

import base64

from socmint.dashboard import create_app
from socmint.dossier_finalization_export_v7_5_2 import build_finalization_export_packet
from socmint.dossier_finalization_export_v7_5_2 import build_finalization_export_zip
from socmint.dossier_finalization_export_verify_routes_v7_5_3 import (
    register_dossier_finalization_export_verify_routes,
)

CSRF_TOKEN = "test-csrf-token"
CSRF_HEADERS = {"X-CSRF-Token": CSRF_TOKEN}


def base_payload():
    return {
        "quality_gate": {"status": "pass", "finding_count": 0},
        "export_enforcement": {
            "status": "allowed",
            "allowed": True,
            "final_export_blocked": False,
        },
        "evidence_manifest": {
            "status": "pass",
            "appendix_summary": {
                "missing_ref_count": 0,
                "missing_hash_count": 0,
                "missing_source_count": 0,
            },
        },
        "identity_confidence": {
            "status": "pass",
            "contradiction_count": 0,
            "low_confidence_count": 0,
            "needs_review_count": 0,
        },
        "connector_compliance": {"status": "pass", "finding_count": 0},
        "policy_coverage": {"status": "pass", "finding_count": 0},
    }


def ready_packet():
    return build_finalization_export_packet(base_payload())


def app_client():
    app = create_app()
    register_dossier_finalization_export_verify_routes(app)
    client = app.test_client()
    with client.session_transaction() as session:
        session["_csrf_token"] = CSRF_TOKEN
    return client


def post_json(client, path, payload):
    return client.post(path, json=payload, headers=CSRF_HEADERS)


def test_json_packet_route_returns_verified_report():
    client = app_client()
    response = post_json(
        client,
        "/api/v1/dossier-builder/v3/intelligence/finalization/export/verify",
        {"packet": ready_packet()},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["schema"] == "socmint.v7_5_3.dossier_finalization_export_verification"
    assert data["status"] == "verified"
    assert data["verified"] is True


def test_raw_packet_request_shape_works():
    client = app_client()
    response = post_json(
        client,
        "/api/v1/dossier-builder/v3/intelligence/finalization/export/verify",
        ready_packet(),
    )

    assert response.status_code == 200
    assert response.get_json()["status"] == "verified"


def test_wrapped_packet_request_shape_works():
    client = app_client()
    response = post_json(
        client,
        "/api/v1/dossier-builder/v3/intelligence/finalization/export/verify",
        {"packet": ready_packet()},
    )

    assert response.status_code == 200
    assert response.get_json()["summary"]["status"] == "verified"


def test_zip_base64_route_returns_verified_report():
    zip_bytes = build_finalization_export_zip(ready_packet())
    encoded = base64.b64encode(zip_bytes).decode("ascii")
    client = app_client()
    response = post_json(
        client,
        "/api/v1/dossier-builder/v3/intelligence/finalization/export/verify-zip",
        {"zip_base64": encoded},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "verified"
    assert data["verified"] is True


def test_invalid_base64_returns_failed_report_not_500():
    client = app_client()
    response = post_json(
        client,
        "/api/v1/dossier-builder/v3/intelligence/finalization/export/verify-zip",
        {"zip_base64": "not base64!!!"},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "failed"
    assert data["verified"] is False
    assert any(item["code"] == "invalid_zip" for item in data["failures"])


def test_missing_base64_returns_failed_report_not_500():
    client = app_client()
    response = post_json(
        client,
        "/api/v1/dossier-builder/v3/intelligence/finalization/export/verify-zip",
        {},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "failed"
    assert data["failure_count"] == 1


def test_no_connector_execution_function_is_called(monkeypatch):
    import socmint.dossier_finalization_export_verify_v7_5_3 as verify_module

    def explode(*_args, **_kwargs):
        raise AssertionError("connector execution must not happen")

    monkeypatch.setattr(verify_module, "execute_connector", explode, raising=False)
    client = app_client()
    response = post_json(
        client,
        "/api/v1/dossier-builder/v3/intelligence/finalization/export/verify",
        {"packet": ready_packet()},
    )

    assert response.status_code == 200
    assert response.get_json()["status"] == "verified"
