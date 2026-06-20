from __future__ import annotations

from flask import jsonify, request, session

from .analytic_dossier_contribution_v30_6 import (
    contributions_for_claim,
    current_contribution_decisions,
    review_dossier_contribution,
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


def register_analytic_dossier_contribution_routes_v30_6(app):
    @app.get("/api/v1/analytic-review/dossier-contributions")
    def list_current_dossier_contributions_v30_6():
        actor, error = _authorized()
        if error:
            return error
        return jsonify({
            "schema": "socmint.analytic_dossier_contributions.v30_6",
            "version": "v30.6.0",
            "contributions": current_contribution_decisions(),
        })

    @app.get("/api/v1/analytic-review/claims/<claim_id>/dossier-contributions")
    def list_claim_dossier_contributions_v30_6(claim_id: str):
        actor, error = _authorized()
        if error:
            return error
        return jsonify({
            "schema": "socmint.analytic_dossier_contribution_history.v30_6",
            "version": "v30.6.0",
            "claim_id": claim_id,
            "contributions": contributions_for_claim(claim_id),
        })

    @app.post("/api/v1/analytic-review/claims/<claim_id>/dossier-contributions")
    def create_dossier_contribution_review_v30_6(claim_id: str):
        actor, error = _authorized()
        if error:
            return error
        data = _payload()
        result = review_dossier_contribution(
            actor=actor,
            claim_id=claim_id,
            decision=str(data.get("decision") or ""),
            target_section=str(data.get("target_section") or ""),
            rationale=str(data.get("rationale") or ""),
            reason=str(data.get("reason") or ""),
            confirmed=data.get("confirmed") is True,
            ip_address=request.remote_addr,
        )
        code = 200 if result.get("status") == "analytic_dossier_contribution_reviewed" else 422
        return jsonify(result), code

    return app
