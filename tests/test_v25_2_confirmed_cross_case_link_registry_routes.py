from pathlib import Path

from src.socmint.dashboard import create_app
from src.socmint.dossier_assembly_routes_v21_0 import register_dossier_assembly_routes_v21_0


def _app(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    app = create_app()
    register_dossier_assembly_routes_v21_0(app)
    return app


def test_v25_2_registry_routes_and_ui(tmp_path, monkeypatch):
    from src.socmint import cross_case_intelligence_routes_v25_0 as routes

    workspace = {
        "schema": "socmint.cross_case_confirmed_link_registry.v25_2",
        "version": "v25.2.0",
        "status": "ready",
        "access_scope": {
            "mode": "restricted",
            "allowed_case_ids": ["case-alpha", "case-bravo"],
        },
        "confirmed_links": [{
            "confirmed_link_id": "confirmed-cross-case-link-abc",
            "confirmed_link_sha256": "f" * 64,
            "category": "entity",
            "match_value": "entity-42",
            "display_values": ["entity-42"],
            "case_ids": ["case-alpha", "case-bravo"],
            "source_occurrence_count": 2,
            "source_occurrences_sha256": "o" * 64,
            "accepted_review_decision_id": "correlation-review-accepted",
            "accepted_review_decision_sha256": "d" * 64,
            "registered_by": "registry-manager",
            "registered_at": "2026-06-16T06:00:00+00:00",
        }],
        "confirmed_link_count": 1,
        "accepted_pending_registration": [{
            "correlation_id": "cross-case-identifier-pending",
            "review_decision_id": "correlation-review-pending",
            "review_decision_sha256": "e" * 64,
            "reviewer": "reviewer-one",
            "reason": "Shared identifier confirmed.",
            "case_ids": ["case-alpha", "case-bravo"],
            "category": "identifier",
            "match_value": "shared@example.com",
        }],
        "accepted_pending_count": 1,
        "review_disposition_counts": {
            "accept": 2,
            "reject": 1,
            "defer": 1,
            "split": 1,
        },
        "review_histories": {},
        "unreviewed_candidates_materialized": False,
        "rejected_deferred_split_history_retained": True,
        "source_records_mutated": False,
        "registry_record_created_by_view": False,
        "next_action": "register_accepted_cross_case_links",
    }

    captured = {}
    monkeypatch.setattr(
        routes,
        "build_confirmed_link_registry_workspace",
        lambda **kwargs: workspace,
    )
    monkeypatch.setattr(
        routes,
        "register_confirmed_cross_case_link",
        lambda correlation_id, **kwargs: captured.update(
            {"correlation_id": correlation_id, **kwargs}
        ) or {
            "schema": "socmint.cross_case_confirmed_link_registry.v25_2",
            "version": "v25.2.0",
            "correlation_id": correlation_id,
            "status": "confirmed_link_registered",
            "confirmed_link_id": "confirmed-cross-case-link-new",
            "registry_record_id": 12,
            "accepted_review_decision_id": "correlation-review-pending",
            "source_occurrences_preserved": True,
            "source_records_mutated": False,
        },
    )

    client = _app(tmp_path, monkeypatch).test_client()
    assert client.get("/api/v1/cross-case-intelligence/confirmed-links").status_code == 401
    assert client.get("/cross-case-intelligence/confirmed-links").status_code in {302, 303}

    with client.session_transaction() as sess:
        sess["user"] = "registry-manager"
        sess["allowed_case_ids"] = ["case-alpha", "case-bravo"]
        sess["_csrf_token"] = "test-csrf"

    ui = client.get("/cross-case-intelligence/confirmed-links")
    api = client.get("/api/v1/cross-case-intelligence/confirmed-links")

    assert ui.status_code == 200
    assert b"Confirmed Cross-Case Link Registry" in ui.data
    assert b"Accepted Decisions Pending Registration" in ui.data
    assert b"Register Confirmed Link" in ui.data
    assert b"confirmed-cross-case-link-abc" in ui.data
    assert b"cross-case-identifier-pending" in ui.data
    assert b"Rejected, deferred, and split decisions remain" in ui.data
    assert b"Unreviewed candidates are never materialized" in ui.data
    assert api.status_code == 200
    assert api.get_json()["confirmed_link_count"] == 1

    response = client.post(
        "/api/v1/cross-case-intelligence/cross-case-identifier-pending/confirmed-link",
        json={"confirmed": True, "note": "Register accepted link."},
        headers={"X-CSRF-Token": "test-csrf"},
    )
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["status"] == "confirmed_link_registered"
    assert payload["registry_record_id"] == 12
    assert captured["correlation_id"] == "cross-case-identifier-pending"
    assert captured["registered_by"] == "registry-manager"
    assert captured["allowed_case_ids"] == {"case-alpha", "case-bravo"}
    assert captured["confirmed"] is True


def test_v25_2_blocked_registration_returns_422(tmp_path, monkeypatch):
    from src.socmint import cross_case_intelligence_routes_v25_0 as routes

    monkeypatch.setattr(
        routes,
        "register_confirmed_cross_case_link",
        lambda *args, **kwargs: {
            "status": "blocked",
            "blockers": [{"key": "latest_correlation_review_must_be_accept"}],
        },
    )
    client = _app(tmp_path, monkeypatch).test_client()
    with client.session_transaction() as sess:
        sess["user"] = "registry-manager"
        sess["_csrf_token"] = "test-csrf"

    response = client.post(
        "/api/v1/cross-case-intelligence/candidate/confirmed-link",
        json={"confirmed": True},
        headers={"X-CSRF-Token": "test-csrf"},
    )
    assert response.status_code == 422
    assert response.get_json()["blockers"][0]["key"] == "latest_correlation_review_must_be_accept"


def test_v25_2_release_note_client_and_no_migration():
    note = Path("release/V25_2_CONFIRMED_CROSS_CASE_LINK_REGISTRY.md").read_text(encoding="utf-8")
    script = Path("src/socmint/static/cross_case_confirmed_link_registry_v25_2.js").read_text(encoding="utf-8")
    migrations = [
        path
        for directory in (Path("migrations"), Path("alembic"))
        if directory.exists()
        for path in directory.rglob("*v25_2*")
    ]
    assert "only accepted analyst decisions" in note
    assert "separate immutable link registry" in note
    assert "rejected, deferred, and split history" in note
    assert "accepted decision ID and SHA-256" in note
    assert "all source occurrences" in note
    assert "unreviewed candidates" in note
    assert "access scope" in note
    assert "data-action='register-confirmed-link'" in script
    assert migrations == []
