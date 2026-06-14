from __future__ import annotations

from flask import jsonify, redirect, render_template, request, session, url_for

from .dossier_supervisor_approval_v21_5 import (
    build_supervisor_approval_workspace,
    record_supervisor_dossier_decision,
)


def _login_required() -> bool:
    return bool(session.get("user"))


def _actor() -> str:
    return str(session.get("user") or "unknown")


def _subject_id() -> int | None:
    value = request.args.get("subject_id")
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def register_dossier_supervisor_approval_routes_v21_5(app):
    @app.get("/dossier-assembly/<case_id>/supervisor-approval")
    def dossier_supervisor_approval_get_v21_5(case_id: str):
        if not _login_required():
            return redirect(url_for("dashboard.login"))
        return render_template(
            "dossier_supervisor_approval_v21_5.html",
            title="Supervisor Dossier Approval",
            payload=build_supervisor_approval_workspace(
                case_id,
                subject_id=_subject_id(),
            ),
        )

    @app.get("/api/v1/dossier-assembly/<case_id>/supervisor-approval")
    def api_dossier_supervisor_approval_get_v21_5(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        result = build_supervisor_approval_workspace(
            case_id,
            subject_id=_subject_id(),
        )
        return jsonify(result), 200 if result.get("status") != "blocked" else 422

    @app.post("/api/v1/dossier-assembly/<case_id>/supervisor-decision")
    def api_dossier_supervisor_decision_post_v21_5(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        subject_id = _subject_id()
        if subject_id is None:
            return jsonify({
                "status": "blocked",
                "blockers": [{"key": "subject_id_required_for_supervisor_approval"}],
            }), 422
        payload = request.get_json(silent=True) or {}
        result = record_supervisor_dossier_decision(
            case_id,
            str(payload.get("decision") or ""),
            subject_id=subject_id,
            reviewer=_actor(),
            note=str(payload.get("note") or ""),
            ip_address=request.remote_addr,
        )
        return jsonify(result), 200 if result.get("status") in {
            "approved", "returned", "held"
        } else 422

    return app
