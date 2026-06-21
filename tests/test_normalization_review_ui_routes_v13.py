from socmint.dashboard import create_app
from socmint.normalization_review_ui_routes_v13 import (
    register_normalization_review_ui_routes,
)


def test_normalization_review_ui_route_registers_once():
    app = create_app()
    register_normalization_review_ui_routes(app)
    register_normalization_review_ui_routes(app)

    rules = {rule.rule for rule in app.url_map.iter_rules()}
    assert "/review/normalization-queue" in rules
