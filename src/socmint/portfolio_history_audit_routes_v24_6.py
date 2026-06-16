from __future__ import annotations

from flask import jsonify, redirect, render_template, session, url_for

from .portfolio_history_audit_v24_6 import build_portfolio_history_audit


def register_portfolio_history_audit_routes_v24_6(app):
    @app.get("/portfolio-operations/history")
    def portfolio_history_audit_get_v24_6():
        if not session.get("user"):
            return redirect(url_for("dashboard.login"))
        return render_template(
            "portfolio_history_audit_v24_6.html",
            title="Portfolio History and Audit",
            payload=build_portfolio_history_audit(),
        )

    @app.get("/api/v1/portfolio-operations/history")
    def api_portfolio_history_audit_get_v24_6():
        if not session.get("user"):
            return jsonify({"error": "login required"}), 401
        return jsonify(build_portfolio_history_audit())

    return app
