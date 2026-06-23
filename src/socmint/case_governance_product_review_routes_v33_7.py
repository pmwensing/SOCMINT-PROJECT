from __future__ import annotations

from flask import jsonify, render_template, session

from .action_eligibility_delegate_resolution_routes_v34_1 import (
    register_action_eligibility_delegate_resolution_routes_v34_1,
)
from .case_governance_product_review_v33_7 import (
    build_case_governance_product_review,
)
from .governance_action_routes_v34_2_6 import (
    register_governance_action_routes_v34_2_6,
)
from .governance_execution_product_review_routes_v34_7 import (
    register_governance_execution_product_review_routes_v34_7,
)
from .user_account_workspace_v28_1 import actor_is_administrator


def register_case_governance_product_review_routes_v33_7(app):
    @app.get("/dissemination-governance/v33-product-review")
    def case_governance_product_review_get_v33_7():
        actor = str(session.get("user") or "")
        if not actor:
            return render_template(
                "case_governance_product_review_v33_7.html",
                title="v33 Product Review",
                payload={"status": "unauthorized", "ready": False},
            ), 401
        if not actor_is_administrator(actor):
            return render_template(
                "case_governance_product_review_v33_7.html",
                title="v33 Product Review",
                payload={"status": "forbidden", "ready": False},
            ), 403
        payload = build_case_governance_product_review(
            routes=list(app.url_map.iter_rules())
        )
        return render_template(
            "case_governance_product_review_v33_7.html",
            title="v33 Product Review",
            payload=payload,
        ), 200 if payload.get("ready") else 503

    @app.get("/api/v1/dissemination-governance/v33-product-review")
    def api_case_governance_product_review_get_v33_7():
        actor = str(session.get("user") or "")
        if not actor:
            return jsonify({"error": "login required"}), 401
        if not actor_is_administrator(actor):
            return jsonify({"error": "administrator required"}), 403
        payload = build_case_governance_product_review(
            routes=list(app.url_map.iter_rules())
        )
        return jsonify(payload), 200 if payload.get("ready") else 503

    register_action_eligibility_delegate_resolution_routes_v34_1(app)
    register_governance_action_routes_v34_2_6(app)
    register_governance_execution_product_review_routes_v34_7(app)
    return app
