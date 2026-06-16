from __future__ import annotations

from flask import redirect, render_template, session, url_for

from .portfolio_supervisor_escalation_v24_4 import build_escalation_control_state


def register_portfolio_supervisor_escalation_routes_v24_4(app):
    @app.get("/portfolio-operations/escalations")
    def portfolio_supervisor_escalations_get_v24_4():
        if not session.get("user"):
            return redirect(url_for("dashboard.login"))
        return render_template(
            "portfolio_supervisor_escalations_v24_4.html",
            title="Supervisor Escalation Controls",
            payload=build_escalation_control_state(),
        )

    return app
