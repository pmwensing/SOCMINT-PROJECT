from pathlib import Path


def test_full_report_history_ui_endpoint_alias_registered_in_source():
    source = Path("src/socmint/full_report_history.py").read_text()

    assert 'endpoint="ui_full_report_history"' in source
    assert '"/spine/subjects/<int:subject_id>/full-report/history"' in source


def test_full_dossier_template_references_registered_history_endpoint():
    template = Path("src/socmint/templates/entity_dossier_v2.html").read_text()
    assert "'ui_full_report_history'" in template
