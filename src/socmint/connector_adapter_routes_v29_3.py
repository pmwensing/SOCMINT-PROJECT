from __future__ import annotations

from flask import jsonify, redirect, render_template, request, session, url_for

from .connector_adapter_contract_v29_3 import (
    create_adapter_contract,
    evaluate_adapter_conformance,
    revise_adapter_contract,
)
from .connector_adapter_workspace_v29_3 import build_connector_adapter_workspace
from .evidence_ingestion_routes_v29_4 import register_evidence_ingestion_routes_v29_4
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


def _code(result: dict, success: str) -> int:
    return 200 if result.get("status") == success else 422


def register_connector_adapter_routes_v29_3(app):
    @app.get("/collection-operations/adapters")
    def connector_adapter_workspace_get_v29_3():
        actor = str(session.get("user") or "")
        if not actor:
            return redirect(url_for("dashboard.login"))
        if not actor_is_administrator(actor):
            return render_template(
                "connector_adapter_contract_v29_3.html",
                title="Connector Normalization and Adapter Contract",
                payload={
                    "status": "forbidden",
                    "error": "administrator required",
                    "adapter_summaries": [],
                    "adapter_findings": [],
                    "adapter_history": [],
                },
            ), 403
        return render_template(
            "connector_adapter_contract_v29_3.html",
            title="Connector Normalization and Adapter Contract",
            payload=build_connector_adapter_workspace(),
        )

    @app.get("/api/v1/collection-operations/adapters")
    def api_connector_adapter_workspace_get_v29_3():
        actor, error = _authorized()
        if error:
            return error
        return jsonify(build_connector_adapter_workspace())

    @app.post("/api/v1/collection-operations/adapters")
    def api_connector_adapter_create_post_v29_3():
        actor, error = _authorized()
        if error:
            return error
        payload = _payload()
        result = create_adapter_contract(
            actor=actor,
            connector_id=str(payload.get("connector_id") or ""),
            capabilities=payload.get("capabilities"),
            input_schema=payload.get("input_schema"),
            output_schema=payload.get("output_schema"),
            authorization_requirements=payload.get("authorization_requirements"),
            rate_limit_metadata=payload.get("rate_limit_metadata"),
            error_classes=payload.get("error_classes"),
            provenance_requirements=payload.get("provenance_requirements"),
            health_contract=payload.get("health_contract"),
            dossier_value_declaration=payload.get("dossier_value_declaration"),
            reason=str(payload.get("reason") or ""),
            confirmed=payload.get("confirmed") is True,
            ip_address=request.remote_addr,
        )
        return jsonify(result), _code(result, "adapter_contract_created")

    @app.post("/api/v1/collection-operations/adapters/<adapter_contract_id>/revise")
    def api_connector_adapter_revise_post_v29_3(adapter_contract_id: str):
        actor, error = _authorized()
        if error:
            return error
        payload = _payload()
        result = revise_adapter_contract(
            adapter_contract_id,
            actor=actor,
            definition=payload.get("definition"),
            reason=str(payload.get("reason") or ""),
            confirmed=payload.get("confirmed") is True,
            ip_address=request.remote_addr,
        )
        return jsonify(result), _code(result, "adapter_contract_revised")

    @app.post("/api/v1/collection-operations/adapters/<adapter_contract_id>/evaluate")
    def api_connector_adapter_evaluate_post_v29_3(adapter_contract_id: str):
        actor, error = _authorized()
        if error:
            return error
        payload = _payload()
        result = evaluate_adapter_conformance(
            actor=actor,
            adapter_contract_id=adapter_contract_id,
            observed_capabilities=payload.get("observed_capabilities"),
            observed_input_schema=payload.get("observed_input_schema"),
            observed_output_schema=payload.get("observed_output_schema"),
            observed_error_classes=payload.get("observed_error_classes"),
            observed_provenance_fields=payload.get("observed_provenance_fields"),
            observed_health_fields=payload.get("observed_health_fields"),
            reason=str(payload.get("reason") or ""),
            confirmed=payload.get("confirmed") is True,
            ip_address=request.remote_addr,
        )
        return jsonify(result), _code(result, "adapter_conformance_evaluated")

    register_evidence_ingestion_routes_v29_4(app)
    return app
