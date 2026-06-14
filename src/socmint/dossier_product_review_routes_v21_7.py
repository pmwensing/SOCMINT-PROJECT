from __future__ import annotations

from flask import jsonify, session

from .dossier_product_review_checkpoint_v21_7 import (
    build_dossier_product_review_checkpoint,
)


def register_dossier_product_review_routes_v21_7(app):
    @app.get("/api/v1/dossier-assembly/product-review-checkpoint")
    def api_dossier_product_review_checkpoint_get_v21_7():
        if not session.get("user"):
            return jsonify({"error": "login required"}), 401
        result = build_dossier_product_review_checkpoint(
            routes=list(app.url_map.iter_rules())
        )
        return jsonify(result), 200 if result.get("ready") else 409

    return app
