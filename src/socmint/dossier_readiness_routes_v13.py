from __future__ import annotations

from flask import jsonify

from . import database as db
from .dossier_readiness_v13 import ReadinessInput, compute_dossier_readiness
from .full_report_history import full_report_export_history


def subject_readiness_input(subject_id: int) -> ReadinessInput:
    db.ensure_configured()
    session = db.Session()
    try:
        subject = session.query(db.SpineSubject).filter_by(id=subject_id).first()
        if not subject:
            return ReadinessInput(subject_id=subject_id, subject_exists=False)

        seed_count = (
            session.query(db.SpineSeed).filter_by(subject_id=subject_id).count()
        )
        observation_count = (
            session.query(db.SpineObservation).filter_by(subject_id=subject_id).count()
        )
        assertion_query = session.query(db.SpineDossierAssertion).filter_by(
            subject_id=subject_id
        )
        assertion_count = assertion_query.count()
        finding_count = observation_count + assertion_count
        pending_review_count = assertion_query.filter(
            db.SpineDossierAssertion.validation_state.in_({"unreviewed", "pending"})
        ).count()
        account_pending_count = (
            session.query(db.AccountDiscovery)
            .filter_by(subject_id=subject_id, review_state="unreviewed")
            .count()
        )
        report_count = int(
            full_report_export_history(subject_id, limit=1).get("count", 0)
        )
        return ReadinessInput(
            subject_id=subject_id,
            subject_exists=True,
            seed_count=seed_count,
            finding_count=finding_count,
            report_count=report_count,
            pending_review_count=pending_review_count + account_pending_count,
        )
    finally:
        session.close()


def subject_dossier_readiness(subject_id: int) -> dict:
    return compute_dossier_readiness(subject_readiness_input(subject_id))


def command_center_dossier_readiness() -> dict:
    db.ensure_configured()
    session = db.Session()
    try:
        subjects = (
            session.query(db.SpineSubject)
            .order_by(db.SpineSubject.created_at.desc())
            .limit(10)
            .all()
        )
        items = [subject_dossier_readiness(subject.id) for subject in subjects]
        blocked = sum(1 for item in items if item["state"] == "blocked")
        needs_review = sum(1 for item in items if item["state"] == "needs_review")
        draft_ready = sum(1 for item in items if item["state"] == "draft_ready")
        exported = sum(1 for item in items if item["state"] == "exported")
        return {
            "schema": "socmint.command_center_dossier_readiness.v13_4",
            "subject_count": len(items),
            "blocked": blocked,
            "needs_review": needs_review,
            "draft_ready": draft_ready,
            "exported": exported,
            "subjects": items,
        }
    finally:
        session.close()


def register_dossier_readiness_routes(app) -> None:
    if "api_subject_dossier_readiness_v13" in app.view_functions:
        return

    from .dashboard import login_required

    @login_required
    def api_subject_dossier_readiness_v13(subject_id: int):
        return jsonify(subject_dossier_readiness(subject_id))

    @login_required
    def api_command_center_dossier_readiness_v13():
        return jsonify(command_center_dossier_readiness())

    app.add_url_rule(
        "/api/v1/subjects/<int:subject_id>/dossier/readiness",
        endpoint="api_subject_dossier_readiness_v13",
        view_func=api_subject_dossier_readiness_v13,
        methods=["GET"],
    )
    app.add_url_rule(
        "/api/v1/command-center/dossier-readiness",
        endpoint="api_command_center_dossier_readiness_v13",
        view_func=api_command_center_dossier_readiness_v13,
        methods=["GET"],
    )
