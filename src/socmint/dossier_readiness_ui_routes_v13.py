from __future__ import annotations

from flask import render_template

from .dossier_readiness_routes_v13 import subject_dossier_readiness


def register_dossier_readiness_ui_routes(app) -> None:
    if "dossier_readiness_view_v13" in app.view_functions:
        return

    from .dashboard import login_required

    @login_required
    def dossier_readiness_view_v13(subject_id: int):
        payload = subject_dossier_readiness(subject_id)
        return render_template(
            "dossier_readiness.html",
            payload=payload,
            subject_id=subject_id,
        )

    app.add_url_rule(
        "/subjects/<int:subject_id>/dossier/readiness",
        endpoint="dossier_readiness_view_v13",
        view_func=dossier_readiness_view_v13,
        methods=["GET"],
    )
