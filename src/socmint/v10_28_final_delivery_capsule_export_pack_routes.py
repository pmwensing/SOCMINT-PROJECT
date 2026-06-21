from __future__ import annotations

import base64

from flask import Response, jsonify, request

from .v10_28_final_delivery_capsule_export_pack import (
    build_final_delivery_capsule_export_pack_files,
)
from .v10_28_final_delivery_capsule_export_pack import (
    build_final_delivery_capsule_export_pack_from_request,
)
from .v10_28_final_delivery_capsule_export_pack import (
    build_final_delivery_capsule_export_zip,
)
from .v10_28_final_delivery_capsule_export_pack import (
    build_final_delivery_capsule_export_zip_from_request,
)


def _request_payload() -> dict:
    payload = request.get_json(silent=True) or {}
    return payload if isinstance(payload, dict) else {}


def _json_response_payload(pack: dict) -> dict:
    files = build_final_delivery_capsule_export_pack_files(pack)
    zip_bytes = build_final_delivery_capsule_export_zip(pack)
    return {
        **pack,
        "text_files": {path: data.decode("utf-8") for path, data in files.items()},
        "zip_base64": base64.b64encode(zip_bytes).decode("ascii"),
        "zip_size_bytes": len(zip_bytes),
    }


def register_v10_28_final_delivery_capsule_export_pack_routes(app):
    @app.post("/api/v1/v10/final-delivery/evidence-capsule/export")
    def api_v10_final_delivery_capsule_export():
        pack = build_final_delivery_capsule_export_pack_from_request(_request_payload())
        return jsonify(_json_response_payload(pack))

    @app.post("/api/v1/v10/final-delivery/evidence-capsule/export.zip")
    def api_v10_final_delivery_capsule_export_zip():
        zip_bytes = build_final_delivery_capsule_export_zip_from_request(
            _request_payload()
        )
        return Response(zip_bytes, mimetype="application/zip")

    return app
