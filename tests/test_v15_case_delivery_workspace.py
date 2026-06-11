from __future__ import annotations

from pathlib import Path

from src.socmint.case_delivery_authorization_record_v15_5 import CASE_DELIVERY_AUTHORIZATION_RECORD_SCHEMA
from src.socmint.case_delivery_authorization_record_v15_5 import build_case_delivery_authorization_record
from src.socmint.case_delivery_execution_envelope_v15_6 import CASE_DELIVERY_EXECUTION_ENVELOPE_SCHEMA
from src.socmint.case_delivery_execution_envelope_v15_6 import build_case_delivery_execution_envelope
from src.socmint.case_delivery_attempt_ledger_v16_1 import CASE_DELIVERY_ATTEMPT_LEDGER_SCHEMA
from src.socmint.case_delivery_attempt_ledger_v16_1 import build_case_delivery_attempt_ledger
from src.socmint.case_delivery_operations_v16_0 import CASE_DELIVERY_OPERATIONS_SCHEMA
from src.socmint.case_delivery_operations_v16_0 import build_case_delivery_operations
from src.socmint.case_delivery_handoff_package_v15_1 import CASE_DELIVERY_HANDOFF_PACKAGE_SCHEMA
from src.socmint.case_delivery_handoff_package_v15_1 import build_case_delivery_handoff_package
from src.socmint.case_delivery_handoff_verification_v15_2 import CASE_DELIVERY_HANDOFF_VERIFICATION_SCHEMA
from src.socmint.case_delivery_handoff_verification_v15_2 import verify_case_delivery_handoff_package
from src.socmint.case_delivery_readiness_receipt_v15_3 import CASE_DELIVERY_READINESS_RECEIPT_SCHEMA
from src.socmint.case_delivery_readiness_receipt_v15_3 import build_case_delivery_readiness_receipt
from src.socmint.case_delivery_readiness_receipt_verification_v15_4 import (
    CASE_DELIVERY_READINESS_RECEIPT_VERIFICATION_SCHEMA,
)
from src.socmint.case_delivery_readiness_receipt_verification_v15_4 import (
    verify_case_delivery_readiness_receipt,
)
from src.socmint.case_delivery_workspace_routes_v15 import register_case_delivery_workspace_routes_v15
from src.socmint.case_delivery_workspace_v15 import CASE_DELIVERY_GATE_SCHEMA
from src.socmint.case_delivery_workspace_v15 import CASE_DELIVERY_WORKSPACE_SCHEMA
from src.socmint.case_delivery_workspace_v15 import build_case_delivery_workspace
from src.socmint.dashboard import create_app
from src.socmint.dossier_finalization_master_delivery_export_bundle_v7_5_14 import build_master_delivery_export_bundle
from src.socmint.dossier_finalization_master_delivery_index_v7_5_13 import build_master_delivery_index
from src.socmint.v10_24_final_delivery_workspace import build_final_delivery_workspace_from_bundle
from src.socmint.v10_25_final_delivery_operator_console import build_operator_console_from_workspace
from src.socmint.v10_26_final_delivery_audit_trail import build_final_delivery_audit_trail_from_console
from src.socmint.v10_27_final_delivery_evidence_capsule import build_final_delivery_evidence_capsule_from_audit_trail
from src.socmint.v10_28_final_delivery_capsule_export_pack import build_final_delivery_capsule_export_pack
from src.socmint.v10_29_final_delivery_dashboard_api import build_final_delivery_dashboard_api_from_pack


def verification_report(status: str = "verified") -> dict:
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
        "closeout_action": "closeout_ready" if status == "verified" else "regenerate_export",
        "verification_status": status,
        "failures": [],
        "warnings": [],
        "summary": {"status": status, "verified": status == "verified"},
    }


