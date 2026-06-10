from __future__ import annotations

from flask import jsonify, redirect, render_template, request, session, url_for

from .case_delivery_workspace_v15 import build_case_delivery_workspace_from_request


def _login_required() -> bool:
    return bool(session.get("user"))


def _request_payload() -> dict:
    payload = request.get_json(silent=True) or {}
    return payload if isinstance(payload, dict) else {}


def register_case_delivery_workspace_routes_v15(app):
    @app.get("/case-delivery")
    def case_delivery_workspace_v15():
        if not _login_required():
            return redirect(url_for("dashboard.login"))
        case_id = request.args.get("case_id", "case-delivery-preview")
        payload = build_case_delivery_workspace_from_request(case_id, {})
        return render_template(
            "case_delivery_workspace.html",
            title="Case Delivery Workspace",
            payload=payload,
        )

    @app.get("/api/v1/case-delivery/<case_id>")
    def api_case_delivery_workspace_get_v15(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(build_case_delivery_workspace_from_request(case_id, {}))

    @app.post("/api/v1/case-delivery/<case_id>")
    def api_case_delivery_workspace_post_v15(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(build_case_delivery_workspace_from_request(case_id, _request_payload()))

    return app
