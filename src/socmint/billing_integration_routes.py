from __future__ import annotations

from flask import jsonify, request, session

from .billing_integration import billing_link_status
from .billing_integration import billing_provider_config
from .billing_integration import link_customer
from .billing_integration import process_provider_event


def _admin_required():
    return bool(session.get("user") and session.get("is_admin"))


def register_billing_integration_routes(app):
    @app.get("/api/v1/admin/billing/provider-config")
    def api_billing_provider_config():
        if not _admin_required():
            return jsonify({"error": "admin required"}), 403
        return jsonify(billing_provider_config())

    @app.get("/api/v1/admin/billing/customer-links/<username>")
    def api_billing_customer_link(username: str):
        if not _admin_required():
            return jsonify({"error": "admin required"}), 403
        return jsonify(billing_link_status(username))

    @app.post("/api/v1/admin/billing/customer-links/<username>")
    def api_billing_link_customer(username: str):
        if not _admin_required():
            return jsonify({"error": "admin required"}), 403
        payload = request.get_json(silent=True) or {}
        try:
            return jsonify(
                link_customer(
                    username,
                    payload["customer_id"],
                    subscription_id=payload.get("subscription_id"),
                    plan_key=payload.get("plan"),
                    status=payload.get("status", "active"),
                    provider=payload.get("provider", "stripe"),
                    metadata=payload.get("metadata") or {},
                )
            )
        except KeyError as exc:
            return jsonify({"error": f"missing field: {exc}"}), 400

    @app.post("/api/v1/admin/billing/provider-events")
    def api_billing_provider_event():
        if not _admin_required():
            return jsonify({"error": "admin required"}), 403
        return jsonify(process_provider_event(request.get_json(silent=True) or {})), 202

    return app
