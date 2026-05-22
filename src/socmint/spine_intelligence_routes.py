from __future__ import annotations

from flask import Response, abort, flash, jsonify, redirect, render_template, request, session, url_for

from .candidate_profile_review_v12_10_4 import export_profile_review_report, review_candidate_profile
from .connectors import connector_mode_report
from .dossier_assertion_projection_v12_10_8 import export_dossier_assertion_projection_report
from .dossier_assertion_review_packet_v12_10_9 import export_dossier_assertion_review_packet_report
from .entity_alias_graph_v12_10_6 import export_entity_alias_graph_report
from .entity_alias_review_v12_10_7 import merge_alias_cluster, promote_alias_to_assertion, review_entity_alias, split_alias_from_clusters
from .identity_link_hypothesis_v12_10_7 import export_identity_link_hypothesis_report
from .legacy_assertion_scrubber_v12_10_7_2 import scrub_legacy_assertions
from .spine import run_spine_for_subject
from .spine_connector_queue_v12_10_1 import queue_subject_connector_jobs
from .spine_intelligence_v11_9 import promote_observation_to_assertion
from .spine_intelligence_v11_9 import review_spine_assertion
from .spine_intelligence_v11_9 import spine_intelligence_payload


def register_spine_intelligence_routes(app) -> None:
    if "spine_intelligence_view" in app.view_functions:
        return

    from .dashboard import audit, login_required, run_required

    @login_required
    def spine_intelligence_view(subject_id: int):
        try:
            payload = spine_intelligence_payload(subject_id)
            payload["connector_mode"] = connector_mode_report()
        except ValueError:
            abort(404)
        return render_template("spine_intelligence.html", payload=payload)

    @run_required
    def spine_intelligence_run(subject_id: int):
        connectors = request.form.getlist("connectors")
        try:
            if request.form.get("run_inline") == "1":
                result = run_spine_for_subject(subject_id, connectors or None)
                audit("spine_intelligence_run_inline", details=result)
                flash(f"Ran {len(result['run_ids'])} Spine connector runs inline.", "success")
            else:
                result = queue_subject_connector_jobs(subject_id, connectors or None, actor=session.get("user"))
                audit("spine_intelligence_queue", details=result)
                flash(f"Queued {result['queued_count']} connector job(s). Worker will run live connectors; web UI will not block.", "success")
        except Exception as exc:
            flash(str(exc), "error")
        return redirect(url_for("spine_intelligence_view", subject_id=subject_id))

    @run_required
    def spine_candidate_profile_review(subject_id: int, candidate_id: str):
        action = request.form.get("action", "").strip()
        note = request.form.get("note", "").strip() or None
        try:
            payload = spine_intelligence_payload(subject_id)
            result = review_candidate_profile(subject_id, candidate_id, action, payload.get("profile_fingerprints", {}), actor=session.get("user"), note=note)
            audit("spine_candidate_profile_review", details=result)
            flash(f"Candidate profile {candidate_id} marked {result['review_state']}.", "success")
        except Exception as exc:
            flash(str(exc), "error")
        return redirect(url_for("spine_intelligence_view", subject_id=subject_id))

    @run_required
    def spine_entity_alias_review(subject_id: int, alias_id: str):
        action = request.form.get("action", "").strip()
        note = request.form.get("note", "").strip() or None
        try:
            payload = spine_intelligence_payload(subject_id)
            result = review_entity_alias(subject_id, alias_id, action, payload.get("entity_alias_graph", {}), actor=session.get("user"), note=note)
            audit("spine_entity_alias_review", details=result)
            flash(f"Alias {alias_id} marked {result['review_state']}.", "success")
        except Exception as exc:
            flash(str(exc), "error")
        return redirect(url_for("spine_intelligence_view", subject_id=subject_id))

    @run_required
    def spine_entity_alias_cluster(subject_id: int):
        action = request.form.get("action", "").strip()
        note = request.form.get("note", "").strip() or None
        alias_ids = request.form.getlist("alias_ids") or [item.strip() for item in request.form.get("alias_ids_text", "").split(",") if item.strip()]
        alias_id = request.form.get("alias_id", "").strip()
        try:
            payload = spine_intelligence_payload(subject_id)
            if action == "merge_aliases":
                result = merge_alias_cluster(subject_id, alias_ids, payload.get("entity_alias_graph", {}), actor=session.get("user"), note=note)
                flash(f"Merged {len(result['alias_ids'])} alias(es) into {result['cluster_id']}.", "success")
            elif action == "split_alias":
                result = split_alias_from_clusters(subject_id, alias_id, actor=session.get("user"), note=note)
                flash(f"Split alias {alias_id} from {len(result['split_from_clusters'])} cluster(s).", "success")
            else:
                raise ValueError(f"Unsupported alias cluster action: {action}")
            audit("spine_entity_alias_cluster", details=result)
        except Exception as exc:
            flash(str(exc), "error")
        return redirect(url_for("spine_intelligence_view", subject_id=subject_id))

    @run_required
    def spine_entity_alias_promote(subject_id: int, alias_id: str):
        note = request.form.get("note", "").strip() or None
        try:
            payload = spine_intelligence_payload(subject_id)
            result = promote_alias_to_assertion(subject_id, alias_id, payload.get("entity_alias_graph", {}), actor=session.get("user"), note=note)
            audit("spine_entity_alias_promote", details=result)
            flash(f"Alias promoted to confirmed assertion {result['assertion_id']}.", "success")
        except Exception as exc:
            flash(str(exc), "error")
        return redirect(url_for("spine_intelligence_view", subject_id=subject_id))

    @login_required
    def spine_candidate_profile_report(subject_id: int):
        fmt = request.args.get("format", "json")
        try:
            payload = spine_intelligence_payload(subject_id)
            mime_type, filename, body = export_profile_review_report(subject_id, payload.get("profile_fingerprints", {}), fmt=fmt)
        except ValueError:
            abort(404)
        return Response(body, mimetype=mime_type, headers={"Content-Disposition": f"attachment; filename={filename}"})

    @login_required
    def spine_entity_alias_graph_report(subject_id: int):
        fmt = request.args.get("format", "json")
        try:
            payload = spine_intelligence_payload(subject_id)
            mime_type, filename, body = export_entity_alias_graph_report(payload.get("entity_alias_graph", {}), fmt=fmt)
        except ValueError:
            abort(404)
        return Response(body, mimetype=mime_type, headers={"Content-Disposition": f"attachment; filename={filename}"})

    @login_required
    def spine_identity_link_hypothesis_report(subject_id: int):
        fmt = request.args.get("format", "json")
        try:
            payload = spine_intelligence_payload(subject_id)
            mime_type, filename, body = export_identity_link_hypothesis_report(payload.get("identity_link_hypotheses", {}), fmt=fmt)
        except ValueError:
            abort(404)
        return Response(body, mimetype=mime_type, headers={"Content-Disposition": f"attachment; filename={filename}"})

    @login_required
    def spine_dossier_assertion_projection_report(subject_id: int):
        fmt = request.args.get("format", "json")
        try:
            payload = spine_intelligence_payload(subject_id)
            mime_type, filename, body = export_dossier_assertion_projection_report(payload.get("dossier_assertion_projection", {}), fmt=fmt)
        except ValueError:
            abort(404)
        return Response(body, mimetype=mime_type, headers={"Content-Disposition": f"attachment; filename={filename}"})

    @login_required
    def spine_dossier_assertion_review_packet_report(subject_id: int):
        fmt = request.args.get("format", "json")
        try:
            payload = spine_intelligence_payload(subject_id)
            mime_type, filename, body = export_dossier_assertion_review_packet_report(payload.get("dossier_assertion_review_packet", {}), fmt=fmt)
        except ValueError:
            abort(404)
        return Response(body, mimetype=mime_type, headers={"Content-Disposition": f"attachment; filename={filename}"})

    @run_required
    def spine_legacy_assertions_scrub(subject_id: int):
        try:
            result = scrub_legacy_assertions(subject_id, actor=session.get("user"), dry_run=False)
            audit("spine_legacy_assertions_scrub", details=result)
            flash(f"Suppressed {result['suppressed_count']} legacy assertion(s) that are not identity evidence.", "success")
        except Exception as exc:
            flash(str(exc), "error")
        return redirect(url_for("spine_intelligence_view", subject_id=subject_id))

    @run_required
    def spine_observation_promote(observation_id: int):
        subject_id = request.form.get("subject_id", type=int)
        note = request.form.get("note", "").strip() or None
        try:
            result = promote_observation_to_assertion(observation_id, actor=session.get("user"), note=note)
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
            result = review_spine_assertion(assertion_id, action, actor=session.get("user"), note=note)
            audit("spine_intelligence_assertion_review", details=result)
            flash(f"Assertion marked {action}.", "success")
        except Exception as exc:
            flash(str(exc), "error")
        return redirect(url_for("spine_intelligence_view", subject_id=subject_id))

    @login_required
    def api_spine_intelligence(subject_id: int):
        try:
            payload = spine_intelligence_payload(subject_id)
            payload["connector_mode"] = connector_mode_report()
        except ValueError:
            abort(404)
        return jsonify(payload)

    @login_required
    def api_spine_entity_alias_graph(subject_id: int):
        try:
            payload = spine_intelligence_payload(subject_id)
        except ValueError:
            abort(404)
        return jsonify(payload.get("entity_alias_graph", {}))

    @login_required
    def api_spine_identity_link_hypotheses(subject_id: int):
        try:
            payload = spine_intelligence_payload(subject_id)
        except ValueError:
            abort(404)
        return jsonify(payload.get("identity_link_hypotheses", {}))

    @login_required
    def api_spine_dossier_assertion_projection(subject_id: int):
        try:
            payload = spine_intelligence_payload(subject_id)
        except ValueError:
            abort(404)
        return jsonify(payload.get("dossier_assertion_projection", {}))

    @login_required
    def api_spine_dossier_assertion_review_packet(subject_id: int):
        try:
            payload = spine_intelligence_payload(subject_id)
        except ValueError:
            abort(404)
        return jsonify(payload.get("dossier_assertion_review_packet", {}))

    @run_required
    def api_spine_candidate_profile_review(subject_id: int, candidate_id: str):
        payload = request.get_json(silent=True) or {}
        current = spine_intelligence_payload(subject_id)
        result = review_candidate_profile(subject_id, candidate_id, payload.get("action", ""), current.get("profile_fingerprints", {}), actor=session.get("user"), note=payload.get("note"))
        audit("spine_candidate_profile_review", details=result)
        return jsonify(result), 202

    @run_required
    def api_spine_entity_alias_review(subject_id: int, alias_id: str):
        payload = request.get_json(silent=True) or {}
        current = spine_intelligence_payload(subject_id)
        result = review_entity_alias(subject_id, alias_id, payload.get("action", ""), current.get("entity_alias_graph", {}), actor=session.get("user"), note=payload.get("note"))
        audit("spine_entity_alias_review", details=result)
        return jsonify(result), 202

    @run_required
    def api_spine_entity_alias_promote(subject_id: int, alias_id: str):
        payload = request.get_json(silent=True) or {}
        current = spine_intelligence_payload(subject_id)
        result = promote_alias_to_assertion(subject_id, alias_id, current.get("entity_alias_graph", {}), actor=session.get("user"), note=payload.get("note"))
        audit("spine_entity_alias_promote", details=result)
        return jsonify(result), 202

    @run_required
    def api_spine_entity_alias_cluster(subject_id: int):
        payload = request.get_json(silent=True) or {}
        current = spine_intelligence_payload(subject_id)
        action = payload.get("action", "")
        if action == "merge_aliases":
            result = merge_alias_cluster(subject_id, payload.get("alias_ids") or [], current.get("entity_alias_graph", {}), actor=session.get("user"), note=payload.get("note"))
        elif action == "split_alias":
            result = split_alias_from_clusters(subject_id, payload.get("alias_id", ""), actor=session.get("user"), note=payload.get("note"))
        else:
            raise ValueError(f"Unsupported alias cluster action: {action}")
        audit("spine_entity_alias_cluster", details=result)
        return jsonify(result), 202

    @run_required
    def api_spine_intelligence_run(subject_id: int):
        payload = request.get_json(silent=True) or {}
        if payload.get("run_inline"):
            result = run_spine_for_subject(subject_id, payload.get("connectors") or None)
            audit("spine_intelligence_run_inline", details=result)
            return jsonify(result), 202
        result = queue_subject_connector_jobs(subject_id, payload.get("connectors") or None, actor=session.get("user"))
        audit("spine_intelligence_queue", details=result)
        return jsonify(result), 202

    @run_required
    def api_spine_observation_promote(observation_id: int):
        payload = request.get_json(silent=True) or {}
        result = promote_observation_to_assertion(observation_id, actor=session.get("user"), note=payload.get("note"))
        audit("spine_observation_promote", details=result)
        return jsonify(result), 202

    @run_required
    def api_spine_intelligence_assertion_review(assertion_id: int):
        payload = request.get_json(silent=True) or {}
        result = review_spine_assertion(assertion_id, payload.get("action", ""), actor=session.get("user"), note=payload.get("note"))
        audit("spine_intelligence_assertion_review", details=result)
        return jsonify(result), 202

    app.add_url_rule("/spine/subjects/<int:subject_id>/intelligence", endpoint="spine_intelligence_view", view_func=spine_intelligence_view, methods=["GET"])
    app.add_url_rule("/spine/subjects/<int:subject_id>/intelligence/run", endpoint="spine_intelligence_run", view_func=spine_intelligence_run, methods=["POST"])
    app.add_url_rule("/spine/subjects/<int:subject_id>/candidate-profiles/<candidate_id>/review", endpoint="spine_candidate_profile_review", view_func=spine_candidate_profile_review, methods=["POST"])
    app.add_url_rule("/spine/subjects/<int:subject_id>/aliases/<alias_id>/review", endpoint="spine_entity_alias_review", view_func=spine_entity_alias_review, methods=["POST"])
    app.add_url_rule("/spine/subjects/<int:subject_id>/aliases/<alias_id>/promote", endpoint="spine_entity_alias_promote", view_func=spine_entity_alias_promote, methods=["POST"])
    app.add_url_rule("/spine/subjects/<int:subject_id>/alias-clusters", endpoint="spine_entity_alias_cluster", view_func=spine_entity_alias_cluster, methods=["POST"])
    app.add_url_rule("/spine/subjects/<int:subject_id>/candidate-profiles/report", endpoint="spine_candidate_profile_report", view_func=spine_candidate_profile_report, methods=["GET"])
    app.add_url_rule("/spine/subjects/<int:subject_id>/entity-alias-graph/report", endpoint="spine_entity_alias_graph_report", view_func=spine_entity_alias_graph_report, methods=["GET"])
    app.add_url_rule("/spine/subjects/<int:subject_id>/identity-link-hypotheses/report", endpoint="spine_identity_link_hypothesis_report", view_func=spine_identity_link_hypothesis_report, methods=["GET"])
    app.add_url_rule("/spine/subjects/<int:subject_id>/dossier-assertion-projection/report", endpoint="spine_dossier_assertion_projection_report", view_func=spine_dossier_assertion_projection_report, methods=["GET"])
    app.add_url_rule("/spine/subjects/<int:subject_id>/dossier-assertion-review-packet/report", endpoint="spine_dossier_assertion_review_packet_report", view_func=spine_dossier_assertion_review_packet_report, methods=["GET"])
    app.add_url_rule("/spine/subjects/<int:subject_id>/assertions/scrub", endpoint="spine_legacy_assertions_scrub", view_func=spine_legacy_assertions_scrub, methods=["POST"])
    app.add_url_rule("/spine/observations/<int:observation_id>/promote", endpoint="spine_observation_promote", view_func=spine_observation_promote, methods=["POST"])
    app.add_url_rule("/spine/intelligence/assertions/<int:assertion_id>/review", endpoint="spine_intelligence_assertion_review", view_func=spine_intelligence_assertion_review, methods=["POST"])
    app.add_url_rule("/api/v1/spine/subjects/<int:subject_id>/intelligence", endpoint="api_spine_intelligence", view_func=api_spine_intelligence, methods=["GET"])
    app.add_url_rule("/api/v1/spine/subjects/<int:subject_id>/entity-alias-graph", endpoint="api_spine_entity_alias_graph", view_func=api_spine_entity_alias_graph, methods=["GET"])
    app.add_url_rule("/api/v1/spine/subjects/<int:subject_id>/identity-link-hypotheses", endpoint="api_spine_identity_link_hypotheses", view_func=api_spine_identity_link_hypotheses, methods=["GET"])
    app.add_url_rule("/api/v1/spine/subjects/<int:subject_id>/dossier-assertion-projection", endpoint="api_spine_dossier_assertion_projection", view_func=api_spine_dossier_assertion_projection, methods=["GET"])
    app.add_url_rule("/api/v1/spine/subjects/<int:subject_id>/dossier-assertion-review-packet", endpoint="api_spine_dossier_assertion_review_packet", view_func=api_spine_dossier_assertion_review_packet, methods=["GET"])
    app.add_url_rule("/api/v1/spine/subjects/<int:subject_id>/aliases/<alias_id>/review", endpoint="api_spine_entity_alias_review", view_func=api_spine_entity_alias_review, methods=["POST"])
    app.add_url_rule("/api/v1/spine/subjects/<int:subject_id>/aliases/<alias_id>/promote", endpoint="api_spine_entity_alias_promote", view_func=api_spine_entity_alias_promote, methods=["POST"])
    app.add_url_rule("/api/v1/spine/subjects/<int:subject_id>/alias-clusters", endpoint="api_spine_entity_alias_cluster", view_func=api_spine_entity_alias_cluster, methods=["POST"])
    app.add_url_rule("/api/v1/spine/subjects/<int:subject_id>/intelligence/run", endpoint="api_spine_intelligence_run", view_func=api_spine_intelligence_run, methods=["POST"])
    app.add_url_rule("/api/v1/spine/subjects/<int:subject_id>/candidate-profiles/<candidate_id>/review", endpoint="api_spine_candidate_profile_review", view_func=api_spine_candidate_profile_review, methods=["POST"])
    app.add_url_rule("/api/v1/spine/observations/<int:observation_id>/promote", endpoint="api_spine_observation_promote", view_func=api_spine_observation_promote, methods=["POST"])
    app.add_url_rule("/api/v1/spine/intelligence/assertions/<int:assertion_id>/review", endpoint="api_spine_intelligence_assertion_review", view_func=api_spine_intelligence_assertion_review, methods=["POST"])
