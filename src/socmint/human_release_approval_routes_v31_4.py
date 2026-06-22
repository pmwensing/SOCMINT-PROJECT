from __future__ import annotations

from flask import jsonify, request, session

from .human_release_approval_v31_4 import approvals_for_revision, current_release_approvals, record_human_release_decision
from .immutable_published_revision_routes_v31_5 import register_immutable_published_revision_routes_v31_5
from .user_account_workspace_v28_1 import actor_is_administrator


def _payload() -> dict:
    value = request.get_json(silent=True)
    return value if isinstance(value, dict) else {}


def _authorized():
    actor = str(session.get("user") or "")
    if not actor:
        return None, (jsonify({"error": "login required"}), 401)
    if not actor_is_administrator(actor):
        return None, (jsonify({"error": "administrator required"}), 403)
    return actor, None


def register_human_release_approval_routes_v31_4(app):
    @app.get("/api/v1/publication-review/release-approvals")
    def list_release_approvals_v31_4():
        actor, error = _authorized()
        if error:
            return error
        return jsonify({"schema": "socmint.human_release_approvals.v31_4", "version": "v31.4.0", "release_approvals": current_release_approvals()})

    @app.get("/api/v1/publication-review/draft-revisions/<draft_revision_id>/release-approvals")
    def list_revision_release_approvals_v31_4(draft_revision_id: str):
        actor, error = _authorized()
        if error:
            return error
        return jsonify({"schema": "socmint.human_release_approval_history.v31_4", "version": "v31.4.0", "draft_revision_id": draft_revision_id, "release_approvals": approvals_for_revision(draft_revision_id)})

    @app.post("/api/v1/publication-review/draft-revisions/<draft_revision_id>/release-approvals")
    def create_release_approval_v31_4(draft_revision_id: str):
        actor, error = _authorized()
        if error:
            return error
        data = _payload()
        result = record_human_release_decision(
            reviewer=actor,
            draft_revision_id=draft_revision_id,
            decision=str(data.get("decision") or ""),
            note=str(data.get("note") or ""),
            reason=str(data.get("reason") or ""),
            confirmed=data.get("confirmed") is True,
            ip_address=request.remote_addr,
        )
        return jsonify(result), 201 if result.get("status") in {"approved", "returned", "held"} else 422

    register_immutable_published_revision_routes_v31_5(app)
    return app
