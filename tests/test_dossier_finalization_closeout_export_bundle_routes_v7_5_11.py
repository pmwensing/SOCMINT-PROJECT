from __future__ import annotations

import io
import zipfile

from socmint.dashboard import create_app
from socmint.dossier_finalization_closeout_export_bundle_routes_v7_5_11 import register_dossier_finalization_closeout_export_bundle_routes
from socmint.dossier_finalization_closeout_report_v7_5_10 import build_closeout_report

CSRF_TOKEN = "test-csrf-token"
CSRF_HEADERS = {"X-CSRF-Token": CSRF_TOKEN}
REQUIRED_FILES = {
    "README.md",
    "closeout_report.json",
    "closeout_report.md",
    "closeout_report_summary.json",
    "manifest.json",
}


def verified_report():
    return {
        "schema": "socmint.v7_5_9.dossier_finalization_handoff_export_verification",
        "status": "verified",
        "verified": True,
        "failure_count": 0,
        "warning_count": 0,
        "recommended_action": "archive_ready",
        "verification_status": "verified",
        "certificate_status": "valid",
        "present_files": ["README.md", "handoff_index.json", "manifest.json"],
        "missing_files": [],
        "unexpected_files": [],
        "failures": [],
        "warnings": [],
        "summary": {"status": "verified", "verified": True},
    }


def closeout_ready_report():
    return build_closeout_report(verified_report(), operator="operator-a")


def app_client():
    app = create_app()
    register_dossier_finalization_closeout_export_bundle_routes(app)
    client = app.test_client()
    with client.session_transaction() as session:
        session["_csrf_token"] = CSRF_TOKEN
    return client


def post_json(client, path, payload):
    return client.post(path, json=payload, headers=CSRF_HEADERS)


def test_json_route_returns_export_bundle_metadata_from_wrapped_report():
    client = app_client()
    response = post_json(
        client,
        "/api/v1/dossier-builder/v3/intelligence/finalization/closeout-report/export",
        {"report": closeout_ready_report(), "bundle_name": "Closeout Bundle"},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["schema"] == "socmint.v7_5_11.dossier_finalization_closeout_export_bundle"
    assert data["bundle_name"] == "closeout-bundle"
    assert data["closeout_action"] == "closeout_ready"


def test_raw_report_request_shape_works():
    client = app_client()
    response = post_json(client, "/api/v1/dossier-builder/v3/intelligence/finalization/closeout-report/export", closeout_ready_report())

    assert response.status_code == 200
    assert response.get_json()["closeout_action"] == "closeout_ready"


def test_zip_route_returns_application_zip():
    client = app_client()
    response = post_json(
        client,
        "/api/v1/dossier-builder/v3/intelligence/finalization/closeout-report/export.zip",
        {"report": closeout_ready_report(), "bundle_name": "Closeout Bundle"},
    )

    assert response.status_code == 200
    assert response.mimetype == "application/zip"
    assert "closeout-bundle.zip" in response.headers["Content-Disposition"]


def test_zip_route_contains_required_files():
    client = app_client()
    response = post_json(
        client,
        "/api/v1/dossier-builder/v3/intelligence/finalization/closeout-report/export.zip",
        {"report": closeout_ready_report()},
    )

    with zipfile.ZipFile(io.BytesIO(response.get_data())) as archive:
        assert set(archive.namelist()) == REQUIRED_FILES


def test_csrf_token_is_used_in_route_tests():
    client = app_client()
    response = post_json(client, "/api/v1/dossier-builder/v3/intelligence/finalization/closeout-report/export", {"report": closeout_ready_report()})

    assert response.status_code == 200


def test_no_connector_execution_function_is_called(monkeypatch):
    import socmint.dossier_finalization_closeout_export_bundle_v7_5_11 as bundle_module

    def explode(*_args, **_kwargs):
        raise AssertionError("connector execution must not happen")

    monkeypatch.setattr(bundle_module, "execute_connector", explode, raising=False)
    client = app_client()
    response = post_json(client, "/api/v1/dossier-builder/v3/intelligence/finalization/closeout-report/export", {"report": closeout_ready_report()})

    assert response.status_code == 200
    assert response.get_json()["closeout_action"] == "closeout_ready"
