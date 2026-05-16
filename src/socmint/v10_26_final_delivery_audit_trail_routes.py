from __future__ import annotations

from flask import jsonify, request

from .v10_26_final_delivery_audit_trail import build_final_delivery_audit_receipt_from_request
from .v10_26_final_delivery_audit_trail import build_final_delivery_audit_trail_from_request


def _request_payload() -> dict:
    payload = request.get_json(silent=True) or {}
    return payload if isinstance(payload, dict) else {}


def register_v10_26_final_delivery_audit_trail_routes(app):
    @app.post("/api/v1/v10/final-delivery/audit-trail")
    def api_v10_final_delivery_audit_trail():
        return jsonify(build_final_delivery_audit_trail_from_request(_request_payload()))

    @app.post("/api/v1/v10/final-delivery/audit-receipt")
    def api_v10_final_delivery_audit_receipt():
        return jsonify(build_final_delivery_audit_receipt_from_request(_request_payload()))

    return app
