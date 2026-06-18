from __future__ import annotations

from flask import jsonify, redirect, render_template, request, session, url_for

from .search_reporting_history_audit_v27_6 import build_search_reporting_history_audit
from .search_reporting_product_review_routes_v27_7 import register_search_reporting_product_review_routes_v27_7


def _list(name: str) -> list[str]:
    values = request.args.getlist(name)
    if values:
        return [str(item).strip() for item in values if str(item).strip()]
    plural = {"family": "families", "actor": "actors"}.get(name, name + "s")
    raw = request.args.get(plural, "")
    return [item.strip() for item in raw.split(",") if item.strip()]


def _limit() -> int:
    try:
        return int(request.args.get("limit", "500"))
    except ValueError:
        return 500


def _build():
    return build_search_reporting_history_audit(
        families=_list("family"), actors=_list("actor"), limit=_limit()
    )


def register_search_reporting_history_audit_routes_v27_6(app):
    @app.get("/global-search/history")
    def search_reporting_history_audit_get_v27_6():
        if not session.get("user"):
            return redirect(url_for("dashboard.login"))
        return render_template(
            "search_reporting_history_audit_v27_6.html",
            title="Search, Watchlist, and Reporting History and Audit",
            payload=_build(),
        )

    @app.get("/api/v1/global-search/history")
    def api_search_reporting_history_audit_get_v27_6():
        if not session.get("user"):
            return jsonify({"error": "login required"}), 401
        return jsonify(_build())

    register_search_reporting_product_review_routes_v27_7(app)
    return app
