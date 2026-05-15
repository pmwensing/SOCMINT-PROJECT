from __future__ import annotations

import base64

from flask import Flask

from socmint.dossier_finalization_closeout_export_bundle_v7_5_11 import build_closeout_export_bundle
from socmint.dossier_finalization_closeout_export_bundle_v7_5_11 import build_closeout_export_zip
from socmint.dossier_finalization_closeout_export_verify_routes_v7_5_12 import register_dossier_finalization_closeout_export_verify_routes
from socmint.dossier_finalization_closeout_report_v7_5_10 import build_closeout_report


def app_client():
    app = Flask(__name__)
    register_dossier_finalization_closeout_export_verify_routes(app)
    return app.test_client()


def verified_verification_report():
    return {
        "schema": "socmint.v7_5_9.dossier_finalization_handoff_export_verification",
        "status": "verified",
        "verified": True,
        "failure_count": 0,
        "warning_count": 0,
        "recommended_action": "archive_and_deliver",
        "verification_status": "verified",
        "certificate_status": "valid",
        "missing_files": [],
        "unexpected_files": [],
        "failures": [],
        "warnings": [],
        "summary": {"status": "verified", "verified": True},
    }


def closeout_bundle():
    closeout = build_closeout_report(verified_verification_report(), operator="analyst")
    return build_closeout_export_bundle(closeout, bundle_name="route-closeout-export")


def test_verify_closeout_export_bundle_route():
    client = app_client()

    response = client.post(
        "/api/v1/dossier-builder/v3/intelligence/finalization/closeout-report/export/verify",
        json={"bundle": closeout_bundle()},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["schema"] == "socmint.v7_5_12.dossier_finalization_closeout_export_verification"
    assert payload["status"] == "verified"
    assert payload["verified"] is True


def test_verify_closeout_export_zip_route():
    client = app_client()
    encoded = base64.b64encode(build_closeout_export_zip(closeout_bundle())).decode("ascii")

    response = client.post(
        "/api/v1/dossier-builder/v3/intelligence/finalization/closeout-report/export/verify-zip",
        json={"zip_base64": encoded},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "verified"
    assert payload["verified"] is True


def test_verify_closeout_export_zip_route_rejects_missing_base64():
    client = app_client()

    response = client.post(
        "/api/v1/dossier-builder/v3/intelligence/finalization/closeout-report/export/verify-zip",
        json={},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "failed"
    assert payload["failure_count"] == 1
    assert payload["failures"][0]["code"] == "invalid_zip"


def test_verify_closeout_export_zip_route_rejects_invalid_base64():
    client = app_client()

    response = client.post(
        "/api/v1/dossier-builder/v3/intelligence/finalization/closeout-report/export/verify-zip",
        json={"zip_base64": "not valid base64"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "failed"
    assert payload["failure_count"] == 1
    assert payload["failures"][0]["code"] == "invalid_zip"
