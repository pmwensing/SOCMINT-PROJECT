from __future__ import annotations

from flask import jsonify, request, session

from .access_policy_events_v28_2 import (
    create_case_access_rule,
    define_role,
    revise_role,
    revoke_case_access_rule,
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


def _code(result: dict, success: str) -> int:
    return 200 if result.get("status") == success else 422


def register_access_policy_write_routes_v28_2(app):
    @app.post("/api/v1/administration/access-policy/roles")
    def api_access_policy_role_post_v28_2():
        actor, error = _authorized()
        if error:
            return error
        payload = _payload()
        result = define_role(
            actor=actor,
            name=str(payload.get("name") or ""),
            permissions=payload.get("permissions"),
            inherits_role_ids=payload.get("inherits_role_ids"),
            description=str(payload.get("description") or ""),
            reason=str(payload.get("reason") or ""),
            confirmed=payload.get("confirmed") is True,
            ip_address=request.remote_addr,
        )
        return jsonify(result), _code(result, "role_defined")

    @app.post("/api/v1/administration/access-policy/roles/<role_id>/revise")
    def api_access_policy_role_revise_post_v28_2(role_id: str):
        actor, error = _authorized()
        if error:
            return error
        payload = _payload()
        result = revise_role(
            role_id,
            actor=actor,
            name=str(payload.get("name") or ""),
            permissions=payload.get("permissions"),
            inherits_role_ids=payload.get("inherits_role_ids"),
            description=str(payload.get("description") or ""),
            reason=str(payload.get("reason") or ""),
            confirmed=payload.get("confirmed") is True,
            ip_address=request.remote_addr,
        )
        return jsonify(result), _code(result, "role_revised")

    @app.post("/api/v1/administration/access-policy/case-rules")
    def api_access_policy_case_rule_post_v28_2():
        actor, error = _authorized()
        if error:
            return error
        payload = _payload()
        result = create_case_access_rule(
            actor=actor,
            subject_type=str(payload.get("subject_type") or ""),
            subject_id=str(payload.get("subject_id") or ""),
            case_id=str(payload.get("case_id") or ""),
            permissions=payload.get("permissions"),
            effect=str(payload.get("effect") or "allow"),
            reason=str(payload.get("reason") or ""),
            confirmed=payload.get("confirmed") is True,
            ip_address=request.remote_addr,
        )
        return jsonify(result), _code(result, "case_access_rule_created")

    @app.post("/api/v1/administration/access-policy/case-rules/<access_rule_id>/revoke")
    def api_access_policy_case_rule_revoke_post_v28_2(access_rule_id: str):
        actor, error = _authorized()
        if error:
            return error
        payload = _payload()
        result = revoke_case_access_rule(
            access_rule_id,
            actor=actor,
            reason=str(payload.get("reason") or ""),
            confirmed=payload.get("confirmed") is True,
            ip_address=request.remote_addr,
        )
        return jsonify(result), _code(result, "case_access_rule_revoked")

    return app
