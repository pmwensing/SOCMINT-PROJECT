from __future__ import annotations

from flask import jsonify

from .export_manifest_draft_v13 import build_export_manifest_draft


def register_export_manifest_draft_routes(app) -> None:
    if "api_export_manifest_draft_v13" in app.view_functions:
        return

    from .dashboard import login_required

    @login_required
    def api_export_manifest_draft_v13(subject_id: int):
        return jsonify(build_export_manifest_draft(subject_id))

    app.add_url_rule(
        "/api/v1/subjects/<int:subject_id>/export-manifest-draft",
        endpoint="api_export_manifest_draft_v13",
        view_func=api_export_manifest_draft_v13,
        methods=["GET"],
    )
