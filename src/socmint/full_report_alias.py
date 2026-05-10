from __future__ import annotations

from pathlib import Path

from flask import jsonify, redirect, request, send_from_directory, url_for

from .entity_dossier_v2 import build_full_entity_dossier_v2
from .entity_dossier_v2 import export_full_entity_dossier_v2
from .entity_dossier_v2 import safe_dossier_path


def register_full_report_aliases(app) -> None:
    """Register v7.5.1 full-report aliases for the dossier-v2 engine.

    These aliases preserve the existing dossier-v2 implementation while giving
    analysts the simpler "full-report" API surface requested for case work.
    The function is idempotent so tests and production entrypoints can call it
    safely.
    """

    if "api_full_report_get" in app.view_functions:
        return

    from .dashboard import login_required, run_required

    @login_required
    def api_full_report_get(subject_id: int):
        return jsonify(build_full_entity_dossier_v2(subject_id))

    @run_required
    def api_full_report_run(subject_id: int):
        result = export_full_entity_dossier_v2(subject_id)
        return jsonify(result), 202

    @login_required
    def api_full_report_latest(subject_id: int):
        root = safe_dossier_path(".").parent if False else Path("var/socmint/dossiers")
        pattern = f"subject-{subject_id}-full-entity-dossier-v2-*-EXPORT.json"
        matches = sorted(root.glob(pattern), reverse=True) if root.exists() else []
        if not matches:
            return jsonify({"subject_id": subject_id, "available": False, "latest": None}), 404
        latest = matches[0]
        return jsonify({"subject_id": subject_id, "available": True, "latest": latest.name})

    @login_required
    def api_full_report_download(subject_id: int):
        name = request.args.get("name", "").strip()
        if not name:
            return jsonify({"detail": "name query parameter is required"}), 400
        path = safe_dossier_path(name)
        return send_from_directory(path.parent, path.name, as_attachment=True)

    @run_required
    def ui_full_report_run(subject_id: int):
        result = export_full_entity_dossier_v2(subject_id)
        return redirect(result["download_url"])

    app.add_url_rule(
        "/api/v1/spine/subjects/<int:subject_id>/full-report",
        endpoint="api_full_report_get",
        view_func=api_full_report_get,
        methods=["GET"],
    )
    app.add_url_rule(
        "/api/v1/spine/subjects/<int:subject_id>/full-report/run",
        endpoint="api_full_report_run",
        view_func=api_full_report_run,
        methods=["POST"],
    )
    app.add_url_rule(
        "/api/v1/spine/subjects/<int:subject_id>/full-report/latest",
        endpoint="api_full_report_latest",
        view_func=api_full_report_latest,
        methods=["GET"],
    )
    app.add_url_rule(
        "/api/v1/spine/subjects/<int:subject_id>/full-report/download",
        endpoint="api_full_report_download",
        view_func=api_full_report_download,
        methods=["GET"],
    )
    app.add_url_rule(
        "/spine/subjects/<int:subject_id>/full-report/run",
        endpoint="ui_full_report_run",
        view_func=ui_full_report_run,
        methods=["POST"],
    )
