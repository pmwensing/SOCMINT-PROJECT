from __future__ import annotations

from flask import jsonify, redirect, render_template, request, session, url_for

from .dossier_assembly_workspace_v21_0 import (
    build_dossier_assembly_workspace,
    save_dossier_arrangement,
)


def _login_required() -> bool:
    return bool(session.get("user"))


def _actor() -> str:
    return str(session.get("user") or "unknown")


def _payload() -> dict:
    value = request.get_json(silent=True)
    if isinstance(value, dict):
        return value
    return request.form.to_dict() if request.form else {}


def _subject_id() -> int | None:
    value = request.args.get("subject_id")
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def register_dossier_assembly_routes_v21_0(app):
    @app.get("/dossier-assembly/<case_id>")
    def dossier_assembly_workspace_get_v21_0(case_id: str):
        if not _login_required():
            return redirect(url_for("dashboard.login"))
        return render_template(
            "dossier_assembly_workspace_v21_0.html",
            title="Dossier Assembly Workspace",
            payload=build_dossier_assembly_workspace(
                case_id,
                subject_id=_subject_id(),
            ),
        )

    @app.get("/api/v1/dossier-assembly/<case_id>")
    def api_dossier_assembly_workspace_get_v21_0(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(
            build_dossier_assembly_workspace(
                case_id,
                subject_id=_subject_id(),
            )
        )

    @app.post("/api/v1/dossier-assembly/<case_id>/arrangement")
    def api_dossier_assembly_arrangement_post_v21_0(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        result = save_dossier_arrangement(
            case_id,
            _payload(),
            actor=_actor(),
            ip_address=request.remote_addr,
        )
        return jsonify(result), 200 if result.get("status") == "saved" else 422

    return app
