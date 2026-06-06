from __future__ import annotations

from flask import jsonify, render_template, request, session

from .dossier_export_gate import export_gate_decision
from .dossier_export_gate import export_gate_report
from .dossier_export_gate import export_gate_summary


def _login_required() -> bool:
    return bool(session.get("user"))


def register_dossier_export_gate_routes(app):
    @app.get("/dossier/export-blockers")
    def ui_dossier_export_blockers():
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        case_id = (request.args.get("case_id") or "").strip()
        subject_id = (request.args.get("subject_id") or "").strip()
        decision = None
        if case_id and subject_id:
            decision = export_gate_decision(subject_id=subject_id, case_id=case_id)
        return render_template(
            "export_blockers.html",
            title="Export Blockers",
            case_id=case_id,
            subject_id=subject_id,
            decision=decision,
        )

    @app.get("/api/v1/dossier-builder/v3/export-gate/<case_id>/<subject_id>")
    def api_dossier_export_gate(case_id: str, subject_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(export_gate_report(subject_id=subject_id, case_id=case_id))

    @app.get("/api/v1/dossier-builder/v3/export-gate/<case_id>/<subject_id>/summary")
    def api_dossier_export_gate_summary(case_id: str, subject_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(export_gate_summary(subject_id=subject_id, case_id=case_id))

    @app.get("/api/v1/dossier-builder/v3/export-gate/<case_id>/<subject_id>/decision")
    def api_dossier_export_gate_decision(case_id: str, subject_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(export_gate_decision(subject_id=subject_id, case_id=case_id))

    return app
