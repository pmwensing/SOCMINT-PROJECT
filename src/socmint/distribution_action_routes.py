from __future__ import annotations

from flask import Response, jsonify, request, session

from .distribution_actions import distribution_action_markdown
from .distribution_actions import distribution_action_packet
from .distribution_actions import distribution_action_summary
from .distribution_actions import record_distribution_action


def _login_required() -> bool:
    return bool(session.get("user"))


def register_distribution_action_routes(app):
    @app.get("/api/v1/dossier-builder/v3/distribution-actions/<case_id>/<subject_id>")
    def api_distribution_actions(case_id: str, subject_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(distribution_action_summary(case_id=case_id, subject_id=subject_id))

    @app.post("/api/v1/dossier-builder/v3/distribution-actions/<case_id>/<subject_id>")
    def api_record_distribution_action(case_id: str, subject_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        payload = request.get_json(silent=True) or request.form or {}
        try:
            event = record_distribution_action(
                case_id=case_id,
                subject_id=subject_id,
                action=str(payload.get("action") or "").strip(),
                actor=session.get("user"),
                note=str(payload.get("note") or "").strip(),
            )
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify(event), 201

    @app.get("/api/v1/dossier-builder/v3/distribution-packet/<case_id>/<subject_id>")
    def api_distribution_packet(case_id: str, subject_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(distribution_action_packet(case_id=case_id, subject_id=subject_id))

    @app.get("/api/v1/dossier-builder/v3/distribution-packet/<case_id>/<subject_id>/markdown")
    def api_distribution_packet_markdown(case_id: str, subject_id: str):
        if not _login_required():
            return Response("login required\n", status=401, mimetype="text/plain")
        return Response(distribution_action_markdown(case_id=case_id, subject_id=subject_id), mimetype="text/markdown")

    return app
