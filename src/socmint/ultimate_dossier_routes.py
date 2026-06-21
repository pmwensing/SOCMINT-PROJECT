from __future__ import annotations

from flask import Response, abort, jsonify, render_template, request

from .ultimate_dossier import assertions_csv
from .ultimate_dossier import dossier_export_manifest
from .ultimate_dossier import redacted_dossier_payload
from .ultimate_dossier import ultimate_dossier_payload


def register_ultimate_dossier_routes(app) -> None:
    if "ultimate_dossier_view" in app.view_functions:
        return

    from .dashboard import login_required

    @login_required
    def ultimate_dossier_view(subject_id: int):
        try:
            payload = ultimate_dossier_payload(subject_id)
        except ValueError:
            abort(404)
        return render_template("ultimate_dossier.html", payload=payload)

    @login_required
    def api_ultimate_dossier(subject_id: int):
        try:
            payload = ultimate_dossier_payload(subject_id)
        except ValueError:
            abort(404)
        if request.args.get("redacted", "").strip().lower() in {"1", "true", "yes"}:
            payload = redacted_dossier_payload(payload)
        return jsonify(payload)

    @login_required
    def api_ultimate_dossier_manifest(subject_id: int):
        try:
            payload = ultimate_dossier_payload(subject_id)
        except ValueError:
            abort(404)
        redacted = request.args.get("redacted", "").strip().lower() in {
            "1",
            "true",
            "yes",
        }
        return jsonify(dossier_export_manifest(payload, redacted=redacted))

    @login_required
    def ultimate_dossier_assertions_csv(subject_id: int):
        try:
            payload = ultimate_dossier_payload(subject_id)
        except ValueError:
            abort(404)
        return Response(
            assertions_csv(payload),
            mimetype="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=subject-{subject_id}-assertions.csv"
            },
        )

    app.add_url_rule(
        "/spine/subjects/<int:subject_id>/ultimate-dossier",
        endpoint="ultimate_dossier_view",
        view_func=ultimate_dossier_view,
        methods=["GET"],
    )
    app.add_url_rule(
        "/api/v1/spine/subjects/<int:subject_id>/ultimate-dossier",
        endpoint="api_ultimate_dossier",
        view_func=api_ultimate_dossier,
        methods=["GET"],
    )
    app.add_url_rule(
        "/api/v1/spine/subjects/<int:subject_id>/ultimate-dossier/manifest",
        endpoint="api_ultimate_dossier_manifest",
        view_func=api_ultimate_dossier_manifest,
        methods=["GET"],
    )
    app.add_url_rule(
        "/spine/subjects/<int:subject_id>/ultimate-dossier/assertions.csv",
        endpoint="ultimate_dossier_assertions_csv",
        view_func=ultimate_dossier_assertions_csv,
        methods=["GET"],
    )
