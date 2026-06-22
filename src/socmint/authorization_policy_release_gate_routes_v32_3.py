from __future__ import annotations

from flask import jsonify, request, session

from .authorization_policy_release_gate_v32_3 import (
    authorization_decision_history,
    decisions_for_package,
    find_authorization_decision,
    record_authorization_policy_decision,
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


def register_authorization_policy_release_gate_routes_v32_3(app):
    @app.get("/api/v1/dissemination-governance/authorization-decisions")
    def list_authorization_decisions_v32_3():
        actor, error = _authorized()
        if error:
            return error
        return jsonify(
            {
                "schema": "socmint.authorization_policy_decisions.v32_3",
                "version": "v32.3.0",
                "authorization_decisions": authorization_decision_history(),
            }
        )

    @app.get(
        "/api/v1/dissemination-governance/packages/"
        "<dissemination_package_id>/authorization-decisions"
    )
    def list_package_authorization_decisions_v32_3(
        dissemination_package_id: str,
    ):
        actor, error = _authorized()
        if error:
            return error
        return jsonify(
            {
                "schema": "socmint.package_authorization_decisions.v32_3",
                "version": "v32.3.0",
                "dissemination_package_id": dissemination_package_id,
                "authorization_decisions": decisions_for_package(
                    dissemination_package_id
                ),
            }
        )

    @app.get(
        "/api/v1/dissemination-governance/authorization-decisions/"
        "<authorization_decision_id>"
    )
    def get_authorization_decision_v32_3(authorization_decision_id: str):
        actor, error = _authorized()
        if error:
            return error
        decision = find_authorization_decision(authorization_decision_id)
        if decision is None:
            return jsonify({"error": "authorization decision not found"}), 404
        return jsonify(decision)

    @app.post(
        "/api/v1/dissemination-governance/packages/"
        "<dissemination_package_id>/authorization-decisions"
    )
    def create_authorization_decision_v32_3(
        dissemination_package_id: str,
    ):
        actor, error = _authorized()
        if error:
            return error
        data = _payload()
        result = record_authorization_policy_decision(
            reviewer=actor,
            dissemination_package_id=dissemination_package_id,
            decision=str(data.get("decision") or ""),
            reason=str(data.get("reason") or ""),
            confirmed=data.get("confirmed") is True,
            policy_note=str(data.get("policy_note") or ""),
            ip_address=request.remote_addr,
        )
        status = 201 if result.get("status") in {
            "approved_for_delivery_attempt",
            "release_denied",
            "release_held",
        } else 422
        return jsonify(result), status

    return app
