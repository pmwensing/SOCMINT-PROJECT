from __future__ import annotations

from flask import jsonify, request

from .v10_31_human_approval_gate import build_human_approval_gate_from_request
from .v10_31_human_approval_gate import build_human_approval_summary_from_request


def _request_payload() -> dict:
    payload = request.get_json(silent=True) or {}
    return payload if isinstance(payload, dict) else {}


def register_v10_31_human_approval_gate_routes(app):
    @app.post("/api/v1/v10/final-delivery/cases/<case_id>/approval-gate")
    def api_v10_human_approval_gate(case_id: str):
        gate = build_human_approval_gate_from_request(case_id, _request_payload())
        if not gate.get("found"):
            return jsonify(gate), 404
        return jsonify(gate)

    @app.post("/api/v1/v10/final-delivery/cases/<case_id>/approval-gate/summary")
    def api_v10_human_approval_gate_summary(case_id: str):
        summary = build_human_approval_summary_from_request(case_id, _request_payload())
        if not summary.get("found"):
            return jsonify(summary), 404
        return jsonify(summary)

    return app
