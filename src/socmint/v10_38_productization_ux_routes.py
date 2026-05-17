from __future__ import annotations

from flask import Flask, jsonify, request

from .v10_38_productization_ux_layer import ProductizationUXV1038


class _DictCaseRegistry:
    def __init__(self, registry: dict):
        self.registry = registry or {}

    def get_case(self, case_id: str) -> dict:
        cases = self.registry.get("cases") if isinstance(self.registry, dict) else None
        if isinstance(cases, dict) and isinstance(cases.get(case_id), dict):
            return cases[case_id]
        if isinstance(self.registry, dict) and any(
            key in self.registry for key in {"status", "deliveries", "operator_hints"}
        ):
            return self.registry
        return {}


def _request_payload() -> dict:
    payload = request.get_json(silent=True) or {}
    return payload if isinstance(payload, dict) else {}


def register_v10_38_productization_ux_routes(app: Flask) -> Flask:
    @app.post("/api/v10.38/productization/cases/<case_id>/summary")
    def productization_summary_v10_38(case_id: str):
        payload = _request_payload()
        ux = ProductizationUXV1038(_DictCaseRegistry(payload.get("registry", {})))
        return jsonify(ux.enhanced_summary(case_id))

    @app.post("/api/v10.38/productization/cases/<case_id>/ui")
    def productization_ui_v10_38(case_id: str):
        payload = _request_payload()
        ux = ProductizationUXV1038(_DictCaseRegistry(payload.get("registry", {})))
        return jsonify(ux.ui_polish(case_id))

    return app
