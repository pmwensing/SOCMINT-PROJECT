from __future__ import annotations
from flask import jsonify, redirect, render_template, request, session, url_for
from .collaboration_requests_handoffs_v26_3 import (
    build_workspace,
    create_handoff,
    create_request,
    transition,
)


def _allowed():
    v = session.get("allowed_case_ids")
    if v is None:
        return None
    if not isinstance(v, (list, tuple, set)):
        return set()
    return {str(x).strip() for x in v if str(x).strip()}


def _can(case_id):
    a = _allowed()
    return a is None or case_id in a


def register_collaboration_requests_handoffs_routes_v26_3(app):
    @app.get("/cases/<case_id>/collaboration-requests")
    def page(case_id):
        if not session.get("user"):
            return redirect(url_for("dashboard.login"))
        if not _can(case_id):
            return jsonify({"error": "case access required"}), 403
        return render_template(
            "collaboration_requests_handoffs_v26_3.html",
            title="Review Requests and Task Handoffs",
            payload=build_workspace(case_id),
        )

    @app.get("/api/v1/cases/<case_id>/collaboration-requests")
    def api(case_id):
        if not session.get("user"):
            return jsonify({"error": "login required"}), 401
        if not _can(case_id):
            return jsonify({"error": "case access required"}), 403
        return jsonify(build_workspace(case_id))

    @app.post("/api/v1/cases/<case_id>/collaboration-requests")
    def create_req(case_id):
        if not session.get("user"):
            return jsonify({"error": "login required"}), 401
        if not _can(case_id):
            return jsonify({"error": "case access required"}), 403
        p = request.get_json(silent=True) or {}
        r = create_request(
            case_id,
            actor=str(session.get("user")),
            other=str(p.get("requested_from") or ""),
            item_type=str(p.get("request_type") or ""),
            reason=str(p.get("reason") or ""),
            priority=str(p.get("priority") or "normal"),
            due_at=p.get("due_at"),
            source_records=p.get("source_records")
            if isinstance(p.get("source_records"), list)
            else [],
            confirmed=p.get("confirmed") is True,
            allowed_case_ids=_allowed(),
            ip_address=request.remote_addr,
        )
        return jsonify(r), 200 if r.get(
            "status"
        ) == "collaboration_request_recorded" else 422

    @app.post("/api/v1/cases/<case_id>/collaboration-handoffs")
    def create_hand(case_id):
        if not session.get("user"):
            return jsonify({"error": "login required"}), 401
        if not _can(case_id):
            return jsonify({"error": "case access required"}), 403
        p = request.get_json(silent=True) or {}
        r = create_handoff(
            case_id,
            actor=str(session.get("user")),
            other=str(p.get("handoff_to") or ""),
            item_type=str(p.get("handoff_type") or ""),
            reason=str(p.get("reason") or ""),
            priority=str(p.get("priority") or "normal"),
            due_at=p.get("due_at"),
            source_records=p.get("source_records")
            if isinstance(p.get("source_records"), list)
            else [],
            confirmed=p.get("confirmed") is True,
            allowed_case_ids=_allowed(),
            ip_address=request.remote_addr,
        )
        return jsonify(r), 200 if r.get(
            "status"
        ) == "collaboration_handoff_recorded" else 422

    @app.post("/api/v1/cases/<case_id>/collaboration-requests/<item_id>/<decision>")
    def req_transition(case_id, item_id, decision):
        if not session.get("user"):
            return jsonify({"error": "login required"}), 401
        if not _can(case_id):
            return jsonify({"error": "case access required"}), 403
        p = request.get_json(silent=True) or {}
        r = transition(
            "request",
            case_id,
            item_id,
            actor=str(session.get("user")),
            decision=decision,
            reason=str(p.get("reason") or ""),
            confirmed=p.get("confirmed") is True,
            allowed_case_ids=_allowed(),
            ip_address=request.remote_addr,
        )
        return jsonify(r), 200 if r.get("status", "").startswith(
            "collaboration_request_"
        ) and r.get("status") != "blocked" else 422

    @app.post("/api/v1/cases/<case_id>/collaboration-handoffs/<item_id>/<decision>")
    def hand_transition(case_id, item_id, decision):
        if not session.get("user"):
            return jsonify({"error": "login required"}), 401
        if not _can(case_id):
            return jsonify({"error": "case access required"}), 403
        p = request.get_json(silent=True) or {}
        r = transition(
            "handoff",
            case_id,
            item_id,
            actor=str(session.get("user")),
            decision=decision,
            reason=str(p.get("reason") or ""),
            confirmed=p.get("confirmed") is True,
            allowed_case_ids=_allowed(),
            ip_address=request.remote_addr,
        )
        return jsonify(r), 200 if r.get("status", "").startswith(
            "collaboration_handoff_"
        ) and r.get("status") != "blocked" else 422

    return app
