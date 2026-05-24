from __future__ import annotations

from flask import redirect, render_template, session, url_for

from .release_status_v12_10_19 import latest_gate_reports, release_status


def _login_required() -> bool:
    return bool(session.get("user"))


def register_release_status_ui_routes(app):
    @app.get("/release/status")
    def release_status_dashboard_v12_10_19():
        if not _login_required():
            return redirect(url_for("dashboard.login"))
        status = release_status()
        latest = latest_gate_reports()
        tor = status.get("tor", status.get("runtime", {}))
        return render_template(
            "release_status.html",
            title="Release Status",
            status=status,
            latest=latest,
            tor=tor,
        )

    @app.get("/release/gates")
    def release_gates_dashboard_v12_10_19():
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
