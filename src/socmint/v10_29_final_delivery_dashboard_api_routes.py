from __future__ import annotations

from flask import jsonify, request

from .v10_29_final_delivery_dashboard_api import build_final_delivery_dashboard_actions_from_request
from .v10_29_final_delivery_dashboard_api import build_final_delivery_dashboard_api_from_request


def _request_payload() -> dict:
    payload = request.get_json(silent=True) or {}
    return payload if isinstance(payload, dict) else {}


def register_v10_29_final_delivery_dashboard_api_routes(app):
    @app.post("/api/v1/v10/final-delivery/dashboard")
    def api_v10_final_delivery_dashboard():
        return jsonify(build_final_delivery_dashboard_api_from_request(_request_payload()))

    @app.post("/api/v1/v10/final-delivery/dashboard/actions")
    def api_v10_final_delivery_dashboard_actions():
        return jsonify({"api_actions": build_final_delivery_dashboard_actions_from_request(_request_payload())})

    return app
