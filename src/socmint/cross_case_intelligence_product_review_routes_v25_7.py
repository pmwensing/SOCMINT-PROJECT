from __future__ import annotations

from flask import jsonify, redirect, render_template, session, url_for

from .cross_case_intelligence_product_review_v25_7 import (
    build_cross_case_intelligence_product_review,
)


def register_cross_case_intelligence_product_review_routes_v25_7(app):
    @app.get("/cross-case-intelligence/product-review")
    def cross_case_intelligence_product_review_get_v25_7():
        if not session.get("user"):
            return redirect(url_for("dashboard.login"))
        payload = build_cross_case_intelligence_product_review(
            routes=list(app.url_map.iter_rules())
        )
        return render_template(
            "cross_case_intelligence_product_review_v25_7.html",
            title="Cross-Case Intelligence Product Review",
            payload=payload,
        ), 200 if payload.get("ready") else 503

    @app.get("/api/v1/cross-case-intelligence/product-review-checkpoint")
    def api_cross_case_intelligence_product_review_get_v25_7():
        if not session.get("user"):
            return jsonify({"error": "login required"}), 401
        payload = build_cross_case_intelligence_product_review(
            routes=list(app.url_map.iter_rules())
        )
        return jsonify(payload), 200 if payload.get("ready") else 503

    return app
