from __future__ import annotations

import io
import zipfile

from flask import Flask

from socmint.dossier_finalization_master_delivery_export_bundle_v7_5_14 import build_master_delivery_export_bundle
from socmint.dossier_finalization_master_delivery_index_v7_5_13 import build_master_delivery_index
from socmint.v10_24_final_delivery_workspace_routes import register_v10_24_final_delivery_workspace_routes

REQUIRED_FILES = {
    "README.md",
    "master_delivery_index.json",
    "master_delivery_index.md",
    "master_delivery_index_summary.json",
    "manifest.json",
}


def app_client():
    app = Flask(__name__)
    register_v10_24_final_delivery_workspace_routes(app)
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


def delivery_bundle():
    return build_master_delivery_export_bundle(delivery_index(), bundle_name="Route Bundle")


def test_workspace_route_accepts_bundle_shape():
    client = app_client()
    response = client.post("/api/v1/v10/final-delivery/workspace", json={"bundle": delivery_bundle()})

    assert response.status_code == 200
    data = response.get_json()
    assert data["schema"] == "socmint.v10_24.final_delivery_workspace"
    assert data["delivery_action"] == "deliver_ready"
    assert data["package_ready"] is True
    assert data["bundle_name"] == "route-bundle"


def test_workspace_route_accepts_index_shape():
    client = app_client()
    response = client.post(
        "/api/v1/v10/final-delivery/workspace",
        json={"index": delivery_index(), "bundle_name": "Route Index"},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["delivery_action"] == "deliver_ready"
    assert data["bundle_name"] == "route-index"
    assert data["manifest_file_count"] == 5


def test_export_zip_route_returns_application_zip_for_bundle_shape():
    client = app_client()
    response = client.post("/api/v1/v10/final-delivery/export.zip", json={"bundle": delivery_bundle()})

    assert response.status_code == 200
    assert response.mimetype == "application/zip"
    assert response.data.startswith(b"PK")


def test_export_zip_route_returns_required_files_for_index_shape():
    client = app_client()
    response = client.post(
        "/api/v1/v10/final-delivery/export.zip",
        json={"index": delivery_index(), "bundle_name": "Route Zip"},
    )

    assert response.status_code == 200
    with zipfile.ZipFile(io.BytesIO(response.data)) as archive:
        assert set(archive.namelist()) == REQUIRED_FILES


def test_no_connector_execution_function_is_called(monkeypatch):
    import socmint.v10_24_final_delivery_workspace as workspace_module

    def explode(*_args, **_kwargs):
        raise AssertionError("connector execution must not happen")

    monkeypatch.setattr(workspace_module, "execute_connector", explode, raising=False)
    client = app_client()
    response = client.post("/api/v1/v10/final-delivery/workspace", json={"index": delivery_index()})

    assert response.status_code == 200
    assert response.get_json()["delivery_action"] == "deliver_ready"
