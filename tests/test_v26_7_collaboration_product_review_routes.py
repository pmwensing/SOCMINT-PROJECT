from src.socmint.dashboard import create_app
from src.socmint.dossier_assembly_routes_v21_0 import register_dossier_assembly_routes_v21_0


def _app(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    monkeypatch.setenv("SOCMINT_SECRET_KEY", "v26-route-test-secret-key-with-more-than-32-characters")
    app = create_app()
    register_dossier_assembly_routes_v21_0(app)
    return app


def _payload():
    return {
        "schema": "socmint.collaboration_product_review.v26_7",
        "version": "v26.7.0", "status": "ready_for_browser_e2e", "ready": True,
        "module_checks": [], "asset_checks": [], "release_note_checks": [],
        "route_checks": [], "duplicate_routes": [], "migration_artifacts": [],
        "journey": [{"step": "collaboration_workspace", "route": "/collaboration"}],
        "journey_step_count": 7, "blocker_count": 0, "blockers": [],
        "authentication_validated": True, "case_scope_enforcement_validated": True,
        "append_only_write_boundaries_validated": True,
        "mention_does_not_grant_access_validated": True,
        "acknowledgement_not_completion_validated": True,
        "source_records_mutated": False, "checkpoint_record_created": False,
        "v26_closed_when_browser_e2e_passes": True, "next_action": "run_v26_browser_e2e",
    }


def test_v26_7_routes_require_login_and_render(tmp_path, monkeypatch):
    from src.socmint import collaboration_product_review_routes_v26_7 as routes
    monkeypatch.setattr(routes, "build_collaboration_product_review", lambda **kwargs: _payload())
    client = _app(tmp_path, monkeypatch).test_client()
    assert client.get("/api/v1/collaboration/product-review-checkpoint").status_code == 401
    assert client.get("/collaboration/product-review").status_code in {302, 303}
    with client.session_transaction() as sess:
        sess["user"] = "paul"
    ui = client.get("/collaboration/product-review")
    api = client.get("/api/v1/collaboration/product-review-checkpoint")
    assert ui.status_code == 200
    for phrase in (b"Collaboration Product Review", b"Product Journey", b"Module Checks", b"Route Checks", b"Blockers"):
        assert phrase in ui.data
    assert api.status_code == 200
    assert api.get_json()["status"] == "ready_for_browser_e2e"
