from __future__ import annotations

from .hardening_routes import register_hardening_routes


def register_all(app):
    register_hardening_routes(app)
    return app
