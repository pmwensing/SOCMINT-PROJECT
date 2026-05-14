from __future__ import annotations

from flask import Response, jsonify, session

from .distribution_handoff_packet import distribution_handoff_markdown
from .distribution_handoff_packet import distribution_handoff_packet


def _login_required() -> bool:
    return bool(session.get("user"))


def register_distribution_handoff_packet_routes(app):
    @app.get("/api/v1/dossier-builder/v3/distribution-handoff/<case_id>")
    def api_distribution_handoff_packet(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(distribution_handoff_packet(case_id=case_id))

    @app.get("/api/v1/dossier-builder/v3/distribution-handoff/<case_id>/markdown")
    def api_distribution_handoff_markdown(case_id: str):
        if not _login_required():
            return Response("login required\n", status=401, mimetype="text/plain")
        return Response(distribution_handoff_markdown(case_id=case_id), mimetype="text/markdown")

    return app
