from __future__ import annotations

from flask import jsonify, redirect, render_template, session, url_for

from .analytic_product_review_v30_7 import build_analytic_product_review
from .user_account_workspace_v28_1 import actor_is_administrator


def register_analytic_product_review_routes_v30_7(app):
    @app.get("/analytic-review/product-review")
    def analytic_product_review_get_v30_7():
        actor = str(session.get("user") or "")
        if not actor:
            return redirect(url_for("dashboard.login"))
        if not actor_is_administrator(actor):
            return render_template(
                "analytic_product_review_v30_7.html",
                title="Analytic Product Review",
                payload={"status": "forbidden", "error": "administrator required", "ready": False, "blockers": []},
            ), 403
        payload = build_analytic_product_review(routes=list(app.url_map.iter_rules()))
        return render_template("analytic_product_review_v30_7.html", title="Analytic Product Review", payload=payload), 200 if payload.get("ready") else 503

    @app.get("/api/v1/analytic-review/product-review-checkpoint")
    def api_analytic_product_review_get_v30_7():
        actor = str(session.get("user") or "")
        if not actor:
            return jsonify({"error": "login required"}), 401
        if not actor_is_administrator(actor):
            return jsonify({"error": "administrator required"}), 403
        payload = build_analytic_product_review(routes=list(app.url_map.iter_rules()))
        return jsonify(payload), 200 if payload.get("ready") else 503

    return app
