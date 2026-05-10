from __future__ import annotations

from flask import abort, flash, jsonify, redirect, render_template, request, session, url_for

from .connector_review import connector_run_detail_payload
from .connector_review import connector_runs_payload
from .connector_review import finding_queue_payload
from .connector_review import review_finding


def register_connector_review_routes(app) -> None:
    if "connector_runs_view" in app.view_functions:
        return

    from .dashboard import audit, login_required, run_required

    @login_required
    def connector_runs_view():
        return render_template("connector_runs.html", payload=connector_runs_payload())

    @login_required
    def connector_run_detail_view(run_id: int):
        payload = connector_run_detail_payload(run_id)
        if not payload:
            abort(404)
        return render_template("connector_run_detail.html", payload=payload)

    @run_required
    def connector_finding_queue_view():
        return render_template("connector_finding_queue.html", payload=finding_queue_payload())

    @run_required
    def connector_finding_review_action(finding_id: int):
        action = request.form.get("action", "").strip()
        note = request.form.get("note", "").strip() or None
        subject_id = request.form.get("subject_id", type=int)
        try:
            result = review_finding(
                finding_id,
                action,
                actor=session.get("user"),
                note=note,
                subject_id=subject_id,
            )
            audit("connector_finding_review", details=result)
            if result.get("assertion_id"):
                flash(
                    f"Finding promoted into subject {subject_id} as assertion {result['assertion_id']}.",
                    "success",
                )
            else:
                flash(f"Finding marked {action}.", "success")
        except Exception as exc:
            flash(str(exc), "error")
        return redirect(request.referrer or url_for("connector_finding_queue_view"))

    @login_required
    def api_connector_runs():
        return jsonify(connector_runs_payload())

    @login_required
    def api_connector_run_detail(run_id: int):
        payload = connector_run_detail_payload(run_id)
        if not payload:
            abort(404)
        return jsonify(payload)

    @run_required
    def api_connector_finding_queue():
        return jsonify(finding_queue_payload())

    @run_required
    def api_connector_finding_review(finding_id: int):
        payload = request.get_json(silent=True) or {}
        result = review_finding(
            finding_id,
            payload.get("action", ""),
            actor=session.get("user"),
            note=payload.get("note"),
            subject_id=payload.get("subject_id"),
        )
        audit("connector_finding_review", details=result)
        return jsonify(result), 202

    app.add_url_rule(
        "/connectors/runs",
        endpoint="connector_runs_view",
        view_func=connector_runs_view,
        methods=["GET"],
    )
    app.add_url_rule(
        "/connectors/runs/<int:run_id>",
        endpoint="connector_run_detail_view",
        view_func=connector_run_detail_view,
        methods=["GET"],
    )
    app.add_url_rule(
        "/connectors/findings",
        endpoint="connector_finding_queue_view",
        view_func=connector_finding_queue_view,
        methods=["GET"],
    )
    app.add_url_rule(
        "/connectors/findings/<int:finding_id>/review",
        endpoint="connector_finding_review_action",
        view_func=connector_finding_review_action,
        methods=["POST"],
    )
    app.add_url_rule(
        "/api/v1/connectors/runs",
        endpoint="api_connector_runs",
        view_func=api_connector_runs,
        methods=["GET"],
    )
    app.add_url_rule(
        "/api/v1/connectors/runs/<int:run_id>",
        endpoint="api_connector_run_detail",
        view_func=api_connector_run_detail,
        methods=["GET"],
    )
    app.add_url_rule(
        "/api/v1/connectors/findings",
        endpoint="api_connector_finding_queue",
        view_func=api_connector_finding_queue,
        methods=["GET"],
    )
    app.add_url_rule(
        "/api/v1/connectors/findings/<int:finding_id>/review",
        endpoint="api_connector_finding_review",
        view_func=api_connector_finding_review,
        methods=["POST"],
    )
