from socmint.dashboard import create_app
from socmint.dossier_readiness_ui_routes_v13 import register_dossier_readiness_ui_routes


def test_dossier_readiness_ui_route_registers_once():
    app = create_app()
    register_dossier_readiness_ui_routes(app)
    register_dossier_readiness_ui_routes(app)

    rules = {rule.rule for rule in app.url_map.iter_rules()}
    assert "/subjects/<int:subject_id>/dossier/readiness" in rules
