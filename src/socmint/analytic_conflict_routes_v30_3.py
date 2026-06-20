from __future__ import annotations

from flask import jsonify, request, session

from .analytic_conflict_v30_3 import current_conflicts, record_conflict, resolve_conflict
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


def register_analytic_conflict_routes_v30_3(app):
    @app.get("/api/v1/analytic-review/conflicts")
    def list_conflicts_v30_3():
        actor, error = _authorized()
        if error:
            return error
        return jsonify({"version": "v30.3.0", "conflicts": current_conflicts()})

    @app.post("/api/v1/analytic-review/conflicts")
    def create_conflict_v30_3():
        actor, error = _authorized()
        if error:
            return error
        data = _payload()
        result = record_conflict(actor=actor, conflict_type=str(data.get("conflict_type") or ""), claim_a_id=str(data.get("claim_a_id") or ""), claim_b_id=str(data.get("claim_b_id") or ""), disagreement_basis=str(data.get("disagreement_basis") or ""), reason=str(data.get("reason") or ""), confirmed=data.get("confirmed") is True, ip_address=request.remote_addr)
        return jsonify(result), 200 if result.get("status") == "analytic_conflict_recorded" else 422

    @app.post("/api/v1/analytic-review/conflicts/<conflict_id>/resolution")
    def resolve_conflict_v30_3(conflict_id: str):
        actor, error = _authorized()
        if error:
            return error
        data = _payload()
        result = resolve_conflict(actor=actor, conflict_id=conflict_id, resolution=str(data.get("resolution") or ""), reason=str(data.get("reason") or ""), confirmed=data.get("confirmed") is True, ip_address=request.remote_addr)
        return jsonify(result), 200 if result.get("status") == "analytic_conflict_resolved" else 422

    return app
