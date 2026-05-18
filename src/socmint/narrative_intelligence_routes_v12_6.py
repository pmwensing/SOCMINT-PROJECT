from __future__ import annotations

from flask import jsonify, render_template, request

from .narrative_intelligence_v12_6 import story_reconstruction_payload


def register_narrative_intelligence_routes(app) -> None:
    if "narrative_intelligence_dashboard" in app.view_functions:
        return

    from .dashboard import login_required

    @login_required
    def narrative_intelligence_dashboard():
        subject_id_raw = request.args.get("subject_id")
        subject_id = int(subject_id_raw) if subject_id_raw and subject_id_raw.isdigit() else None
        payload = story_reconstruction_payload(subject_id=subject_id)
        return render_template("narrative_intelligence_dashboard.html", payload=payload)

    @login_required
    def api_narrative_intelligence():
        subject_id_raw = request.args.get("subject_id")
        subject_id = int(subject_id_raw) if subject_id_raw and subject_id_raw.isdigit() else None
        return jsonify(story_reconstruction_payload(subject_id=subject_id))

    app.add_url_rule("/narrative/storyboard", endpoint="narrative_intelligence_dashboard", view_func=narrative_intelligence_dashboard, methods=["GET"])
    app.add_url_rule("/api/v1/narrative/story-reconstruction", endpoint="api_narrative_intelligence", view_func=api_narrative_intelligence, methods=["GET"])
