from __future__ import annotations

from flask import jsonify, session

from .audience_package_authorization_panels_v33_3 import (
    build_case_audience_package_authorization_panels,
    build_case_governance_panel,
)
from .delivery_receipt_feedback_panels_routes_v33_4 import (
    register_delivery_receipt_feedback_panels_routes_v33_4,
)
from .delivery_receipt_feedback_panels_v33_4 import (
    build_case_delivery_receipt_feedback_panel,
)
from .user_account_workspace_v28_1 import actor_is_administrator


V33_4_PANEL_NAMES = {"delivery", "receipt", "feedback", "correction"}


def _authorized():
    actor = str(session.get("user") or "")
    if not actor:
        return None, (jsonify({"error": "login required"}), 401)
    if not actor_is_administrator(actor):
        return None, (jsonify({"error": "administrator required"}), 403)
    return actor, None


def register_audience_package_authorization_panels_routes_v33_3(app):
    @app.get(
        "/api/v1/dissemination-governance/cases/"
        "<case_id>/audience-package-authorization-panels"
    )
    def get_case_audience_package_authorization_panels_v33_3(case_id: str):
        actor, error = _authorized()
        if error:
            return error
        payload = build_case_audience_package_authorization_panels(case_id)
        status_code = 200
        if payload.get("status") == "blocked":
            status_code = 422
        return jsonify(payload), status_code

    @app.get(
        "/api/v1/dissemination-governance/cases/"
        "<case_id>/governance-panels/<panel_name>"
    )
    def get_case_governance_panel_v33_3(case_id: str, panel_name: str):
        actor, error = _authorized()
        if error:
            return error
        normalized_panel = str(panel_name or "").strip().lower()
        if normalized_panel in V33_4_PANEL_NAMES:
            payload = build_case_delivery_receipt_feedback_panel(
                case_id, normalized_panel
            )
        else:
            payload = build_case_governance_panel(case_id, normalized_panel)
        status_code = 200
        if payload.get("status") == "blocked":
            status_code = 422
        return jsonify(payload), status_code

    register_delivery_receipt_feedback_panels_routes_v33_4(app)
    return app
