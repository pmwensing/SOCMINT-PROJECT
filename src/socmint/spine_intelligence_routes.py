from __future__ import annotations

from flask import abort, flash, jsonify, redirect, render_template, request, session, url_for

from .spine import run_spine_for_subject
from .spine_intelligence import promote_observation_to_assertion
from .spine_intelligence import review_spine_assertion
from .spine_intelligence import spine_intelligence_payload


def register_spine_intelligence_routes(app) -> None:
    if "spine_intelligence_view" in app.view_functions:
        return

    from .dashboard import audit, login_required, run_required

    @login_required
    def spine_intelligence_view(subject_id: int):
        try:
            payload = spine_intelligence_payload(subject_id)
        except ValueError:
            abort(404)
        return render_template("spine_intelligence.html", payload=payload)

    @run_required
    def spine_intelligence_run(subject_id: int):
        connectors = request.form.getlist("connectors")
        try:
            result = run_spine_for_subject(subject_id, connectors or None)
            audit("spine_intelligence_run", details=result)
            flash(f"Ran {len(result['run_ids'])} Spine connector runs.", "success")
        except Exception as exc:
            flash(str(exc), "error")
        return redirect(url_for("spine_intelligence_view", subject_id=subject_id))

    @run_required
    def spine_observation_promote(observation_id: int):
        subject_id = request.form.get("subject_id", type=int)
        note = request.form.get("note", "").strip() or None
        try:
            result = promote_observation_to_assertion(
                observation_id,
                actor=session.get("user"),
                note=note,
            )
            audit("spine_observation_promote", details=result)
            flash(f"Observation promoted to assertion {result['assertion_id']}.", "success")
            subject_id = result["subject_id"]
        except Exception as exc:
            flash(str(exc), "error")
        return redirect(url_for("spine_intelligence_view", subject_id=subject_id))

    @run_required
    def spine_intelligence_assertion_review(assertion_id: int):
        subject_id = request.form.get("subject_id", type=int)
        action = request.form.get("action", "").strip()
        note = request.form.get("note", "").strip() or None
        try:
            result = review_spine_assertion(
                assertion_id,
                action,
                actor=session.get("user"),
                note=note,
            )
            audit("spine_intelligence_assertion_review", details=result)
            flash(f"Assertion marked {action}.", "success")
        except Exception as exc:
            flash(str(exc), "error")
        return redirect(url_for("spine_intelligence_view", subject_id=subject_id))

    @login_required
    def api_spine_intelligence(subject_id: int):
        try:
            payload = spine_intelligence_payload(subject_id)
        except ValueError:
            abort(404)
        return jsonify(payload)

    @run_required
    def api_spine_intelligence_run(subject_id: int):
        payload = request.get_json(silent=True) or {}
        result = run_spine_for_subject(subject_id, payload.get("connectors") or None)
        audit("spine_intelligence_run", details=result)
        return jsonify(result), 202

    @run_required
    def api_spine_observation_promote(observation_id: int):
        payload = request.get_json(silent=True) or {}
        result = promote_observation_to_assertion(
            observation_id,
            actor=session.get("user"),
            note=payload.get("note"),
        )
        audit("spine_observation_promote", details=result)
        return jsonify(result), 202

    @run_required
    def api_spine_intelligence_assertion_review(assertion_id: int):
        payload = request.get_json(silent=True) or {}
        result = review_spine_assertion(
            assertion_id,
            payload.get("action", ""),
            actor=session.get("user"),
            note=payload.get("note"),
        )
        audit("spine_intelligence_assertion_review", details=result)
        return jsonify(result), 202

    app.add_url_rule(
        "/spine/subjects/<int:subject_id>/intelligence",
        endpoint="spine_intelligence_view",
        view_func=spine_intelligence_view,
        methods=["GET"],
    )
    app.add_url_rule(
        "/spine/subjects/<int:subject_id>/intelligence/run",
        endpoint="spine_intelligence_run",
        view_func=spine_intelligence_run,
        methods=["POST"],
    )
    app.add_url_rule(
        "/spine/observations/<int:observation_id>/promote",
        endpoint="spine_observation_promote",
        view_func=spine_observation_promote,
        methods=["POST"],
    )
    app.add_url_rule(
        "/spine/intelligence/assertions/<int:assertion_id>/review",
        endpoint="spine_intelligence_assertion_review",
        view_func=spine_intelligence_assertion_review,
        methods=["POST"],
    )
    app.add_url_rule(
        "/api/v1/spine/subjects/<int:subject_id>/intelligence",
        endpoint="api_spine_intelligence",
        view_func=api_spine_intelligence,
        methods=["GET"],
    )
    app.add_url_rule(
        "/api/v1/spine/subjects/<int:subject_id>/intelligence/run",
        endpoint="api_spine_intelligence_run",
        view_func=api_spine_intelligence_run,
        methods=["POST"],
    )
    app.add_url_rule(
        "/api/v1/spine/observations/<int:observation_id>/promote",
        endpoint="api_spine_observation_promote",
        view_func=api_spine_observation_promote,
        methods=["POST"],
    )
    app.add_url_rule(
        "/api/v1/spine/intelligence/assertions/<int:assertion_id>/review",
        endpoint="api_spine_intelligence_assertion_review",
        view_func=api_spine_intelligence_assertion_review,
        methods=["POST"],
    )
