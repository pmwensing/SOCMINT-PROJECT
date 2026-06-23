from __future__ import annotations

from flask import jsonify, request, session

from .audience_recipient_contract_v32_1 import (
    record_audience_recipient_contract,
)
from .authorization_policy_release_gate_v32_3 import (
    record_authorization_policy_decision,
)
from .delivery_attempt_receipt_ledger_v32_4 import (
    record_delivery_attempt,
    record_delivery_receipt,
)
from .dissemination_package_v32_2 import assemble_dissemination_package
from .governance_action_execution_v34_3_6 import execute_confirmed_action
from .human_confirmation_framework_v34_2 import build_confirmation_contract
from .recall_retention_lifecycle_v32_6 import (
    record_recall_decision,
    record_retention_decision,
)
from .recipient_feedback_correction_intake_v32_5 import record_correction_intake
from .user_account_workspace_v28_1 import actor_is_administrator

DELEGATES = {
    "audience_recipient_contract_v32_1.record_audience_recipient_contract": record_audience_recipient_contract,
    "dissemination_package_v32_2.assemble_dissemination_package": assemble_dissemination_package,
    "authorization_policy_release_gate_v32_3.record_authorization_policy_decision": record_authorization_policy_decision,
    "delivery_attempt_receipt_ledger_v32_4.record_delivery_attempt": record_delivery_attempt,
    "delivery_attempt_receipt_ledger_v32_4.record_delivery_receipt": record_delivery_receipt,
    "recipient_feedback_correction_intake_v32_5.record_correction_intake": record_correction_intake,
    "recall_retention_lifecycle_v32_6.record_recall_decision": record_recall_decision,
    "recall_retention_lifecycle_v32_6.record_retention_decision": record_retention_decision,
}


def _actor_or_error():
    actor = str(session.get("user") or "")
    if not actor:
        return None, (jsonify({"error": "login required"}), 401)
    if not actor_is_administrator(actor):
        return None, (jsonify({"error": "administrator required"}), 403)
    return actor, None


def register_governance_action_routes_v34_2_6(app):
    @app.post(
        "/api/v1/dissemination-governance/cases/<case_id>/actions/"
        "<action>/confirmation"
    )
    def api_build_confirmation_v34_2(case_id: str, action: str):
        actor, error = _actor_or_error()
        if error:
            return error
        body = request.get_json(silent=True) or {}
        payload = build_confirmation_contract(
            case_id,
            action,
            inputs=dict(body.get("inputs") or {}),
        )
        payload["actor"] = actor
        return jsonify(payload), 200 if payload.get("status") != "blocked" else 422

    @app.post(
        "/api/v1/dissemination-governance/cases/<case_id>/actions/"
        "<action>/execute"
    )
    def api_execute_confirmed_action_v34_3_6(case_id: str, action: str):
        actor, error = _actor_or_error()
        if error:
            return error
        body = request.get_json(silent=True) or {}
        contract = dict(body.get("contract") or {})
        if contract.get("case_id") != case_id or contract.get("action") != action:
            return jsonify({"error": "contract route mismatch"}), 409
        payload = execute_confirmed_action(
            contract,
            confirmation_id=str(body.get("confirmation_id") or ""),
            confirmed=body.get("confirmed") is True,
            actor=actor,
            delegates=DELEGATES,
        )
        code = 200 if payload.get("status") == "executed" else 409
        return jsonify(payload), code

    return app
