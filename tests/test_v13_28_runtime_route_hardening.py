from pathlib import Path

from socmint import full_report_alias


def test_latest_full_report_export_handles_unwritable_dossier_root(monkeypatch):
    def raise_permission_error() -> Path:
        raise PermissionError("blocked dossier root")

    monkeypatch.setattr(full_report_alias, "dossier_root", raise_permission_error)

    payload = full_report_alias.latest_full_report_export(subject_id=123)

    assert payload["subject_id"] == 123
    assert payload["available"] is False
    assert payload["latest"] is None
    assert "blocked dossier root" in payload["error"]


def test_normalization_review_queue_template_uses_items_key():
    template = Path("src/socmint/templates/normalization_review_queue.html").read_text()

    assert "{% for item in payload['items'] %}" in template
    assert "{% for item in payload.items %}" not in template
