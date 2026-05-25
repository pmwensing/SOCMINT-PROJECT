from __future__ import annotations

from flask import Blueprint, jsonify

from .v12_10_54_runtime_guard import (
    VERSION,
    archive_integrity,
    assert_real_db_upgrade_allowed,
    rollback_instructions,
    runtime_schema_status,
    version_payload,
)


v12_10_54_bp = Blueprint("v12_10_54_runtime_guard", __name__)


@v12_10_54_bp.get("/api/version")
def api_version():
    return jsonify(version_payload())


@v12_10_54_bp.get("/api/schema/status")
def api_schema_status():
    return jsonify(runtime_schema_status())


@v12_10_54_bp.get("/api/schema/upgrade-guard")
def api_schema_upgrade_guard():
    return jsonify(assert_real_db_upgrade_allowed())


@v12_10_54_bp.get("/api/release/archive-integrity")
def api_release_archive_integrity():
    return jsonify(archive_integrity())


@v12_10_54_bp.get("/api/schema/rollback/0018")
def api_schema_rollback_0018():
    return jsonify(rollback_instructions())


def register_v12_10_54_routes(app):
    existing = set(getattr(app, "blueprints", {}).keys())
    if "v12_10_54_runtime_guard" not in existing:
        app.register_blueprint(v12_10_54_bp)
    return app
