from __future__ import annotations

import base64
import io
import zipfile

from flask import Flask

from socmint.dossier_finalization_master_delivery_export_bundle_v7_5_14 import (
    build_master_delivery_export_bundle,
)
from socmint.dossier_finalization_master_delivery_index_v7_5_13 import (
    build_master_delivery_index,
)
from socmint.v10_24_final_delivery_workspace import (
    build_final_delivery_workspace_from_bundle,
)
from socmint.v10_25_final_delivery_operator_console import (
    build_operator_console_from_workspace,
)
from socmint.v10_26_final_delivery_audit_trail import (
    build_final_delivery_audit_trail_from_console,
)
from socmint.v10_27_final_delivery_evidence_capsule import (
    build_final_delivery_evidence_capsule_from_audit_trail,
)
from socmint.v10_28_final_delivery_capsule_export_pack_routes import (
    register_v10_28_final_delivery_capsule_export_pack_routes,
)

REQUIRED_FILES = {
    "README.md",
    "final_delivery_evidence_capsule.json",
    "final_delivery_evidence_capsule_summary.json",
    "operator_receipt.json",
    "manifest.json",
}


def app_client():
    app = Flask(__name__)
    register_v10_28_final_delivery_capsule_export_pack_routes(app)
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
    return build_master_delivery_index(
        verification_report(), operator="analyst", notes="Ready."
    )


def capsule():
    bundle = build_master_delivery_export_bundle(
        delivery_index(), bundle_name="Route Export Pack"
    )
    workspace = build_final_delivery_workspace_from_bundle(bundle)
    console = build_operator_console_from_workspace(workspace)
    audit_trail = build_final_delivery_audit_trail_from_console(console)
    return build_final_delivery_evidence_capsule_from_audit_trail(audit_trail)


def test_json_export_route_returns_text_files_and_base64_zip_for_capsule_shape():
    client = app_client()
    response = client.post(
        "/api/v1/v10/final-delivery/evidence-capsule/export",
        json={"capsule": capsule()},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["schema"] == "socmint.v10_28.final_delivery_capsule_export_pack"
    assert data["readiness"] == "ready"
    assert set(data["text_files"]) == REQUIRED_FILES
    assert data["zip_base64"]
    assert data["zip_size_bytes"] > 0
    assert base64.b64decode(data["zip_base64"]).startswith(b"PK")


def test_json_export_route_accepts_index_shape():
    client = app_client()
    response = client.post(
        "/api/v1/v10/final-delivery/evidence-capsule/export",
        json={"index": delivery_index(), "bundle_name": "Route Index Export"},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["readiness"] == "ready"
    assert data["bundle_name"] == "route-index-export"


def test_zip_route_returns_application_zip_for_capsule_shape():
    client = app_client()
    response = client.post(
        "/api/v1/v10/final-delivery/evidence-capsule/export.zip",
        json={"capsule": capsule()},
    )

    assert response.status_code == 200
    assert response.mimetype == "application/zip"
    assert response.data.startswith(b"PK")


def test_zip_route_contains_required_files_for_index_shape():
    client = app_client()
    response = client.post(
        "/api/v1/v10/final-delivery/evidence-capsule/export.zip",
        json={"index": delivery_index(), "bundle_name": "Zip Route Index"},
    )

    assert response.status_code == 200
    with zipfile.ZipFile(io.BytesIO(response.data)) as archive:
        assert set(archive.namelist()) == REQUIRED_FILES


def test_no_connector_execution_function_is_called(monkeypatch):
    import socmint.v10_28_final_delivery_capsule_export_pack as pack_module

    def explode(*_args, **_kwargs):
        raise AssertionError("connector execution must not happen")

    monkeypatch.setattr(pack_module, "execute_connector", explode, raising=False)
    client = app_client()
    response = client.post(
        "/api/v1/v10/final-delivery/evidence-capsule/export",
        json={"index": delivery_index()},
    )

    assert response.status_code == 200
    assert response.get_json()["readiness"] == "ready"
