from pathlib import Path


def test_full_dossier_template_has_artifact_cards_and_labels():
    template = Path("src/socmint/templates/entity_dossier_v2.html").read_text()

    for label in [
        "Download ZIP",
        "Download Manifest",
        "Open HTML",
        "View JSON",
        "View Markdown",
        "Download Markdown",
    ]:
        assert label in template

    assert "export-artifact-grid" in template
    assert "export-artifact-card" in template
    assert "latest_export.json_name" in template
    assert "latest_export.markdown_name" in template


def test_full_report_browser_has_styled_artifact_panel():
    source = Path("src/socmint/full_report_browser.py").read_text()

    for label in ["ZIP Bundle", "Manifest", "HTML Report", "JSON", "Markdown"]:
        assert label in source

    assert "runtime_visual.css" in source
    assert "export-artifact-card" in source
    assert "export-artifact-grid" in source
    assert "Download" in source
    assert "Open HTML" in source
    assert "View" in source


def test_full_report_history_is_styled_and_links_artifacts():
    source = Path("src/socmint/full_report_history.py").read_text()

    assert "runtime_visual.css" in source
    assert "Export Artifact Cards" in source
    for label in ["Download ZIP", "Download Manifest", "View Manifest", "Open HTML", "View JSON", "View Markdown"]:
        assert label in source


def test_v13_31_runtime_scripts_committed():
    acceptance = Path("scripts/runtime_acceptance_v13_31.sh").read_text()
    capture = Path("scripts/capture_runtime_pages_v13_31.py").read_text()

    assert "v13.31 runtime acceptance" in acceptance
    assert "export_full_entity_dossier_v2" in acceptance
    assert "full_report_export_history" in acceptance
    assert "sync_playwright" in capture
    assert "SOCMINT_CAPTURE_PASSWORD" in capture
