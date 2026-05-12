from __future__ import annotations

from flask import jsonify, session

from .operator_smoke import operator_smoke_matrix
from .operator_smoke import operator_smoke_summary
from .operator_smoke import validate_smoke_routes


def _admin_required() -> bool:
    return bool(session.get("user") and session.get("is_admin"))


def register_operator_smoke_routes(app):
    @app.get("/api/v1/admin/operator-smoke/matrix")
    def api_operator_smoke_matrix():
        if not _admin_required():
            return jsonify({"error": "admin required"}), 403
        return jsonify(operator_smoke_matrix())

    @app.get("/api/v1/admin/operator-smoke/summary")
    def api_operator_smoke_summary():
        if not _admin_required():
            return jsonify({"error": "admin required"}), 403
        return jsonify(operator_smoke_summary())

    @app.get("/api/v1/admin/operator-smoke/validate")
    def api_operator_smoke_validate():
        if not _admin_required():
            return jsonify({"error": "admin required"}), 403
        return jsonify(validate_smoke_routes(app))

    return app
