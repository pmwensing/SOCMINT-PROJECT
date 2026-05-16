from __future__ import annotations

import base64

from flask import Flask

from socmint.dossier_finalization_closeout_export_bundle_v7_5_11 import build_closeout_export_bundle
from socmint.dossier_finalization_closeout_export_bundle_v7_5_11 import build_closeout_export_zip
from socmint.dossier_finalization_closeout_report_v7_5_10 import build_closeout_report
from socmint.dossier_finalization_master_delivery_index_routes_v7_5_13 import register_dossier_finalization_master_delivery_index_routes


def app_client():
    app = Flask(__name__)
    register_dossier_finalization_master_delivery_index_routes(app)
    return app.test_client()


def verified_v7512_report():
    return {
        "schema": "socmint.v7_5_12.dossier_finalization_closeout_export_verification",
        "status": "verified",
        "verified": True,
        "failure_count": 0,
        "warning_count": 0,
        "required_files": ["README.md", "closeout_report.json"],
        "present_files": ["README.md", "closeout_report.json"],
        "missing_files": [],
        "unexpected_files": [],
        "manifest": {"file_count": 5, "files": []},
        "closeout_action": "closeout_ready",
        "verification_status": "verified",
        "failures": [],
        "warnings": [],
        "summary": {"status": "verified", "verified": True},
    }


def verified_v759_report():
    return {
        "schema": "socmint.v7_5_9.dossier_finalization_handoff_export_verification",
        "status": "verified",
        "verified": True,
        "failure_count": 0,
        "warning_count": 0,
        "recommended_action": "archive_ready",
        "verification_status": "verified",
        "certificate_status": "valid",
        "missing_files": [],
        "unexpected_files": [],
        "failures": [],
        "warnings": [],
        "summary": {"status": "verified", "verified": True},
    }


def closeout_bundle():
    closeout = build_closeout_report(verified_v759_report(), operator="analyst")
    return build_closeout_export_bundle(closeout, bundle_name="delivery-index-source")


def test_json_route_returns_deliver_ready_index_from_wrapped_verification_report():
    client = app_client()
    response = client.post(
        "/api/v1/dossier-builder/v3/intelligence/finalization/master-delivery-index",
        json={"verification_report": verified_v7512_report(), "operator": "analyst", "notes": "Ready."},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["schema"] == "socmint.v7_5_13.dossier_finalization_master_delivery_index"
    assert data["delivery_action"] == "deliver_ready"
    assert data["operator"] == "analyst"


def test_raw_verification_report_request_shape_works():
    client = app_client()
    response = client.post(
        "/api/v1/dossier-builder/v3/intelligence/finalization/master-delivery-index",
        json=verified_v7512_report(),
    )

    assert response.status_code == 200
    assert response.get_json()["delivery_action"] == "deliver_ready"


def test_markdown_route_returns_text_markdown():
    client = app_client()
    response = client.post(
        "/api/v1/dossier-builder/v3/intelligence/finalization/master-delivery-index/markdown",
        json={"verification_report": verified_v7512_report(), "notes": "Ready."},
    )

    assert response.status_code == 200
    assert response.mimetype == "text/markdown"
    text = response.get_data(as_text=True)
    assert "# SOCMINT v7.5.13 Master Dossier Delivery Index" in text
    assert "Delivery action: DELIVER_READY" in text


def test_from_bundle_route_returns_deliver_ready_index():
    client = app_client()
    response = client.post(
        "/api/v1/dossier-builder/v3/intelligence/finalization/master-delivery-index/from-bundle",
        json={"bundle": closeout_bundle(), "operator": "analyst"},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["delivery_action"] == "deliver_ready"
    assert data["verification_status"] == "verified"


def test_from_zip_route_returns_deliver_ready_index_for_valid_base64_zip():
    client = app_client()
    encoded = base64.b64encode(build_closeout_export_zip(closeout_bundle())).decode("ascii")
    response = client.post(
        "/api/v1/dossier-builder/v3/intelligence/finalization/master-delivery-index/from-zip",
        json={"zip_base64": encoded, "operator": "analyst"},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["delivery_action"] == "deliver_ready"
    assert data["verified"] is True


def test_invalid_base64_returns_regenerate_export_index_not_500():
    client = app_client()
    response = client.post(
        "/api/v1/dossier-builder/v3/intelligence/finalization/master-delivery-index/from-zip",
        json={"zip_base64": "not base64!!!"},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["delivery_action"] == "regenerate_export"
    assert data["verification_status"] == "failed"
    assert data["failure_count"] == 1


def test_missing_base64_returns_regenerate_export_index_not_500():
    client = app_client()
    response = client.post(
        "/api/v1/dossier-builder/v3/intelligence/finalization/master-delivery-index/from-zip",
        json={},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["delivery_action"] == "regenerate_export"
    assert data["failure_count"] == 1


def test_no_connector_execution_function_is_called(monkeypatch):
    import socmint.dossier_finalization_master_delivery_index_v7_5_13 as delivery_module

    def explode(*_args, **_kwargs):
        raise AssertionError("connector execution must not happen")

    monkeypatch.setattr(delivery_module, "execute_connector", explode, raising=False)
    client = app_client()
    response = client.post(
        "/api/v1/dossier-builder/v3/intelligence/finalization/master-delivery-index",
        json={"verification_report": verified_v7512_report()},
    )

    assert response.status_code == 200
    assert response.get_json()["delivery_action"] == "deliver_ready"
