from __future__ import annotations

from flask import jsonify

from .build_scope_lock import evaluate_scope_lock


def register_scope_lock_routes(app) -> None:
    if "api_v7_5_scope_lock" in app.view_functions:
        return

    from .dashboard import login_required

    @login_required
    def api_v7_5_scope_lock():
        return jsonify(evaluate_scope_lock(app))

    @login_required
    def api_v7_5_scope_manifest():
        payload = evaluate_scope_lock(app)
        return jsonify(
            {
                "schema": payload["schema"],
                "status": payload["status"],
                "approved_build_line": payload["approved_build_line"],
                "approved_build_name": payload["approved_build_name"],
                "approved_source": payload["approved_source"],
                "approved_pillars": payload["approved_pillars"],
                "scope_gates": payload["scope_gates"],
                "human_approval_required_for": payload["human_approval_required_for"],
            }
        )

    app.add_url_rule(
        "/api/v1/workbench/scope-lock",
        endpoint="api_v7_5_scope_lock",
        view_func=api_v7_5_scope_lock,
        methods=["GET"],
    )
    app.add_url_rule(
        "/api/v1/workbench/build-spec-lock",
        endpoint="api_v7_5_scope_manifest",
        view_func=api_v7_5_scope_manifest,
        methods=["GET"],
    )
