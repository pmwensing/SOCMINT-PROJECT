from __future__ import annotations

import base64

from flask import jsonify, request

from .dossier_finalization_export_verify_v7_5_3 import _base_report
from .dossier_finalization_export_verify_v7_5_3 import _finding
from .dossier_finalization_export_verify_v7_5_3 import summarize_verification
from .dossier_finalization_export_verify_v7_5_3 import verify_finalization_export_packet
from .dossier_finalization_export_verify_v7_5_3 import verify_finalization_export_zip


def _request_payload() -> dict:
    payload = request.get_json(silent=True) or {}
    return payload if isinstance(payload, dict) else {}


def _failed_base64_report(detail: str) -> dict:
    report = _base_report({})
    report["failures"] = [_finding("fail", "invalid_zip", detail)]
    report["failure_count"] = 1
    report["summary"] = summarize_verification(report)
    return report


def register_dossier_finalization_export_verify_routes(app):
    @app.post("/api/v1/dossier-builder/v3/intelligence/finalization/export/verify")
    def api_verify_finalization_export_packet():
        payload = _request_payload()
        packet = payload.get("packet") if isinstance(payload.get("packet"), dict) else payload
        return jsonify(verify_finalization_export_packet(packet))

    @app.post("/api/v1/dossier-builder/v3/intelligence/finalization/export/verify-zip")
    def api_verify_finalization_export_zip():
        payload = _request_payload()
        encoded = payload.get("zip_base64")
        if not isinstance(encoded, str) or not encoded.strip():
            return jsonify(_failed_base64_report("zip_base64 is missing or empty."))
        try:
            zip_bytes = base64.b64decode(encoded, validate=True)
        except Exception:
            return jsonify(_failed_base64_report("zip_base64 is invalid base64."))
        return jsonify(verify_finalization_export_zip(zip_bytes))

    return app
