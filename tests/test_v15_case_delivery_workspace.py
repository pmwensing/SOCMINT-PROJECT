from __future__ import annotations

from pathlib import Path

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


def test_case_delivery_workspace_routes_require_login(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    app = create_app()
    register_case_delivery_workspace_routes_v15(app)
    client = app.test_client()

    assert client.get("/api/v1/case-delivery/case-1").status_code == 401
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
    ui_response = client.get("/case-delivery?case_id=case-1")

    assert api_response.status_code == 200
    assert api_response.get_json()["gate"]["decision"] == "READY_FOR_DELIVERY"
    assert ui_response.status_code == 200
    assert b"Case Delivery Workspace" in ui_response.data


def test_v15_release_note_and_changelog_are_present():
    note = Path("release/V15_0_CASE_DELIVERY_WORKSPACE.md").read_text(encoding="utf-8")
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")

    assert "/api/v1/case-delivery/<case_id>" in note
    assert "v15.0 Case Delivery Workspace" in changelog
