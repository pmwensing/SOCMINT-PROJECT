from __future__ import annotations

from flask import jsonify, request, session

from .recipient_feedback_correction_intake_v32_5 import (
    correction_intake_history,
    corrections_for_feedback,
    feedback_for_receipt,
    find_correction_intake,
    find_recipient_feedback,
    recipient_feedback_history,
    record_correction_intake,
    record_recipient_feedback,
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


def register_recipient_feedback_correction_intake_routes_v32_5(app):
    @app.get("/api/v1/dissemination-governance/recipient-feedback")
    def list_recipient_feedback_v32_5():
        actor, error = _authorized()
        if error:
            return error
        return jsonify({
            "schema": "socmint.recipient_feedback.v32_5",
            "version": "v32.5.0",
            "recipient_feedback": recipient_feedback_history(),
        })

    @app.get("/api/v1/dissemination-governance/correction-intakes")
    def list_correction_intakes_v32_5():
        actor, error = _authorized()
        if error:
            return error
        return jsonify({
            "schema": "socmint.correction_intakes.v32_5",
            "version": "v32.5.0",
            "correction_intakes": correction_intake_history(),
        })

    @app.get(
        "/api/v1/dissemination-governance/delivery-receipts/"
        "<receipt_id>/recipient-feedback"
    )
    def list_receipt_feedback_v32_5(receipt_id: str):
        actor, error = _authorized()
        if error:
            return error
        return jsonify({
            "schema": "socmint.receipt_recipient_feedback.v32_5",
            "version": "v32.5.0",
            "delivery_receipt_id": receipt_id,
            "recipient_feedback": feedback_for_receipt(receipt_id),
        })

    @app.post(
        "/api/v1/dissemination-governance/delivery-receipts/"
        "<receipt_id>/recipient-feedback"
    )
    def create_recipient_feedback_v32_5(receipt_id: str):
        actor, error = _authorized()
        if error:
            return error
        data = _payload()
        result = record_recipient_feedback(
            recorder=actor,
            delivery_receipt_id=receipt_id,
            feedback_type=str(data.get("feedback_type") or ""),
            severity=str(data.get("severity") or ""),
            recipient_reference=str(data.get("recipient_reference") or ""),
            summary=str(data.get("summary") or ""),
            detail=str(data.get("detail") or ""),
            confirmed=data.get("confirmed") is True,
            source_reference=str(data.get("source_reference") or ""),
            note=str(data.get("note") or ""),
            ip_address=request.remote_addr,
        )
        status = 201 if result.get("status") == "recipient_feedback_recorded" else 422
        return jsonify(result), status

    @app.get(
        "/api/v1/dissemination-governance/recipient-feedback/<feedback_id>"
    )
    def get_recipient_feedback_v32_5(feedback_id: str):
        actor, error = _authorized()
        if error:
            return error
        value = find_recipient_feedback(feedback_id)
        if value is None:
            return jsonify({"error": "recipient feedback not found"}), 404
        return jsonify(value)

    @app.get(
        "/api/v1/dissemination-governance/recipient-feedback/"
        "<feedback_id>/correction-intakes"
    )
    def list_feedback_corrections_v32_5(feedback_id: str):
        actor, error = _authorized()
        if error:
            return error
        return jsonify({
            "schema": "socmint.feedback_correction_intakes.v32_5",
            "version": "v32.5.0",
            "recipient_feedback_id": feedback_id,
            "correction_intakes": corrections_for_feedback(feedback_id),
        })

    @app.post(
        "/api/v1/dissemination-governance/recipient-feedback/"
        "<feedback_id>/correction-intakes"
    )
    def create_correction_intake_v32_5(feedback_id: str):
        actor, error = _authorized()
        if error:
            return error
        data = _payload()
        affected = data.get("affected_section_ids")
        result = record_correction_intake(
            reviewer=actor,
            recipient_feedback_id=feedback_id,
            correction_action=str(data.get("correction_action") or ""),
            reason=str(data.get("reason") or ""),
            confirmed=data.get("confirmed") is True,
            affected_section_ids=(affected if isinstance(affected, list) else []),
            proposed_resolution=str(data.get("proposed_resolution") or ""),
            note=str(data.get("note") or ""),
            ip_address=request.remote_addr,
        )
        status = 201 if result.get("status") == "correction_intake_recorded" else 422
        return jsonify(result), status

    @app.get(
        "/api/v1/dissemination-governance/correction-intakes/<correction_id>"
    )
    def get_correction_intake_v32_5(correction_id: str):
        actor, error = _authorized()
        if error:
            return error
        value = find_correction_intake(correction_id)
        if value is None:
            return jsonify({"error": "correction intake not found"}), 404
        return jsonify(value)

    return app
