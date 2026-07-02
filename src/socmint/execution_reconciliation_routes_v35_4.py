from __future__ import annotations

import json
import secrets
from typing import Any

from flask import (
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from .durable_execution_ledger_v35_1 import (
    ExecutionNotFound,
    ExecutionStateConflict,
)
from .execution_reconciliation_read_v35_4 import (
    execution_reconciliation_detail,
    list_uncertain_executions,
)
from .execution_reconciliation_service_v35_4 import (
    ReconciliationBindingError,
    reconcile_execution,
)
from .governance_execution_result_store_v35_3 import ExecutionResultConflict
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
                "execution_reconciliation_v35_4.html",
                title="Execution Reconciliation",
                payload={"status": "forbidden", "executions": []},
                csrf_token="",
            ),
            403,
        )
    return actor, None


def _csrf_token() -> str:
    token = str(session.get("_csrf_token") or "")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_csrf_token"] = token
    return token


def _form_payload() -> dict[str, Any]:
    record_ids: Any = None
    evidence: Any = None
    try:
        record_ids = json.loads(
            request.form.get("authoritative_record_ids", "")
        )
    except (TypeError, ValueError):
        record_ids = None
    try:
        evidence = json.loads(request.form.get("evidence_references", ""))
    except (TypeError, ValueError):
        evidence = None
    return {
        "expected_state": request.form.get("expected_state"),
        "expected_version": request.form.get("expected_version"),
        "authoritative_record_ids": record_ids,
        "result_reference_sha256": request.form.get("result_reference_sha256"),
        "workspace_sha256": request.form.get("workspace_sha256"),
        "reconciliation_reason": request.form.get("reconciliation_reason"),
        "evidence_references": evidence,
    }


def _error_response(exc: Exception):
    if isinstance(exc, ExecutionNotFound):
        return jsonify({"error": "execution not found"}), 404
    if isinstance(exc, ExecutionStateConflict):
        return jsonify({"error": "execution state conflict"}), 409
    if isinstance(exc, ExecutionResultConflict):
        return jsonify({"error": "reconciliation conflict"}), 409
    if isinstance(exc, ReconciliationBindingError):
        return jsonify({"error": "reconciliation bindings unavailable"}), 422
    raise exc


def register_execution_reconciliation_routes_v35_4(app):
    @app.get("/api/v1/dissemination-governance/executions/uncertain")
    def api_uncertain_executions_v35_4():
        _, error = _actor_or_error()
        if error:
            return error
        payload = list_uncertain_executions(
            limit=request.args.get("limit", 100, type=int),
            offset=request.args.get("offset", 0, type=int),
        )
        return jsonify(payload), 200

    @app.get("/api/v1/dissemination-governance/executions/<execution_id>")
    def api_execution_reconciliation_detail_v35_4(execution_id: str):
        _, error = _actor_or_error()
        if error:
            return error
        payload = execution_reconciliation_detail(execution_id)
        if payload is None:
            return jsonify({"error": "execution not found"}), 404
        return jsonify(payload), 200

    @app.post(
        "/api/v1/dissemination-governance/executions/<execution_id>/reconcile"
    )
    def api_reconcile_execution_v35_4(execution_id: str):
        actor, error = _actor_or_error()
        if error:
            return error
        body = request.get_json(silent=True)
        try:
            payload = reconcile_execution(execution_id, body, actor=actor)
        except (
            ExecutionNotFound,
            ExecutionStateConflict,
            ExecutionResultConflict,
            ReconciliationBindingError,
        ) as exc:
            return _error_response(exc)
        if payload.get("status") == "invalid_request":
            return jsonify(payload), 422
        return jsonify(payload), 200

    @app.get("/dissemination-governance/execution-reconciliation")
    def execution_reconciliation_page_v35_4():
        _, error = _page_actor()
        if error:
            return error
        payload = list_uncertain_executions(limit=200, offset=0)
        return render_template(
            "execution_reconciliation_v35_4.html",
            title="Execution Reconciliation",
            payload=payload,
            csrf_token=_csrf_token(),
        )

    @app.post(
        "/dissemination-governance/execution-reconciliation/"
        "<execution_id>/reconcile"
    )
    def execution_reconciliation_submit_v35_4(execution_id: str):
        actor, error = _page_actor()
        if error:
            return error
        expected_csrf = str(session.get("_csrf_token") or "")
        supplied_csrf = str(request.form.get("csrf_token") or "")
        if not expected_csrf or not secrets.compare_digest(
            expected_csrf, supplied_csrf
        ):
            return render_template(
                "execution_reconciliation_v35_4.html",
                title="Execution Reconciliation",
                payload={"status": "invalid_request", "executions": []},
                csrf_token=_csrf_token(),
            ), 400
        try:
            result = reconcile_execution(
                execution_id,
                _form_payload(),
                actor=actor,
            )
            if result.get("status") == "invalid_request":
                flash("Reconciliation request did not pass validation.", "error")
            else:
                flash("Execution reconciled without delegate retry.", "success")
        except ExecutionNotFound:
            flash("Execution was not found.", "error")
        except ExecutionStateConflict:
            flash("Execution state changed; refresh before reconciling.", "error")
        except ExecutionResultConflict:
            flash("A different authoritative result is already recorded.", "error")
        except ReconciliationBindingError:
            flash("Durable invocation bindings are unavailable.", "error")
        return redirect(
            url_for("execution_reconciliation_page_v35_4")
        )

    return app
