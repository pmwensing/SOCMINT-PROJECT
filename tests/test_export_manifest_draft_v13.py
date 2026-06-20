from socmint.dashboard import create_app
from socmint.export_manifest_draft_routes_v13 import (
    register_export_manifest_draft_routes,
)
from socmint.export_manifest_draft_v13 import manifest_entry


def test_export_manifest_entry_shape():
    entry = manifest_entry("readiness", "api", "blocked", "/api/test", "detail")

    assert entry == {
        "name": "readiness",
        "kind": "api",
        "status": "blocked",
        "ref": "/api/test",
        "detail": "detail",
    }


def test_export_manifest_draft_route_registers_once():
    app = create_app()
    register_export_manifest_draft_routes(app)
    register_export_manifest_draft_routes(app)

    rules = {rule.rule for rule in app.url_map.iter_rules()}
    assert "/api/v1/subjects/<int:subject_id>/export-manifest-draft" in rules
