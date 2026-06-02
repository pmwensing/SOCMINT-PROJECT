from pathlib import Path


def test_full_dossier_has_operator_status_banner_and_review_map():
    template = Path("src/socmint/templates/entity_dossier_v2.html").read_text()

    assert "operator-status-banner" in template
    assert "Operator Status" in template
    assert "Dossier generated" in template
    assert "Latest export" in template
    assert "Artifact count" in template
    assert "Review state" in template
    assert "Dossier Review Map" in template
    assert "Section summaries" in template


def test_full_dossier_replaces_raw_record_table_with_collapsible_record_cards():
    template = Path("src/socmint/templates/entity_dossier_v2.html").read_text()

    assert "dossier-record-card" in template
    assert "dossier-record-grid" in template
    assert "View raw JSON" in template
    assert "Showing first 25 records" in template
    assert "Expand all records" in template
    assert "Collapse all records" in template
    assert "Expand section" in template
    assert "Collapse section" in template
    assert "<td><pre>{{ item | tojson(indent=2) }}</pre></td>" not in template


def test_full_dossier_section_summaries_include_core_sections():
    template = Path("src/socmint/templates/entity_dossier_v2.html").read_text()

    for label in [
        "identity_summary",
        "identity_graph",
        "dossier_assertions",
        "observations",
        "connector_diagnostics",
        "review_decisions",
        "linked_evidence",
        "custody_hash_status",
    ]:
        assert label in template or "payload.sections.items()" in template


def test_runtime_visual_has_record_card_styles():
    css = Path("src/socmint/static/runtime_visual.css").read_text()

    for selector in [
        ".operator-status-banner",
        ".section-header-row",
        ".dossier-record-grid",
        ".dossier-record-card",
        ".dossier-record-card-static",
        ".record-raw-json",
    ]:
        assert selector in css
