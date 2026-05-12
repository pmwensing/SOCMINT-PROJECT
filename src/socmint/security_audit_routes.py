from __future__ import annotations

import os

from flask import jsonify, session

from .security_audit import scan_repo_for_secrets
from .security_audit import security_audit_summary
from .security_audit import security_header_expectations
from .security_audit import session_cookie_expectations
from .security_audit import validate_secret_value


def _admin_required():
    return bool(session.get("user") and session.get("is_admin"))


def register_security_audit_routes(app):
    @app.get("/api/v1/admin/security/audit")
    def api_security_audit():
        if not _admin_required():
            return jsonify({"error": "admin required"}), 403
        return jsonify(security_audit_summary())

    @app.get("/api/v1/admin/security/secrets/scan")
    def api_security_secret_scan():
        if not _admin_required():
            return jsonify({"error": "admin required"}), 403
        return jsonify(scan_repo_for_secrets())

    @app.get("/api/v1/admin/security/headers")
    def api_security_headers():
        if not _admin_required():
            return jsonify({"error": "admin required"}), 403
        return jsonify(security_header_expectations())

    @app.get("/api/v1/admin/security/cookies")
    def api_security_cookies():
        if not _admin_required():
            return jsonify({"error": "admin required"}), 403
        https_enabled = str(os.getenv("SOCMINT_HTTPS", "false")).lower() == "true"
        return jsonify(session_cookie_expectations(https_enabled=https_enabled))

    @app.get("/api/v1/admin/security/secret-key")
    def api_security_secret_key():
        if not _admin_required():
            return jsonify({"error": "admin required"}), 403
        return jsonify(validate_secret_value(os.getenv("SOCMINT_SECRET_KEY")))

    return app
