from __future__ import annotations

from flask import jsonify, request

from .normalization_review_decisions_v13 import apply_normalization_review_decision


def register_normalization_review_update_routes(app) -> None:
    if "api_normalization_review_update_v13" in app.view_functions:
        return

    from .dashboard import login_required

    @login_required
    def api_normalization_review_update_v13():
        payload = request.get_json(silent=True) or {}
        result = apply_normalization_review_decision(
            kind=str(payload.get("kind") or ""),
            item_id=int(payload.get("id") or 0),
            decision=str(payload.get("review_state") or payload.get("decision") or ""),
            actor=str(payload.get("actor") or ""),
            note=payload.get("note"),
        )
        return jsonify(result)

    app.add_url_rule(
        "/api/v1/review/normalization-update",
        endpoint="api_normalization_review_update_v13",
        view_func=api_normalization_review_update_v13,
        methods=["POST"],
    )
