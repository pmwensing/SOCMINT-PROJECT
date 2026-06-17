from __future__ import annotations

from flask import jsonify, redirect, render_template, request, session, url_for

from .advanced_search_filters_v27_2 import build_advanced_search_filters
from .saved_search_views_routes_v27_3 import register_saved_search_views_routes_v27_3


def _allowed_case_ids() -> set[str] | None:
    value = session.get("allowed_case_ids")
    if value is None:
        return None
    if not isinstance(value, (list, tuple, set)):
        return set()
    return {str(item).strip() for item in value if str(item).strip()}


def _list(name: str) -> list[str]:
    values = request.args.getlist(name)
    if values:
        return [str(item).strip() for item in values if str(item).strip()]
    plural_names = {
        "type": "types", "case_id": "case_ids", "actor": "actors",
        "status": "statuses", "stage": "stages", "source_action": "source_actions",
        "confidence": "confidences", "priority": "priorities",
        "include_term": "include_terms", "exclude_term": "exclude_terms",
    }
    raw = request.args.get(plural_names.get(name, name + "s"), "")
    return [item.strip() for item in raw.split(",") if item.strip()]


def _exact_fields() -> dict[str, str]:
    return {key[6:]: str(value).strip() for key, value in request.args.items() if key.startswith("field.") and str(value).strip()}


def _limit() -> int:
    try:
        return int(request.args.get("limit", "100"))
    except ValueError:
        return 100


def _build():
    return build_advanced_search_filters(
        request.args.get("q", ""), record_types=_list("type"), case_ids=_list("case_id"),
        actors=_list("actor"), statuses=_list("status"), stages=_list("stage"),
        source_actions=_list("source_action"), confidences=_list("confidence"),
        priorities=_list("priority"), date_from=request.args.get("date_from"),
        date_to=request.args.get("date_to"), include_terms=_list("include_term"),
        exclude_terms=_list("exclude_term"), exact_fields=_exact_fields(),
        sort=request.args.get("sort", "relevance"), allowed_case_ids=_allowed_case_ids(),
        limit=_limit(),
    )


def register_advanced_search_filters_routes_v27_2(app):
    @app.get("/global-search/advanced")
    def advanced_search_filters_get_v27_2():
        if not session.get("user"):
            return redirect(url_for("dashboard.login"))
        return render_template("advanced_search_filters_v27_2.html", title="Advanced Filters and Search Facets", payload=_build())

    @app.get("/api/v1/global-search/advanced")
    def api_advanced_search_filters_get_v27_2():
        if not session.get("user"):
            return jsonify({"error": "login required"}), 401
        return jsonify(_build())

    register_saved_search_views_routes_v27_3(app)
    return app
