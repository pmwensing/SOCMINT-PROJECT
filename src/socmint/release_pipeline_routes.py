from __future__ import annotations

from flask import jsonify, session

from .release_pipeline import release_pipeline_check
from .release_pipeline import release_pipeline_summary
from .release_pipeline import release_workflow_spec


def _admin_required() -> bool:
    return bool(session.get("user") and session.get("is_admin"))


def register_release_pipeline_routes(app):
    @app.get("/api/v1/admin/release-pipeline")
    def api_release_pipeline():
        if not _admin_required():
            return jsonify({"error": "admin required"}), 403
        return jsonify(release_pipeline_check())

    @app.get("/api/v1/admin/release-pipeline/summary")
    def api_release_pipeline_summary():
        if not _admin_required():
            return jsonify({"error": "admin required"}), 403
        return jsonify(release_pipeline_summary())

    @app.get("/api/v1/admin/release-pipeline/workflow")
    def api_release_pipeline_workflow():
        if not _admin_required():
            return jsonify({"error": "admin required"}), 403
        return jsonify(release_workflow_spec())

    return app
