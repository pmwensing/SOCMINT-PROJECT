from __future__ import annotations

from flask import jsonify, request, session

from .source_independence_v36_4 import (
    assess_source_independence,
    current_independence_assessments,
    find_independence_group,
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


def register_source_independence_routes_v36_4(app):
    @app.get("/api/v1/entity-accuracy/source-independence")
    def api_source_independence_get_v36_4():
        _, error = _authorized()
        if error:
            return error
        items = current_independence_assessments()
        return jsonify(
            {
                "schema": "socmint.source_independence_inventory.v36_4",
                "version": "v36.4.0",
                "assessments": items,
                "count": len(items),
                "source_mutated": False,
            }
        )

    @app.post("/api/v1/entity-accuracy/source-independence")
    def api_source_independence_post_v36_4():
        actor, error = _authorized()
        if error:
            return error
        payload = _payload()
        result = assess_source_independence(
            actor=actor,
            case_id=str(payload.get("case_id") or ""),
            source_ids=payload.get("source_ids"),
            relationship=str(payload.get("relationship") or ""),
            signals=payload.get("signals"),
            limitations=payload.get("limitations"),
            reason=str(payload.get("reason") or ""),
            confirmed=payload.get("confirmed") is True,
            ip_address=request.remote_addr,
        )
        code = 200 if result.get("status") == "source_independence_assessed" else 422
        return jsonify(result), code

    @app.get(
        "/api/v1/entity-accuracy/source-independence/"
        "<independence_group_id>"
    )
    def api_source_independence_detail_get_v36_4(
        independence_group_id: str,
    ):
        _, error = _authorized()
        if error:
            return error
        item = find_independence_group(independence_group_id)
        if item is None:
            return jsonify({"error": "source independence group not found"}), 404
        return jsonify(item), 200

    return app
