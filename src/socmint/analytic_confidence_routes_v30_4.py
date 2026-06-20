from __future__ import annotations

from flask import jsonify, request, session

from .analytic_confidence_v30_4 import assess_confidence, confidence_assessments
from .human_analytic_review_routes_v30_5 import register_human_analytic_review_routes_v30_5
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


def register_analytic_confidence_routes_v30_4(app):
    @app.get("/api/v1/analytic-review/claims/<claim_id>/confidence-assessments")
    def list_confidence_assessments_v30_4(claim_id: str):
        actor, error = _authorized()
        if error:
            return error
        return jsonify({"version": "v30.4.0", "claim_id": claim_id, "assessments": confidence_assessments(claim_id)})

    @app.post("/api/v1/analytic-review/claims/<claim_id>/confidence-assessments")
    def create_confidence_assessment_v30_4(claim_id: str):
        actor, error = _authorized()
        if error:
            return error
        data = _payload()
        result = assess_confidence(
            actor=actor,
            claim_id=claim_id,
            methodology=str(data.get("methodology") or ""),
            limitations=data.get("limitations"),
            reason=str(data.get("reason") or ""),
            confirmed=data.get("confirmed") is True,
            ip_address=request.remote_addr,
        )
        code = 200 if result.get("status") == "analytic_confidence_assessed" else 422
        return jsonify(result), code

    register_human_analytic_review_routes_v30_5(app)
    return app
