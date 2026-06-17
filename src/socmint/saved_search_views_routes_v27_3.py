from __future__ import annotations

from flask import jsonify, redirect, render_template, request, session, url_for

from .saved_search_view_events_v27_3 import create_view, deactivate_view, revise_view
from .saved_search_views_workspace_v27_3 import build_saved_views_workspace, run_saved_view
from .watchlist_monitoring_routes_v27_4 import register_watchlist_monitoring_routes_v27_4


def _allowed_case_ids() -> set[str] | None:
    value = session.get("allowed_case_ids")
    if value is None:
        return None
    if not isinstance(value, (list, tuple, set)):
        return set()
    return {str(item).strip() for item in value if str(item).strip()}


def _payload() -> dict:
    value = request.get_json(silent=True)
    return value if isinstance(value, dict) else {}


def _filters(payload: dict) -> dict:
    value = payload.get("filters")
    return dict(value) if isinstance(value, dict) else {}


def _code(result: dict, success: str) -> int:
    return 200 if result.get("status") == success else 422


def register_saved_search_views_routes_v27_3(app):
    @app.get("/global-search/saved-views")
    def saved_search_views_get_v27_3():
        if not session.get("user"):
            return redirect(url_for("dashboard.login"))
        return render_template(
            "saved_search_views_v27_3.html",
            title="Saved Views and Search Presets",
            payload=build_saved_views_workspace(str(session.get("user"))),
        )

    @app.get("/api/v1/global-search/saved-views")
    def api_saved_search_views_get_v27_3():
        if not session.get("user"):
            return jsonify({"error": "login required"}), 401
        return jsonify(build_saved_views_workspace(str(session.get("user"))))

    @app.post("/api/v1/global-search/saved-views")
    def api_saved_search_view_post_v27_3():
        if not session.get("user"):
            return jsonify({"error": "login required"}), 401
        payload = _payload()
        result = create_view(
            name=str(payload.get("name") or ""), owner=str(session.get("user")),
            query=str(payload.get("query") or ""), filters=_filters(payload),
            visibility=str(payload.get("visibility") or "private"),
            description=str(payload.get("description") or ""),
            confirmed=payload.get("confirmed") is True, ip_address=request.remote_addr,
        )
        return jsonify(result), _code(result, "saved_view_created")

    @app.post("/api/v1/global-search/saved-views/<view_id>/revise")
    def api_saved_search_view_revise_post_v27_3(view_id: str):
        if not session.get("user"):
            return jsonify({"error": "login required"}), 401
        payload = _payload()
        result = revise_view(
            view_id, actor=str(session.get("user")), name=str(payload.get("name") or ""),
            query=str(payload.get("query") or ""), filters=_filters(payload),
            visibility=str(payload.get("visibility") or "private"),
            description=str(payload.get("description") or ""), reason=str(payload.get("reason") or ""),
            confirmed=payload.get("confirmed") is True, ip_address=request.remote_addr,
        )
        return jsonify(result), _code(result, "saved_view_revised")

    @app.post("/api/v1/global-search/saved-views/<view_id>/deactivate")
    def api_saved_search_view_deactivate_post_v27_3(view_id: str):
        if not session.get("user"):
            return jsonify({"error": "login required"}), 401
        payload = _payload()
        result = deactivate_view(
            view_id, actor=str(session.get("user")), reason=str(payload.get("reason") or ""),
            confirmed=payload.get("confirmed") is True, ip_address=request.remote_addr,
        )
        return jsonify(result), _code(result, "saved_view_deactivated")

    @app.get("/api/v1/global-search/saved-views/<view_id>/run")
    def api_saved_search_view_run_get_v27_3(view_id: str):
        if not session.get("user"):
            return jsonify({"error": "login required"}), 401
        try:
            limit = int(request.args.get("limit", "100"))
        except ValueError:
            limit = 100
        result = run_saved_view(
            view_id, user_identity=str(session.get("user")),
            allowed_case_ids=_allowed_case_ids(), limit=limit,
        )
        return jsonify(result), _code(result, "saved_view_executed")

    register_watchlist_monitoring_routes_v27_4(app)
    return app
