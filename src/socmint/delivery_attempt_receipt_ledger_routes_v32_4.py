from __future__ import annotations

from flask import jsonify, request, session

from .delivery_attempt_receipt_ledger_v32_4 import (
    attempts_for_package,
    delivery_attempt_history,
    delivery_receipt_history,
    find_delivery_attempt,
    find_delivery_receipt,
    receipts_for_attempt,
    record_delivery_attempt,
    record_delivery_receipt,
)
from .user_account_workspace_v28_1 import actor_is_administrator


def _payload() -> dict:
    value = request.get_json(silent=True)
    return value if isinstance(value, dict) else {}


def _authorized():
    actor = str(session.get("user") or "")
    if not actor:
        return None, (jsonify({"error": "login required"}), 401)
    if not actor_is_administrator(actor):
        return None, (jsonify({"error": "administrator required"}), 403)
    return actor, None


def register_delivery_attempt_receipt_ledger_routes_v32_4(app):
    @app.get("/api/v1/dissemination-governance/delivery-attempts")
    def list_delivery_attempts_v32_4():
        actor, error = _authorized()
        if error:
            return error
        return jsonify({
            "schema": "socmint.delivery_attempts.v32_4",
            "version": "v32.4.0",
            "delivery_attempts": delivery_attempt_history(),
        })

    @app.get("/api/v1/dissemination-governance/delivery-receipts")
    def list_delivery_receipts_v32_4():
        actor, error = _authorized()
        if error:
            return error
        return jsonify({
            "schema": "socmint.delivery_receipts.v32_4",
            "version": "v32.4.0",
            "delivery_receipts": delivery_receipt_history(),
        })

    return app
