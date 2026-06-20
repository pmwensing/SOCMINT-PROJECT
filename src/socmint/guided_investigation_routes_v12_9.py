from __future__ import annotations

from flask import jsonify, render_template, request

from .guided_investigation_v12_9 import guided_investigation_payload


def _subject_id() -> int | None:
    raw = request.args.get("subject_id")
    return int(raw) if raw and raw.isdigit() else None


def register_guided_investigation_routes(app) -> None:
    if "guided_investigation_dashboard" in app.view_functions:
        return

    from .dashboard import login_required

    @login_required
    def guided_investigation_dashboard():
        payload = guided_investigation_payload(subject_id=_subject_id())
        return render_template("guided_investigation_dashboard.html", payload=payload)

    @login_required
    def api_guided_investigation():
        return jsonify(guided_investigation_payload(subject_id=_subject_id()))

    app.add_url_rule(
        "/investigation/flow",
        endpoint="guided_investigation_dashboard",
        view_func=guided_investigation_dashboard,
        methods=["GET"],
    )
    app.add_url_rule(
        "/api/v1/investigation/flow",
        endpoint="api_guided_investigation",
        view_func=api_guided_investigation,
        methods=["GET"],
    )
