from __future__ import annotations

from flask import jsonify, session

from .dossier_release_product_review_v22_7 import build_dossier_release_product_review


def register_dossier_release_product_review_routes_v22_7(app):
    @app.get("/api/v1/dossier-release/product-review-checkpoint")
    def api_dossier_release_product_review_checkpoint_get_v22_7():
        if not session.get("user"):
            return jsonify({"error": "login required"}), 401
        result = build_dossier_release_product_review(
            routes=list(app.url_map.iter_rules())
        )
        return jsonify(result), 200 if result.get("ready") else 422

    return app
