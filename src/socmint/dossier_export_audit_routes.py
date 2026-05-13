from __future__ import annotations

from flask import jsonify, request, session

from .dossier_export_audit import audit_event
from .dossier_export_audit import audit_index
from .dossier_export_audit import audit_summary
from .dossier_export_audit import read_audit_events


def _login_required() -> bool:
    return bool(session.get("user"))


def _actor() -> str:
    return str(session.get("user") or "system")


def register_dossier_export_audit_routes(app):
    @app.get("/api/v1/dossier-builder/v3/export-audit")
    def api_dossier_export_audit_index():
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(audit_index())

    @app.get("/api/v1/dossier-builder/v3/export-audit/<case_id>/<subject_id>")
    def api_dossier_export_audit_events(case_id: str, subject_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(
            {
                "schema": "socmint.dossier_export_audit.v10_7_0",
                "case_id": case_id,
                "subject_id": subject_id,
                "events": read_audit_events(case_id=case_id, subject_id=subject_id),
            }
        )

    @app.get("/api/v1/dossier-builder/v3/export-audit/<case_id>/<subject_id>/summary")
    def api_dossier_export_audit_summary(case_id: str, subject_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(audit_summary(case_id=case_id, subject_id=subject_id))

    @app.post("/api/v1/dossier-builder/v3/export-audit/<case_id>/<subject_id>/event")
    def api_dossier_export_audit_event(case_id: str, subject_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        payload = request.get_json(silent=True) or {}
        event = audit_event(
            action=str(payload.get("action") or "manifest_read"),
            case_id=case_id,
            subject_id=subject_id,
            actor=_actor(),
            detail=payload.get("detail") or {},
        )
        return jsonify(event)

    return app
