from __future__ import annotations

from flask import jsonify, request, session

from .case_reopen_control_v23_5 import (
    authorize_reopen_request,
    create_reopen_request,
)


def register_case_reopen_routes_v23_5(app):
    @app.post("/api/v1/case-closure/<case_id>/reopen-request")
    def api_case_reopen_request_post_v23_5(case_id: str):
        if not session.get("user"):
            return jsonify({"error": "login required"}), 401
        payload = request.get_json(silent=True) or {}
        result = create_reopen_request(
            case_id,
            reason=str(payload.get("reason") or ""),
            confirmed=payload.get("confirmed") is True,
            requester=str(session.get("user") or "unknown"),
            note=str(payload.get("note") or ""),
            ip_address=request.remote_addr,
        )
        code = 200 if result.get("status") == "reopen_request_recorded" else 422
        return jsonify(result), code

    @app.post("/api/v1/case-closure/<case_id>/reopen-authorization")
    def api_case_reopen_authorization_post_v23_5(case_id: str):
        if not session.get("user"):
            return jsonify({"error": "login required"}), 401
        payload = request.get_json(silent=True) or {}
        result = authorize_reopen_request(
            case_id,
            decision=str(payload.get("decision") or ""),
            confirmed=payload.get("confirmed") is True,
            supervisor=str(session.get("user") or "unknown"),
            note=str(payload.get("note") or ""),
            ip_address=request.remote_addr,
        )
        code = 200 if result.get("status") == "reopen_authorization_recorded" else 422
        return jsonify(result), code

    return app
