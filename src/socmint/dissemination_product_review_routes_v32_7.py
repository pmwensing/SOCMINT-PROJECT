from __future__ import annotations

from flask import jsonify, redirect, render_template, session, url_for

from .case_governance_snapshot_routes_v33_1 import (
    register_case_governance_snapshot_routes_v33_1,
)
from .dissemination_product_review_v32_7 import (
    build_dissemination_product_review,
)
from .user_account_workspace_v28_1 import actor_is_administrator


def register_dissemination_product_review_routes_v32_7(app):
    @app.get("/dissemination-governance/product-review")
    def dissemination_product_review_get_v32_7():
        actor = str(session.get("user") or "")
        if not actor:
            return redirect(url_for("dashboard.login"))
        if not actor_is_administrator(actor):
            return render_template(
                "dissemination_product_review_v32_7.html",
                title="Dissemination Product Review",
                payload={
                    "status": "forbidden",
                    "error": "administrator required",
                    "ready": False,
                    "blockers": [],
                },
            ), 403
        payload = build_dissemination_product_review(
            routes=list(app.url_map.iter_rules())
        )
        return render_template(
            "dissemination_product_review_v32_7.html",
            title="Dissemination Product Review",
            payload=payload,
        ), 200 if payload.get("ready") else 503

    @app.get(
        "/api/v1/dissemination-governance/product-review-checkpoint"
    )
    def api_dissemination_product_review_get_v32_7():
        actor = str(session.get("user") or "")
        if not actor:
            return jsonify({"error": "login required"}), 401
        if not actor_is_administrator(actor):
            return jsonify({"error": "administrator required"}), 403
        payload = build_dissemination_product_review(
            routes=list(app.url_map.iter_rules())
        )
        return jsonify(payload), 200 if payload.get("ready") else 503

    register_case_governance_snapshot_routes_v33_1(app)
    return app
