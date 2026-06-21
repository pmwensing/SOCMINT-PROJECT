from __future__ import annotations

import base64

from socmint.dashboard import create_app
from socmint.dossier_finalization_certificate_handoff_index_v7_5_7 import (
    build_handoff_index,
)
from socmint.dossier_finalization_closeout_report_routes_v7_5_10 import (
    register_dossier_finalization_closeout_report_routes,
)
from socmint.dossier_finalization_handoff_export_bundle_v7_5_8 import (
    build_handoff_export_bundle,
)
from socmint.dossier_finalization_handoff_export_bundle_v7_5_8 import (
    build_handoff_export_zip,
)
from socmint.dossier_finalization_handoff_export_verify_v7_5_9 import (
    verify_handoff_export_bundle,
)

CSRF_TOKEN = "test-csrf-token"
CSRF_HEADERS = {"X-CSRF-Token": CSRF_TOKEN}


def v756_report():
    return {
        "schema": "socmint.v7_5_6.dossier_finalization_certificate_bundle_verification",
        "status": "verified",
        "verified": True,
        "failure_count": 0,
        "warning_count": 0,
        "certificate_status": "valid",
        "certificate_valid": True,
        "required_files": ["handoff_index.json", "manifest.json"],
        "present_files": ["handoff_index.json", "manifest.json"],
        "missing_files": [],
        "unexpected_files": [],
        "manifest": {
            "files": [
                {
                    "path": "handoff_index.json",
                    "content_type": "application/json",
                    "size_bytes": 123,
                    "sha256": "a" * 64,
                }
            ]
        },
        "file_results": [
            {"path": "handoff_index.json", "hash_match": True, "size_match": True}
        ],
        "failures": [],
        "warnings": [],
        "summary": {"status": "verified", "verified": True},
    }


def handoff_export_bundle():
    index = build_handoff_index(
        v756_report(), bundle_name="bundle-a", operator="analyst"
    )
    return build_handoff_export_bundle(index, bundle_name="closeout-source")


def verified_report():
    return verify_handoff_export_bundle(handoff_export_bundle())


def app_client():
    app = create_app()
    register_dossier_finalization_closeout_report_routes(app)
    client = app.test_client()
    with client.session_transaction() as session:
        session["_csrf_token"] = CSRF_TOKEN
    return client


def post_json(client, path, payload):
    return client.post(path, json=payload, headers=CSRF_HEADERS)


def test_json_route_returns_closeout_ready_report_from_wrapped_verification_report():
    client = app_client()
    response = post_json(
        client,
        "/api/v1/dossier-builder/v3/intelligence/finalization/closeout-report",
        {
            "verification_report": verified_report(),
            "operator": "analyst",
            "notes": "Ready.",
        },
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["schema"] == "socmint.v7_5_10.dossier_finalization_closeout_report"
    assert data["closeout_action"] == "closeout_ready"
    assert data["operator"] == "analyst"


def test_raw_verification_report_request_shape_works():
    client = app_client()
    response = post_json(
        client,
        "/api/v1/dossier-builder/v3/intelligence/finalization/closeout-report",
        verified_report(),
    )

    assert response.status_code == 200
    assert response.get_json()["closeout_action"] == "closeout_ready"


def test_markdown_route_returns_closeout_markdown():
    client = app_client()
    response = post_json(
        client,
        "/api/v1/dossier-builder/v3/intelligence/finalization/closeout-report/markdown",
        {"verification_report": verified_report(), "notes": "Ready."},
    )

    assert response.status_code == 200
    assert response.mimetype == "text/markdown"
    text = response.get_data(as_text=True)
    assert "# SOCMINT v7.5.10 Finalization Chain Closeout Report" in text
    assert "Closeout action: CLOSEOUT READY" in text


def test_zip_route_returns_closeout_ready_report_for_valid_base64_zip():
    zip_bytes = build_handoff_export_zip(handoff_export_bundle())
    encoded = base64.b64encode(zip_bytes).decode("ascii")
    client = app_client()
    response = post_json(
        client,
        "/api/v1/dossier-builder/v3/intelligence/finalization/closeout-report/from-zip",
        {"zip_base64": encoded, "operator": "analyst"},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["closeout_action"] == "closeout_ready"
    assert data["operator"] == "analyst"


def test_invalid_base64_returns_regenerate_export_report_not_500():
    client = app_client()
    response = post_json(
        client,
        "/api/v1/dossier-builder/v3/intelligence/finalization/closeout-report/from-zip",
        {"zip_base64": "not base64!!!"},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["closeout_action"] == "regenerate_export"
    assert data["verification_status"] == "failed"


def test_csrf_token_is_used_in_route_tests():
    client = app_client()
    response = post_json(
        client,
        "/api/v1/dossier-builder/v3/intelligence/finalization/closeout-report",
        {"verification_report": verified_report()},
    )

    assert response.status_code == 200


def test_no_connector_execution_function_is_called(monkeypatch):
    import socmint.dossier_finalization_closeout_report_v7_5_10 as closeout_module

    def explode(*_args, **_kwargs):
        raise AssertionError("connector execution must not happen")

    monkeypatch.setattr(closeout_module, "execute_connector", explode, raising=False)
    client = app_client()
    response = post_json(
        client,
        "/api/v1/dossier-builder/v3/intelligence/finalization/closeout-report",
        {"verification_report": verified_report()},
    )

    assert response.status_code == 200
    assert response.get_json()["closeout_action"] == "closeout_ready"
