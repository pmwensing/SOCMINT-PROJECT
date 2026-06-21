from __future__ import annotations

from flask import jsonify, redirect, render_template, session, url_for

from .analytic_review_routes_v30_0 import register_analytic_review_routes_v30_0
from .collection_product_review_v29_7 import build_collection_product_review
from .user_account_workspace_v28_1 import actor_is_administrator


def register_collection_product_review_routes_v29_7(app):
    @app.get("/collection-operations/product-review")
    def collection_product_review_get_v29_7():
        actor = str(session.get("user") or "")
        if not actor:
            return redirect(url_for("dashboard.login"))
        if not actor_is_administrator(actor):
            return render_template(
                "collection_product_review_v29_7.html",
                title="Collection Product Review",
                payload={
                    "status": "forbidden",
                    "error": "administrator required",
                    "ready": False,
                    "blockers": [],
                },
            ), 403
        payload = build_collection_product_review(routes=list(app.url_map.iter_rules()))
        return render_template(
            "collection_product_review_v29_7.html",
            title="Collection Product Review",
            payload=payload,
        ), 200 if payload.get("ready") else 503

    @app.get("/api/v1/collection-operations/product-review-checkpoint")
    def api_collection_product_review_get_v29_7():
        actor = str(session.get("user") or "")
        if not actor:
            return jsonify({"error": "login required"}), 401
        if not actor_is_administrator(actor):
            return jsonify({"error": "administrator required"}), 403
        payload = build_collection_product_review(routes=list(app.url_map.iter_rules()))
        return jsonify(payload), 200 if payload.get("ready") else 503

    register_analytic_review_routes_v30_0(app)
    return app
