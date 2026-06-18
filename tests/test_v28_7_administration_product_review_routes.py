from pathlib import Path

from src.socmint.dashboard import create_app
from src.socmint.dossier_assembly_routes_v21_0 import register_dossier_assembly_routes_v21_0


def _app(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    monkeypatch.setenv("SOCMINT_SECRET_KEY", "v28-7-route-test-secret-key-with-more-than-32-characters")
    app = create_app()
    register_dossier_assembly_routes_v21_0(app)
    return app


def _payload(ready=True):
    return {
        "schema":"socmint.administration_product_review.v28_7",
        "version":"v28.7.0",
        "status":"ready_for_browser_e2e" if ready else "blocked",
        "ready":ready,
        "module_checks":[],"asset_checks":[],"release_note_checks":[],"route_checks":[],
        "duplicate_routes":[],"migration_artifacts":[],
        "journey":[{"step":"administration_workspace","route":"/administration"}],
        "journey_step_count":1,
        "blocker_count":0 if ready else 1,
        "blockers":[] if ready else [{"key":"missing_v28_route"}],
        "source_records_mutated":False,
        "checkpoint_record_created":False,
        "v28_closed_when_browser_e2e_passes":True,
        "next_action":"run_v28_browser_e2e" if ready else "resolve_v28_product_blockers",
    }


def test_v28_7_routes_require_login_and_render_ready_checkpoint(tmp_path, monkeypatch):
    from src.socmint import administration_product_review_routes_v28_7 as routes
    captured = []
    def build(**kwargs):
        captured.append(kwargs)
        return _payload(True)
    monkeypatch.setattr(routes, "build_administration_product_review", build)
    client = _app(tmp_path, monkeypatch).test_client()
    assert client.get("/api/v1/administration/product-review-checkpoint").status_code == 401
    assert client.get("/administration/product-review").status_code in {302,303}
    with client.session_transaction() as sess:
        sess["user"] = "admin"
    ui = client.get("/administration/product-review")
    api = client.get("/api/v1/administration/product-review-checkpoint")
    assert ui.status_code == 200
    for phrase in (b"Administration Product Review", b"Checkpoint Status", b"Administration Journey", b"ready_for_browser_e2e"):
        assert phrase in ui.data
    assert api.status_code == 200
    assert api.get_json()["ready"] is True
    assert len(captured) == 2
    assert all("routes" in item for item in captured)


def test_v28_7_blocked_checkpoint_returns_503_and_release_contract(tmp_path, monkeypatch):
    from src.socmint import administration_product_review_routes_v28_7 as routes
    monkeypatch.setattr(routes, "build_administration_product_review", lambda **kwargs: _payload(False))
    client = _app(tmp_path, monkeypatch).test_client()
    with client.session_transaction() as sess:
        sess["user"] = "admin"
    assert client.get("/administration/product-review").status_code == 503
    assert client.get("/api/v1/administration/product-review-checkpoint").status_code == 503
    note = Path("release/V28_7_PRODUCT_REVIEW_BROWSER_E2E_CHECKPOINT.md").read_text(encoding="utf-8")
    for phrase in (
        "Product Review and Browser E2E Checkpoint",
        "complete v28 administration journey",
        "Administration Workspace",
        "User and Account Administration",
        "Role, Permission, and Access Policy Management",
        "Team and Organizational Structure",
        "Access Review and Certification",
        "Connector and Integration Administration",
        "Platform Health, Jobs, and Operational Audit",
        "browser E2E",
        "v28_closed",
        "begin_v29",
        "no migration",
    ):
        assert phrase in note
    migrations = [path for directory in (Path("migrations"),Path("alembic")) if directory.exists() for path in directory.rglob("*v28_7*")]
    assert migrations == []
