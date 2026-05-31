from pathlib import Path

from socmint.dashboard import create_app
from socmint.export_manifest_ui_routes_v13 import register_export_manifest_ui_routes


def test_export_manifest_ui_route_registers_once():
    app = create_app()
    register_export_manifest_ui_routes(app)
    register_export_manifest_ui_routes(app)

    rules = {rule.rule for rule in app.url_map.iter_rules()}
    assert "/subjects/<int:subject_id>/export-manifest" in rules


def test_export_manifest_template_links_workflow():
    template = Path("src/socmint/templates/export_manifest.html").read_text()

    for expected in [
        "/command-center",
        "/subjects/{{ subject_id }}/dossier/readiness",
        "/subjects/{{ subject_id }}/claim-evidence-ledger",
        "/api/v1/subjects/{{ subject_id }}/export-manifest-draft",
    ]:
        assert expected in template
