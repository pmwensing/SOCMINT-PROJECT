from pathlib import Path

from src.socmint.dashboard import create_app
from src.socmint.dossier_assembly_routes_v21_0 import (
    register_dossier_assembly_routes_v21_0,
)


def _app(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    monkeypatch.setenv(
        "SOCMINT_SECRET_KEY", "v28-4-route-test-secret-key-with-more-than-32-characters"
    )
    app = create_app()
    register_dossier_assembly_routes_v21_0(app)
    return app


def test_v28_4_routes_require_admin_and_dispatch(tmp_path, monkeypatch):
    from src.socmint import access_review_routes_v28_4 as routes

    payload = {
        "schema": "socmint.access_review_certification.v28_4",
        "version": "v28.4.0",
        "status": "ready",
        "reviews": [],
        "open_reviews": [],
        "closed_reviews": [],
        "review_count": 0,
        "open_review_count": 0,
        "closed_review_count": 0,
        "pending_assignments": [],
        "pending_assignment_count": 0,
        "decision_counts": {},
        "certification_decisions": [],
        "certification_decision_count": 0,
        "expired_access_findings": [],
        "expired_access_finding_count": 0,
        "excessive_access_findings": [],
        "excessive_access_finding_count": 0,
        "remediation_queue": [],
        "remediation_queue_count": 0,
        "access_review_history": [],
        "access_review_event_count": 0,
    }
    monkeypatch.setattr(
        routes, "actor_is_administrator", lambda actor: actor == "admin"
    )
    monkeypatch.setattr(routes, "build_access_review_workspace", lambda: payload)
    monkeypatch.setattr(
        routes,
        "create_review",
        lambda **kwargs: {"status": "access_review_created", "review_id": "review-1"},
    )
    monkeypatch.setattr(
        routes,
        "assign_review",
        lambda *args, **kwargs: {
            "status": "access_review_assigned",
            "review_assignment_id": "assignment-1",
        },
    )
    monkeypatch.setattr(
        routes,
        "decide_review",
        lambda *args, **kwargs: {
            "status": "access_review_decided",
            "review_decision_id": "decision-1",
        },
    )
    monkeypatch.setattr(
        routes,
        "close_review",
        lambda *args, **kwargs: {"status": "access_review_closed"},
    )
    client = _app(tmp_path, monkeypatch).test_client()
    assert client.get("/api/v1/administration/access-reviews").status_code == 401
    with client.session_transaction() as sess:
        sess["user"] = "viewer"
    assert client.get("/api/v1/administration/access-reviews").status_code == 403
    csrf = "v28-4-csrf-token"
    with client.session_transaction() as sess:
        sess["user"] = "admin"
        sess["_csrf_token"] = csrf
    headers = {"X-CSRF-Token": csrf}
    assert client.get("/administration/access-reviews").status_code == 200
    assert (
        client.post(
            "/api/v1/administration/access-reviews",
            json={
                "name": "Review",
                "scope": {"users": ["alice"]},
                "reason": "create",
                "confirmed": True,
            },
            headers=headers,
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/v1/administration/access-reviews/review-1/assign",
            json={
                "reviewer_username": "reviewer",
                "subject_type": "user",
                "subject_id": "alice",
                "reason": "assign",
                "confirmed": True,
            },
            headers=headers,
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/v1/administration/access-reviews/review-1/decide",
            json={
                "assignment_id": "assignment-1",
                "decision": "certify",
                "reason": "valid",
                "confirmed": True,
            },
            headers=headers,
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/v1/administration/access-reviews/review-1/close",
            json={"reason": "complete", "confirmed": True},
            headers=headers,
        ).status_code
        == 200
    )


def test_v28_4_release_note_and_no_migration():
    note = Path("release/V28_4_ACCESS_REVIEW_CERTIFICATION.md").read_text(
        encoding="utf-8"
    )
    for phrase in (
        "Access Review and Certification",
        "review campaigns",
        "review assignments",
        "certify, revoke, reduce, or defer",
        "expired access",
        "excessive access",
        "remediation queue",
        "immutable certification history",
        "administrator required",
        "explicit confirmation",
        "decision reason",
        "review decisions do not directly mutate access policy",
        "no migration",
    ):
        assert phrase in note
    migrations = [
        path
        for directory in (Path("migrations"), Path("alembic"))
        if directory.exists()
        for path in directory.rglob("*v28_4*")
    ]
    assert migrations == []
