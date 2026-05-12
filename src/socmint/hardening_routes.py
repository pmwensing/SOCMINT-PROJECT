from __future__ import annotations

from flask import jsonify, session

from .export_gate import export_preflight
from .export_gate import export_preflight_summary
from .gate_audit import gate_audit_summary
from .gate_audit import route_gate_matrix

SECURITY_HARDENING_SCHEMA = "socmint.security_hardening.v9_0_2"


def _admin_required():
    return bool(session.get("user") and session.get("is_admin"))


def security_hardening_checklist() -> dict:
    return {
        "schema": SECURITY_HARDENING_SCHEMA,
        "status": "checklist_ready",
        "controls": {
            "secret_scanning": "recommended: enable gitleaks/detect-secrets in CI",
            "csrf": "recommended: verify every state-changing form/API route",
            "security_headers": "recommended: verify CSP, X-Frame-Options, nosniff, referrer policy",
            "session_cookies": "recommended: verify HttpOnly, SameSite, Secure when HTTPS is enabled",
            "rate_limits": "recommended: verify login/signup/scan throttles",
            "branch_protection": "recommended: require PR review and CI before merge",
            "route_gate_matrix": "available at /api/v1/admin/gates/matrix",
            "export_preflight": "available at /api/v1/spine/subjects/<id>/export-preflight",
        },
    }


def register_hardening_routes(app):
    @app.get("/api/v1/admin/gates/matrix")
    def api_gate_matrix():
        if not _admin_required():
            return jsonify({"error": "admin required"}), 403
        return jsonify(route_gate_matrix(app))

    @app.get("/api/v1/admin/gates/summary")
    def api_gate_summary():
        if not _admin_required():
            return jsonify({"error": "admin required"}), 403
        return jsonify(gate_audit_summary(app))

    @app.get("/api/v1/admin/security/checklist")
    def api_security_checklist():
        if not _admin_required():
            return jsonify({"error": "admin required"}), 403
        return jsonify(security_hardening_checklist())

    @app.get("/api/v1/spine/subjects/<int:subject_id>/export-preflight")
    def api_export_preflight(subject_id: int):
        if not session.get("user"):
            return jsonify({"error": "login required"}), 401
        return jsonify(export_preflight(subject_id, external=True))

    @app.get("/api/v1/spine/subjects/<int:subject_id>/export-preflight/summary")
    def api_export_preflight_summary(subject_id: int):
        if not session.get("user"):
            return jsonify({"error": "login required"}), 401
        return jsonify(export_preflight_summary(subject_id))

    return app
