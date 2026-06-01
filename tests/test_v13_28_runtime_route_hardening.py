from pathlib import Path

from jinja2 import DictLoader

from socmint import full_report_alias
from socmint import full_report_history
from socmint.dashboard import app


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
    template = app.jinja_env.get_template("normalization_review_queue.html")

    rendered = template.render(
        payload={
            "count": 1,
            "state_counts": {"unreviewed": 1},
            "items": [
                {
                    "kind": "finding",
                    "review_state": "unreviewed",
                    "type": "profile_url",
                    "value": "https://example.test/profile",
                    "subject_id": 4,
                    "confidence": 0.9,
                    "source": "runtime-test",
                    "evidence_ref": "sha256:test",
                    "id": "finding:1",
                }
            ],
        },
        review_state="unreviewed",
        min_confidence=None,
    )

    assert "https://example.test/profile" in rendered
    assert "finding · unreviewed" in rendered
