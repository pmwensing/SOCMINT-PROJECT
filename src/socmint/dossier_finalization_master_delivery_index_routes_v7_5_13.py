from __future__ import annotations

import base64

from flask import Response, jsonify, request

from .dossier_finalization_master_delivery_index_v7_5_13 import build_master_delivery_index
from .dossier_finalization_master_delivery_index_v7_5_13 import build_master_delivery_index_from_bundle
from .dossier_finalization_master_delivery_index_v7_5_13 import build_master_delivery_index_from_zip_bytes
from .dossier_finalization_master_delivery_index_v7_5_13 import render_master_delivery_index_markdown


def _request_payload() -> dict:
    payload = request.get_json(silent=True) or {}
    return payload if isinstance(payload, dict) else {}


def _operator_notes(payload: dict) -> tuple[str | None, str | None]:
    return payload.get("operator"), payload.get("notes")


def _unwrap_verification_report(payload: dict) -> dict:
    if isinstance(payload.get("verification_report"), dict):
        return payload.get("verification_report") or {}
    return payload


def _unwrap_bundle(payload: dict) -> dict:
    if isinstance(payload.get("bundle"), dict):
        return payload.get("bundle") or {}
    return payload


def _invalid_zip_index(payload: dict, detail: str) -> dict:
    operator, notes = _operator_notes(payload)
    failure_report = {
        "status": "failed",
        "verified": False,
        "failure_count": 1,
        "warning_count": 0,
        "required_files": [],
        "present_files": [],
        "missing_files": [],
        "unexpected_files": [],
        "closeout_action": None,
        "failures": [
            {
                "severity": "fail",
                "code": "invalid_zip_base64",
                "path": None,
                "detail": detail,
                "action": "Provide a valid base64-encoded v7.5.11 closeout export ZIP.",
            }
        ],
        "warnings": [],
        "summary": {"status": "failed", "verified": False},
    }
    return build_master_delivery_index(failure_report, operator=operator, notes=notes)


def register_dossier_finalization_master_delivery_index_routes(app):
    @app.post("/api/v1/dossier-builder/v3/intelligence/finalization/master-delivery-index")
    def api_master_delivery_index():
        payload = _request_payload()
        operator, notes = _operator_notes(payload)
        report = _unwrap_verification_report(payload)
        return jsonify(build_master_delivery_index(report, operator=operator, notes=notes))

    @app.post("/api/v1/dossier-builder/v3/intelligence/finalization/master-delivery-index/markdown")
    def api_master_delivery_index_markdown():
        payload = _request_payload()
        operator, notes = _operator_notes(payload)
        report = _unwrap_verification_report(payload)
        index = build_master_delivery_index(report, operator=operator, notes=notes)
        return Response(render_master_delivery_index_markdown(index), mimetype="text/markdown")

    @app.post("/api/v1/dossier-builder/v3/intelligence/finalization/master-delivery-index/from-bundle")
    def api_master_delivery_index_from_bundle():
        payload = _request_payload()
        operator, notes = _operator_notes(payload)
        bundle = _unwrap_bundle(payload)
        return jsonify(build_master_delivery_index_from_bundle(bundle, operator=operator, notes=notes))

    @app.post("/api/v1/dossier-builder/v3/intelligence/finalization/master-delivery-index/from-zip")
    def api_master_delivery_index_from_zip():
        payload = _request_payload()
        operator, notes = _operator_notes(payload)
        encoded = payload.get("zip_base64")
        if not isinstance(encoded, str) or not encoded.strip():
            return jsonify(_invalid_zip_index(payload, "zip_base64 is missing or empty."))
        try:
            zip_bytes = base64.b64decode(encoded, validate=True)
        except Exception:
            return jsonify(_invalid_zip_index(payload, "zip_base64 is invalid base64."))
        return jsonify(build_master_delivery_index_from_zip_bytes(zip_bytes, operator=operator, notes=notes))

    return app
