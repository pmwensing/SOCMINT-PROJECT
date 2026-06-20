from __future__ import annotations

from flask import (
    Response,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from .release_ledger_dashboard import release_ledger_dashboard
from .release_ledger_dashboard import release_ledger_dashboard_markdown


def _login_required() -> bool:
    return bool(session.get("user"))


def register_release_ledger_dashboard_routes(app):
    @app.get("/dossier/release-ledger-dashboard")
    def release_ledger_dashboard_view():
        if not _login_required():
            return redirect(url_for("dashboard.login"))
        case_id = (request.args.get("case_id") or "").strip()
        payload = release_ledger_dashboard(case_id) if case_id else None
        return render_template(
            "release_ledger_dashboard.html",
            title="Release Ledger Dashboard",
            case_id=case_id,
            payload=payload,
        )

    @app.get("/api/v1/dossier-builder/v3/release-ledger-dashboard/<case_id>")
    def api_release_ledger_dashboard(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(release_ledger_dashboard(case_id=case_id))

    @app.get("/api/v1/dossier-builder/v3/release-ledger-dashboard/<case_id>/markdown")
    def api_release_ledger_dashboard_markdown(case_id: str):
        if not _login_required():
            return Response("login required\n", status=401, mimetype="text/plain")
        return Response(
            release_ledger_dashboard_markdown(case_id=case_id), mimetype="text/markdown"
        )

    return app
