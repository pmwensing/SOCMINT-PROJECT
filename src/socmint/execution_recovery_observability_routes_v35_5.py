from __future__ import annotations

from flask import jsonify, redirect, render_template, request, session, url_for

from .execution_recovery_observability_v35_5 import (
    attention_queue,
    execution_recovery_workspace,
    reconciled_executions,
    recovery_summary,
)
from .user_account_workspace_v28_1 import actor_is_administrator


def _actor_or_error():
    actor = str(session.get("user") or "")
    if not actor:
        return None, (jsonify({"error": "login required"}), 401)
    if not actor_is_administrator(actor):
        return None, (jsonify({"error": "administrator required"}), 403)
    return actor, None


def _page_actor():
    actor = str(session.get("user") or "")
    if not actor:
        return None, redirect(url_for("dashboard.login"))
    if not actor_is_administrator(actor):
        return None, (
            render_template(
                "execution_recovery_observability_v35_5.html",
                title="Execution Recovery Observability",
                payload={"status": "forbidden", "read_only": True},
            ),
            403,
        )
    return actor, None


def register_execution_recovery_observability_routes_v35_5(app):
    @app.get("/api/v1/dissemination-governance/executions/recovery-summary")
    def api_execution_recovery_summary_v35_5():
        _, error = _actor_or_error()
        if error:
            return error
        return jsonify(recovery_summary()), 200

    @app.get("/api/v1/dissemination-governance/executions/attention")
    def api_execution_attention_queue_v35_5():
        _, error = _actor_or_error()
        if error:
            return error
        return jsonify(
            attention_queue(limit=request.args.get("limit", 200, type=int))
        ), 200

    @app.get("/api/v1/dissemination-governance/executions/reconciled")
    def api_reconciled_executions_v35_5():
        _, error = _actor_or_error()
        if error:
            return error
        return jsonify(
            reconciled_executions(limit=request.args.get("limit", 200, type=int))
        ), 200

    @app.get("/dissemination-governance/execution-recovery-observability")
    def execution_recovery_observability_page_v35_5():
        _, error = _page_actor()
        if error:
            return error
        return render_template(
            "execution_recovery_observability_v35_5.html",
            title="Execution Recovery Observability",
            payload=execution_recovery_workspace(),
        )

    return app
