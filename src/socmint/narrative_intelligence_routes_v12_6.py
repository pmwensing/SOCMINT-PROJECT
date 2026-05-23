from __future__ import annotations

from flask import jsonify, render_template, request

from .narrative_export_v12_6_1 import narrative_dashboard_polish_payload
from .narrative_export_v12_6_1 import write_story_exports
from .narrative_intelligence_v12_6 import story_reconstruction_payload


def _subject_id() -> int | None:
    subject_id_raw = request.args.get("subject_id")
    return int(subject_id_raw) if subject_id_raw and subject_id_raw.isdigit() else None


def register_narrative_intelligence_routes(app) -> None:
    if "narrative_intelligence_dashboard" in app.view_functions:
        return

    from .dashboard import login_required

    @login_required
    def narrative_intelligence_dashboard():
        subject_id = _subject_id()
        payload = story_reconstruction_payload(subject_id=subject_id)
        polish = narrative_dashboard_polish_payload(subject_id=subject_id, sort=request.args.get("sort", "timestamp"), event_type=request.args.get("event_type") or None)
        return render_template("narrative_intelligence_dashboard.html", payload=payload, polish=polish)

    @login_required
    def api_narrative_intelligence():
        return jsonify(story_reconstruction_payload(subject_id=_subject_id()))

    @login_required
    def api_narrative_polish():
        return jsonify(narrative_dashboard_polish_payload(subject_id=_subject_id(), sort=request.args.get("sort", "timestamp"), event_type=request.args.get("event_type") or None))

    @login_required
    def api_narrative_export():
        written = write_story_exports(subject_id=_subject_id())
        return jsonify(written)

    app.add_url_rule("/narrative/storyboard", endpoint="narrative_intelligence_dashboard", view_func=narrative_intelligence_dashboard, methods=["GET"])
    app.add_url_rule("/api/v1/narrative/story-reconstruction", endpoint="api_narrative_intelligence", view_func=api_narrative_intelligence, methods=["GET"])
    app.add_url_rule("/api/v1/narrative/story-polish", endpoint="api_narrative_polish", view_func=api_narrative_polish, methods=["GET"])
    app.add_url_rule("/api/v1/narrative/story-export", endpoint="api_narrative_export", view_func=api_narrative_export, methods=["GET"])
