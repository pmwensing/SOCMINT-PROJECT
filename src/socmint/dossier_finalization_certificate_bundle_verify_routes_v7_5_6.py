from __future__ import annotations

import base64

from flask import jsonify, request

from .dossier_finalization_certificate_bundle_verify_v7_5_6 import _base_report
from .dossier_finalization_certificate_bundle_verify_v7_5_6 import _finding
from .dossier_finalization_certificate_bundle_verify_v7_5_6 import (
    summarize_bundle_verification,
)
from .dossier_finalization_certificate_bundle_verify_v7_5_6 import (
    verify_certificate_bundle,
)
from .dossier_finalization_certificate_bundle_verify_v7_5_6 import (
    verify_certificate_bundle_zip,
)


def _request_payload() -> dict:
    payload = request.get_json(silent=True) or {}
    return payload if isinstance(payload, dict) else {}


def _failed_base64_report(detail: str) -> dict:
    report = _base_report({})
    report["failures"] = [_finding("fail", "invalid_zip", detail)]
    report["failure_count"] = 1
    report["summary"] = summarize_bundle_verification(report)
    return report


def register_dossier_finalization_certificate_bundle_verify_routes(app):
    @app.post(
        "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/bundle/verify"
    )
    def api_verify_certificate_bundle():
        payload = _request_payload()
        bundle = (
            payload.get("bundle")
            if isinstance(payload.get("bundle"), dict)
            else payload
        )
        return jsonify(verify_certificate_bundle(bundle))

    @app.post(
        "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/bundle/verify-zip"
    )
    def api_verify_certificate_bundle_zip():
        payload = _request_payload()
        encoded = payload.get("zip_base64")
        if not isinstance(encoded, str) or not encoded.strip():
            return jsonify(_failed_base64_report("zip_base64 is missing or empty."))
        try:
            zip_bytes = base64.b64decode(encoded, validate=True)
        except Exception:
            return jsonify(_failed_base64_report("zip_base64 is invalid base64."))
        return jsonify(verify_certificate_bundle_zip(zip_bytes))

    return app
