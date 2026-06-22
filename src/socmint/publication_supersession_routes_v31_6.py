from __future__ import annotations

from flask import jsonify, request, session

from .publication_product_review_routes_v31_7 import (
    register_publication_product_review_routes_v31_7,
)
from .publication_supersession_v31_6 import (
    record_publication_supersession,
    revision_history_for_case,
    supersession_history,
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


def register_publication_supersession_routes_v31_6(app):
    @app.get("/api/v1/publication-review/supersessions")
    def list_publication_supersessions_v31_6():
        actor, error = _authorized()
        if error:
            return error
        return jsonify(
            {
                "schema": "socmint.publication_supersessions.v31_6",
                "version": "v31.6.0",
                "supersessions": supersession_history(),
            }
        )

    @app.get("/api/v1/publication-review/cases/<case_id>/revision-history")
    def get_case_revision_history_v31_6(case_id: str):
        actor, error = _authorized()
        if error:
            return error
        return jsonify(revision_history_for_case(case_id))

    @app.post("/api/v1/publication-review/supersessions")
    def create_publication_supersession_v31_6():
        actor, error = _authorized()
        if error:
            return error
        data = _payload()
        result = record_publication_supersession(
            actor=actor,
            predecessor_revision_id=str(data.get("predecessor_revision_id") or ""),
            successor_revision_id=str(data.get("successor_revision_id") or ""),
            reason=str(data.get("reason") or ""),
            note=str(data.get("note") or ""),
            confirmed=data.get("confirmed") is True,
            ip_address=request.remote_addr,
        )
        return jsonify(result), 201 if result.get("status") == "supersession_recorded" else 422

    register_publication_product_review_routes_v31_7(app)
    return app
