from __future__ import annotations

import base64

from flask import jsonify, request

from .dossier_finalization_handoff_export_verify_v7_5_9 import _base_report
from .dossier_finalization_handoff_export_verify_v7_5_9 import _finding
from .dossier_finalization_handoff_export_verify_v7_5_9 import summarize_handoff_export_verification
from .dossier_finalization_handoff_export_verify_v7_5_9 import verify_handoff_export_bundle
from .dossier_finalization_handoff_export_verify_v7_5_9 import verify_handoff_export_zip


def _request_payload() -> dict:
    payload = request.get_json(silent=True) or {}
    return payload if isinstance(payload, dict) else {}


def _failed_base64_report(detail: str) -> dict:
    report = _base_report({})
    report["failures"] = [_finding("fail", "invalid_zip", detail)]
    report["failure_count"] = 1
    report["summary"] = summarize_handoff_export_verification(report)
    return report


def register_dossier_finalization_handoff_export_verify_routes(app):
    @app.post("/api/v1/dossier-builder/v3/intelligence/finalization/certificate/handoff-index/export/verify")
    def api_verify_handoff_export_bundle():
        payload = _request_payload()
        bundle = payload.get("bundle") if isinstance(payload.get("bundle"), dict) else payload
        return jsonify(verify_handoff_export_bundle(bundle))

    @app.post("/api/v1/dossier-builder/v3/intelligence/finalization/certificate/handoff-index/export/verify-zip")
    def api_verify_handoff_export_zip():
        payload = _request_payload()
        encoded = payload.get("zip_base64")
        if not isinstance(encoded, str) or not encoded.strip():
            return jsonify(_failed_base64_report("zip_base64 is missing or empty."))
        try:
            zip_bytes = base64.b64decode(encoded, validate=True)
        except Exception:
            return jsonify(_failed_base64_report("zip_base64 is invalid base64."))
        return jsonify(verify_handoff_export_zip(zip_bytes))

    return app
