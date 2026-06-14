from __future__ import annotations

from flask import jsonify, redirect, render_template, request, session, url_for

from .dossier_release_workspace_v22_0 import build_dossier_release_workspace


def _login_required() -> bool:
    return bool(session.get("user"))


def _selection() -> tuple[str | None, str | None]:
    payload = request.get_json(silent=True) if request.method == "POST" else None
    payload = payload if isinstance(payload, dict) else {}
    recipient_id = payload.get("recipient_id") or request.args.get("recipient_id")
    channel = payload.get("delivery_channel") or request.args.get("delivery_channel")
    return (
        str(recipient_id) if recipient_id else None,
        str(channel) if channel else None,
    )


def register_dossier_release_workspace_routes_v22_0(app):
    @app.get("/dossier-release/<case_id>")
    def dossier_release_workspace_get_v22_0(case_id: str):
        if not _login_required():
            return redirect(url_for("dashboard.login"))
        recipient_id, channel = _selection()
        return render_template(
            "dossier_release_workspace_v22_0.html",
            title="Dossier Release Workspace",
            payload=build_dossier_release_workspace(
                case_id,
                selected_recipient_id=recipient_id,
                selected_channel=channel,
            ),
        )

    @app.get("/api/v1/dossier-release/<case_id>")
    def api_dossier_release_workspace_get_v22_0(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        recipient_id, channel = _selection()
        return jsonify(build_dossier_release_workspace(
            case_id,
            selected_recipient_id=recipient_id,
            selected_channel=channel,
        ))

    @app.post("/api/v1/dossier-release/<case_id>/preview")
    def api_dossier_release_preview_post_v22_0(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        recipient_id, channel = _selection()
        result = build_dossier_release_workspace(
            case_id,
            selected_recipient_id=recipient_id,
            selected_channel=channel,
        )
        return jsonify(result), 200 if result.get("release_ready") else 422

    return app
