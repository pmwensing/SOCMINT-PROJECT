from __future__ import annotations

from flask import jsonify, render_template

from .authenticity_integrity_v12_7 import integrity_dashboard_payload


def register_authenticity_integrity_routes(app) -> None:
    if "authenticity_integrity_dashboard" in app.view_functions:
        return

    from .dashboard import login_required

    @login_required
    def authenticity_integrity_dashboard():
        payload = integrity_dashboard_payload()
        return render_template("authenticity_integrity_dashboard.html", payload=payload)

    @login_required
    def api_authenticity_integrity_dashboard():
        return jsonify(integrity_dashboard_payload())

    app.add_url_rule("/evidence/integrity", endpoint="authenticity_integrity_dashboard", view_func=authenticity_integrity_dashboard, methods=["GET"])
    app.add_url_rule("/api/v1/evidence/integrity", endpoint="api_authenticity_integrity_dashboard", view_func=api_authenticity_integrity_dashboard, methods=["GET"])
