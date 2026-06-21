from __future__ import annotations

from flask import jsonify, redirect, render_template, request, session, url_for

from .dossier_final_export_package_v21_6 import (
    build_final_export_package,
    generate_final_export_package,
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


def register_dossier_final_export_routes_v21_6(app):
    @app.get("/dossier-assembly/<case_id>/final-export")
    def dossier_final_export_get_v21_6(case_id: str):
        if not _login_required():
            return redirect(url_for("dashboard.login"))
        return render_template(
            "dossier_final_export_v21_6.html",
            title="Final Export Package Generation",
            payload=build_final_export_package(
                case_id,
                subject_id=_subject_id(),
            ),
        )

    @app.get("/api/v1/dossier-assembly/<case_id>/final-export")
    def api_dossier_final_export_get_v21_6(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        result = build_final_export_package(
            case_id,
            subject_id=_subject_id(),
        )
        return jsonify(result), 200 if result.get("status") == "ready" else 422

    @app.post("/api/v1/dossier-assembly/<case_id>/final-export")
    def api_dossier_final_export_post_v21_6(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        subject_id = _subject_id()
        if subject_id is None:
            return jsonify(
                {
                    "status": "blocked",
                    "blockers": [{"key": "subject_id_required_for_final_export"}],
                }
            ), 422
        result = generate_final_export_package(
            case_id,
            subject_id=subject_id,
            actor=_actor(),
            ip_address=request.remote_addr,
        )
        return jsonify(result), 200 if result.get("status") == "generated" else 422

    return app
