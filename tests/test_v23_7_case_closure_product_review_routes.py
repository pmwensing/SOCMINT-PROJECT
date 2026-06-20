from pathlib import Path

from src.socmint.dashboard import create_app
from src.socmint.dossier_assembly_routes_v21_0 import (
    register_dossier_assembly_routes_v21_0,
)


def _app(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    app = create_app()
    register_dossier_assembly_routes_v21_0(app)
    return app


def test_v23_7_checkpoint_route_requires_login_and_reports_ready(tmp_path, monkeypatch):
    client = _app(tmp_path, monkeypatch).test_client()
    assert (
        client.get("/api/v1/case-closure/product-review-checkpoint").status_code == 401
    )

    with client.session_transaction() as sess:
        sess["user"] = "supervisor"

    response = client.get("/api/v1/case-closure/product-review-checkpoint")
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["schema"] == "socmint.case_closure_product_review.v23_7"
    assert payload["version"] == "v23.7.0"
    assert payload["ready"] is True
    assert payload["blocker_count"] == 0
    assert payload["next_action"] == "run_v23_browser_e2e"


def test_v23_7_release_note_script_and_no_migration():
    note = Path("release/V23_7_PRODUCT_REVIEW_BROWSER_E2E_CHECKPOINT.md").read_text(
        encoding="utf-8"
    )
    script = Path("scripts/run_v23_7_case_closure_browser_e2e.py").read_text(
        encoding="utf-8"
    )
    migrations = [
        path
        for directory in (Path("migrations"), Path("alembic"))
        if directory.exists()
        for path in directory.rglob("*v23_7*")
    ]
    assert "full browser journey" in note
    assert "closure readiness" in note
    assert "supervisor decision" in note
    assert "retention assignment" in note
    assert "archive generation" in note
    assert "reopen request and authorization" in note
    assert "consolidated history" in note
    assert "closes v23" in note
    assert "socmint.case_closure_browser_e2e.v23_7" in script
    assert "product_checkpoint" in script
    assert migrations == []
