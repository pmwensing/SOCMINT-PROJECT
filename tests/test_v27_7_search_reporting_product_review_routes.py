from pathlib import Path

from src.socmint.dashboard import create_app
from src.socmint.dossier_assembly_routes_v21_0 import register_dossier_assembly_routes_v21_0


def _app(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    monkeypatch.setenv("SOCMINT_SECRET_KEY", "v27-7-route-test-secret-key-with-more-than-32-characters")
    app = create_app()
    register_dossier_assembly_routes_v21_0(app)
    return app


def _payload(ready=True):
    return {
        "schema":"socmint.search_reporting_product_review.v27_7","version":"v27.7.0",
        "status":"ready_for_browser_e2e" if ready else "blocked","ready":ready,
        "module_checks":[],"asset_checks":[],"release_note_checks":[],"route_checks":[],
        "duplicate_routes":[],"migration_artifacts":[],"journey":[{"step":"global_search","route":"/global-search"}],
        "journey_step_count":1,"blocker_count":0 if ready else 1,"blockers":[] if ready else [{"key":"missing_v27_route"}],
        "source_records_mutated":False,"checkpoint_record_created":False,
        "v27_closed_when_browser_e2e_passes":True,
        "next_action":"run_v27_browser_e2e" if ready else "resolve_v27_product_blockers",
    }


def test_v27_7_routes_require_login_and_render_ready_checkpoint(tmp_path, monkeypatch):
    from src.socmint import search_reporting_product_review_routes_v27_7 as routes
    captured = []
    def build(**kwargs):
        captured.append(kwargs)
        return _payload(True)
    monkeypatch.setattr(routes, "build_search_reporting_product_review", build)
    client = _app(tmp_path, monkeypatch).test_client()
    assert client.get("/api/v1/global-search/product-review-checkpoint").status_code == 401
    assert client.get("/global-search/product-review").status_code in {302,303}
    with client.session_transaction() as sess:
        sess["user"] = "alice"
    ui = client.get("/global-search/product-review")
    api = client.get("/api/v1/global-search/product-review-checkpoint")
    assert ui.status_code == 200
    for phrase in (b"Search and Reporting Product Review", b"Checkpoint Status", b"Product Journey", b"ready_for_browser_e2e"):
        assert phrase in ui.data
    assert api.status_code == 200
    assert api.get_json()["ready"] is True
    assert len(captured) == 2
    assert all("routes" in item for item in captured)


def test_v27_7_blocked_checkpoint_returns_503_and_release_contract(tmp_path, monkeypatch):
    from src.socmint import search_reporting_product_review_routes_v27_7 as routes
    monkeypatch.setattr(routes, "build_search_reporting_product_review", lambda **kwargs: _payload(False))
    client = _app(tmp_path, monkeypatch).test_client()
    with client.session_transaction() as sess:
        sess["user"] = "alice"
    assert client.get("/global-search/product-review").status_code == 503
    assert client.get("/api/v1/global-search/product-review-checkpoint").status_code == 503
    note = Path("release/V27_7_PRODUCT_REVIEW_BROWSER_E2E_CHECKPOINT.md").read_text(encoding="utf-8")
    for phrase in (
        "Product Review and Browser E2E Checkpoint", "complete v27 journey",
        "global search", "advanced filters", "saved views", "watchlists",
        "report builder", "history and audit", "current access scope",
        "append-only boundaries", "browser E2E", "v27_closed", "begin_v28", "no migration",
    ):
        assert phrase in note
    migrations = [path for directory in (Path("migrations"),Path("alembic")) if directory.exists() for path in directory.rglob("*v27_7*")]
    assert migrations == []
