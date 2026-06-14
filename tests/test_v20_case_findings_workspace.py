from __future__ import annotations

from pathlib import Path

from src.socmint import database
from src.socmint.case_findings_routes_v20 import register_case_findings_routes_v20
from src.socmint.case_findings_v20 import (
    DOSSIER_PACKAGE_SCHEMA,
    FINDING_WORKSPACE_SCHEMA,
    build_dossier_promotion_package,
    build_v20_product_checkpoint,
    decide_finding,
    list_findings,
    propose_finding,
    revise_finding,
)
from src.socmint.dashboard import create_app


def _configure(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'app.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    database.configure_database(url)


def _app(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    app = create_app()
    register_case_findings_routes_v20(app)
    return app


def _proposal(case_id="case-alpha"):
    return propose_finding(
        case_id,
        {
            "text": "The subject controlled the reviewed account.",
            "confidence": "high",
            "claim_ids": ["claim-2", "claim-1"],
            "evidence_ids": ["evidence-1", "evidence-2"],
            "entity_ids": ["entity-1"],
            "timeline_refs": ["timeline-1"],
            "note": "supported by reviewed evidence",
        },
        actor="analyst",
    )


def test_v20_0_workspace_and_v20_1_claim_promotion(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    result = _proposal()
    workspace = list_findings("case-alpha")

    assert result["status"] == "proposed"
    assert workspace["schema"] == FINDING_WORKSPACE_SCHEMA
    assert workspace["counts"]["proposed"] == 1
    assert workspace["findings"][0]["text"].startswith("The subject")


def test_v20_2_provenance_is_sorted_hashed_and_confidence_preserved(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    result = _proposal()

    assert result["provenance"]["claim_ids"] == ["claim-1", "claim-2"]
    assert result["provenance"]["evidence_ids"] == ["evidence-1", "evidence-2"]
    assert len(result["provenance_sha256"]) == 64
    assert result["confidence"] == "high"


def test_v20_3_supervisor_approval_and_rejection(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    first = _proposal()
    approved = decide_finding(
        "case-alpha", first["finding_id"], "approve", actor="supervisor"
    )
    second = propose_finding(
        "case-alpha",
        {
            "text": "A second reviewed finding.",
            "confidence": "medium",
            "claim_ids": ["claim-3"],
            "evidence_ids": ["evidence-3"],
        },
        actor="analyst",
    )
    rejected = decide_finding(
        "case-alpha", second["finding_id"], "reject", actor="supervisor", note="weak"
    )

    assert approved["status"] == "approved"
    assert rejected["status"] == "rejected"
    assert list_findings("case-alpha")["counts"]["approved"] == 1


def test_v20_4_return_and_revision_history(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    proposal = _proposal()
    returned = decide_finding(
        "case-alpha",
        proposal["finding_id"],
        "return_to_analyst",
        actor="supervisor",
        note="clarify timeline",
    )
    revised = revise_finding(
        "case-alpha",
        proposal["finding_id"],
        {"text": "Revised account-control finding.", "confidence": "medium"},
        actor="analyst",
    )
    workspace = list_findings("case-alpha")

    assert returned["status"] == "revision_required"
    assert revised["status"] == "proposed"
    assert len(workspace["history"][proposal["finding_id"]]) >= 3
    assert workspace["findings"][0]["text"] == "Revised account-control finding."


def test_v20_5_dossier_package_is_deterministic_and_promotable(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    proposal = _proposal()
    decide_finding("case-alpha", proposal["finding_id"], "approve", actor="supervisor")

    first = build_dossier_promotion_package("case-alpha", actor="supervisor")
    second = build_dossier_promotion_package("case-alpha", actor="supervisor")
    promoted = build_dossier_promotion_package(
        "case-alpha", actor="supervisor", promote=True
    )

    assert first["schema"] == DOSSIER_PACKAGE_SCHEMA
    assert first["package_id"] == second["package_id"]
    assert first["manifest_sha256"] == second["manifest_sha256"]
    assert first["finding_count"] == 1
    assert promoted["status"] == "promoted"
    assert list_findings("case-alpha")["counts"]["promoted"] == 1


def test_v20_6_history_is_immutable_audit_projection(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    proposal = _proposal()
    decide_finding("case-alpha", proposal["finding_id"], "approve", actor="supervisor")
    build_dossier_promotion_package("case-alpha", actor="supervisor", promote=True)

    workspace = list_findings("case-alpha")
    events = workspace["history"][proposal["finding_id"]]

    assert [event["event"] for event in events] == ["proposed", "approve", "promoted"]
    assert all(event["event_record_id"] for event in events)
    assert all(event["event_actor"] for event in events)


def test_v20_routes_ui_and_authentication(tmp_path, monkeypatch):
    client = _app(tmp_path, monkeypatch).test_client()
    assert client.get("/api/v1/case-findings/case-alpha").status_code == 401
    assert client.get("/case-findings/case-alpha").status_code == 302

    with client.session_transaction() as sess:
        sess["user"] = "analyst"
        sess["_csrf_token"] = "test-csrf"
    proposal = client.post(
        "/api/v1/case-findings/case-alpha/proposals",
        json={
            "text": "Reviewed finding",
            "claim_ids": ["claim-1"],
            "evidence_ids": ["evidence-1"],
            "confidence": "high",
        },
        headers={"X-CSRF-Token": "test-csrf"},
    )
    ui = client.get("/case-findings/case-alpha")

    assert proposal.status_code == 200
    assert ui.status_code == 200
    assert b"Case Findings Workspace" in ui.data
    assert b"Promote reviewed claims to finding" in ui.data
    assert b"Dossier Promotion" in ui.data


def test_v20_7_product_checkpoint_release_notes_and_no_migration(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    result = build_v20_product_checkpoint(routes=list(app.url_map.iter_rules()))
    migration_matches = [
        path
        for directory in (Path("migrations"), Path("alembic"))
        if directory.exists()
        for path in directory.rglob("*v20*")
    ]

    assert result["ready"] is True
    assert result["status"] == "ready_for_browser_validation"
    for index in range(8):
        assert list(Path("release").glob(f"V20_{index}_*.md"))
    assert migration_matches == []
