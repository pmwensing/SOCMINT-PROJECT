from pathlib import Path

from src.socmint.dashboard import create_app
from src.socmint.dossier_assembly_routes_v21_0 import register_dossier_assembly_routes_v21_0


def _app(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    app = create_app()
    register_dossier_assembly_routes_v21_0(app)
    return app


def test_v22_7_checkpoint_route_requires_login_and_reports_ready(tmp_path, monkeypatch):
    client = _app(tmp_path, monkeypatch).test_client()
    assert client.get("/api/v1/dossier-release/product-review-checkpoint").status_code == 401
    with client.session_transaction() as sess:
        sess["user"] = "operator"
    response = client.get("/api/v1/dossier-release/product-review-checkpoint")
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["ready"] is True
    assert payload["status"] == "ready_for_browser_e2e"
    assert payload["duplicate_routes"] == []
    assert payload["migration_artifacts"] == []


def test_v22_7_browser_runner_and_release_note():
    script = Path("scripts/run_v22_7_dossier_release_browser_e2e.py").read_text(encoding="utf-8")
    note = Path("release/V22_7_PRODUCT_REVIEW_BROWSER_E2E_CHECKPOINT.md").read_text(encoding="utf-8")
    required_script_tokens = (
        "release_authorization",
        "release_preview_acknowledged",
        "secure_distribution",
        "delivery_receipt",
        "recipient_acknowledgement",
        "recovery_state",
        "consolidated_history",
        "closure_ready",
        "product_checkpoint",
    )
    assert all(token in script for token in required_script_tokens)
    assert "complete browser journey" in note
    assert "release authorization" in note
    assert "recovery controls" in note
    assert "closure readiness" in note
    assert "clean product checkpoint" in note
    assert "new product slice" in note
