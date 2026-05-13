from src.socmint.dossier_export_audit import audit_event
from src.socmint.dossier_export_audit import audit_index
from src.socmint.dossier_export_audit import audit_summary
from src.socmint.dossier_export_audit import read_audit_events
from src.socmint.wsgi import app


def test_v10_7_audit_event_writes_jsonl(tmp_path):
    event = audit_event(
        action="export_created",
        case_id="case-audit-107",
        subject_id="subject-audit-107",
        actor="tester",
        detail={"artifact_count": 2},
        root=tmp_path,
    )
    events = read_audit_events("case-audit-107", "subject-audit-107", root=tmp_path)

    assert event["schema"] == "socmint.dossier_export_audit.v10_7_0"
    assert event["action"] == "export_created"
    assert len(events) == 1
    assert events[0]["actor"] == "tester"


def test_v10_7_audit_summary_counts_actions(tmp_path):
    audit_event("export_created", "case-audit-107", "subject-audit-107", root=tmp_path)
    audit_event("manifest_read", "case-audit-107", "subject-audit-107", root=tmp_path)
    audit_event("manifest_read", "case-audit-107", "subject-audit-107", root=tmp_path)

    summary = audit_summary("case-audit-107", "subject-audit-107", root=tmp_path)

    assert summary["schema"] == "socmint.dossier_export_audit.v10_7_0"
    assert summary["event_count"] == 3
    assert summary["counts"]["export_created"] == 1
    assert summary["counts"]["manifest_read"] == 2


def test_v10_7_unknown_action_is_normalized(tmp_path):
    event = audit_event("unexpected_action", "case-audit-107", "subject-audit-107", root=tmp_path)

    assert event["action"] == "download_blocked"


def test_v10_7_audit_index_lists_audit_files(tmp_path):
    audit_event("export_created", "case-audit-107", "subject-audit-107", root=tmp_path)
    index = audit_index(root=tmp_path)

    assert index["schema"] == "socmint.dossier_export_audit.v10_7_0"
    assert index["status"] == "ready"
    assert index["entry_count"] == 1
    assert index["entries"][0]["event_count"] == 1


def test_v10_7_audit_routes_are_registered():
    routes = {rule.rule for rule in app.url_map.iter_rules()}

    assert "/api/v1/dossier-builder/v3/export-audit" in routes
    assert "/api/v1/dossier-builder/v3/export-audit/<case_id>/<subject_id>" in routes
    assert "/api/v1/dossier-builder/v3/export-audit/<case_id>/<subject_id>/summary" in routes
    assert "/api/v1/dossier-builder/v3/export-audit/<case_id>/<subject_id>/event" in routes
