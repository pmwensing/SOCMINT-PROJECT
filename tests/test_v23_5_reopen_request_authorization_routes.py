from pathlib import Path


def test_v23_5_assets_and_no_migration():
    note = Path("release/V23_5_REOPEN_CONTROLS.md").read_text(encoding="utf-8")
    script = Path("src/socmint/static/case_closure_workspace_v23_0.js").read_text(encoding="utf-8")
    template = Path("src/socmint/templates/case_closure_workspace_v23_0.html").read_text(encoding="utf-8")
    migrations = [
        path
        for directory in (Path("migrations"), Path("alembic"))
        if directory.exists()
        for path in directory.rglob("*v23_5*")
    ]
    assert "existing archive package" in note
    assert "separate reopen request" in note
    assert "supervisor approval or denial" in note
    assert "archive package ID and hash" in note
    assert "closed case and archive records unchanged" in note
    assert "record-reopen-request" in script
    assert "record-reopen-authorization" in script
    assert "Reopen Request and Authorization" in template
    assert migrations == []
