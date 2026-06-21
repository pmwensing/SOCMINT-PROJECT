from __future__ import annotations

from flask import jsonify, redirect, render_template, session, url_for

from .cross_case_intelligence_metrics_v25_6 import (
    build_cross_case_intelligence_metrics,
)


def _allowed_case_ids() -> set[str] | None:
    value = session.get("allowed_case_ids")
    if value is None:
        return None
    if not isinstance(value, (list, tuple, set)):
        return set()
    return {str(item).strip() for item in value if str(item).strip()}


def register_cross_case_intelligence_metrics_routes_v25_6(app):
    @app.get("/cross-case-intelligence/metrics")
    def cross_case_intelligence_metrics_get_v25_6():
        if not session.get("user"):
            return redirect(url_for("dashboard.login"))
        return render_template(
            "cross_case_intelligence_metrics_v25_6.html",
            title="Cross-Case Intelligence Metrics and Confidence",
            payload=build_cross_case_intelligence_metrics(
                allowed_case_ids=_allowed_case_ids()
            ),
        )

    @app.get("/api/v1/cross-case-intelligence/metrics")
    def api_cross_case_intelligence_metrics_get_v25_6():
        if not session.get("user"):
            return jsonify({"error": "login required"}), 401
        return jsonify(
            build_cross_case_intelligence_metrics(allowed_case_ids=_allowed_case_ids())
        )

    return app
