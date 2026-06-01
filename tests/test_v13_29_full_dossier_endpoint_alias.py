def test_full_report_history_ui_endpoint_alias_registered():
    from socmint.dashboard import app

    assert "ui_full_report_history" in app.view_functions
    with app.test_request_context():
        url = app.url_for("ui_full_report_history", subject_id=4)
    assert url == "/spine/subjects/4/full-report/history"


def test_full_dossier_template_references_registered_history_endpoint():
    from pathlib import Path

    template = Path("src/socmint/templates/entity_dossier_v2.html").read_text()
    assert "'ui_full_report_history'" in template
