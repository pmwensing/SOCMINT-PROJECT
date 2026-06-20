from __future__ import annotations

import base64

from flask import Response, jsonify, request

from .dossier_finalization_closeout_report_v7_5_10 import build_closeout_report
from .dossier_finalization_closeout_report_v7_5_10 import (
    build_closeout_report_from_zip_bytes,
)
from .dossier_finalization_closeout_report_v7_5_10 import (
    render_closeout_report_markdown,
)
from .dossier_finalization_handoff_export_verify_routes_v7_5_9 import (
    _failed_base64_report,
)


def _request_payload() -> dict:
    payload = request.get_json(silent=True) or {}
    return payload if isinstance(payload, dict) else {}


def _unwrap_report(payload: dict) -> tuple[dict, str | None, str | None]:
    if isinstance(payload.get("verification_report"), dict):
        return (
            payload.get("verification_report") or {},
            payload.get("operator"),
            payload.get("notes"),
        )
    return payload, payload.get("operator"), payload.get("notes")


def _zip_report_from_payload(payload: dict) -> dict:
    encoded = payload.get("zip_base64")
    operator = payload.get("operator")
    notes = payload.get("notes")
    if not isinstance(encoded, str) or not encoded.strip():
        return build_closeout_report(
            _failed_base64_report("zip_base64 is missing or empty."),
            operator=operator,
            notes=notes,
        )
    try:
        zip_bytes = base64.b64decode(encoded, validate=True)
    except Exception:
        return build_closeout_report(
            _failed_base64_report("zip_base64 is invalid base64."),
            operator=operator,
            notes=notes,
        )
    return build_closeout_report_from_zip_bytes(
        zip_bytes, operator=operator, notes=notes
    )


def register_dossier_finalization_closeout_report_routes(app):
    @app.post("/api/v1/dossier-builder/v3/intelligence/finalization/closeout-report")
    def api_finalization_closeout_report():
        payload = _request_payload()
        verification_report, operator, notes = _unwrap_report(payload)
        return jsonify(
            build_closeout_report(verification_report, operator=operator, notes=notes)
        )

    @app.post(
        "/api/v1/dossier-builder/v3/intelligence/finalization/closeout-report/markdown"
    )
    def api_finalization_closeout_report_markdown():
        payload = _request_payload()
        verification_report, operator, notes = _unwrap_report(payload)
        report = build_closeout_report(
            verification_report, operator=operator, notes=notes
        )
        return Response(
            render_closeout_report_markdown(report), mimetype="text/markdown"
        )

    @app.post(
        "/api/v1/dossier-builder/v3/intelligence/finalization/closeout-report/from-zip"
    )
    def api_finalization_closeout_report_from_zip():
        return jsonify(_zip_report_from_payload(_request_payload()))

    return app
