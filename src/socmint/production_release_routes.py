from __future__ import annotations

from flask import jsonify, session

from .hardening_routes import register_hardening_routes
from .production_release import production_release_check
from .production_release import production_release_summary


def register_production_release_routes(app):
    register_hardening_routes(app)

    @app.get("/api/v1/production-release")
    def api_production_release():
        username = session.get("user")
        return jsonify(production_release_check(username=username))

    @app.get("/api/v1/production-release/summary")
    def api_production_release_summary():
        return jsonify(production_release_summary())

    return app
