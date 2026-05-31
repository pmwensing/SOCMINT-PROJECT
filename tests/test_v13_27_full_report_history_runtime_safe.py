from pathlib import Path

from socmint import full_report_history


def test_full_report_export_history_handles_unwritable_dossier_root(monkeypatch):
    def raise_permission_error() -> Path:
        raise PermissionError("blocked dossier root")

    monkeypatch.setattr(full_report_history, "dossier_root", raise_permission_error)

    payload = full_report_history.full_report_export_history(subject_id=123)

    assert payload["subject_id"] == 123
    assert payload["count"] == 0
    assert payload["exports"] == []
    assert payload["available"] is False
    assert "blocked dossier root" in payload["error"]
