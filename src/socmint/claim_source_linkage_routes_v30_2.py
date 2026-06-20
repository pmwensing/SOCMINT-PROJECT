from __future__ import annotations

from flask import jsonify, request, session

from .claim_source_linkage_v30_2 import claim_linkages, link_claim_sources
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


def register_claim_source_linkage_routes_v30_2(app):
    @app.get("/api/v1/analytic-review/claims/<claim_id>/source-linkages")
    def api_claim_source_linkages_get_v30_2(claim_id: str):
        actor, error = _authorized()
        if error:
            return error
        return jsonify({
            "schema": "socmint.claim_source_linkages.v30_2",
            "version": "v30.2.0",
            "claim_id": claim_id,
            "linkages": claim_linkages(claim_id),
        })

    @app.post("/api/v1/analytic-review/claims/<claim_id>/source-linkages")
    def api_claim_source_linkage_post_v30_2(claim_id: str):
        actor, error = _authorized()
        if error:
            return error
        payload = _payload()
        result = link_claim_sources(
            actor=actor,
            claim_id=claim_id,
            artifact_ids=payload.get("artifact_ids"),
            observation_ids=payload.get("observation_ids"),
            reason=str(payload.get("reason") or ""),
            confirmed=payload.get("confirmed") is True,
            ip_address=request.remote_addr,
        )
        return jsonify(result), 200 if result.get("status") == "corroboration_claim_sources_linked" else 422

    return app
