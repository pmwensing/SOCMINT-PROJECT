from __future__ import annotations

from flask import jsonify, request, session

from .dissemination_product_review_routes_v32_7 import (
    register_dissemination_product_review_routes_v32_7,
)
from .recall_retention_lifecycle_v32_6 import (
    find_recall_decision,
    find_retention_decision,
    lifecycle_history,
    lifecycle_snapshot,
    recall_decision_history,
    recalls_for_correction,
    recalls_for_package,
    record_recall_decision,
    record_retention_decision,
    retention_decision_history,
    retentions_for_case,
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


def register_recall_retention_lifecycle_routes_v32_6(app):
    @app.get("/api/v1/dissemination-governance/recall-decisions")
    def list_recall_decisions_v32_6():
        actor, error = _authorized()
        if error:
            return error
        return jsonify({
            "schema": "socmint.recall_decisions.v32_6",
            "version": "v32.6.0",
            "recall_decisions": recall_decision_history(),
        })

    @app.get("/api/v1/dissemination-governance/recall-decisions/<recall_id>")
    def get_recall_decision_v32_6(recall_id: str):
        actor, error = _authorized()
        if error:
            return error
        value = find_recall_decision(recall_id)
        if value is None:
            return jsonify({"error": "recall decision not found"}), 404
        return jsonify(value)

    @app.get(
        "/api/v1/dissemination-governance/packages/"
        "<package_id>/recall-decisions"
    )
    def list_package_recall_decisions_v32_6(package_id: str):
        actor, error = _authorized()
        if error:
            return error
        return jsonify({
            "schema": "socmint.package_recall_decisions.v32_6",
            "version": "v32.6.0",
            "dissemination_package_id": package_id,
            "recall_decisions": recalls_for_package(package_id),
        })

    @app.get(
        "/api/v1/dissemination-governance/correction-intakes/"
        "<correction_id>/recall-decisions"
    )
    def list_correction_recall_decisions_v32_6(correction_id: str):
        actor, error = _authorized()
        if error:
            return error
        return jsonify({
            "schema": "socmint.correction_recall_decisions.v32_6",
            "version": "v32.6.0",
            "correction_intake_id": correction_id,
            "recall_decisions": recalls_for_correction(correction_id),
        })

    @app.post(
        "/api/v1/dissemination-governance/correction-intakes/"
        "<correction_id>/recall-decisions"
    )
    def create_recall_decision_v32_6(correction_id: str):
        actor, error = _authorized()
        if error:
            return error
        data = _payload()
        result = record_recall_decision(
            reviewer=actor,
            correction_intake_id=correction_id,
            decision=str(data.get("decision") or ""),
            reason=str(data.get("reason") or ""),
            confirmed=data.get("confirmed") is True,
            effective_at=str(data.get("effective_at") or ""),
            replacement_published_revision_id=str(
                data.get("replacement_published_revision_id") or ""
            ),
            note=str(data.get("note") or ""),
            ip_address=request.remote_addr,
        )
        status = 201 if result.get("status") == "recall_decision_recorded" else 422
        return jsonify(result), status

    @app.get("/api/v1/dissemination-governance/retention-decisions")
    def list_retention_decisions_v32_6():
        actor, error = _authorized()
        if error:
            return error
        return jsonify({
            "schema": "socmint.retention_decisions.v32_6",
            "version": "v32.6.0",
            "retention_decisions": retention_decision_history(),
        })

    @app.get(
        "/api/v1/dissemination-governance/retention-decisions/<retention_id>"
    )
    def get_retention_decision_v32_6(retention_id: str):
        actor, error = _authorized()
        if error:
            return error
        value = find_retention_decision(retention_id)
        if value is None:
            return jsonify({"error": "retention decision not found"}), 404
        return jsonify(value)

    @app.get(
        "/api/v1/dissemination-governance/cases/"
        "<case_id>/retention-decisions"
    )
    def list_case_retention_decisions_v32_6(case_id: str):
        actor, error = _authorized()
        if error:
            return error
        return jsonify({
            "schema": "socmint.case_retention_decisions.v32_6",
            "version": "v32.6.0",
            "case_id": case_id,
            "retention_decisions": retentions_for_case(case_id),
        })

    @app.post(
        "/api/v1/dissemination-governance/cases/"
        "<case_id>/retention-decisions"
    )
    def create_retention_decision_v32_6(case_id: str):
        actor, error = _authorized()
        if error:
            return error
        data = _payload()
        result = record_retention_decision(
            reviewer=actor,
            case_id=case_id,
            disposition=str(data.get("disposition") or ""),
            policy_id=str(data.get("policy_id") or ""),
            reason=str(data.get("reason") or ""),
            confirmed=data.get("confirmed") is True,
            review_at=str(data.get("review_at") or ""),
            note=str(data.get("note") or ""),
            ip_address=request.remote_addr,
        )
        status = (
            201 if result.get("status") == "retention_decision_recorded" else 422
        )
        return jsonify(result), status

    @app.get("/api/v1/dissemination-governance/lifecycle-history")
    def list_lifecycle_history_v32_6():
        actor, error = _authorized()
        if error:
            return error
        case_id = str(request.args.get("case_id") or "").strip() or None
        return jsonify({
            "schema": "socmint.lifecycle_history.v32_6",
            "version": "v32.6.0",
            "case_id": case_id,
            "lifecycle_history": lifecycle_history(case_id),
        })

    @app.get(
        "/api/v1/dissemination-governance/cases/"
        "<case_id>/lifecycle-history"
    )
    def get_case_lifecycle_history_v32_6(case_id: str):
        actor, error = _authorized()
        if error:
            return error
        return jsonify({
            "schema": "socmint.case_lifecycle_history.v32_6",
            "version": "v32.6.0",
            "case_id": case_id,
            "snapshot": lifecycle_snapshot(case_id),
            "lifecycle_history": lifecycle_history(case_id),
        })

    register_dissemination_product_review_routes_v32_7(app)
    return app
