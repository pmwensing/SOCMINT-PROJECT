from __future__ import annotations

from flask import jsonify, request, session

from .draft_dossier_revision_v31_2 import (
    assemble_draft_dossier_revision,
    current_draft_revisions,
    revisions_for_candidate,
)
from .editorial_validation_routes_v31_3 import (
    register_editorial_validation_routes_v31_3,
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


def register_draft_dossier_revision_routes_v31_2(app):
    @app.get("/api/v1/publication-review/draft-revisions")
    def list_draft_dossier_revisions_v31_2():
        actor, error = _authorized()
        if error:
            return error
        return jsonify(
            {
                "schema": "socmint.draft_dossier_revisions.v31_2",
                "version": "v31.2.0",
                "draft_revisions": current_draft_revisions(),
            }
        )

    @app.get(
        "/api/v1/publication-review/candidates/<candidate_id>/draft-revisions"
    )
    def list_candidate_draft_revisions_v31_2(candidate_id: str):
        actor, error = _authorized()
        if error:
            return error
        return jsonify(
            {
                "schema": "socmint.draft_dossier_revision_history.v31_2",
                "version": "v31.2.0",
                "publication_candidate_id": candidate_id,
                "draft_revisions": revisions_for_candidate(candidate_id),
            }
        )

    @app.post(
        "/api/v1/publication-review/candidates/<candidate_id>/draft-revisions"
    )
    def create_draft_dossier_revision_v31_2(candidate_id: str):
        actor, error = _authorized()
        if error:
            return error
        data = _payload()
        subject_id = data.get("subject_id")
        result = assemble_draft_dossier_revision(
            actor=actor,
            publication_candidate_id=candidate_id,
            revision_label=str(data.get("revision_label") or ""),
            editorial_note=str(data.get("editorial_note") or ""),
            reason=str(data.get("reason") or ""),
            confirmed=data.get("confirmed") is True,
            subject_id=int(subject_id) if subject_id not in (None, "") else None,
            ip_address=request.remote_addr,
        )
        return jsonify(result), 201 if result.get(
            "status"
        ) == "draft_dossier_revision_assembled" else 422

    register_editorial_validation_routes_v31_3(app)
    return app
