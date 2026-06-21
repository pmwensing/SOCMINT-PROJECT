from __future__ import annotations

from copy import deepcopy

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
    build_operator_commands_from_request,
)
from socmint.v10_25_final_delivery_operator_console import (
    build_operator_console_from_request,
)
from socmint.v10_25_final_delivery_operator_console import (
    build_operator_console_from_workspace,
)
from socmint.v10_25_final_delivery_operator_console import readiness_for_workspace

REQUIRED_CARD_TYPES = {
    "delivery_readiness",
    "package_inventory",
    "findings",
    "export_availability",
    "operator_next_action",
}


def verification_report(status="verified"):
    return {
        "schema": "socmint.v7_5_12.dossier_finalization_closeout_export_verification",
        "status": status,
        "verified": status == "verified",
        "failure_count": 1 if status == "failed" else 0,
        "warning_count": 1 if status == "needs_human_review" else 0,
        "required_files": ["README.md", "closeout_report.json"],
        "present_files": ["README.md", "closeout_report.json"],
        "missing_files": [],
        "unexpected_files": [],
        "manifest": {"file_count": 5, "files": []},
        "closeout_action": "closeout_ready"
        if status == "verified"
        else "regenerate_export",
        "verification_status": status,
        "failures": [
            {
                "severity": "fail",
                "code": "failed_export",
                "path": "master_delivery_index.json",
                "detail": "Export failed.",
                "action": "Regenerate export.",
            }
        ]
        if status == "failed"
        else [],
        "warnings": [
            {
                "severity": "warn",
                "code": "review_required",
                "path": "master_delivery_index.json",
                "detail": "Review required.",
                "action": "Review package.",
            }
        ]
        if status == "needs_human_review"
        else [],
        "summary": {"status": status, "verified": status == "verified"},
    }


def delivery_index(status="verified"):
    return build_master_delivery_index(
        verification_report(status), operator="analyst", notes="Ready."
    )


def workspace(status="verified"):
    bundle = build_master_delivery_export_bundle(
        delivery_index(status), bundle_name="Console Package"
    )
    return build_final_delivery_workspace_from_bundle(bundle)


def test_builds_ready_console_from_deliver_ready_workspace():
    console = build_operator_console_from_workspace(workspace())

    assert console["schema"] == "socmint.v10_25.final_delivery_operator_console"
    assert console["version"] == "v10.25.0"
    assert console["readiness"] == "ready"
    assert console["delivery_action"] == "deliver_ready"
    assert console["package_ready"] is True
    assert "export_zip" in console["allowed_actions"]
    assert console["blocked_actions"] == []


def test_builds_review_required_console_from_human_review_workspace():
    console = build_operator_console_from_workspace(workspace("needs_human_review"))

    assert console["readiness"] == "review_required"
    assert console["delivery_action"] == "human_review_required"
    assert "review_findings" in console["allowed_actions"]
    assert "record_delivery" in console["blocked_actions"]


def test_builds_blocked_console_from_regenerate_workspace():
    console = build_operator_console_from_workspace(workspace("failed"))

    assert console["readiness"] == "blocked"
    assert console["delivery_action"] == "regenerate_export"
    assert "regenerate_v7_5_14_package" in console["allowed_actions"]
    assert "export_zip" in console["blocked_actions"]


def test_cards_include_all_required_card_types():
    console = build_operator_console_from_workspace(workspace())

    assert {card["type"] for card in console["cards"]} == REQUIRED_CARD_TYPES


def test_export_command_enabled_only_when_ready():
    ready_commands = build_operator_console_from_workspace(workspace())["commands"]
    review_commands = build_operator_console_from_workspace(
        workspace("needs_human_review")
    )["commands"]
    blocked_commands = build_operator_console_from_workspace(workspace("failed"))[
        "commands"
    ]

    assert (
        next(command for command in ready_commands if command["id"] == "export_zip")[
            "enabled"
        ]
        is True
    )
    assert (
        next(command for command in review_commands if command["id"] == "export_zip")[
            "enabled"
        ]
        is False
    )
    assert (
        next(command for command in blocked_commands if command["id"] == "export_zip")[
            "enabled"
        ]
        is False
    )


def test_readiness_mapping_respects_package_ready_false():
    data = workspace()
    data["package_ready"] = False

    assert readiness_for_workspace(data) == "blocked"


def test_builds_console_from_request_workspace_shape():
    payload = {"workspace": workspace()}
    console = build_operator_console_from_request(payload)

    assert console["readiness"] == "ready"
    assert console["workspace"]["bundle_name"] == "console-package"


def test_builds_console_from_request_index_shape():
    console = build_operator_console_from_request(
        {"index": delivery_index(), "bundle_name": "Index Shape"}
    )

    assert console["readiness"] == "ready"
    assert console["workspace"]["bundle_name"] == "index-shape"


def test_commands_from_request_returns_command_list():
    commands = build_operator_commands_from_request({"workspace": workspace()})

    assert isinstance(commands, list)
    assert {command["id"] for command in commands} >= {
        "review_final_package",
        "export_zip",
        "record_delivery",
    }


def test_input_payload_is_not_mutated():
    payload = {"workspace": workspace()}
    original = deepcopy(payload)

    build_operator_console_from_request(payload)

    assert payload == original


def test_no_connector_execution_function_is_called(monkeypatch):
    import socmint.v10_25_final_delivery_operator_console as console_module

    def explode(*_args, **_kwargs):
        raise AssertionError("connector execution must not happen")

    monkeypatch.setattr(console_module, "execute_connector", explode, raising=False)

    console = build_operator_console_from_request({"index": delivery_index()})

    assert console["readiness"] == "ready"
