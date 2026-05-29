from __future__ import annotations

from flask import jsonify, request

from .normalization_promote_confirmed_v13 import promote_confirmed_item


def register_normalization_promote_confirmed_routes(app) -> None:
    if "api_normalization_promote_confirmed_v13" in app.view_functions:
        return

    from .dashboard import login_required

    @login_required
    def api_normalization_promote_confirmed_v13():
        payload = request.get_json(silent=True) or dict(request.form.items())
        result = promote_confirmed_item(
            kind=str(payload.get("kind") or ""),
            item_id=int(payload.get("id") or 0),
        )
        return jsonify(result)

    app.add_url_rule(
        "/api/v1/review/normalization-promote",
        endpoint="api_normalization_promote_confirmed_v13",
        view_func=api_normalization_promote_confirmed_v13,
        methods=["POST"],
    )
