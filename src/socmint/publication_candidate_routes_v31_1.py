from __future__ import annotations

from flask import jsonify, request, session

from .draft_dossier_revision_routes_v31_2 import (
    register_draft_dossier_revision_routes_v31_2,
)
from .publication_candidate_v31_1 import (
    candidates_for_contribution,
    create_publication_candidate,
    current_publication_candidates,
    update_publication_candidate_state,
)
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


def register_publication_candidate_routes_v31_1(app):
    @app.get("/api/v1/publication-review/candidates")
    def list_publication_candidates_v31_1():
        actor, error = _authorized()
        if error:
            return error
        return jsonify(
            {
                "schema": "socmint.publication_candidates.v31_1",
                "version": "v31.1.0",
                "candidates": current_publication_candidates(),
            }
        )

    @app.get(
        "/api/v1/publication-review/contributions/<dossier_contribution_id>/candidates"
    )
    def list_contribution_publication_candidates_v31_1(
        dossier_contribution_id: str,
    ):
        actor, error = _authorized()
        if error:
            return error
        return jsonify(
            {
                "schema": "socmint.publication_candidate_history.v31_1",
                "version": "v31.1.0",
                "dossier_contribution_id": dossier_contribution_id,
                "candidates": candidates_for_contribution(dossier_contribution_id),
            }
        )

    @app.post("/api/v1/publication-review/candidates")
    def create_publication_candidate_v31_1():
        actor, error = _authorized()
        if error:
            return error
        data = _payload()
        result = create_publication_candidate(
            actor=actor,
            dossier_contribution_id=str(data.get("dossier_contribution_id") or ""),
            publication_purpose=str(data.get("publication_purpose") or ""),
            release_scope=str(data.get("release_scope") or ""),
            rationale=str(data.get("rationale") or ""),
            reason=str(data.get("reason") or ""),
            confirmed=data.get("confirmed") is True,
            ip_address=request.remote_addr,
        )
        return jsonify(result), 201 if result.get(
            "status"
        ) == "publication_candidate_recorded" else 422

    @app.post("/api/v1/publication-review/candidates/<candidate_id>/state")
    def update_publication_candidate_state_v31_1(candidate_id: str):
        actor, error = _authorized()
        if error:
            return error
        data = _payload()
        result = update_publication_candidate_state(
            actor=actor,
            candidate_id=candidate_id,
            candidate_state=str(data.get("candidate_state") or ""),
            reason=str(data.get("reason") or ""),
            confirmed=data.get("confirmed") is True,
            ip_address=request.remote_addr,
        )
        return jsonify(result), 200 if result.get(
            "status"
        ) == "publication_candidate_state_recorded" else 422

    register_draft_dossier_revision_routes_v31_2(app)
    return app
