from __future__ import annotations

from flask import jsonify, redirect, render_template, request, session, url_for

from .core_record_search_routes_v27_1 import register_core_record_search_routes_v27_1
from .global_investigation_search_v27_0 import build_global_investigation_search


def _allowed_case_ids() -> set[str] | None:
    value = session.get("allowed_case_ids")
    if value is None:
        return None
    if not isinstance(value, (list, tuple, set)):
        return set()
    return {str(item).strip() for item in value if str(item).strip()}


def _types() -> list[str]:
    values = request.args.getlist("type")
    if not values:
        raw = request.args.get("types", "")
        values = [item.strip() for item in raw.split(",") if item.strip()]
    return values


def _limit() -> int:
    try:
        return int(request.args.get("limit", "100"))
    except ValueError:
        return 100


def register_global_investigation_search_routes_v27_0(app):
    @app.get("/global-search")
    def global_investigation_search_get_v27_0():
        if not session.get("user"):
            return redirect(url_for("dashboard.login"))
        payload = build_global_investigation_search(
            request.args.get("q", ""),
            result_types=_types(),
            allowed_case_ids=_allowed_case_ids(),
            limit=_limit(),
        )
        return render_template(
            "global_investigation_search_v27_0.html",
            title="Global Investigation Search",
            payload=payload,
        )

    @app.get("/api/v1/global-search")
    def api_global_investigation_search_get_v27_0():
        if not session.get("user"):
            return jsonify({"error": "login required"}), 401
        return jsonify(
            build_global_investigation_search(
                request.args.get("q", ""),
                result_types=_types(),
                allowed_case_ids=_allowed_case_ids(),
                limit=_limit(),
            )
        )

    register_core_record_search_routes_v27_1(app)
    return app
