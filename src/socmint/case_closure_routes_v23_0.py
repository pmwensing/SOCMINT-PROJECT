from __future__ import annotations

from flask import jsonify, redirect, render_template, request, session, url_for

from .case_closure_decision_v23_2 import (
    latest_supervisor_closure_decision,
    record_supervisor_closure_decision,
)
from .case_closure_readiness_review_v23_1 import (
    latest_closure_readiness_review,
    review_case_closure_readiness,
)
from .case_closure_workspace_v23_0 import build_case_closure_workspace
from .case_retention_assignment_v23_3 import (
    assign_retention_policy,
    latest_retention_assignment,
)


def _login_required() -> bool:
    return bool(session.get("user"))


def _workspace(case_id: str) -> dict:
    payload = build_case_closure_workspace(case_id)
    payload["latest_readiness_review"] = latest_closure_readiness_review(case_id)
    payload["latest_closure_decision"] = latest_supervisor_closure_decision(case_id)
    payload["latest_retention_assignment"] = latest_retention_assignment(case_id)
    return payload


def register_case_closure_routes_v23_0(app):
    @app.get("/case-closure/<case_id>")
    def case_closure_workspace_get_v23_0(case_id: str):
        if not _login_required():
            return redirect(url_for("dashboard.login"))
        return render_template(
            "case_closure_workspace_v23_0.html",
            title="Case Closure Workspace",
            payload=_workspace(case_id),
        )

    @app.get("/api/v1/case-closure/<case_id>")
    def api_case_closure_workspace_get_v23_0(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        payload = _workspace(case_id)
        return jsonify(payload), 200 if payload.get("closure_eligible") else 422

    @app.post("/api/v1/case-closure/<case_id>/readiness-review")
    def api_case_closure_readiness_review_post_v23_1(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        payload = request.get_json(silent=True) or {}
        result = review_case_closure_readiness(
            case_id,
            decision=str(payload.get("decision") or ""),
            confirmed=payload.get("confirmed") is True,
            reviewer=str(session.get("user") or "unknown"),
            note=str(payload.get("note") or ""),
            ip_address=request.remote_addr,
        )
        return jsonify(result), 200 if result.get("status") == "review_recorded" else 422

    @app.post("/api/v1/case-closure/<case_id>/closure-decision")
    def api_case_closure_decision_post_v23_2(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        payload = request.get_json(silent=True) or {}
        result = record_supervisor_closure_decision(
            case_id,
            decision=str(payload.get("decision") or ""),
            confirmed=payload.get("confirmed") is True,
            supervisor=str(session.get("user") or "unknown"),
            note=str(payload.get("note") or ""),
            ip_address=request.remote_addr,
        )
        return jsonify(result), 200 if result.get("status") == "closure_decision_recorded" else 422

    @app.post("/api/v1/case-closure/<case_id>/retention-assignment")
    def api_case_retention_assignment_post_v23_3(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        payload = request.get_json(silent=True) or {}
        result = assign_retention_policy(
            case_id,
            policy_id=str(payload.get("policy_id") or ""),
            confirmed=payload.get("confirmed") is True,
            assigner=str(session.get("user") or "unknown"),
            note=str(payload.get("note") or ""),
            ip_address=request.remote_addr,
        )
        return jsonify(result), 200 if result.get("status") == "retention_assignment_recorded" else 422

    return app
