from socmint.dashboard import create_app
from socmint.normalization_review_update_routes_v13 import (
    register_normalization_review_update_routes,
)


def test_normalization_review_update_route_registers_once():
    app = create_app()
    register_normalization_review_update_routes(app)
    register_normalization_review_update_routes(app)

    rules = {rule.rule for rule in app.url_map.iter_rules()}
    assert "/api/v1/review/normalization-update" in rules
