from socmint.dashboard import create_app
from socmint.handoff_status_routes_v13 import register_handoff_status_routes
from socmint.handoff_status_v13 import row


def test_handoff_status_row_shape():
    item = row("readiness", "pass", "draft_ready")

    assert item == {"name": "readiness", "status": "pass", "detail": "draft_ready"}


def test_handoff_status_route_registers_once():
    app = create_app()
    register_handoff_status_routes(app)
    register_handoff_status_routes(app)

    rules = {rule.rule for rule in app.url_map.iter_rules()}
    assert "/api/v1/subjects/<int:subject_id>/handoff-status" in rules
