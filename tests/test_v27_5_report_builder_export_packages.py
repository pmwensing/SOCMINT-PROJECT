from src.socmint.report_builder_events_v27_5 import create_report_definition, revise_report_definition
from src.socmint.report_export_packages_v27_5 import generate_report_package


def test_v27_5_create_revise_and_generate_package(tmp_path, monkeypatch):
    from src.socmint import database
    from src.socmint import report_export_packages_v27_5 as exports
    database.configure_database(f"sqlite:///{tmp_path / 'app.db'}")
    sections = [{"section_type":"saved_view","title":"Findings","source_id":"view-1"},{"section_type":"text","title":"Notes","text":"Analyst summary"}]
    created = create_report_definition(name="Case Report", owner="alice", description="report", visibility="private", sections=sections, export_formats=["json","csv","html"], confirmed=True)
    assert created["status"] == "report_definition_created"
    revised = revise_report_definition(created["report_id"], actor="alice", name="Case Report v2", description="updated", visibility="shared", sections=sections, export_formats=["json","html"], reason="update", confirmed=True)
    assert revised["status"] == "report_definition_revised"
    assert revised["revision"] == 2
    assert revised["prior_report_mutated"] is False
    monkeypatch.setattr(exports, "find_report", lambda report_id, user: {**revised, "report_status":"active"})
    resolved = [
        {"status":"ready","source":{"saved_view_id":"view-1"},"summary":{"result_count":1,"access_scope":{"allowed_case_ids":["case-a"]}},"results":[{"result_id":"r1","record_type":"finding","case_id":"case-a","title":"Finding","summary":"Summary"}]},
        {"status":"text","text":"Analyst summary","results":[]},
    ]
    result = generate_report_package(revised["report_id"], user_identity="alice", allowed_case_ids={"case-a"}, formats=["json","csv","html"], confirmed=True, resolved_sections=resolved)
    assert result["status"] == "report_package_generated"
    assert result["result_count"] == 1
    assert result["section_count"] == 2
    assert {item["format"] for item in result["files"]} == {"json","csv","html"}
    assert all(len(item["sha256"]) == 64 for item in result["files"])
    assert len(result["package_sha256"]) == 64
    assert result["report_grants_access"] is False
    assert result["case_access_scope_changed"] is False


def test_v27_5_requires_valid_sections_and_confirmation(tmp_path):
    from src.socmint import database
    database.configure_database(f"sqlite:///{tmp_path / 'blocked.db'}")
    result = create_report_definition(name="Bad", owner="alice", description="", visibility="private", sections=[], export_formats=["json"], confirmed=True)
    assert result["status"] == "blocked"
    result = create_report_definition(name="Bad", owner="alice", description="", visibility="private", sections=[{"section_type":"text","title":"T","text":"x"}], export_formats=["json"], confirmed=False)
    assert result["status"] == "blocked"