def dashboard(status: str = "verified") -> dict:
    index = build_master_delivery_index(verification_report(status), operator="analyst", notes="Ready.")
    bundle = build_master_delivery_export_bundle(index, bundle_name="V15 Case Delivery")
    workspace = build_final_delivery_workspace_from_bundle(bundle)
    console = build_operator_console_from_workspace(workspace)
    audit_trail = build_final_delivery_audit_trail_from_console(console)
    capsule = build_final_delivery_evidence_capsule_from_audit_trail(audit_trail)
    pack = build_final_delivery_capsule_export_pack(capsule)
    return build_final_delivery_dashboard_api_from_pack(pack)


def ready_payload(**overrides) -> dict:
    payload = {
        "dashboards": [dashboard()],
        "approval_decision": "approved",
        "readiness_input": {
            "subject_id": 101,
            "subject_exists": True,
            "seed_count": 2,
            "finding_count": 5,
            "report_count": 0,
            "pending_review_count": 0,
            "promoted_claim_without_evidence_count": 0,
            "hash_mismatch_count": 0,
            "unresolved_contradiction_count": 0,
        },
        "evidence_summary": {"complete": True, "finding_count": 5, "hash_mismatch_count": 0},
        "export_blockers": [],
    }
    payload.update(overrides)
    return payload


def test_case_delivery_workspace_ready_for_delivery():
    workspace = build_case_delivery_workspace("case-v15-ready", ready_payload())

    assert workspace["schema"] == CASE_DELIVERY_WORKSPACE_SCHEMA
    assert workspace["gate"]["schema"] == CASE_DELIVERY_GATE_SCHEMA
    assert workspace["gate"]["decision"] == "READY_FOR_DELIVERY"
    assert workspace["gate"]["status"] == "pass"
    assert workspace["gate"]["blocker_count"] == 0
    assert workspace["delivery_registry"]["delivery_count"] == 1
    assert workspace["approval_gate"]["decision"] == "approved"


def test_case_delivery_workspace_needs_human_approval_when_only_approval_blocks():
    workspace = build_case_delivery_workspace("case-v15-review", ready_payload(approval_decision="pending_review"))

    assert workspace["gate"]["decision"] == "NEEDS_HUMAN_APPROVAL"
    assert workspace["gate"]["blocker_count"] == 1
    assert workspace["gate"]["blockers"][0]["key"] == "human_approved"


def test_case_delivery_workspace_blocks_on_export_blockers():
    workspace = build_case_delivery_workspace(
        "case-v15-blocked",
        ready_payload(export_blockers=[{"key": "audit_coverage", "label": "Audit coverage missing"}]),
    )

    assert workspace["gate"]["decision"] == "BLOCKED"
    assert any(blocker["key"] == "export_clear" for blocker in workspace["gate"]["blockers"])
    assert workspace["export_blockers"][0]["key"] == "audit_coverage"


def test_case_delivery_workspace_blocks_without_subject_or_delivery():
    workspace = build_case_delivery_workspace("case-v15-empty", {})

    assert workspace["gate"]["decision"] == "BLOCKED"
    assert any(blocker["key"] == "dossier_ready" for blocker in workspace["gate"]["blockers"])
    assert any(blocker["key"] == "delivery_registered" for blocker in workspace["gate"]["blockers"])


def test_case_delivery_handoff_package_delivers_ready_case():
    package = build_case_delivery_handoff_package(
        "case-v15-handoff",
        ready_payload(operator="lead-analyst", notes="Ready for client handoff."),
        operator="lead-analyst",
        notes="Ready for client handoff.",
    )

    assert package["schema"] == CASE_DELIVERY_HANDOFF_PACKAGE_SCHEMA
    assert package["disposition"] == "deliver"
    assert package["gate_decision"] == "READY_FOR_DELIVERY"
    assert package["operator_receipt"]["accepted_for_delivery"] is True
    assert package["manifest"]["file_count"] == 5
    assert any(row["path"] == "delivery_gate.json" and row["sha256"] for row in package["files"])


