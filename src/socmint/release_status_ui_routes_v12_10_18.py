from __future__ import annotations

from flask import redirect, render_template, session, url_for

from .release_status_v12_10_17 import latest_gate_reports, release_status
from .tor_production import tor_hidden_service_diagnostics


def _login_required() -> bool:
    return bool(session.get("user"))


def register_release_status_ui_routes(app):
    @app.get("/release/status")
    def release_status_dashboard_v12_10_18():
        if not _login_required():
            return redirect(url_for("dashboard.login"))
        status = release_status()
        latest = latest_gate_reports()
        try:
            tor = tor_hidden_service_diagnostics()
        except Exception as exc:
            tor = {
                "schema": "socmint.tor_hidden_service_diagnostics.v12_10_16",
                "status": "needs_review",
                "decision": "HOLD",
                "error": str(exc),
                "checks": {},
            }
        return render_template(
            "release_status.html",
            title="Release Status",
            status=status,
            latest=latest,
            tor=tor,
        )

    @app.get("/release/gates")
    def release_gates_dashboard_v12_10_18():
        if not _login_required():
            return redirect(url_for("dashboard.login"))
        latest = latest_gate_reports()
        return render_template(
            "release_gates.html",
            title="Release Gates",
            latest=latest,
            reports=latest.get("reports", []),
        )

    return app
