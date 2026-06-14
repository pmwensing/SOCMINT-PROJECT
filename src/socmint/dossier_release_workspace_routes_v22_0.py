from __future__ import annotations

from flask import jsonify, redirect, render_template, request, session, url_for

from .dossier_release_authorization_v22_1 import (
    authorize_dossier_release,
    latest_release_authorization,
)
from .dossier_release_preview_v22_2 import (
    acknowledge_release_package_preview,
    build_release_package_preview,
    latest_release_preview,
)
from .dossier_release_workspace_v22_0 import build_dossier_release_workspace
from .dossier_secure_distribution_v22_3 import (
    build_secure_distribution_readiness,
    dispatch_secure_distribution,
)


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
        payload = build_dossier_release_workspace(
            case_id,
            selected_recipient_id=recipient_id,
            selected_channel=channel,
        )
        payload["latest_authorization"] = latest_release_authorization(case_id)
        payload["release_package_preview"] = build_release_package_preview(case_id)
        payload["latest_release_preview"] = latest_release_preview(case_id)
        payload["secure_distribution"] = build_secure_distribution_readiness(case_id)
        return render_template(
            "dossier_release_workspace_v22_0.html",
            title="Dossier Release Workspace",
            payload=payload,
        )

    @app.get("/api/v1/dossier-release/<case_id>")
    def api_dossier_release_workspace_get_v22_0(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        recipient_id, channel = _selection()
        payload = build_dossier_release_workspace(
            case_id,
            selected_recipient_id=recipient_id,
            selected_channel=channel,
        )
        payload["latest_authorization"] = latest_release_authorization(case_id)
        payload["release_package_preview"] = build_release_package_preview(case_id)
        payload["latest_release_preview"] = latest_release_preview(case_id)
        payload["secure_distribution"] = build_secure_distribution_readiness(case_id)
        return jsonify(payload)

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

    @app.post("/api/v1/dossier-release/<case_id>/authorize")
    def api_dossier_release_authorize_post_v22_1(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        payload = request.get_json(silent=True) or {}
        result = authorize_dossier_release(
            case_id,
            recipient_id=str(payload.get("recipient_id") or ""),
            delivery_channel=str(payload.get("delivery_channel") or ""),
            confirmed=payload.get("confirmed") is True,
            authorizer=str(session.get("user") or "unknown"),
            note=str(payload.get("note") or ""),
            ip_address=request.remote_addr,
        )
        return jsonify(result), 200 if result.get("status") == "authorized" else 422

    @app.get("/api/v1/dossier-release/<case_id>/package-preview")
    def api_dossier_release_package_preview_get_v22_2(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(build_release_package_preview(case_id))

    @app.post("/api/v1/dossier-release/<case_id>/package-preview/acknowledge")
    def api_dossier_release_package_preview_ack_post_v22_2(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        payload = request.get_json(silent=True) or {}
        result = acknowledge_release_package_preview(
            case_id,
            acknowledged=payload.get("acknowledged") is True,
            operator=str(session.get("user") or "unknown"),
            note=str(payload.get("note") or ""),
            ip_address=request.remote_addr,
        )
        return jsonify(result), 200 if result.get("status") in {
            "acknowledged_ready", "acknowledged_with_blockers"
        } else 422

    @app.get("/api/v1/dossier-release/<case_id>/distribution-readiness")
    def api_dossier_distribution_readiness_get_v22_3(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        result = build_secure_distribution_readiness(case_id)
        return jsonify(result), 200 if result.get("ready") else 422

    @app.post("/api/v1/dossier-release/<case_id>/dispatch")
    def api_dossier_secure_distribution_post_v22_3(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        payload = request.get_json(silent=True) or {}
        result = dispatch_secure_distribution(
            case_id,
            confirmed=payload.get("confirmed") is True,
            operator=str(session.get("user") or "unknown"),
            note=str(payload.get("note") or ""),
            ip_address=request.remote_addr,
        )
        return jsonify(result), 200 if result.get("status") == "dispatch_recorded" else 422

    return app
