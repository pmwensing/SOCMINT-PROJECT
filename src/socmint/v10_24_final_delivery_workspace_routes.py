from __future__ import annotations

from flask import Response, jsonify, request

from .v10_24_final_delivery_workspace import build_final_delivery_export_zip_from_request
from .v10_24_final_delivery_workspace import build_final_delivery_workspace_from_request


def _request_payload() -> dict:
    payload = request.get_json(silent=True) or {}
    return payload if isinstance(payload, dict) else {}


def register_v10_24_final_delivery_workspace_routes(app):
    @app.post("/api/v1/v10/final-delivery/workspace")
    def api_v10_final_delivery_workspace():
        return jsonify(build_final_delivery_workspace_from_request(_request_payload()))

    @app.post("/api/v1/v10/final-delivery/export.zip")
    def api_v10_final_delivery_export_zip():
        zip_bytes = build_final_delivery_export_zip_from_request(_request_payload())
        return Response(zip_bytes, mimetype="application/zip")

    return app
