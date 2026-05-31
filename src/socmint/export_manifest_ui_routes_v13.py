from __future__ import annotations

from flask import render_template

from .export_manifest_draft_v13 import build_export_manifest_draft


def register_export_manifest_ui_routes(app) -> None:
    if "export_manifest_view_v13" in app.view_functions:
        return

    from .dashboard import login_required

    @login_required
    def export_manifest_view_v13(subject_id: int):
        payload = build_export_manifest_draft(subject_id)
        return render_template(
            "export_manifest.html",
            payload=payload,
            subject_id=subject_id,
        )

    app.add_url_rule(
        "/subjects/<int:subject_id>/export-manifest",
        endpoint="export_manifest_view_v13",
        view_func=export_manifest_view_v13,
        methods=["GET"],
    )
