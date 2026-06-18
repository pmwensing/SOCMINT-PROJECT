from __future__ import annotations

from flask import jsonify, redirect, render_template, request, session, url_for

from .user_account_mutations_v28_1 import provision_user, update_user
from .user_account_workspace_v28_1 import actor_is_administrator, build_user_account_workspace


def _payload() -> dict:
    value = request.get_json(silent=True)
    return value if isinstance(value, dict) else {}


def _actor() -> str:
    return str(session.get("user") or "")


def _authorized():
    actor = _actor()
    if not actor:
        return None, (jsonify({"error": "login required"}), 401)
    if not actor_is_administrator(actor):
        return None, (jsonify({"error": "administrator required"}), 403)
    return actor, None


def _code(result: dict, success: str) -> int:
    return 200 if result.get("status") == success else 422


def register_user_account_routes_v28_1(app):
    @app.get("/administration/users")
    def user_account_workspace_get_v28_1():
        actor = _actor()
        if not actor:
            return redirect(url_for("dashboard.login"))
        if not actor_is_administrator(actor):
            return render_template("user_account_administration_v28_1.html", title="User and Account Administration", payload={"status":"forbidden","error":"administrator required","users":[],"account_history":[]}), 403
        return render_template("user_account_administration_v28_1.html", title="User and Account Administration", payload=build_user_account_workspace())

    @app.get("/api/v1/administration/users")
    def api_user_account_workspace_get_v28_1():
        actor, error = _authorized()
        if error:
            return error
        return jsonify(build_user_account_workspace())

    @app.post("/api/v1/administration/users")
    def api_user_provision_post_v28_1():
        actor, error = _authorized()
        if error:
            return error
        payload = _payload()
        result = provision_user(
            actor=actor,
            username=str(payload.get("username") or ""),
            role=str(payload.get("role") or "viewer"),
            is_admin=payload.get("is_admin") is True,
            reason=str(payload.get("reason") or ""),
            confirmed=payload.get("confirmed") is True,
            ip_address=request.remote_addr,
        )
        return jsonify(result), _code(result, "user_provisioned")

    @app.post("/api/v1/administration/users/<username>/activate")
    def api_user_activate_post_v28_1(username: str):
        actor, error = _authorized()
        if error:
            return error
        payload = _payload()
        result = update_user(username, actor=actor, is_active=True, reason=str(payload.get("reason") or ""), confirmed=payload.get("confirmed") is True, ip_address=request.remote_addr)
        return jsonify(result), _code(result, "user_updated")

    @app.post("/api/v1/administration/users/<username>/suspend")
    def api_user_suspend_post_v28_1(username: str):
        actor, error = _authorized()
        if error:
            return error
        payload = _payload()
        result = update_user(username, actor=actor, is_active=False, reason=str(payload.get("reason") or ""), confirmed=payload.get("confirmed") is True, ip_address=request.remote_addr)
        return jsonify(result), _code(result, "user_updated")

    @app.post("/api/v1/administration/users/<username>/update")
    def api_user_update_post_v28_1(username: str):
        actor, error = _authorized()
        if error:
            return error
        payload = _payload()
        result = update_user(
            username,
            actor=actor,
            role=str(payload["role"]) if "role" in payload else None,
            is_admin=bool(payload["is_admin"]) if "is_admin" in payload else None,
            reason=str(payload.get("reason") or ""),
            confirmed=payload.get("confirmed") is True,
            ip_address=request.remote_addr,
        )
        return jsonify(result), _code(result, "user_updated")

    return app
