from __future__ import annotations

from flask import jsonify, redirect, render_template, session, url_for

from .administration_workspace_routes_v28_0 import register_administration_workspace_routes_v28_0
from .search_reporting_product_review_v27_7 import build_search_reporting_product_review


def register_search_reporting_product_review_routes_v27_7(app):
    @app.get("/global-search/product-review")
    def search_reporting_product_review_get_v27_7():
        if not session.get("user"):
            return redirect(url_for("dashboard.login"))
        payload = build_search_reporting_product_review(routes=list(app.url_map.iter_rules()))
        code = 200 if payload.get("ready") else 503
        return render_template(
            "search_reporting_product_review_v27_7.html",
            title="Search and Reporting Product Review",
            payload=payload,
        ), code

    @app.get("/api/v1/global-search/product-review-checkpoint")
    def api_search_reporting_product_review_get_v27_7():
        if not session.get("user"):
            return jsonify({"error": "login required"}), 401
        payload = build_search_reporting_product_review(routes=list(app.url_map.iter_rules()))
        return jsonify(payload), 200 if payload.get("ready") else 503

    register_administration_workspace_routes_v28_0(app)
    return app
