from __future__ import annotations

import base64

from flask import Response, jsonify, request

from .dossier_finalization_certificate_v7_5_4 import build_certificate_from_zip_bytes
from .dossier_finalization_certificate_v7_5_4 import build_verification_certificate
from .dossier_finalization_certificate_v7_5_4 import render_certificate_markdown
from .dossier_finalization_export_verify_routes_v7_5_3 import _failed_base64_report


def _request_payload() -> dict:
    payload = request.get_json(silent=True) or {}
    return payload if isinstance(payload, dict) else {}


def _unwrap_report(payload: dict) -> tuple[dict, str | None, str | None, str | None]:
    if isinstance(payload.get("verification_report"), dict):
        return (
            payload.get("verification_report") or {},
            payload.get("packet_name"),
            payload.get("reviewer"),
            payload.get("notes"),
        )
    return (
        payload,
        payload.get("packet_name"),
        payload.get("reviewer"),
        payload.get("notes"),
    )


def _zip_certificate_from_payload(payload: dict) -> dict:
    encoded = payload.get("zip_base64")
    packet_name = payload.get("packet_name")
    reviewer = payload.get("reviewer")
    notes = payload.get("notes")
    if not isinstance(encoded, str) or not encoded.strip():
        report = _failed_base64_report("zip_base64 is missing or empty.")
        return build_verification_certificate(
            report, packet_name=packet_name, reviewer=reviewer, notes=notes
        )
    try:
        zip_bytes = base64.b64decode(encoded, validate=True)
    except Exception:
        report = _failed_base64_report("zip_base64 is invalid base64.")
        return build_verification_certificate(
            report, packet_name=packet_name, reviewer=reviewer, notes=notes
        )
    return build_certificate_from_zip_bytes(
        zip_bytes, packet_name=packet_name, reviewer=reviewer, notes=notes
    )


def register_dossier_finalization_certificate_routes(app):
    @app.post("/api/v1/dossier-builder/v3/intelligence/finalization/certificate")
    def api_finalization_certificate():
        payload = _request_payload()
        report, packet_name, reviewer, notes = _unwrap_report(payload)
        return jsonify(
            build_verification_certificate(
                report, packet_name=packet_name, reviewer=reviewer, notes=notes
            )
        )

    @app.post(
        "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/markdown"
    )
    def api_finalization_certificate_markdown():
        payload = _request_payload()
        report, packet_name, reviewer, notes = _unwrap_report(payload)
        certificate = build_verification_certificate(
            report, packet_name=packet_name, reviewer=reviewer, notes=notes
        )
        return Response(
            render_certificate_markdown(certificate), mimetype="text/markdown"
        )

    @app.post(
        "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/from-zip"
    )
    def api_finalization_certificate_from_zip():
        return jsonify(_zip_certificate_from_payload(_request_payload()))

    return app
