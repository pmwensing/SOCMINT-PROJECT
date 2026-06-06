from __future__ import annotations

from pathlib import Path

from flask import jsonify, render_template, request, send_file, session

from .dossier_export_gate import export_gate_decision
from .dossier_export_gate import export_gate_report
from .dossier_export_gate import export_gate_summary

REPO_ROOT = Path(__file__).resolve().parents[2]
EXPORT_BLOCKER_SCREENSHOT_MANIFEST = REPO_ROOT / "release/V13_42_EXPORT_BLOCKER_SCREENSHOT_ARTIFACT_MANIFEST.json"


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

    @app.get("/api/v1/dossier-builder/v3/export-blockers/screenshot-manifest")
    def api_export_blocker_screenshot_manifest():
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        if not EXPORT_BLOCKER_SCREENSHOT_MANIFEST.exists():
            return jsonify({"status": "missing", "manifest_path": str(EXPORT_BLOCKER_SCREENSHOT_MANIFEST)}), 404
        return send_file(EXPORT_BLOCKER_SCREENSHOT_MANIFEST, mimetype="application/json")

    @app.get("/dossier/export-blockers/screenshot-manifest/download")
    def download_export_blocker_screenshot_manifest():
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        if not EXPORT_BLOCKER_SCREENSHOT_MANIFEST.exists():
            return jsonify({"status": "missing", "manifest_path": str(EXPORT_BLOCKER_SCREENSHOT_MANIFEST)}), 404
        return send_file(
            EXPORT_BLOCKER_SCREENSHOT_MANIFEST,
            as_attachment=True,
            download_name=EXPORT_BLOCKER_SCREENSHOT_MANIFEST.name,
            mimetype="application/json",
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
