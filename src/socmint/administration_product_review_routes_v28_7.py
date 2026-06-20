from __future__ import annotations

from flask import jsonify, redirect, render_template, session, url_for

from .administration_product_review_v28_7 import build_administration_product_review
from .collection_operations_routes_v29_0 import (
    register_collection_operations_routes_v29_0,
)


def register_administration_product_review_routes_v28_7(app):
    @app.get("/administration/product-review")
    def administration_product_review_get_v28_7():
        if not session.get("user"):
            return redirect(url_for("dashboard.login"))
        payload = build_administration_product_review(
            routes=list(app.url_map.iter_rules())
        )
        return render_template(
            "administration_product_review_v28_7.html",
            title="Administration Product Review",
            payload=payload,
        ), 200 if payload.get("ready") else 503

    @app.get("/api/v1/administration/product-review-checkpoint")
    def api_administration_product_review_get_v28_7():
        if not session.get("user"):
            return jsonify({"error": "login required"}), 401
        payload = build_administration_product_review(
            routes=list(app.url_map.iter_rules())
        )
        return jsonify(payload), 200 if payload.get("ready") else 503

    register_collection_operations_routes_v29_0(app)
    return app
