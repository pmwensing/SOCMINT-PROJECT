from __future__ import annotations

from flask import jsonify, redirect, render_template, request, session, url_for

from .advanced_search_filters_routes_v27_2 import register_advanced_search_filters_routes_v27_2
from .core_record_search_v27_1 import build_core_record_search


def _allowed_case_ids() -> set[str] | None:
    value = session.get("allowed_case_ids")
    if value is None:
        return None
    if not isinstance(value, (list, tuple, set)):
        return set()
    return {str(item).strip() for item in value if str(item).strip()}


def _csv(name: str) -> list[str]:
    values = request.args.getlist(name)
    if values:
        return [str(item).strip() for item in values if str(item).strip()]
    raw = request.args.get(name + "s", "")
    return [item.strip() for item in raw.split(",") if item.strip()]


def _limit() -> int:
    try:
        return int(request.args.get("limit", "100"))
    except ValueError:
        return 100


def _build():
    return build_core_record_search(
        request.args.get("q", ""),
        record_types=_csv("type"),
        case_ids=_csv("case_id"),
        actors=_csv("actor"),
        statuses=_csv("status"),
        allowed_case_ids=_allowed_case_ids(),
        limit=_limit(),
    )


def register_core_record_search_routes_v27_1(app):
    @app.get("/global-search/core-records")
    def core_record_search_get_v27_1():
        if not session.get("user"):
            return redirect(url_for("dashboard.login"))
        return render_template(
            "core_record_search_v27_1.html",
            title="Case, Entity, Evidence, and Finding Search",
            payload=_build(),
        )

    @app.get("/api/v1/global-search/core-records")
    def api_core_record_search_get_v27_1():
        if not session.get("user"):
            return jsonify({"error": "login required"}), 401
        return jsonify(_build())

    register_advanced_search_filters_routes_v27_2(app)
    return app
