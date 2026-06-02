from pathlib import Path


def test_full_dossier_template_has_export_artifact_ux():
    template = Path("src/socmint/templates/entity_dossier_v2.html").read_text()

    assert "Latest Full Report Export" in template
    assert "export-artifact-grid" in template
    assert "export-artifact-card" in template
    assert "latest_export.zip_name" in template
    assert "latest_export.manifest_name" in template
    assert "latest_export.html_name" in template
    assert "latest_export.json_name" in template
    assert "latest_export.markdown_name" in template


def test_full_report_pages_use_runtime_visual_artifact_classes():
    browser = Path("src/socmint/full_report_browser.py").read_text()
    history = Path("src/socmint/full_report_history.py").read_text()
    css = Path("src/socmint/static/runtime_visual.css").read_text()

    for source in [browser, history]:
        assert "runtime_visual.css" in source
        assert "export-artifact-card" in source
        assert "export-artifact-grid" in source

    assert ".export-artifact-card" in css
    assert ".export-artifact-grid" in css
    assert ".export-artifact-actions" in css
    assert ".export-artifact-primary" in css


def test_v13_31_runtime_scripts_committed():
    acceptance = Path("scripts/runtime_acceptance_v13_31.sh").read_text()
    capture = Path("scripts/capture_runtime_pages_v13_31.py").read_text()

    assert "v13.31 runtime acceptance" in acceptance
    assert "export_full_entity_dossier_v2" in acceptance
    assert "full_report_export_history" in acceptance
    assert "SOCMINT_CAPTURE_PASSWORD" in capture
    assert "runtime_screenshots_v13_31" in capture
