from __future__ import annotations

from flask import jsonify, request

from .v10_30_case_delivery_registry import build_case_delivery_registry_from_request
from .v10_30_case_delivery_registry import build_case_delivery_summaries_from_request
from .v10_30_case_delivery_registry import get_case_delivery_from_request


def _request_payload() -> dict:
    payload = request.get_json(silent=True) or {}
    return payload if isinstance(payload, dict) else {}


def register_v10_30_case_delivery_registry_routes(app):
    @app.post("/api/v1/v10/final-delivery/cases/<case_id>/registry")
    def api_v10_case_delivery_registry(case_id: str):
        return jsonify(build_case_delivery_registry_from_request(case_id, _request_payload()))

    @app.post("/api/v1/v10/final-delivery/cases/<case_id>/registry/summaries")
    def api_v10_case_delivery_registry_summaries(case_id: str):
        return jsonify({"summaries": build_case_delivery_summaries_from_request(case_id, _request_payload())})

    @app.post("/api/v1/v10/final-delivery/cases/<case_id>/registry/delivery")
    def api_v10_case_delivery_registry_delivery(case_id: str):
        delivery = get_case_delivery_from_request(case_id, _request_payload())
        if delivery is None:
            return jsonify({"delivery": None, "found": False}), 404
        return jsonify({"delivery": delivery, "found": True})

    return app
