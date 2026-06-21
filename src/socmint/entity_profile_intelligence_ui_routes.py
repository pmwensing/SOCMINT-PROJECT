from __future__ import annotations

import json

from flask import jsonify, redirect, render_template, request, session, url_for

from .entity_profile_intelligence import build_entity_profile_intelligence
from .entity_profile_intelligence import entity_profile_intelligence_markdown
from .entity_profile_intelligence import entity_profile_intelligence_summary


def _login_required() -> bool:
    return bool(session.get("user"))


def _sample_subject() -> dict:
    return {
        "subject_id": "sample-entity-profile",
        "display_name": "Sample Entity Profile",
        "case_id": "sample-case",
        "aliases": ["Sample Entity"],
        "handles": ["@sampleentity"],
    }


def _sample_evidence() -> list[dict]:
    return [
        {
            "evidence_id": "ev-sample-profile",
            "label": "sample public profile",
            "source": "public_profile",
            "platform": "example",
            "handle": "@sampleentity",
            "confidence": 0.91,
            "artifact_id": "art-sample-profile",
            "date": "2026-01-01",
            "event": "profile observed",
        },
        {
            "evidence_id": "ev-sample-location-a",
            "label": "Kingston",
            "source": "registry",
            "attribute": "location",
            "value": "Kingston",
            "confidence": 0.86,
        },
    ]


def _payload_from_form() -> dict:
    subject_raw = (request.form.get("subject_json") or "").strip()
    evidence_raw = (request.form.get("evidence_json") or "").strip()
    analyst_reviewed = request.form.get("analyst_reviewed") == "on"
    subject = json.loads(subject_raw) if subject_raw else _sample_subject()
    evidence = json.loads(evidence_raw) if evidence_raw else _sample_evidence()
    return build_entity_profile_intelligence(
        subject, evidence=evidence, analyst_reviewed=analyst_reviewed
    )


def register_entity_profile_intelligence_ui_routes(app):
    @app.get("/dossier/entity-profile-intelligence")
    def entity_profile_intelligence_view():
        if not _login_required():
            return redirect(url_for("dashboard.login"))
        sample_payload = build_entity_profile_intelligence(
            _sample_subject(), evidence=_sample_evidence(), analyst_reviewed=True
        )
        return render_template(
            "entity_profile_intelligence.html",
            title="Entity Profile Intelligence Dossier",
            payload=sample_payload,
            summary=entity_profile_intelligence_summary(sample_payload),
            markdown=entity_profile_intelligence_markdown(sample_payload),
            subject_json=json.dumps(_sample_subject(), indent=2, sort_keys=True),
            evidence_json=json.dumps(_sample_evidence(), indent=2, sort_keys=True),
            error=None,
        )

    @app.post("/dossier/entity-profile-intelligence")
    def entity_profile_intelligence_submit():
        if not _login_required():
            return redirect(url_for("dashboard.login"))
        subject_json = request.form.get("subject_json") or ""
        evidence_json = request.form.get("evidence_json") or ""
        try:
            payload = _payload_from_form()
            error = None
        except (TypeError, json.JSONDecodeError) as exc:
            payload = build_entity_profile_intelligence(
                _sample_subject(), evidence=_sample_evidence(), analyst_reviewed=True
            )
            error = f"Invalid JSON input: {exc}"
        return render_template(
            "entity_profile_intelligence.html",
            title="Entity Profile Intelligence Dossier",
            payload=payload,
            summary=entity_profile_intelligence_summary(payload),
            markdown=entity_profile_intelligence_markdown(payload),
            subject_json=subject_json
            or json.dumps(_sample_subject(), indent=2, sort_keys=True),
            evidence_json=evidence_json
            or json.dumps(_sample_evidence(), indent=2, sort_keys=True),
            error=error,
        )

    @app.get("/api/v1/dossier-builder/v3/intelligence/sample")
    def api_entity_profile_intelligence_sample():
        return jsonify({"subject": _sample_subject(), "evidence": _sample_evidence()})

    return app
