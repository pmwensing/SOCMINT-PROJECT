from __future__ import annotations

from flask import jsonify, session

from .case_closure_product_review_v23_7 import build_case_closure_product_review


def register_case_closure_product_review_routes_v23_7(app):
    @app.get("/api/v1/case-closure/product-review-checkpoint")
    def api_case_closure_product_review_checkpoint_get_v23_7():
        if not session.get("user"):
            return jsonify({"error": "login required"}), 401
        result = build_case_closure_product_review(
            routes=list(app.url_map.iter_rules())
        )
        return jsonify(result), 200 if result.get("ready") else 422

    return app
