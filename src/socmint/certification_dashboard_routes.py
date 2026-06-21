from __future__ import annotations

from flask import jsonify, redirect, render_template, request, session, url_for

from .dossier_certification_index import certification_index
from .dossier_certification_index import certification_index_entry
from .dossier_certification_index import certification_index_markdown
from .dossier_certification_index import certification_index_summary


def _login_required() -> bool:
    return bool(session.get("user"))


def _dashboard_payload(case_id: str | None, subject_id: str | None = None) -> dict:
    if not case_id:
        return {
            "case_id": "",
            "subject_id": subject_id or "",
            "index": None,
            "summary": None,
            "entry": None,
            "markdown": "",
            "status": "empty",
        }
    payload = {
        "case_id": case_id,
        "subject_id": subject_id or "",
        "index": certification_index(case_id=case_id),
        "summary": certification_index_summary(case_id=case_id),
        "entry": None,
        "markdown": certification_index_markdown(case_id=case_id),
        "status": "ready",
    }
    if subject_id:
        payload["entry"] = certification_index_entry(
            case_id=case_id, subject_id=subject_id
        )
    return payload


def register_certification_dashboard_routes(app):
    @app.get("/dossier/certification-dashboard")
    def dossier_certification_dashboard():
        if not _login_required():
            return redirect(url_for("dashboard.login"))
        case_id = (request.args.get("case_id") or "").strip()
        subject_id = (request.args.get("subject_id") or "").strip() or None
        return render_template(
            "certification_dashboard.html",
            title="Certification Index Dashboard",
            payload=_dashboard_payload(case_id=case_id or None, subject_id=subject_id),
        )

    @app.get("/api/v1/dossier-builder/v3/certification-dashboard/<case_id>")
    def api_dossier_certification_dashboard(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        subject_id = (request.args.get("subject_id") or "").strip() or None
        return jsonify(_dashboard_payload(case_id=case_id, subject_id=subject_id))

    return app
