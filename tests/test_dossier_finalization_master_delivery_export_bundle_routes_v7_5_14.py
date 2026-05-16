from __future__ import annotations

import io
import zipfile

from flask import Flask

from socmint.dossier_finalization_master_delivery_export_bundle_routes_v7_5_14 import register_dossier_finalization_master_delivery_export_bundle_routes
from socmint.dossier_finalization_master_delivery_index_v7_5_13 import build_master_delivery_index

REQUIRED_FILES = {
    "README.md",
    "master_delivery_index.json",
    "master_delivery_index.md",
    "master_delivery_index_summary.json",
    "manifest.json",
}


def app_client():
    app = Flask(__name__)
    register_dossier_finalization_master_delivery_export_bundle_routes(app)
    return app.test_client()


def verification_report():
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


def delivery_index():
    return build_master_delivery_index(verification_report(), operator="analyst", notes="Ready.")


def test_json_export_route_returns_bundle_metadata():
    client = app_client()
    response = client.post(
        "/api/v1/dossier-builder/v3/intelligence/finalization/master-delivery-index/export",
        json={"index": delivery_index(), "bundle_name": "Route Export"},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["schema"] == "socmint.v7_5_14.dossier_finalization_master_delivery_export_bundle"
    assert data["bundle_name"] == "route-export"
    assert data["delivery_action"] == "deliver_ready"
    assert data["file_count"] == 5
    assert set(data["text_files"]) == REQUIRED_FILES
    assert data["zip_base64"]
    assert data["zip_size_bytes"] > 0


def test_raw_index_request_shape_works():
    client = app_client()
    response = client.post(
        "/api/v1/dossier-builder/v3/intelligence/finalization/master-delivery-index/export",
        json=delivery_index(),
    )

    assert response.status_code == 200
    assert response.get_json()["delivery_action"] == "deliver_ready"


def test_wrapped_index_request_shape_works():
    client = app_client()
    response = client.post(
        "/api/v1/dossier-builder/v3/intelligence/finalization/master-delivery-index/export",
        json={"index": delivery_index()},
    )

    assert response.status_code == 200
    assert response.get_json()["verification_status"] == "verified"


def test_zip_route_returns_application_zip():
    client = app_client()
    response = client.post(
        "/api/v1/dossier-builder/v3/intelligence/finalization/master-delivery-index/export.zip",
        json={"index": delivery_index(), "bundle_name": "Zip Export"},
    )

    assert response.status_code == 200
    assert response.mimetype == "application/zip"
    assert response.data.startswith(b"PK")


def test_returned_zip_contains_required_files():
    client = app_client()
    response = client.post(
        "/api/v1/dossier-builder/v3/intelligence/finalization/master-delivery-index/export.zip",
        json={"index": delivery_index()},
    )

    with zipfile.ZipFile(io.BytesIO(response.data)) as archive:
        assert set(archive.namelist()) == REQUIRED_FILES


def test_no_connector_execution_function_is_called(monkeypatch):
    import socmint.dossier_finalization_master_delivery_export_bundle_v7_5_14 as bundle_module

    def explode(*_args, **_kwargs):
        raise AssertionError("connector execution must not happen")

    monkeypatch.setattr(bundle_module, "execute_connector", explode, raising=False)
    client = app_client()
    response = client.post(
        "/api/v1/dossier-builder/v3/intelligence/finalization/master-delivery-index/export",
        json={"index": delivery_index()},
    )

    assert response.status_code == 200
    assert response.get_json()["delivery_action"] == "deliver_ready"
