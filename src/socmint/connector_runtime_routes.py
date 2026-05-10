from __future__ import annotations

from flask import jsonify, render_template

from .connector_runtime import connector_runtime_health


def register_connector_runtime_routes(app) -> None:
    if "connector_runtime_health_api" in app.view_functions:
        return

    from .dashboard import login_required

    @login_required
    def connector_runtime_health_view():
        return render_template(
            "connector_runtime.html",
            payload=connector_runtime_health(),
        )

    @login_required
    def connector_runtime_health_api():
        return jsonify(connector_runtime_health())

    app.add_url_rule(
        "/connectors/runtime",
        endpoint="connector_runtime_health_view",
        view_func=connector_runtime_health_view,
        methods=["GET"],
    )
    app.add_url_rule(
        "/api/v1/connectors/runtime",
        endpoint="connector_runtime_health_api",
        view_func=connector_runtime_health_api,
        methods=["GET"],
    )
