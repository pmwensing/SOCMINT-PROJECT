from __future__ import annotations

from flask import jsonify, request, session

from .editorial_validation_v31_3 import (
    current_editorial_validations,
    run_editorial_validation,
    validations_for_revision,
)
from .human_release_approval_routes_v31_4 import (
    register_human_release_approval_routes_v31_4,
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


def register_editorial_validation_routes_v31_3(app):
    @app.get("/api/v1/publication-review/editorial-validations")
    def list_editorial_validations_v31_3():
        actor, error = _authorized()
        if error:
            return error
        return jsonify(
            {
                "schema": "socmint.editorial_validations.v31_3",
                "version": "v31.3.0",
                "editorial_validations": current_editorial_validations(),
            }
        )

    @app.get(
        "/api/v1/publication-review/draft-revisions/<draft_revision_id>/editorial-validations"
    )
    def list_revision_editorial_validations_v31_3(draft_revision_id: str):
        actor, error = _authorized()
        if error:
            return error
        return jsonify(
            {
                "schema": "socmint.editorial_validation_history.v31_3",
                "version": "v31.3.0",
                "draft_revision_id": draft_revision_id,
                "editorial_validations": validations_for_revision(draft_revision_id),
            }
        )

    @app.post(
        "/api/v1/publication-review/draft-revisions/<draft_revision_id>/editorial-validations"
    )
    def create_editorial_validation_v31_3(draft_revision_id: str):
        actor, error = _authorized()
        if error:
            return error
        data = _payload()
        result = run_editorial_validation(
            actor=actor,
            draft_revision_id=draft_revision_id,
            editorial_summary=str(data.get("editorial_summary") or ""),
            policy_acknowledgements=data.get("policy_acknowledgements") or {},
            reason=str(data.get("reason") or ""),
            confirmed=data.get("confirmed") is True,
            ip_address=request.remote_addr,
        )
        return jsonify(result), 201 if result.get(
            "status"
        ) == "editorial_validation_recorded" else 422

    register_human_release_approval_routes_v31_4(app)
    return app
