import pytest

from socmint.dashboard import create_app
from socmint.normalization_promote_confirmed_routes_v13 import (
    register_normalization_promote_confirmed_routes,
)
from socmint.normalization_promote_confirmed_v13 import promote_confirmed_item


def test_promote_confirmed_invalid_kind_raises():
    with pytest.raises(ValueError):
        promote_confirmed_item("bad", 1)


def test_promote_confirmed_route_registers_once():
    app = create_app()
    register_normalization_promote_confirmed_routes(app)
    register_normalization_promote_confirmed_routes(app)

    rules = {rule.rule for rule in app.url_map.iter_rules()}
    assert "/api/v1/review/normalization-promote" in rules
