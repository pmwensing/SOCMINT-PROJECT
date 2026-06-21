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


def test_v24_7_checkpoint_route_requires_login_and_reports_ready(tmp_path, monkeypatch):
    client = _app(tmp_path, monkeypatch).test_client()
    assert (
        client.get("/api/v1/portfolio-operations/product-review-checkpoint").status_code
        == 401
    )

    with client.session_transaction() as sess:
        sess["user"] = "manager"

    response = client.get("/api/v1/portfolio-operations/product-review-checkpoint")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["schema"] == "socmint.portfolio_product_review.v24_7"
    assert payload["version"] == "v24.7.0"
    assert payload["ready"] is True
    assert payload["blocker_count"] == 0
    assert payload["next_action"] == "run_v24_browser_e2e"
    assert payload["source_records_mutated"] is False
    assert payload["checkpoint_record_created"] is False


def test_v24_7_release_note_script_and_no_migration():
    note = Path("release/V24_7_PRODUCT_REVIEW_BROWSER_E2E_CHECKPOINT.md").read_text(
        encoding="utf-8"
    )
    script = Path("scripts/run_v24_7_portfolio_browser_e2e.py").read_text(
        encoding="utf-8"
    )
    migrations = [
        path
        for directory in (Path("migrations"), Path("alembic"))
        if directory.exists()
        for path in directory.rglob("*v24_7*")
    ]

    assert "complete portfolio journey" in note
    assert "Portfolio Operations Dashboard" in note
    assert "Case Status and Stage Overview" in note
    assert "Workload and Assignment Monitoring" in note
    assert "Blocked and Overdue Case Queue" in note
    assert "Supervisor Escalation Controls" in note
    assert "Operational Metrics and Throughput" in note
    assert "Portfolio History and Audit" in note
    assert "closes v24" in note
    assert "socmint.portfolio_browser_e2e.v24_7" in script
    assert "product_checkpoint" in script
    assert migrations == []
