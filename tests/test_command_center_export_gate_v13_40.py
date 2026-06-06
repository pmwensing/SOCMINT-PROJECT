from src.socmint.command_center import command_center_payload
from src.socmint.export_blocker_demo_v13_40 import create_export_blocker_demo


def test_command_center_summary_includes_export_blocker_counts(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    create_export_blocker_demo()

    payload = command_center_payload()

    assert payload["summary"]["export_count"] == 2
    assert payload["summary"]["export_allowed_count"] == 1
    assert payload["summary"]["export_blocker_count"] == 1
    assert payload["export_gate"]["blocked_exports"][0]["href"].startswith("/dossier/export-blockers")
