from __future__ import annotations

from flask import jsonify, redirect, render_template, request, session, url_for

from .report_builder_routes_v27_5 import register_report_builder_routes_v27_5
from .watchlist_monitoring_events_v27_4 import create_watchlist, set_watchlist_status
from .watchlist_monitoring_workspace_v27_4 import build_watchlist_workspace, run_watchlist_monitoring


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


def _code(result: dict, success: str) -> int:
    return 200 if result.get("status") == success else 422


def register_watchlist_monitoring_routes_v27_4(app):
    @app.get("/global-search/watchlists")
    def watchlist_monitoring_get_v27_4():
        if not session.get("user"):
            return redirect(url_for("dashboard.login"))
        return render_template(
            "watchlist_monitoring_v27_4.html",
            title="Watchlists and Scheduled Search Monitoring",
            payload=build_watchlist_workspace(str(session.get("user"))),
        )

    @app.get("/api/v1/global-search/watchlists")
    def api_watchlist_monitoring_get_v27_4():
        if not session.get("user"):
            return jsonify({"error": "login required"}), 401
        return jsonify(build_watchlist_workspace(str(session.get("user"))))

    @app.post("/api/v1/global-search/watchlists")
    def api_watchlist_create_post_v27_4():
        if not session.get("user"):
            return jsonify({"error": "login required"}), 401
        payload = _payload()
        result = create_watchlist(
            name=str(payload.get("name") or ""), owner=str(session.get("user")),
            saved_view_id=str(payload.get("saved_view_id") or ""), cadence=str(payload.get("cadence") or "manual"),
            notification_rule=str(payload.get("notification_rule") or "any_change"),
            description=str(payload.get("description") or ""), confirmed=payload.get("confirmed") is True,
            ip_address=request.remote_addr,
        )
        return jsonify(result), _code(result, "watchlist_created")

    @app.post("/api/v1/global-search/watchlists/<watchlist_id>/pause")
    def api_watchlist_pause_post_v27_4(watchlist_id: str):
        if not session.get("user"):
            return jsonify({"error": "login required"}), 401
        payload = _payload()
        result = set_watchlist_status(watchlist_id, actor=str(session.get("user")), status="paused", reason=str(payload.get("reason") or ""), confirmed=payload.get("confirmed") is True, ip_address=request.remote_addr)
        return jsonify(result), _code(result, "watchlist_paused")

    @app.post("/api/v1/global-search/watchlists/<watchlist_id>/resume")
    def api_watchlist_resume_post_v27_4(watchlist_id: str):
        if not session.get("user"):
            return jsonify({"error": "login required"}), 401
        payload = _payload()
        result = set_watchlist_status(watchlist_id, actor=str(session.get("user")), status="active", reason=str(payload.get("reason") or ""), confirmed=payload.get("confirmed") is True, ip_address=request.remote_addr)
        return jsonify(result), _code(result, "watchlist_resumed")

    @app.post("/api/v1/global-search/watchlists/<watchlist_id>/run")
    def api_watchlist_run_post_v27_4(watchlist_id: str):
        if not session.get("user"):
            return jsonify({"error": "login required"}), 401
        payload = _payload()
        try:
            limit = int(payload.get("limit", 100))
        except (TypeError, ValueError):
            limit = 100
        result = run_watchlist_monitoring(watchlist_id, user_identity=str(session.get("user")), allowed_case_ids=_allowed_case_ids(), limit=limit, ip_address=request.remote_addr)
        return jsonify(result), _code(result, "watchlist_monitoring_completed")

    register_report_builder_routes_v27_5(app)
    return app
