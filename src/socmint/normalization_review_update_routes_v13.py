from __future__ import annotations

from flask import jsonify, redirect, request

from .normalization_review_decisions_v13 import apply_normalization_review_decision


def normalization_update_payload() -> dict:
    payload = request.get_json(silent=True)
    if isinstance(payload, dict) and payload:
        return payload
    return dict(request.form.items())


def normalization_update_wants_json() -> bool:
    if request.is_json:
        return True
    accept = request.headers.get("Accept", "")
    return "application/json" in accept and "text/html" not in accept


def normalization_update_return_target() -> str:
    return request.headers.get("Referer") or "/review/normalization-queue"


def register_normalization_review_update_routes(app) -> None:
    if "api_normalization_review_update_v13" in app.view_functions:
        return

    from .dashboard import login_required

    @login_required
    def api_normalization_review_update_v13():
        payload = normalization_update_payload()
        result = apply_normalization_review_decision(
            kind=str(payload.get("kind") or ""),
            item_id=int(payload.get("id") or 0),
            decision=str(payload.get("review_state") or payload.get("decision") or ""),
            actor=str(payload.get("actor") or ""),
            note=payload.get("note"),
        )
        if normalization_update_wants_json():
            return jsonify(result)
        return redirect(normalization_update_return_target())

    app.add_url_rule(
        "/api/v1/review/normalization-update",
        endpoint="api_normalization_review_update_v13",
        view_func=api_normalization_review_update_v13,
        methods=["POST"],
    )
