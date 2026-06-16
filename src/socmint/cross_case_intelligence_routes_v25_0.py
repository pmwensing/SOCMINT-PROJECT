from __future__ import annotations

from flask import jsonify, redirect, render_template, request, session, url_for

from .cross_case_intelligence_workspace_v25_0 import (
    build_cross_case_intelligence_workspace,
)


def _allowed_case_ids() -> set[str] | None:
    value = session.get("allowed_case_ids")
    if value is None:
        return None
    if not isinstance(value, (list, tuple, set)):
        return set()
    return {str(item).strip() for item in value if str(item).strip()}


def _minimum_case_count() -> int:
    try:
        return max(2, int(request.args.get("minimum_case_count", "2")))
    except (TypeError, ValueError):
        return 2


def register_cross_case_intelligence_routes_v25_0(app):
    @app.get("/cross-case-intelligence")
    def cross_case_intelligence_workspace_get_v25_0():
        if not session.get("user"):
            return redirect(url_for("dashboard.login"))
        payload = build_cross_case_intelligence_workspace(
            allowed_case_ids=_allowed_case_ids(),
            minimum_case_count=_minimum_case_count(),
        )
        return render_template(
            "cross_case_intelligence_workspace_v25_0.html",
            title="Cross-Case Intelligence Workspace",
            payload=payload,
        )

    @app.get("/api/v1/cross-case-intelligence")
    def api_cross_case_intelligence_workspace_get_v25_0():
        if not session.get("user"):
            return jsonify({"error": "login required"}), 401
        return jsonify(
            build_cross_case_intelligence_workspace(
                allowed_case_ids=_allowed_case_ids(),
                minimum_case_count=_minimum_case_count(),
            )
        )

    return app