def test_case_delivery_handoff_package_holds_blocked_case_with_remediation():
    package = build_case_delivery_handoff_package(
        "case-v15-hold",
        ready_payload(export_blockers=[{"key": "policy", "label": "Policy review missing"}]),
    )

    assert package["disposition"] == "hold"
    assert package["gate_decision"] == "BLOCKED"
    assert package["operator_receipt"]["accepted_for_delivery"] is False
    assert any(action["key"] == "export_clear" for action in package["remediation_actions"])


def test_case_delivery_handoff_verification_accepts_intact_package():
    package = build_case_delivery_handoff_package("case-v15-verify", ready_payload())
    verification = verify_case_delivery_handoff_package(package)

    assert verification["schema"] == CASE_DELIVERY_HANDOFF_VERIFICATION_SCHEMA
    assert verification["status"] == "verified"
    assert verification["verified"] is True
    assert verification["blocker_count"] == 0
    assert verification["gate_decision"] == "READY_FOR_DELIVERY"


def test_case_delivery_handoff_verification_blocks_tampered_manifest():
    package = build_case_delivery_handoff_package("case-v15-tamper", ready_payload())
    package["manifest"]["files"][0]["sha256"] = "tampered"
    verification = verify_case_delivery_handoff_package(package)

    assert verification["status"] == "blocked"
    assert verification["verified"] is False
    assert any(blocker["key"] == "manifest_mismatch" for blocker in verification["blockers"])


def test_case_delivery_readiness_receipt_issues_after_verified_package():
    package = build_case_delivery_handoff_package("case-v15-receipt", ready_payload(operator="operator"))
    result = build_case_delivery_readiness_receipt(package, issuer="release-lead")

    assert result["status"] == "issued"
    assert result["blocker_count"] == 0
    assert result["receipt"]["schema"] == CASE_DELIVERY_READINESS_RECEIPT_SCHEMA
    assert result["receipt"]["verified"] is True
    assert result["receipt"]["issued_by"] == "release-lead"
    assert result["receipt"]["signature_algorithm"] == "sha256-canonical-json"
    assert result["receipt"]["signature_sha256"]
    assert result["receipt"]["receipt_id"]


def test_case_delivery_readiness_receipt_blocks_tampered_package():
    package = build_case_delivery_handoff_package("case-v15-receipt-block", ready_payload())
    package["manifest"]["files"][0]["sha256"] = "tampered"
    result = build_case_delivery_readiness_receipt(package)

    assert result["status"] == "blocked"
    assert result["receipt"] is None
    assert result["blocker_count"] > 0
    assert any(blocker["key"] == "manifest_mismatch" for blocker in result["blockers"])


def test_case_delivery_readiness_receipt_verification_accepts_valid_receipt():
    package = build_case_delivery_handoff_package("case-v15-receipt-verify", ready_payload(operator="operator"))
    receipt_result = build_case_delivery_readiness_receipt(package, issuer="release-lead")
    verification = verify_case_delivery_readiness_receipt(receipt_result["receipt"], package)

    assert verification["schema"] == CASE_DELIVERY_READINESS_RECEIPT_VERIFICATION_SCHEMA
    assert verification["status"] == "verified"
    assert verification["verified"] is True
    assert verification["receipt_id"] == receipt_result["receipt"]["receipt_id"]


def test_case_delivery_readiness_receipt_verification_blocks_tampered_receipt():
    package = build_case_delivery_handoff_package("case-v15-receipt-tamper", ready_payload(operator="operator"))
    receipt_result = build_case_delivery_readiness_receipt(package, issuer="release-lead")
    receipt = dict(receipt_result["receipt"])
    receipt["issued_by"] = "tampered"
    verification = verify_case_delivery_readiness_receipt(receipt, package)

    assert verification["status"] == "blocked"
    assert verification["verified"] is False
    assert any(blocker["key"] == "payload_hash_mismatch" for blocker in verification["blockers"])


