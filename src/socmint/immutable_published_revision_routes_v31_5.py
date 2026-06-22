from __future__ import annotations

from flask import jsonify, request, session

from .immutable_published_revision_v31_5 import (
    create_immutable_published_revision,
    current_published_revisions,
    published_revisions_for_case,
)
from .publication_supersession_routes_v31_6 import (
    register_publication_supersession_routes_v31_6,
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


def register_immutable_published_revision_routes_v31_5(app):
    @app.get("/api/v1/publication-review/published-revisions")
    def list_published_revisions_v31_5():
        actor, error = _authorized()
        if error:
            return error
        return jsonify(
            {
                "schema": "socmint.immutable_published_revisions.v31_5",
                "version": "v31.5.0",
                "published_revisions": current_published_revisions(),
            }
        )

    @app.get("/api/v1/publication-review/cases/<case_id>/published-revisions")
    def list_case_published_revisions_v31_5(case_id: str):
        actor, error = _authorized()
        if error:
            return error
        return jsonify(
            {
                "schema": "socmint.immutable_published_revision_history.v31_5",
                "version": "v31.5.0",
                "case_id": case_id,
                "published_revisions": published_revisions_for_case(case_id),
            }
        )

    @app.post(
        "/api/v1/publication-review/draft-revisions/<draft_revision_id>/published-revisions"
    )
    def create_published_revision_v31_5(draft_revision_id: str):
        actor, error = _authorized()
        if error:
            return error
        data = _payload()
        result = create_immutable_published_revision(
            publisher=actor,
            draft_revision_id=draft_revision_id,
            publication_label=str(data.get("publication_label") or ""),
            publication_note=str(data.get("publication_note") or ""),
            reason=str(data.get("reason") or ""),
            confirmed=data.get("confirmed") is True,
            ip_address=request.remote_addr,
        )
        return jsonify(result), 201 if result.get(
            "status"
        ) == "published_revision_created" else 422

    register_publication_supersession_routes_v31_6(app)
    return app
