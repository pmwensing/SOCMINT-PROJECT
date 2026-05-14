from __future__ import annotations

import base64

from flask import Response, jsonify, request

from .dossier_finalization_certificate_bundle_verify_routes_v7_5_6 import _failed_base64_report
from .dossier_finalization_certificate_handoff_index_v7_5_7 import build_handoff_index
from .dossier_finalization_certificate_handoff_index_v7_5_7 import build_handoff_index_from_zip_bytes
from .dossier_finalization_certificate_handoff_index_v7_5_7 import render_handoff_index_markdown


def _request_payload() -> dict:
    payload = request.get_json(silent=True) or {}
    return payload if isinstance(payload, dict) else {}


def _unwrap_report(payload: dict) -> tuple[dict, str | None, str | None, str | None]:
    if isinstance(payload.get("verification_report"), dict):
        return payload.get("verification_report") or {}, payload.get("bundle_name"), payload.get("operator"), payload.get("notes")
    return payload, payload.get("bundle_name"), payload.get("operator"), payload.get("notes")


def _zip_index_from_payload(payload: dict) -> dict:
    encoded = payload.get("zip_base64")
    bundle_name = payload.get("bundle_name")
    operator = payload.get("operator")
    notes = payload.get("notes")
    if not isinstance(encoded, str) or not encoded.strip():
        return build_handoff_index(_failed_base64_report("zip_base64 is missing or empty."), bundle_name=bundle_name, operator=operator, notes=notes)
    try:
        zip_bytes = base64.b64decode(encoded, validate=True)
    except Exception:
        return build_handoff_index(_failed_base64_report("zip_base64 is invalid base64."), bundle_name=bundle_name, operator=operator, notes=notes)
    return build_handoff_index_from_zip_bytes(zip_bytes, bundle_name=bundle_name, operator=operator, notes=notes)


def register_dossier_finalization_certificate_handoff_index_routes(app):
    @app.post("/api/v1/dossier-builder/v3/intelligence/finalization/certificate/handoff-index")
    def api_certificate_handoff_index():
        payload = _request_payload()
        report, bundle_name, operator, notes = _unwrap_report(payload)
        return jsonify(build_handoff_index(report, bundle_name=bundle_name, operator=operator, notes=notes))

    @app.post("/api/v1/dossier-builder/v3/intelligence/finalization/certificate/handoff-index/markdown")
    def api_certificate_handoff_index_markdown():
        payload = _request_payload()
        report, bundle_name, operator, notes = _unwrap_report(payload)
        index = build_handoff_index(report, bundle_name=bundle_name, operator=operator, notes=notes)
        return Response(render_handoff_index_markdown(index), mimetype="text/markdown")

    @app.post("/api/v1/dossier-builder/v3/intelligence/finalization/certificate/handoff-index/from-zip")
    def api_certificate_handoff_index_from_zip():
        return jsonify(_zip_index_from_payload(_request_payload()))

    return app
