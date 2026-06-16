from __future__ import annotations

from flask import jsonify, redirect, render_template, request, session, url_for

from .cross_case_correlation_review_v25_1 import (
    correlation_review_history,
    review_correlation_candidate,
)
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


def _workspace() -> dict:
    payload = build_cross_case_intelligence_workspace(
        allowed_case_ids=_allowed_case_ids(),
        minimum_case_count=_minimum_case_count(),
    )
    reviews = {}
    for items in payload.get("correlations", {}).values():
        for item in items:
            correlation_id = str(item.get("correlation_id") or "")
            history = correlation_review_history(correlation_id)
            reviews[correlation_id] = {
                "history": history,
                "latest": history[-1] if history else None,
                "review_count": len(history),
            }
    payload["candidate_reviews"] = reviews
    return payload


def register_cross_case_intelligence_routes_v25_0(app):
    @app.get("/cross-case-intelligence")
    def cross_case_intelligence_workspace_get_v25_0():
        if not session.get("user"):
            return redirect(url_for("dashboard.login"))
        return render_template(
            "cross_case_intelligence_workspace_v25_0.html",
            title="Cross-Case Intelligence Workspace",
            payload=_workspace(),
        )

    @app.get("/api/v1/cross-case-intelligence")
    def api_cross_case_intelligence_workspace_get_v25_0():
        if not session.get("user"):
            return jsonify({"error": "login required"}), 401
        return jsonify(_workspace())

    @app.get("/api/v1/cross-case-intelligence/<correlation_id>/reviews")
    def api_cross_case_correlation_reviews_get_v25_1(correlation_id: str):
        if not session.get("user"):
            return jsonify({"error": "login required"}), 401
        return jsonify({
            "correlation_id": correlation_id,
            "history": correlation_review_history(correlation_id),
        })

    @app.post("/api/v1/cross-case-intelligence/<correlation_id>/review")
    def api_cross_case_correlation_review_post_v25_1(correlation_id: str):
        if not session.get("user"):
            return jsonify({"error": "login required"}), 401
        payload = request.get_json(silent=True) or {}
        result = review_correlation_candidate(
            correlation_id,
            category=str(payload.get("category") or ""),
            decision=str(payload.get("decision") or ""),
            reason=str(payload.get("reason") or ""),
            reviewer=str(session.get("user") or "unknown"),
            confirmed=payload.get("confirmed") is True,
            split_groups=payload.get("split_groups"),
            allowed_case_ids=_allowed_case_ids(),
            minimum_case_count=_minimum_case_count(),
            ip_address=request.remote_addr,
        )
        return jsonify(result), 200 if result.get("status") == "correlation_review_recorded" else 422

    return app
