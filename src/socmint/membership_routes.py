from __future__ import annotations

from flask import jsonify, render_template, request, session

from .membership import assign_membership
from .membership import evaluate_gate
from .membership import ensure_default_membership
from .membership import list_memberships
from .membership import membership_summary
from .membership import set_quota_override


def _login_required():
    if not session.get("user"):
        return False
    return True


def _admin_required():
    return bool(session.get("user") and session.get("is_admin"))


def register_membership_routes(app):
    @app.get("/account/usage")
    def account_usage():
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        payload = ensure_default_membership(session["user"], actor=session.get("user"))
        try:
            return render_template("account_usage.html", payload=payload)
        except Exception:
            return jsonify(payload)

    @app.get("/api/v1/account/membership")
    def api_account_membership():
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(ensure_default_membership(session["user"], actor=session.get("user")))

    @app.post("/api/v1/account/gate")
    def api_account_gate():
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        payload = request.get_json(silent=True) or {}
        return jsonify(
            evaluate_gate(
                session["user"],
                payload.get("action", "review"),
                quota_key=payload.get("quota_key"),
                amount=int(payload.get("amount") or 1),
                scope_state=payload.get("scope_state") or "authorized",
                metadata=payload.get("metadata") or {},
                consume=bool(payload.get("consume")),
            )
        )

    @app.get("/admin/memberships")
    def admin_memberships():
        if not _admin_required():
            return jsonify({"error": "admin required"}), 403
        payload = list_memberships()
        try:
            return render_template("admin_memberships.html", payload=payload)
        except Exception:
            return jsonify(payload)

    @app.get("/api/v1/admin/memberships")
    def api_admin_memberships():
        if not _admin_required():
            return jsonify({"error": "admin required"}), 403
        return jsonify(list_memberships())

    @app.post("/api/v1/admin/memberships/<username>")
    def api_admin_membership_assign(username):
        if not _admin_required():
            return jsonify({"error": "admin required"}), 403
        payload = request.get_json(silent=True) or {}
        try:
            return jsonify(
                assign_membership(
                    username,
                    payload.get("plan", "free"),
                    actor=session.get("user"),
                    metadata=payload.get("metadata") or {},
                )
            )
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

    @app.post("/api/v1/admin/quota-overrides/<username>")
    def api_admin_quota_override(username):
        if not _admin_required():
            return jsonify({"error": "admin required"}), 403
        payload = request.get_json(silent=True) or {}
        try:
            return jsonify(
                set_quota_override(
                    username,
                    payload["quota_key"],
                    int(payload["limit"]),
                    actor=session.get("user"),
                    reason=payload.get("reason"),
                )
            )
        except (KeyError, ValueError) as exc:
            return jsonify({"error": str(exc)}), 400

    return app
