from __future__ import annotations

import base64

from flask import Response, jsonify, request

from .dossier_finalization_master_delivery_export_bundle_v7_5_14 import build_master_delivery_export_bundle
from .dossier_finalization_master_delivery_export_bundle_v7_5_14 import build_master_delivery_export_bundle_files
from .dossier_finalization_master_delivery_export_bundle_v7_5_14 import build_master_delivery_export_zip


def _request_payload() -> dict:
    payload = request.get_json(silent=True) or {}
    return payload if isinstance(payload, dict) else {}


def _unwrap_index(payload: dict) -> dict:
    if isinstance(payload.get("index"), dict):
        return payload.get("index") or {}
    return payload


def _json_route_payload(bundle: dict) -> dict:
    files = build_master_delivery_export_bundle_files(bundle)
    zip_bytes = build_master_delivery_export_zip(bundle)
    return {
        **bundle,
        "text_files": {path: data.decode("utf-8") for path, data in files.items()},
        "zip_base64": base64.b64encode(zip_bytes).decode("ascii"),
        "zip_size_bytes": len(zip_bytes),
    }


def register_dossier_finalization_master_delivery_export_bundle_routes(app):
    @app.post("/api/v1/dossier-builder/v3/intelligence/finalization/master-delivery-index/export")
    def api_master_delivery_index_export():
        payload = _request_payload()
        index = _unwrap_index(payload)
        bundle = build_master_delivery_export_bundle(index, bundle_name=payload.get("bundle_name"))
        return jsonify(_json_route_payload(bundle))

    @app.post("/api/v1/dossier-builder/v3/intelligence/finalization/master-delivery-index/export.zip")
    def api_master_delivery_index_export_zip():
        payload = _request_payload()
        index = _unwrap_index(payload)
        bundle = build_master_delivery_export_bundle(index, bundle_name=payload.get("bundle_name"))
        zip_bytes = build_master_delivery_export_zip(bundle)
        return Response(zip_bytes, mimetype="application/zip")

    return app
