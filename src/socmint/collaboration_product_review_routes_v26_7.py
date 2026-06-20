from __future__ import annotations

from flask import jsonify, redirect, render_template, session, url_for

from .collaboration_product_review_v26_7 import build_collaboration_product_review


def register_collaboration_product_review_routes_v26_7(app):
    @app.get("/collaboration/product-review")
    def collaboration_product_review_get_v26_7():
        if not session.get("user"):
            return redirect(url_for("dashboard.login"))
        payload = build_collaboration_product_review(
            routes=list(app.url_map.iter_rules())
        )
        code = 200 if payload.get("ready") else 503
        return render_template(
            "collaboration_product_review_v26_7.html",
            title="Collaboration Product Review",
            payload=payload,
        ), code

    @app.get("/api/v1/collaboration/product-review-checkpoint")
    def api_collaboration_product_review_get_v26_7():
        if not session.get("user"):
            return jsonify({"error": "login required"}), 401
        payload = build_collaboration_product_review(
            routes=list(app.url_map.iter_rules())
        )
        return jsonify(payload), 200 if payload.get("ready") else 503

    return app