def test_case_delivery_authorization_record_authorizes_verified_chain():
    package = build_case_delivery_handoff_package("case-v15-auth", ready_payload(operator="operator"))
    receipt_result = build_case_delivery_readiness_receipt(package, issuer="release-lead")
    result = build_case_delivery_authorization_record(
        package,
        receipt_result["receipt"],
        authorizer="delivery-lead",
    )

    assert result["status"] == "authorized"
    assert result["authorized"] is True
    assert result["blocker_count"] == 0
    assert result["authorization"]["schema"] == CASE_DELIVERY_AUTHORIZATION_RECORD_SCHEMA
    assert result["authorization"]["authorized_by"] == "delivery-lead"
    assert result["authorization"]["authorization_id"]


def test_case_delivery_authorization_record_blocks_tampered_receipt():
    package = build_case_delivery_handoff_package("case-v15-auth-block", ready_payload(operator="operator"))
    receipt_result = build_case_delivery_readiness_receipt(package, issuer="release-lead")
    receipt = dict(receipt_result["receipt"])
    receipt["operator"] = "tampered"
    result = build_case_delivery_authorization_record(package, receipt)

    assert result["status"] == "blocked"
    assert result["authorized"] is False
    assert result["authorization"] is None
    assert any(blocker["key"] == "payload_hash_mismatch" for blocker in result["blockers"])


def test_case_delivery_execution_envelope_emits_after_authorization():
    package = build_case_delivery_handoff_package("case-v15-execute", ready_payload(operator="operator"))
    receipt_result = build_case_delivery_readiness_receipt(package, issuer="release-lead")
    authorization_result = build_case_delivery_authorization_record(
        package,
        receipt_result["receipt"],
        authorizer="delivery-lead",
    )
    result = build_case_delivery_execution_envelope(
        package,
        receipt_result["receipt"],
        authorization_result["authorization"],
        authorizer="delivery-lead",
    )

    assert result["status"] == "ready_to_execute"
    assert result["executable"] is True
    assert result["blocker_count"] == 0
    assert result["envelope"]["schema"] == CASE_DELIVERY_EXECUTION_ENVELOPE_SCHEMA
    assert result["envelope"]["authorization_id"] == authorization_result["authorization"]["authorization_id"]
    assert result["envelope"]["execution_id"]
    assert all(link["authorized"] is True for link in result["envelope"]["authorized_links"])


def test_case_delivery_execution_envelope_blocks_tampered_authorization():
    package = build_case_delivery_handoff_package("case-v15-execute-block", ready_payload(operator="operator"))
    receipt_result = build_case_delivery_readiness_receipt(package, issuer="release-lead")
    authorization_result = build_case_delivery_authorization_record(
        package,
        receipt_result["receipt"],
        authorizer="delivery-lead",
    )
    authorization = dict(authorization_result["authorization"])
    authorization["authorization_id"] = "tampered"
    result = build_case_delivery_execution_envelope(
        package,
        receipt_result["receipt"],
        authorization,
        authorizer="delivery-lead",
    )

    assert result["status"] == "blocked"
    assert result["executable"] is False
    assert result["envelope"] is None
    assert any(blocker["key"] == "authorization_id_mismatch" for blocker in result["blockers"])


def test_case_delivery_operations_snapshot_is_ready_from_execution_envelope():
    result = build_case_delivery_operations(
        "case-v16-ops",
        ready_payload(operator="operator", issuer="release-lead", authorizer="delivery-lead"),
    )

    assert result["schema"] == CASE_DELIVERY_OPERATIONS_SCHEMA
    assert result["state"] == "ready_for_dispatch"
    assert result["dispatchable"] is True
    assert result["blocker_count"] == 0
    assert result["execution_id"]
    assert result["operation_id"]
    assert result["next_action"] == "dispatch_delivery"


