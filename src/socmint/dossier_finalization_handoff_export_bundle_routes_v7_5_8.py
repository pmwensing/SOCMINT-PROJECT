from __future__ import annotations

from flask import Response, jsonify, request

from .dossier_finalization_handoff_export_bundle_v7_5_8 import (
    build_handoff_export_bundle,
)
from .dossier_finalization_handoff_export_bundle_v7_5_8 import build_handoff_export_zip
from .dossier_finalization_handoff_export_bundle_v7_5_8 import safe_handoff_bundle_name


def _request_payload() -> dict:
    payload = request.get_json(silent=True) or {}
    return payload if isinstance(payload, dict) else {}


def _unwrap_index(payload: dict) -> tuple[dict, str | None]:
    if isinstance(payload.get("index"), dict):
        return payload.get("index") or {}, payload.get("bundle_name")
    return payload, payload.get("bundle_name")


def register_dossier_finalization_handoff_export_bundle_routes(app):
    @app.post(
        "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/handoff-index/export"
    )
    def api_handoff_index_export_bundle():
        payload = _request_payload()
        index, bundle_name = _unwrap_index(payload)
        return jsonify(build_handoff_export_bundle(index, bundle_name=bundle_name))

    @app.post(
        "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/handoff-index/export.zip"
    )
    def api_handoff_index_export_bundle_zip():
        payload = _request_payload()
        index, bundle_name = _unwrap_index(payload)
        bundle = build_handoff_export_bundle(index, bundle_name=bundle_name)
        zip_bytes = build_handoff_export_zip(bundle)
        filename = f"{safe_handoff_bundle_name(bundle.get('bundle_name'))}.zip"
        return Response(
            zip_bytes,
            mimetype="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    return app
