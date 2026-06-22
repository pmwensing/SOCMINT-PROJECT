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

    @app.get("/api/v1/dissemination-governance/packages/<package_id>/delivery-attempts")
    def list_package_attempts_v32_4(package_id: str):
        actor, error = _authorized()
        if error:
            return error
        return jsonify({
            "schema": "socmint.package_delivery_attempts.v32_4",
            "version": "v32.4.0",
            "dissemination_package_id": package_id,
            "delivery_attempts": attempts_for_package(package_id),
        })

    @app.post("/api/v1/dissemination-governance/packages/<package_id>/delivery-attempts")
    def create_attempt_v32_4(package_id: str):
        actor, error = _authorized()
        if error:
            return error
        data = _payload()
        result = record_delivery_attempt(
            operator=actor,
            dissemination_package_id=package_id,
            recipient_id=str(data.get("recipient_id") or ""),
            delivery_channel=str(data.get("delivery_channel") or ""),
            endpoint_reference=str(data.get("endpoint_reference") or ""),
            attempt_result=str(data.get("attempt_result") or ""),
            transport_reference=str(data.get("transport_reference") or ""),
            reason=str(data.get("reason") or ""),
            confirmed=data.get("confirmed") is True,
            failure_code=str(data.get("failure_code") or ""),
            failure_detail=str(data.get("failure_detail") or ""),
            note=str(data.get("note") or ""),
            ip_address=request.remote_addr,
        )
        return jsonify(result), 201 if result.get("status") == "delivery_attempt_recorded" else 422

    @app.get("/api/v1/dissemination-governance/delivery-attempts/<attempt_id>")
    def get_attempt_v32_4(attempt_id: str):
        actor, error = _authorized()
        if error:
            return error
        value = find_delivery_attempt(attempt_id)
        if value is None:
            return jsonify({"error": "delivery attempt not found"}), 404
        return jsonify(value)

    @app.get("/api/v1/dissemination-governance/delivery-attempts/<attempt_id>/receipts")
    def list_attempt_receipts_v32_4(attempt_id: str):
        actor, error = _authorized()
        if error:
            return error
        return jsonify({
            "schema": "socmint.attempt_delivery_receipts.v32_4",
            "version": "v32.4.0",
            "delivery_attempt_id": attempt_id,
            "delivery_receipts": receipts_for_attempt(attempt_id),
        })

    @app.post("/api/v1/dissemination-governance/delivery-attempts/<attempt_id>/receipts")
    def create_receipt_v32_4(attempt_id: str):
        actor, error = _authorized()
        if error:
            return error
        data = _payload()
        result = record_delivery_receipt(
            recorder=actor,
            delivery_attempt_id=attempt_id,
            delivery_result=str(data.get("delivery_result") or ""),
            provider_message_id=str(data.get("provider_message_id") or ""),
            transport_status=str(data.get("transport_status") or ""),
            confirmed=data.get("confirmed") is True,
            delivered_at=str(data.get("delivered_at") or ""),
            failure_code=str(data.get("failure_code") or ""),
            failure_detail=str(data.get("failure_detail") or ""),
            note=str(data.get("note") or ""),
            ip_address=request.remote_addr,
        )
        return jsonify(result), 201 if result.get("status") == "delivery_receipt_recorded" else 422

    @app.get("/api/v1/dissemination-governance/delivery-receipts/<receipt_id>")
    def get_receipt_v32_4(receipt_id: str):
        actor, error = _authorized()
        if error:
            return error
        value = find_delivery_receipt(receipt_id)
        if value is None:
            return jsonify({"error": "delivery receipt not found"}), 404
        return jsonify(value)

    return app
