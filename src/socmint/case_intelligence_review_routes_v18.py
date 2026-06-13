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
    set_persistent_decision_review_state,
)
from .persistent_decision_supervisor_queue_v19_3 import (
    assign_persistent_decision_reviewer,
    build_persistent_decision_supervisor_queue,
)
from .reviewer_work_queue_v19_5 import (
    build_reviewer_work_queue,
    update_assigned_decision_review_state,
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


def _positive_int(value: str | None, default: int) -> int:
    try:
        return max(1, int(value or default))
    except (TypeError, ValueError):
        return default


def _persistent_history(case_id: str) -> dict:
    return list_persistent_case_review_decisions(
        case_id,
        actor=request.args.get("actor") or None,
        decision=request.args.get("decision") or None,
        date_from=request.args.get("date_from") or None,
        date_to=request.args.get("date_to") or None,
        review_state=request.args.get("review_state") or None,
        page=_positive_int(request.args.get("page"), 1),
        page_size=_positive_int(request.args.get("page_size"), 25),
    )


def _supervisor_queue() -> dict:
    return build_persistent_decision_supervisor_queue(
        case_id=request.args.get("case_id") or None,
        review_state=request.args.get("review_state") or None,
        assigned_reviewer=request.args.get("assigned_reviewer") or None,
    )


def _workspace(case_id: str, payload: dict | None = None) -> dict:
    workspace = build_case_intelligence_review_workspace(
        case_id,
        payload or {},
        history=_history(),
        operator=_operator(),
    )
    workspace["persistent_decision_history"] = _persistent_history(case_id)
    return workspace


def register_case_intelligence_review_routes_v18(app):
    @app.get("/case-intelligence-review/<case_id>")
    def case_intelligence_review_workspace_get_v18(case_id: str):
        if not _login_required():
            return redirect(url_for("dashboard.login"))
        return render_template(
            "case_intelligence_review_workspace.html",
            title="Case Intelligence Review Workspace",
            payload=_workspace(case_id),
        )

    @app.get("/case-intelligence-review/supervisor-queue")
    def case_intelligence_supervisor_queue_get_v19_3():
        if not _login_required():
            return redirect(url_for("dashboard.login"))
        return render_template(
            "persistent_decision_supervisor_queue_v19_3.html",
            title="Persistent Decision Supervisor Queue",
            payload=_supervisor_queue(),
        )

    @app.get("/case-intelligence-review/my-assignments")
    def case_intelligence_reviewer_work_queue_get_v19_5():
        if not _login_required():
            return redirect(url_for("dashboard.login"))
        return render_template(
            "reviewer_work_queue_v19_5.html",
            title="Reviewer Work Queue",
            payload=build_reviewer_work_queue(_operator()),
        )

    @app.get("/api/v1/case-intelligence-review/supervisor-queue")
    def api_case_intelligence_supervisor_queue_get_v19_3():
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(_supervisor_queue())

    @app.get("/api/v1/case-intelligence-review/my-assignments")
    def api_case_intelligence_reviewer_work_queue_get_v19_5():
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(build_reviewer_work_queue(_operator()))

    @app.post(
        "/api/v1/case-intelligence-review/my-assignments/<case_id>/decisions/<int:decision_record_id>/review-state"
    )
    def api_case_intelligence_reviewer_work_state_post_v19_5(
        case_id: str, decision_record_id: int
    ):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        request_payload = _payload()
        result = update_assigned_decision_review_state(
            case_id,
            decision_record_id,
            str(request_payload.get("review_state") or ""),
            reviewer=_operator(),
            note=str(request_payload.get("note") or ""),
            ip_address=request.remote_addr,
        )
        return jsonify(result), 200 if result.get("status") == "recorded" else 422

    @app.post(
        "/api/v1/case-intelligence-review/supervisor-queue/<case_id>/decisions/<int:decision_record_id>/assignment"
    )
    def api_case_intelligence_supervisor_assignment_post_v19_4(
        case_id: str, decision_record_id: int
    ):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        request_payload = _payload()
        result = assign_persistent_decision_reviewer(
            case_id,
            decision_record_id,
            str(request_payload.get("assigned_reviewer") or ""),
            actor=_operator(),
            note=str(request_payload.get("note") or ""),
            ip_address=request.remote_addr,
        )
        result["supervisor_queue"] = build_persistent_decision_supervisor_queue()
        return jsonify(result), 200 if result.get("status") == "recorded" else 422

    @app.get("/api/v1/case-intelligence-review/<case_id>")
    def api_case_intelligence_review_get_v18(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(_workspace(case_id))

    @app.post("/api/v1/case-intelligence-review/<case_id>")
    def api_case_intelligence_review_post_v18(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(_workspace(case_id, _payload()))

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
        result["persistent_decision_history"] = list_persistent_case_review_decisions(
            case_id
        )
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
        return jsonify(_persistent_history(case_id))

    @app.post(
        "/api/v1/case-intelligence-review/<case_id>/decisions/<int:decision_record_id>/review-state"
    )
    def api_persistent_case_review_state_post_v19_2(
        case_id: str, decision_record_id: int
    ):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        request_payload = _payload()
        result = set_persistent_decision_review_state(
            case_id,
            decision_record_id,
            str(request_payload.get("review_state") or ""),
            actor=_operator(),
            note=str(request_payload.get("note") or ""),
            ip_address=request.remote_addr,
        )
        result["persistent_decision_history"] = list_persistent_case_review_decisions(
            case_id
        )
        return jsonify(result), 200 if result.get("status") == "recorded" else 422

    @app.get("/api/v1/case-intelligence-review/product-review-checkpoint")
    def api_case_intelligence_product_review_checkpoint_get_v18_7():
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        result = build_v18_product_review_checkpoint(
            routes=list(app.url_map.iter_rules())
        )
        return jsonify(result), 200 if result.get("ready") else 409

    return app
