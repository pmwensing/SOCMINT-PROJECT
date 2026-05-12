from __future__ import annotations

from flask import jsonify, request, session

from .connector_sdk import connector_marketplace_sdk_payload
from .connector_sdk import registered_connector_manifests
from .connector_sdk import sdk_fixture_run
from .connector_sdk import validate_connector_spec


def _login_required():
    return bool(session.get("user"))


def register_connector_sdk_routes(app):
    @app.get("/api/v1/connectors/sdk/catalog")
    def api_connector_sdk_catalog():
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(registered_connector_manifests())

    @app.get("/api/v1/connectors/sdk/marketplace")
    def api_connector_sdk_marketplace():
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(connector_marketplace_sdk_payload())

    @app.post("/api/v1/connectors/sdk/validate")
    def api_connector_sdk_validate():
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(validate_connector_spec(request.get_json(silent=True) or {}))

    @app.post("/api/v1/connectors/sdk/fixture-run")
    def api_connector_sdk_fixture_run():
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        payload = request.get_json(silent=True) or {}
        return jsonify(
            sdk_fixture_run(
                payload.get("connector", ""),
                payload.get("target", ""),
                payload.get("target_type", "target"),
            )
        )

    return app
