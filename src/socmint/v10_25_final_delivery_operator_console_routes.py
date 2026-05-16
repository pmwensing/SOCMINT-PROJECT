from __future__ import annotations

from flask import jsonify, request

from .v10_25_final_delivery_operator_console import build_operator_commands_from_request
from .v10_25_final_delivery_operator_console import build_operator_console_from_request


def _request_payload() -> dict:
    payload = request.get_json(silent=True) or {}
    return payload if isinstance(payload, dict) else {}


def register_v10_25_final_delivery_operator_console_routes(app):
    @app.post("/api/v1/v10/final-delivery/console")
    def api_v10_final_delivery_console():
        return jsonify(build_operator_console_from_request(_request_payload()))

    @app.post("/api/v1/v10/final-delivery/commands")
    def api_v10_final_delivery_commands():
        return jsonify({"commands": build_operator_commands_from_request(_request_payload())})

    return app
