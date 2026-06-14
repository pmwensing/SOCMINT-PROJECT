from __future__ import annotations

from flask import jsonify, redirect, render_template, request, session, url_for

from .dossier_citation_mapping_v21_3 import (
    build_dossier_citation_mapping,
    save_citation_mapping_snapshot,
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


def register_dossier_citation_mapping_routes_v21_3(app):
    @app.get("/dossier-assembly/<case_id>/citations")
    def dossier_citation_workspace_get_v21_3(case_id: str):
        if not _login_required():
            return redirect(url_for("dashboard.login"))
        return render_template(
            "dossier_citation_mapping_v21_3.html",
            title="Source and Evidence Citation Mapping",
            payload=build_dossier_citation_mapping(
                case_id,
                subject_id=_subject_id(),
            ),
        )

    @app.get("/api/v1/dossier-assembly/<case_id>/citations")
    def api_dossier_citation_mapping_get_v21_3(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        result = build_dossier_citation_mapping(
            case_id,
            subject_id=_subject_id(),
        )
        return jsonify(result), 200 if result.get("status") != "blocked" else 422

    @app.post("/api/v1/dossier-assembly/<case_id>/citation-snapshot")
    def api_dossier_citation_snapshot_post_v21_3(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        subject_id = _subject_id()
        if subject_id is None:
            return jsonify(
                {
                    "status": "blocked",
                    "blockers": [
                        {"key": "subject_id_required_for_ledger_mapping"}
                    ],
                }
            ), 422
        result = save_citation_mapping_snapshot(
            case_id,
            subject_id=subject_id,
            actor=_actor(),
            ip_address=request.remote_addr,
        )
        return jsonify(result), 200 if result.get("status") == "saved" else 422

    return app