def test_case_delivery_operations_snapshot_tracks_dispatch_event():
    result = build_case_delivery_operations(
        "case-v16-dispatched",
        ready_payload(
            operator="operator",
            issuer="release-lead",
            authorizer="delivery-lead",
            events=[
                {
                    "type": "dispatch_confirmed",
                    "operator": "delivery-lead",
                    "detail": "Delivery handed off.",
                }
            ],
        ),
    )

    assert result["state"] == "dispatched"
    assert result["dispatchable"] is True
    assert result["event_count"] == 1
    assert result["events"][0]["event_id"]


def test_case_delivery_operations_snapshot_blocks_operator_exception():
    result = build_case_delivery_operations(
        "case-v16-blocked",
        ready_payload(
            operator="operator",
            issuer="release-lead",
            authorizer="delivery-lead",
            events=[
                {
                    "type": "exception",
                    "operator": "delivery-lead",
                    "detail": "Recipient channel unavailable.",
                }
            ],
        ),
    )

    assert result["state"] == "blocked"
    assert result["dispatchable"] is False
    assert result["blocker_count"] == 1
    assert any(blocker["key"] == "operator_exception" for blocker in result["blockers"])


def test_case_delivery_attempt_ledger_is_ready_without_attempts():
    result = build_case_delivery_attempt_ledger(
        "case-v16-ledger-ready",
        ready_payload(operator="operator", issuer="release-lead", authorizer="delivery-lead"),
    )

    assert result["schema"] == CASE_DELIVERY_ATTEMPT_LEDGER_SCHEMA
    assert result["state"] == "ready_for_attempt"
    assert result["retry_eligible"] is True
    assert result["attempt_count"] == 0
    assert result["ledger_id"]
    assert result["next_action"] == "record_delivery_attempt"


def test_case_delivery_attempt_ledger_marks_failed_attempt_retry_ready():
    result = build_case_delivery_attempt_ledger(
        "case-v16-ledger-retry",
        ready_payload(
            operator="operator",
            issuer="release-lead",
            authorizer="delivery-lead",
            attempts=[
                {
                    "channel": "secure_portal",
                    "status": "failed",
                    "operator": "delivery-lead",
                    "detail": "Recipient did not acknowledge.",
                }
            ],
        ),
    )

    assert result["state"] == "retry_ready"
    assert result["retry_eligible"] is True
    assert result["failure_count"] == 1
    assert result["latest_attempt_status"] == "failed"
    assert result["attempts"][0]["attempt_id"]


def test_case_delivery_attempt_ledger_marks_success_delivered():
    result = build_case_delivery_attempt_ledger(
        "case-v16-ledger-delivered",
        ready_payload(
            operator="operator",
            issuer="release-lead",
            authorizer="delivery-lead",
            attempts=[
                {
                    "channel": "secure_portal",
                    "status": "delivered",
                    "operator": "delivery-lead",
                    "detail": "Recipient acknowledged.",
                }
            ],
        ),
    )

    assert result["state"] == "delivered"
    assert result["retry_eligible"] is False
    assert result["success_count"] == 1
    assert result["latest_attempt_status"] == "delivered"


def test_case_delivery_attempt_ledger_blocks_when_operations_block():
    result = build_case_delivery_attempt_ledger(
        "case-v16-ledger-blocked",
        ready_payload(
            operator="operator",
            issuer="release-lead",
            authorizer="delivery-lead",
            events=[{"type": "exception", "operator": "delivery-lead", "detail": "Channel outage."}],
        ),
    )

    assert result["state"] == "blocked"
    assert result["retry_eligible"] is False
    assert any(blocker["key"] == "operations_blocked" for blocker in result["blockers"])


