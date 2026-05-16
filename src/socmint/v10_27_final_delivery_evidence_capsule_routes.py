from __future__ import annotations

from flask import jsonify, request

from .v10_27_final_delivery_evidence_capsule import build_final_delivery_evidence_capsule_from_request
from .v10_27_final_delivery_evidence_capsule import build_final_delivery_evidence_capsule_summary_from_request


def _request_payload() -> dict:
    payload = request.get_json(silent=True) or {}
    return payload if isinstance(payload, dict) else {}


def register_v10_27_final_delivery_evidence_capsule_routes(app):
    @app.post("/api/v1/v10/final-delivery/evidence-capsule")
    def api_v10_final_delivery_evidence_capsule():
        return jsonify(build_final_delivery_evidence_capsule_from_request(_request_payload()))

    @app.post("/api/v1/v10/final-delivery/evidence-capsule/summary")
    def api_v10_final_delivery_evidence_capsule_summary():
        return jsonify(build_final_delivery_evidence_capsule_summary_from_request(_request_payload()))

    return app
