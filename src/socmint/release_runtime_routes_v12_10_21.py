from __future__ import annotations

from flask import jsonify, redirect, render_template, session, url_for

from .release_runtime_readiness_v12_10_21 import release_runtime_readiness


def _login_required() -> bool:
    return bool(session.get("user"))


def register_release_runtime_routes(app):
    @app.get("/api/v1/release/runtime")
    def api_release_runtime_v12_10_21():
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(release_runtime_readiness())

    @app.get("/release/runtime")
    def release_runtime_v12_10_21():
        if not _login_required():
            return redirect(url_for("dashboard.login"))
        payload = release_runtime_readiness()
        return render_template(
            "release_runtime.html",
            title="Release Runtime Readiness",
            payload=payload,
        )

    return app
