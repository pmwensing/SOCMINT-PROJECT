from __future__ import annotations

from flask import jsonify, request, session

from .billing import billing_status
from .billing import create_checkout_session
from .billing import process_subscription_event
from .billing import verify_webhook_signature
from .billing_integration_routes import register_billing_integration_routes


def _login_required():
    return bool(session.get("user"))


def _admin_required():
    return bool(session.get("user") and session.get("is_admin"))


def register_billing_routes(app):
    register_billing_integration_routes(app)

    @app.get("/api/v1/account/billing")
    def api_account_billing():
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(billing_status(session["user"]))

    @app.post("/api/v1/account/billing/checkout")
    def api_account_checkout():
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        payload = request.get_json(silent=True) or {}
        try:
            return jsonify(
                create_checkout_session(
                    session["user"],
                    payload.get("plan", "pro"),
                    success_url=payload.get("success_url"),
                    cancel_url=payload.get("cancel_url"),
                )
            ), 201
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

    @app.post("/api/v1/billing/webhook")
    def api_billing_webhook():
        payload_text = request.get_data(as_text=True)
        webhook_secret = app.config.get("SOCMINT_BILLING_WEBHOOK_SECRET") or ""
        signature = request.headers.get("X-SOCMINT-Signature", "")
        if webhook_secret and not verify_webhook_signature(
            payload_text, signature, webhook_secret
        ):
            return jsonify({"error": "invalid signature"}), 400
        payload = request.get_json(silent=True) or {}
        try:
            return jsonify(process_subscription_event(payload)), 202
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

    @app.post("/api/v1/admin/billing/events")
    def api_admin_billing_event():
        if not _admin_required():
            return jsonify({"error": "admin required"}), 403
        try:
            return jsonify(
                process_subscription_event(request.get_json(silent=True) or {})
            ), 202
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

    return app
