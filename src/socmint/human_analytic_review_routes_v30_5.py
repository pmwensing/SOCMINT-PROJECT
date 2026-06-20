from __future__ import annotations

from flask import jsonify, request, session

from .human_analytic_review_v30_5 import current_review_decisions, record_human_review, reviews_for_claim
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


def register_human_analytic_review_routes_v30_5(app):
    @app.get("/api/v1/analytic-review/human-reviews")
    def list_current_human_reviews_v30_5():
        actor, error = _authorized()
        if error:
            return error
        return jsonify({
            "schema": "socmint.human_analytic_reviews.v30_5",
            "version": "v30.5.0",
            "reviews": current_review_decisions(),
        })

    @app.get("/api/v1/analytic-review/claims/<claim_id>/human-reviews")
    def list_claim_human_reviews_v30_5(claim_id: str):
        actor, error = _authorized()
        if error:
            return error
        return jsonify({
            "schema": "socmint.human_analytic_review_history.v30_5",
            "version": "v30.5.0",
            "claim_id": claim_id,
            "reviews": reviews_for_claim(claim_id),
        })

    @app.post("/api/v1/analytic-review/claims/<claim_id>/human-reviews")
    def create_human_review_v30_5(claim_id: str):
        actor, error = _authorized()
        if error:
            return error
        data = _payload()
        result = record_human_review(
            actor=actor,
            claim_id=claim_id,
            decision=str(data.get("decision") or ""),
            rationale=str(data.get("rationale") or ""),
            findings=data.get("findings"),
            reason=str(data.get("reason") or ""),
            confirmed=data.get("confirmed") is True,
            ip_address=request.remote_addr,
        )
        code = 200 if result.get("status") == "human_analytic_review_recorded" else 422
        return jsonify(result), code

    return app
