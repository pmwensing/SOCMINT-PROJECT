from __future__ import annotations

from flask import Response, jsonify, request

from .dossier_finalization_certificate_bundle_v7_5_5 import build_certificate_bundle
from .dossier_finalization_certificate_bundle_v7_5_5 import build_certificate_bundle_zip
from .dossier_finalization_certificate_bundle_v7_5_5 import safe_bundle_name


def _request_payload() -> dict:
    payload = request.get_json(silent=True) or {}
    return payload if isinstance(payload, dict) else {}


def _unwrap_certificate(payload: dict) -> tuple[dict, str | None]:
    if isinstance(payload.get("certificate"), dict):
        return payload.get("certificate") or {}, payload.get("bundle_name")
    return payload, payload.get("bundle_name")


def register_dossier_finalization_certificate_bundle_routes(app):
    @app.post("/api/v1/dossier-builder/v3/intelligence/finalization/certificate/bundle")
    def api_finalization_certificate_bundle():
        payload = _request_payload()
        certificate, bundle_name = _unwrap_certificate(payload)
        return jsonify(build_certificate_bundle(certificate, bundle_name=bundle_name))

    @app.post(
        "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/bundle.zip"
    )
    def api_finalization_certificate_bundle_zip():
        payload = _request_payload()
        certificate, bundle_name = _unwrap_certificate(payload)
        bundle = build_certificate_bundle(certificate, bundle_name=bundle_name)
        zip_bytes = build_certificate_bundle_zip(bundle)
        filename = f"{safe_bundle_name(bundle.get('bundle_name'))}.zip"
        return Response(
            zip_bytes,
            mimetype="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    return app
