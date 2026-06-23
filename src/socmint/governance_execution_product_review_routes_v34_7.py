from __future__ import annotations

from flask import jsonify, render_template_string, session

from .governance_execution_product_review_v34_7 import (
    build_governance_execution_product_review,
)
from .user_account_workspace_v28_1 import actor_is_administrator

PAGE = """
<!doctype html>
<title>v34 Product Review</title>
<main id="v34-product-review">
  <section id="action-eligibility">Action eligibility and delegate resolution</section>
  <section id="human-confirmation">Human confirmation framework</section>
  <section id="audience-package-authorization">Audience, package, authorization</section>
  <section id="delivery-retry">Delivery and retry</section>
  <section id="feedback-correction">Feedback and correction</section>
  <section id="recall-retention">Recall and retention</section>
  <section id="release-closure">{{ payload.status }}</section>
</main>
"""


def register_governance_execution_product_review_routes_v34_7(app):
    @app.get("/dissemination-governance/v34-product-review")
    def governance_execution_product_review_get_v34_7():
        actor = str(session.get("user") or "")
        if not actor:
            return render_template_string(PAGE, payload={"status": "unauthorized"}), 401
        if not actor_is_administrator(actor):
            return render_template_string(PAGE, payload={"status": "forbidden"}), 403
        payload = build_governance_execution_product_review(app.url_map.iter_rules())
        return render_template_string(PAGE, payload=payload), 200 if payload["ready"] else 503

    @app.get("/api/v1/dissemination-governance/v34-product-review")
    def api_governance_execution_product_review_get_v34_7():
        actor = str(session.get("user") or "")
        if not actor:
            return jsonify({"error": "login required"}), 401
        if not actor_is_administrator(actor):
            return jsonify({"error": "administrator required"}), 403
        payload = build_governance_execution_product_review(app.url_map.iter_rules())
        return jsonify(payload), 200 if payload["ready"] else 503

    return app
