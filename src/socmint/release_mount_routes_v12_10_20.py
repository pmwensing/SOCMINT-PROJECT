from __future__ import annotations

from flask import jsonify, redirect, render_template, session, url_for

from .release_mount_contract_v12_10_20 import release_mount_contract


def _login_required() -> bool:
    return bool(session.get("user"))


def register_release_mount_routes(app):
    @app.get("/api/v1/release/mounts")
    def api_release_mounts_v12_10_20():
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(release_mount_contract())

    @app.get("/release/mounts")
    def release_mounts_v12_10_20():
        if not _login_required():
            return redirect(url_for("dashboard.login"))
        payload = release_mount_contract()
        return render_template(
            "release_mounts.html",
            title="Release Mount Contract",
            payload=payload,
            rows=payload.get("required_paths", []),
            missing=payload.get("missing", []),
        )

    return app
