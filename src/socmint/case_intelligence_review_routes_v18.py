from __future__ import annotations

from flask import jsonify, redirect, render_template, request, session, url_for

from .case_intelligence_review_workspace_v18 import (
    SESSION_KEY,
    append_case_review_history,
    build_case_intelligence_review_workspace,
    build_v18_product_review_checkpoint,
    record_case_review_decision,
)
from .persistent_case_review_decisions_v19_0 import (
    list_persistent_case_review_decisions,
    persist_case_review_decision,
)


def _login_required() -> bool:
    return bool(session.get("user"))


def _payload() -> dict:
    value = request.get_json(silent=True)
    if isinstance(value, dict):
        return value
    return request.form.to_dict() if request.form else {}


def _operator() -> str:
    return str(session.get("user") or "unknown")


def _history() -> list[dict]:
    value = session.get(SESSION_KEY, [])
    return value if isinstance(value, list) else []


def register_case_intelligence_review_routes_v18(app):
    @app.get("/case-intelligence-review/<case_id>")
    def case_intelligence_review_workspace_get_v18(case_id: str):
        if not _login_required():
            return redirect(url_for("dashboard.login"))
        workspace = build_case_intelligence_review_workspace(
            case_id,
            {},
            history=_history(),
            operator=_operator(),
        )
        return render_template(
            "case_intelligence_review_workspace.html",
            title="Case Intelligence Review Workspace",
            payload=workspace,
        )

    @app.get("/api/v1/case-intelligence-review/<case_id>")
    def api_case_intelligence_review_get_v18(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(
            build_case_intelligence_review_workspace(
                case_id,
                {},
                history=_history(),
                operator=_operator(),
            )
        )

    @app.post("/api/v1/case-intelligence-review/<case_id>")
    def api_case_intelligence_review_post_v18(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(
            build_case_intelligence_review_workspace(
                case_id,
                _payload(),
                history=_history(),
                operator=_operator(),
            )
        )

    @app.post("/api/v1/case-intelligence-review/<case_id>/decisions")
    def api_case_intelligence_review_decision_post_v18_5(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        request_payload = _payload()
        result = record_case_review_decision(
            case_id,
            request_payload,
            operator=_operator(),
            recorded_at=(
                str(request_payload.get("recorded_at"))
                if request_payload.get("recorded_at")
                else None
            ),
        )
        if result.get("status") == "recorded":
            result["persistent_decision"] = persist_case_review_decision(
                case_id,
                result,
                actor=_operator(),
                ip_address=request.remote_addr,
            )
        session[SESSION_KEY] = append_case_review_history(_history(), result)
        session.modified = True
        result["review_history"] = build_case_intelligence_review_workspace(
            case_id,
            {},
            history=_history(),
            operator=_operator(),
        )["review_history"]
        return jsonify(result), 200 if result.get("status") == "recorded" else 422

    @app.get("/api/v1/case-intelligence-review/<case_id>/history")
    def api_case_intelligence_review_history_get_v18_6(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(
            build_case_intelligence_review_workspace(
                case_id,
                {},
                history=_history(),
                operator=_operator(),
            )["review_history"]
        )

    @app.get("/api/v1/case-intelligence-review/<case_id>/decisions/persistent")
    def api_persistent_case_review_decisions_get_v19_0(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(list_persistent_case_review_decisions(case_id))

    @app.get("/api/v1/case-intelligence-review/product-review-checkpoint")
    def api_case_intelligence_product_review_checkpoint_get_v18_7():
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        result = build_v18_product_review_checkpoint(
            routes=list(app.url_map.iter_rules())
        )
        return jsonify(result), 200 if result.get("ready") else 409

    return app
