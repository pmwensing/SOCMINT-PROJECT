from __future__ import annotations

from flask import jsonify, render_template, request

from .assertion_trust_v12_8 import build_assertion_trust
from .assertion_trust_v12_8 import corroboration_dashboard_payload


def _subject_id() -> int | None:
    subject_id_raw = request.args.get("subject_id")
    return int(subject_id_raw) if subject_id_raw and subject_id_raw.isdigit() else None


def register_assertion_trust_routes(app) -> None:
    if "assertion_trust_dashboard" in app.view_functions:
        return

    from .dashboard import login_required

    @login_required
    def assertion_trust_dashboard():
        payload = corroboration_dashboard_payload(subject_id=_subject_id())
        return render_template("assertion_trust_dashboard.html", payload=payload)

    @login_required
    def api_assertion_trust():
        return jsonify(build_assertion_trust(subject_id=_subject_id()))

    @login_required
    def api_corroboration_dashboard():
        return jsonify(corroboration_dashboard_payload(subject_id=_subject_id()))

    app.add_url_rule("/assertions/trust", endpoint="assertion_trust_dashboard", view_func=assertion_trust_dashboard, methods=["GET"])
    app.add_url_rule("/api/v1/assertions/trust", endpoint="api_assertion_trust", view_func=api_assertion_trust, methods=["GET"])
    app.add_url_rule("/api/v1/corroboration/dashboard", endpoint="api_corroboration_dashboard", view_func=api_corroboration_dashboard, methods=["GET"])
