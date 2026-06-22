from __future__ import annotations

from flask import jsonify, request, session

from .audience_recipient_contract_v32_1 import (
    audience_contract_history,
    audience_contracts_for_case,
    find_audience_contract,
    record_audience_recipient_contract,
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


def register_audience_recipient_contract_routes_v32_1(app):
    @app.get("/api/v1/dissemination-governance/audience-contracts")
    def list_audience_contracts_v32_1():
        actor, error = _authorized()
        if error:
            return error
        return jsonify(
            {
                "schema": "socmint.audience_recipient_contracts.v32_1",
                "version": "v32.1.0",
                "audience_contracts": audience_contract_history(),
            }
        )

    @app.get(
        "/api/v1/dissemination-governance/cases/<case_id>/audience-contracts"
    )
    def list_case_audience_contracts_v32_1(case_id: str):
        actor, error = _authorized()
        if error:
            return error
        return jsonify(
            {
                "schema": "socmint.case_audience_recipient_contracts.v32_1",
                "version": "v32.1.0",
                "case_id": case_id,
                "audience_contracts": audience_contracts_for_case(case_id),
            }
        )

    @app.get(
        "/api/v1/dissemination-governance/audience-contracts/<audience_contract_id>"
    )
    def get_audience_contract_v32_1(audience_contract_id: str):
        actor, error = _authorized()
        if error:
            return error
        contract = find_audience_contract(audience_contract_id)
        if contract is None:
            return jsonify({"error": "audience contract not found"}), 404
        return jsonify(contract)

    @app.post(
        "/api/v1/dissemination-governance/cases/<case_id>/audience-contracts"
    )
    def create_audience_contract_v32_1(case_id: str):
        actor, error = _authorized()
        if error:
            return error
        data = _payload()
        result = record_audience_recipient_contract(
            actor=actor,
            case_id=case_id,
            audience_name=str(data.get("audience_name") or ""),
            audience_type=str(data.get("audience_type") or ""),
            dissemination_purpose=str(data.get("dissemination_purpose") or ""),
            classification=str(data.get("classification") or ""),
            recipients=data.get("recipients") if isinstance(data.get("recipients"), list) else [],
            reason=str(data.get("reason") or ""),
            confirmed=data.get("confirmed") is True,
            note=str(data.get("note") or ""),
            ip_address=request.remote_addr,
        )
        status = 201 if result.get("status") == "audience_contract_recorded" else 422
        return jsonify(result), status

    return app