def test_case_delivery_workspace_routes_require_login(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    app = create_app()
    register_case_delivery_workspace_routes_v15(app)
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["_csrf_token"] = "test-csrf"

    assert client.get("/api/v1/case-delivery/case-1").status_code == 401
    assert (
        client.post(
            "/api/v1/case-delivery/case-1/handoff-package",
            headers={"X-CSRF-Token": "test-csrf"},
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/v1/case-delivery/case-1/handoff-package/verify",
            headers={"X-CSRF-Token": "test-csrf"},
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/v1/case-delivery/case-1/readiness-receipt",
            headers={"X-CSRF-Token": "test-csrf"},
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/v1/case-delivery/case-1/readiness-receipt/verify",
            headers={"X-CSRF-Token": "test-csrf"},
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/v1/case-delivery/case-1/authorization-record",
            headers={"X-CSRF-Token": "test-csrf"},
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/v1/case-delivery/case-1/execution-envelope",
            headers={"X-CSRF-Token": "test-csrf"},
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/v1/case-delivery/case-1/operations",
            headers={"X-CSRF-Token": "test-csrf"},
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/v1/case-delivery/case-1/attempt-ledger",
            headers={"X-CSRF-Token": "test-csrf"},
        ).status_code
        == 401
    )
    response = client.get("/case-delivery")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_case_delivery_workspace_routes_render_for_logged_in_user(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    app = create_app()
    register_case_delivery_workspace_routes_v15(app)
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["user"] = "operator"
        sess["is_admin"] = False
        sess["_csrf_token"] = "test-csrf"

    api_response = client.post(
        "/api/v1/case-delivery/case-1",
        json=ready_payload(),
        headers={"X-CSRF-Token": "test-csrf"},
    )
    package_response = client.post(
        "/api/v1/case-delivery/case-1/handoff-package",
        json=ready_payload(operator="operator"),
        headers={"X-CSRF-Token": "test-csrf"},
    )
    markdown_response = client.post(
        "/api/v1/case-delivery/case-1/handoff-package/markdown",
        json=ready_payload(operator="operator"),
        headers={"X-CSRF-Token": "test-csrf"},
    )
    verification_response = client.post(
        "/api/v1/case-delivery/case-1/handoff-package/verify",
        json=ready_payload(operator="operator"),
        headers={"X-CSRF-Token": "test-csrf"},
    )
    receipt_response = client.post(
        "/api/v1/case-delivery/case-1/readiness-receipt",
        json=ready_payload(operator="operator", issuer="release-lead"),
        headers={"X-CSRF-Token": "test-csrf"},
    )
    receipt_verify_response = client.post(
        "/api/v1/case-delivery/case-1/readiness-receipt/verify",
        json=ready_payload(operator="operator", issuer="release-lead"),
        headers={"X-CSRF-Token": "test-csrf"},
    )
    authorization_response = client.post(
        "/api/v1/case-delivery/case-1/authorization-record",
        json=ready_payload(operator="operator", issuer="release-lead", authorizer="delivery-lead"),
        headers={"X-CSRF-Token": "test-csrf"},
    )
    execution_response = client.post(
        "/api/v1/case-delivery/case-1/execution-envelope",
        json=ready_payload(operator="operator", issuer="release-lead", authorizer="delivery-lead"),
        headers={"X-CSRF-Token": "test-csrf"},
    )
    operations_response = client.post(
        "/api/v1/case-delivery/case-1/operations",
        json=ready_payload(operator="operator", issuer="release-lead", authorizer="delivery-lead"),
        headers={"X-CSRF-Token": "test-csrf"},
    )
    attempt_ledger_response = client.post(
        "/api/v1/case-delivery/case-1/attempt-ledger",
        json=ready_payload(operator="operator", issuer="release-lead", authorizer="delivery-lead"),
        headers={"X-CSRF-Token": "test-csrf"},
    )
    ui_response = client.get("/case-delivery?case_id=case-1")

    assert api_response.status_code == 200
    assert api_response.get_json()["gate"]["decision"] == "READY_FOR_DELIVERY"
    assert package_response.status_code == 200
    assert package_response.get_json()["disposition"] == "deliver"
    assert markdown_response.status_code == 200
    assert b"Case Delivery Handoff" in markdown_response.data
    assert verification_response.status_code == 200
    assert verification_response.get_json()["status"] == "verified"
    assert receipt_response.status_code == 200
    assert receipt_response.get_json()["status"] == "issued"
    assert receipt_response.get_json()["receipt"]["signature_sha256"]
    assert receipt_verify_response.status_code == 200
    assert receipt_verify_response.get_json()["status"] == "verified"
    assert authorization_response.status_code == 200
    assert authorization_response.get_json()["status"] == "authorized"
    assert authorization_response.get_json()["authorization"]["authorization_id"]
    assert execution_response.status_code == 200
    assert execution_response.get_json()["status"] == "ready_to_execute"
    assert execution_response.get_json()["envelope"]["execution_id"]
    assert operations_response.status_code == 200
    assert operations_response.get_json()["state"] == "ready_for_dispatch"
    assert operations_response.get_json()["operation_id"]
    assert attempt_ledger_response.status_code == 200
    assert attempt_ledger_response.get_json()["state"] == "ready_for_attempt"
    assert attempt_ledger_response.get_json()["ledger_id"]
    assert ui_response.status_code == 200
    assert b"Case Delivery Workspace" in ui_response.data
    assert b"handoff-package" in ui_response.data


def test_v15_release_note_and_changelog_are_present():
    note = Path("release/V15_0_CASE_DELIVERY_WORKSPACE.md").read_text(encoding="utf-8")
    handoff_note = Path("release/V15_1_CASE_DELIVERY_HANDOFF_PACKAGE.md").read_text(encoding="utf-8")
    verification_note = Path("release/V15_2_CASE_DELIVERY_HANDOFF_VERIFICATION.md").read_text(encoding="utf-8")
    receipt_note = Path("release/V15_3_DELIVERY_READINESS_RECEIPT.md").read_text(encoding="utf-8")
    receipt_verify_note = Path("release/V15_4_DELIVERY_READINESS_RECEIPT_VERIFICATION.md").read_text(encoding="utf-8")
    authorization_note = Path("release/V15_5_DELIVERY_AUTHORIZATION_RECORD.md").read_text(encoding="utf-8")
    execution_note = Path("release/V15_6_DELIVERY_EXECUTION_ENVELOPE.md").read_text(encoding="utf-8")
    operations_note = Path("release/V16_0_DELIVERY_OPERATIONS_SNAPSHOT.md").read_text(encoding="utf-8")
    attempt_ledger_note = Path("release/V16_1_DELIVERY_ATTEMPT_LEDGER.md").read_text(encoding="utf-8")
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")

    assert "/api/v1/case-delivery/<case_id>" in note
    assert "/api/v1/case-delivery/<case_id>/handoff-package" in handoff_note
    assert "/api/v1/case-delivery/<case_id>/handoff-package/verify" in verification_note
    assert "/api/v1/case-delivery/<case_id>/readiness-receipt" in receipt_note
    assert "/api/v1/case-delivery/<case_id>/readiness-receipt/verify" in receipt_verify_note
    assert "/api/v1/case-delivery/<case_id>/authorization-record" in authorization_note
    assert "/api/v1/case-delivery/<case_id>/execution-envelope" in execution_note
    assert "/api/v1/case-delivery/<case_id>/operations" in operations_note
    assert "/api/v1/case-delivery/<case_id>/attempt-ledger" in attempt_ledger_note
    assert "v15.0 Case Delivery Workspace" in changelog
    assert "v15.1 Case Delivery Handoff Package" in changelog
    assert "v15.2 Case Delivery Handoff Verification" in changelog
    assert "v15.3 Delivery Readiness Receipt" in changelog
    assert "v15.4 Delivery Readiness Receipt Verification" in changelog
    assert "v15.5 Delivery Authorization Record" in changelog
    assert "v15.6 Delivery Execution Envelope" in changelog
    assert "v16.0 Delivery Operations Snapshot" in changelog
    assert "v16.1 Delivery Attempt Ledger" in changelog
