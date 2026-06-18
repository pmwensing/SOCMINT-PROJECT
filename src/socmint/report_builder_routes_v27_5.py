from __future__ import annotations

from flask import jsonify, redirect, render_template, request, session, url_for

from .report_builder_events_v27_5 import create_report_definition, current_reports, revise_report_definition
from .report_export_packages_v27_5 import generate_report_package, latest_packages
from .search_reporting_history_audit_routes_v27_6 import register_search_reporting_history_audit_routes_v27_6


def _payload() -> dict:
    value = request.get_json(silent=True)
    return value if isinstance(value, dict) else {}


def _allowed_case_ids() -> set[str] | None:
    value = session.get("allowed_case_ids")
    if value is None:
        return None
    if not isinstance(value, (list, tuple, set)):
        return set()
    return {str(item).strip() for item in value if str(item).strip()}


def _visible_reports(user: str) -> list[dict]:
    return [item for item in current_reports() if item.get("owner") == user or item.get("visibility") == "shared"]


def _code(result: dict, success: str) -> int:
    return 200 if result.get("status") == success else 422


def register_report_builder_routes_v27_5(app):
    @app.get("/global-search/reports")
    def report_builder_get_v27_5():
        if not session.get("user"):
            return redirect(url_for("dashboard.login"))
        user = str(session.get("user"))
        reports = _visible_reports(user)
        packages = latest_packages()
        return render_template(
            "report_builder_v27_5.html",
            title="Report Builder and Export Packages",
            payload={"schema":"socmint.report_builder_export_packages.v27_5","version":"v27.5.0","status":"ready","reports":reports,"report_count":len(reports),"packages":packages,"package_count":len(packages)},
        )

    @app.get("/api/v1/global-search/reports")
    def api_report_builder_get_v27_5():
        if not session.get("user"):
            return jsonify({"error": "login required"}), 401
        user = str(session.get("user"))
        reports = _visible_reports(user)
        packages = latest_packages()
        return jsonify({"schema":"socmint.report_builder_export_packages.v27_5","version":"v27.5.0","status":"ready","reports":reports,"report_count":len(reports),"packages":packages,"package_count":len(packages)})

    @app.post("/api/v1/global-search/reports")
    def api_report_create_post_v27_5():
        if not session.get("user"):
            return jsonify({"error": "login required"}), 401
        payload = _payload()
        result = create_report_definition(
            name=str(payload.get("name") or ""), owner=str(session.get("user")),
            description=str(payload.get("description") or ""), visibility=str(payload.get("visibility") or "private"),
            sections=payload.get("sections"), export_formats=payload.get("export_formats"),
            confirmed=payload.get("confirmed") is True, ip_address=request.remote_addr,
        )
        return jsonify(result), _code(result, "report_definition_created")

    @app.post("/api/v1/global-search/reports/<report_id>/revise")
    def api_report_revise_post_v27_5(report_id: str):
        if not session.get("user"):
            return jsonify({"error": "login required"}), 401
        payload = _payload()
        result = revise_report_definition(
            report_id, actor=str(session.get("user")), name=str(payload.get("name") or ""),
            description=str(payload.get("description") or ""), visibility=str(payload.get("visibility") or "private"),
            sections=payload.get("sections"), export_formats=payload.get("export_formats"),
            reason=str(payload.get("reason") or ""), confirmed=payload.get("confirmed") is True,
            ip_address=request.remote_addr,
        )
        return jsonify(result), _code(result, "report_definition_revised")

    @app.post("/api/v1/global-search/reports/<report_id>/generate")
    def api_report_generate_post_v27_5(report_id: str):
        if not session.get("user"):
            return jsonify({"error": "login required"}), 401
        payload = _payload()
        try:
            limit = int(payload.get("limit", 100))
        except (TypeError, ValueError):
            limit = 100
        result = generate_report_package(
            report_id, user_identity=str(session.get("user")), allowed_case_ids=_allowed_case_ids(),
            formats=payload.get("formats"), limit=limit,
            confirmed=payload.get("confirmed") is True, ip_address=request.remote_addr,
        )
        return jsonify(result), _code(result, "report_package_generated")

    register_search_reporting_history_audit_routes_v27_6(app)
    return app
