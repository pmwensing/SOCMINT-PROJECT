from __future__ import annotations

from .connector_administration_routes_v28_5 import register_connector_administration_routes_v28_5


def register_integration_admin_routes_v28_5(app):
    register_connector_administration_routes_v28_5(app)
    return app
