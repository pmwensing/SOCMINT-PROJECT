from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from flask import jsonify, redirect, request, send_from_directory

from .entity_dossier_v2 import build_full_entity_dossier_v2
from .entity_dossier_v2 import dossier_root
from .entity_dossier_v2 import export_full_entity_dossier_v2
from .entity_dossier_v2 import safe_dossier_path


def latest_full_report_export(subject_id: int) -> dict[str, Any]:
    """Return UI/API metadata for the newest full-report export."""

    try:
        root = dossier_root()
    except OSError as exc:
        return {
            "subject_id": subject_id,
            "available": False,
            "latest": None,
            "error": str(exc),
        }
    pattern = f"subject-{subject_id}-full-entity-dossier-v2-*-EXPORT.json"
    matches = sorted(root.glob(pattern), reverse=True) if root.exists() else []
    if not matches:
        return {"subject_id": subject_id, "available": False, "latest": None}

    latest = matches[0]
    try:
        payload = json.loads(latest.read_text())
    except Exception as exc:
        return {
            "subject_id": subject_id,
            "available": False,
            "latest": latest.name,
            "error": str(exc),
        }

    zip_path = Path(payload.get("zip_path") or "")
    manifest_path = Path(payload.get("manifest_path") or "")
    html_path = Path(payload.get("html_path") or "")
    markdown_path = Path(payload.get("markdown_path") or "")
    json_path = Path(payload.get("json_path") or "")

    return {
        "subject_id": subject_id,
        "available": True,
        "latest": latest.name,
        "generated_at": payload.get("generated_at"),
        "schema": payload.get("schema"),
        "result_name": latest.name,
        "zip_name": zip_path.name if zip_path.name else None,
        "manifest_name": manifest_path.name if manifest_path.name else None,
        "html_name": html_path.name if html_path.name else None,
        "markdown_name": markdown_path.name if markdown_path.name else None,
        "json_name": json_path.name if json_path.name else None,
        "download_url": payload.get("download_url"),
        "full_report_download_url": payload.get("full_report_download_url"),
        "manifest": payload.get("manifest") or {},
    }


def register_full_report_aliases(app) -> None:
    """Register full-report aliases and UI helpers for the dossier-v2 engine."""

    if "api_full_report_get" in app.view_functions:
        return

    from .dashboard import login_required, run_required

    @app.context_processor
    def full_report_context():
        return {"latest_full_report_export": latest_full_report_export}

    @login_required
    def api_full_report_get(subject_id: int):
        return jsonify(build_full_entity_dossier_v2(subject_id))

    @run_required
    def api_full_report_run(subject_id: int):
        result = export_full_entity_dossier_v2(subject_id)
        return jsonify(result), 202

    @login_required
    def api_full_report_latest(subject_id: int):
        latest = latest_full_report_export(subject_id)
        return jsonify(latest), 200 if latest.get("available") else 404

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
