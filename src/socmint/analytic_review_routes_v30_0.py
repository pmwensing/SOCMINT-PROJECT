from __future__ import annotations

from flask import jsonify, redirect, render_template, session, url_for

from .analytic_review_workspace_v30_0 import build_analytic_review_workspace
from .canonical_observation_routes_v36_2 import register_canonical_observation_routes_v36_2
from .case_import_pilot_routes_v37_3 import register_case_import_pilot_routes_v37_3
from .claim_verification_routes_v36_5 import register_claim_verification_routes_v36_5
from .corroboration_claim_routes_v30_1 import register_corroboration_claim_routes_v30_1
from .dossier_synthesis_routes_v36_7 import register_dossier_synthesis_routes_v36_7
from .entity_accuracy_workspace_routes_v36_8 import register_entity_accuracy_workspace_routes_v36_8
from .entity_candidate_resolution_routes_v36_3 import register_entity_candidate_resolution_routes_v36_3
from .import_observation_promotion_routes_v37_4 import register_import_observation_promotion_routes_v37_4
from .operational_import_record_routes_v37_2 import register_operational_import_record_routes_v37_2
from .operational_import_routes_v37_1 import register_operational_import_routes_v37_1
from .relationship_timeline_routes_v36_6 import register_relationship_timeline_routes_v36_6
from .source_independence_routes_v36_4 import register_source_independence_routes_v36_4
from .source_registry_routes_v36_1 import register_source_registry_routes_v36_1
from .user_account_workspace_v28_1 import actor_is_administrator


def register_analytic_review_routes_v30_0(app):
    @app.get("/analytic-review")
    def analytic_review_workspace_get_v30_0():
        actor = str(session.get("user") or "")
        if not actor:
            return redirect(url_for("dashboard.login"))
        if not actor_is_administrator(actor):
            return render_template(
                "analytic_review_v30_0.html",
                title="Analytic Review Workspace",
                payload={
                    "status": "forbidden",
                    "error": "administrator required",
                    "evidence_inventory": [],
                    "observation_inventory": [],
                    "claim_inventory": [],
                    "confidence_inventory": [],
                    "review_item_inventory": [],
                    "review_decision_inventory": [],
                    "contradiction_inventory": [],
                    "dossier_contribution_inventory": [],
                    "analytic_findings": [],
                },
            ), 403
        return render_template(
            "analytic_review_v30_0.html",
            title="Analytic Review Workspace",
            payload=build_analytic_review_workspace(),
        )

    @app.get("/api/v1/analytic-review")
    def api_analytic_review_workspace_get_v30_0():
        actor = str(session.get("user") or "")
        if not actor:
            return jsonify({"error": "login required"}), 401
        if not actor_is_administrator(actor):
            return jsonify({"error": "administrator required"}), 403
        return jsonify(build_analytic_review_workspace())

    register_corroboration_claim_routes_v30_1(app)
    register_source_registry_routes_v36_1(app)
    register_canonical_observation_routes_v36_2(app)
    register_entity_candidate_resolution_routes_v36_3(app)
    register_source_independence_routes_v36_4(app)
    register_claim_verification_routes_v36_5(app)
    register_relationship_timeline_routes_v36_6(app)
    register_dossier_synthesis_routes_v36_7(app)
    register_entity_accuracy_workspace_routes_v36_8(app)
    register_operational_import_routes_v37_1(app)
    register_operational_import_record_routes_v37_2(app)
    register_case_import_pilot_routes_v37_3(app)
    register_import_observation_promotion_routes_v37_4(app)
    return app
