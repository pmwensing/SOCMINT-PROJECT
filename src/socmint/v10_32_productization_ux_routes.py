from __future__ import annotations

from flask import Flask, jsonify, request
from .v10_32_productization_ux_layer import ProductizationUX


def _request_payload() -> dict:
    payload = request.get_json(silent=True) or {}
    return payload if isinstance(payload, dict) else {}


def register_v10_32_productization_ux_routes(app: Flask) -> Flask:
    @app.post('/api/v1/v10/productization/cases/<case_id>/summary')
    def productization_summary(case_id: str):
        payload = _request_payload()
        registry = payload.get('registry', {})
        ux = ProductizationUX(case_id, registry)
        return jsonify(ux.enhanced_summary())

    @app.post('/api/v1/v10/productization/cases/<case_id>/ui')
    def productization_ui(case_id: str):
        payload = _request_payload()
        registry = payload.get('registry', {})
        ux = ProductizationUX(case_id, registry)
        return jsonify(ux.ui_polish())

    return app
