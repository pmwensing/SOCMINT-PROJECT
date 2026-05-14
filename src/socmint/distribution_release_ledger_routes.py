from __future__ import annotations

from flask import Response, jsonify, request, session

from .distribution_release_ledger import create_distribution_release_seal
from .distribution_release_ledger import release_ledger_summary
from .distribution_release_ledger import release_seal_markdown
from .distribution_release_ledger import release_state


def _login_required() -> bool:
    return bool(session.get("user"))


def register_distribution_release_ledger_routes(app):
    @app.post("/api/v1/dossier-builder/v3/distribution-release/<case_id>/<subject_id>/seal")
    def api_create_distribution_release_seal(case_id: str, subject_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        payload = request.get_json(silent=True) or request.form or {}
        try:
            seal = create_distribution_release_seal(
                case_id=case_id,
                subject_id=subject_id,
                actor=session.get("user"),
                note=str(payload.get("note") or "").strip(),
            )
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify(seal), 201

    @app.get("/api/v1/dossier-builder/v3/distribution-release/<case_id>/<subject_id>")
    def api_distribution_release_state(case_id: str, subject_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(release_state(case_id=case_id, subject_id=subject_id))

    @app.get("/api/v1/dossier-builder/v3/distribution-release/<case_id>/<subject_id>/markdown")
    def api_distribution_release_markdown(case_id: str, subject_id: str):
        if not _login_required():
            return Response("login required\n", status=401, mimetype="text/plain")
        return Response(release_seal_markdown(case_id=case_id, subject_id=subject_id), mimetype="text/markdown")

    @app.get("/api/v1/dossier-builder/v3/distribution-release-ledger/<case_id>")
    def api_distribution_release_ledger(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(release_ledger_summary(case_id=case_id))

    return app
