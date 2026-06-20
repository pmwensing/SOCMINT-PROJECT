from __future__ import annotations

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
from socmint.v10_25_final_delivery_operator_console_routes import (
    register_v10_25_final_delivery_operator_console_routes,
)


def app_client():
    app = Flask(__name__)
    register_v10_25_final_delivery_operator_console_routes(app)
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


def workspace():
    bundle = build_master_delivery_export_bundle(
        delivery_index(), bundle_name="Route Console"
    )
    return build_final_delivery_workspace_from_bundle(bundle)


def test_console_route_accepts_workspace_shape():
    client = app_client()
    response = client.post(
        "/api/v1/v10/final-delivery/console", json={"workspace": workspace()}
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["schema"] == "socmint.v10_25.final_delivery_operator_console"
    assert data["readiness"] == "ready"
    assert data["delivery_action"] == "deliver_ready"
    assert data["package_ready"] is True


def test_console_route_accepts_index_shape():
    client = app_client()
    response = client.post(
        "/api/v1/v10/final-delivery/console",
        json={"index": delivery_index(), "bundle_name": "Route Index Console"},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["readiness"] == "ready"
    assert data["workspace"]["bundle_name"] == "route-index-console"


def test_commands_route_returns_command_list():
    client = app_client()
    response = client.post(
        "/api/v1/v10/final-delivery/commands", json={"workspace": workspace()}
    )

    assert response.status_code == 200
    data = response.get_json()
    assert "commands" in data
    assert {command["id"] for command in data["commands"]} >= {
        "review_final_package",
        "export_zip",
        "record_delivery",
    }


def test_export_command_is_enabled_for_ready_route_console():
    client = app_client()
    response = client.post(
        "/api/v1/v10/final-delivery/commands", json={"workspace": workspace()}
    )

    commands = response.get_json()["commands"]
    assert (
        next(command for command in commands if command["id"] == "export_zip")[
            "enabled"
        ]
        is True
    )


def test_no_connector_execution_function_is_called(monkeypatch):
    import socmint.v10_25_final_delivery_operator_console as console_module

    def explode(*_args, **_kwargs):
        raise AssertionError("connector execution must not happen")

    monkeypatch.setattr(console_module, "execute_connector", explode, raising=False)
    client = app_client()
    response = client.post(
        "/api/v1/v10/final-delivery/console", json={"index": delivery_index()}
    )

    assert response.status_code == 200
    assert response.get_json()["readiness"] == "ready"
