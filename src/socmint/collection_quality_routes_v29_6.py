from __future__ import annotations

from flask import jsonify, redirect, render_template, request, session, url_for

from .collection_product_review_routes_v29_7 import register_collection_product_review_routes_v29_7
from .collection_quality_v29_6 import assess_collection_quality, review_dossier_contribution
from .collection_quality_workspace_v29_6 import build_collection_quality_workspace
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


def _code(result: dict, expected: str) -> int:
    return 200 if result.get("status") == expected else 422


def register_collection_quality_routes_v29_6(app):
    @app.get("/collection-operations/quality")
    def collection_quality_workspace_get_v29_6():
        actor = str(session.get("user") or "")
        if not actor:
            return redirect(url_for("dashboard.login"))
        if not actor_is_administrator(actor):
            return render_template("collection_quality_v29_6.html", title="Collection Quality, Trust, and Dossier Contribution", payload={"status": "forbidden", "error": "administrator required", "quality_assessments": [], "dossier_contribution_reviews": [], "quality_review_queue": [], "quality_findings": []}), 403
        return render_template("collection_quality_v29_6.html", title="Collection Quality, Trust, and Dossier Contribution", payload=build_collection_quality_workspace())

    @app.get("/api/v1/collection-operations/quality")
    def api_collection_quality_workspace_get_v29_6():
        actor, error = _authorized()
        if error:
            return error
        return jsonify(build_collection_quality_workspace())

    @app.post("/api/v1/collection-operations/evidence/<artifact_id>/quality-assessments")
    def api_collection_quality_assessment_post_v29_6(artifact_id: str):
        actor, error = _authorized()
        if error:
            return error
        payload = _payload()
        result = assess_collection_quality(actor=actor, artifact_id=artifact_id, reason=str(payload.get("reason") or ""), confirmed=payload.get("confirmed") is True, ip_address=request.remote_addr)
        return jsonify(result), _code(result, "collection_quality_assessed")

    @app.post("/api/v1/collection-operations/quality-assessments/<quality_assessment_id>/dossier-contribution")
    def api_dossier_contribution_review_post_v29_6(quality_assessment_id: str):
        actor, error = _authorized()
        if error:
            return error
        payload = _payload()
        result = review_dossier_contribution(actor=actor, quality_assessment_id=quality_assessment_id, decision=str(payload.get("decision") or ""), rationale=str(payload.get("rationale") or ""), confirmed=payload.get("confirmed") is True, ip_address=request.remote_addr)
        return jsonify(result), _code(result, "dossier_contribution_reviewed")

    register_collection_product_review_routes_v29_7(app)
    return app
