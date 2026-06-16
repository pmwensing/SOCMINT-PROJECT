from pathlib import Path

from src.socmint.dashboard import create_app
from src.socmint.dossier_assembly_routes_v21_0 import register_dossier_assembly_routes_v21_0


def _app(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    app = create_app()
    register_dossier_assembly_routes_v21_0(app)
    return app


def test_v25_7_checkpoint_routes_require_login_and_report_ready(tmp_path, monkeypatch):
    client = _app(tmp_path, monkeypatch).test_client()

    assert client.get("/api/v1/cross-case-intelligence/product-review-checkpoint").status_code == 401
    assert client.get("/cross-case-intelligence/product-review").status_code in {302, 303}

    with client.session_transaction() as sess:
        sess["user"] = "analyst"
        sess["allowed_case_ids"] = ["case-alpha", "case-bravo"]

    api = client.get("/api/v1/cross-case-intelligence/product-review-checkpoint")
    ui = client.get("/cross-case-intelligence/product-review")
    payload = api.get_json()

    assert api.status_code == 200
    assert payload["schema"] == "socmint.cross_case_intelligence_product_review.v25_7"
    assert payload["version"] == "v25.7.0"
    assert payload["ready"] is True
    assert payload["blocker_count"] == 0
    assert payload["journey_step_count"] == 7
    assert payload["next_action"] == "run_v25_browser_e2e"
    assert payload["source_records_mutated"] is False
    assert payload["checkpoint_record_created"] is False

    assert ui.status_code == 200
    assert b"Cross-Case Intelligence Product Review" in ui.data
    assert b"Full Browser Journey" in ui.data
    assert b"Candidate Discovery" in ui.data
    assert b"Analyst Review Decision" in ui.data
    assert b"Confirmed Link Registration" in ui.data
    assert b"Relationship Graph" in ui.data
    assert b"Impact Analysis" in ui.data
    assert b"History Audit" in ui.data
    assert b"Metrics Confidence" in ui.data
    assert b"closes v25 only after the standalone browser E2E report passes" in ui.data


def test_v25_7_release_note_script_and_no_migration():
    note = Path("release/V25_7_PRODUCT_REVIEW_BROWSER_E2E_CHECKPOINT.md").read_text(encoding="utf-8")
    script = Path("scripts/run_v25_7_cross_case_browser_e2e.py").read_text(encoding="utf-8")
    migrations = [
        path
        for directory in (Path("migrations"), Path("alembic"))
        if directory.exists()
        for path in directory.rglob("*v25_7*")
    ]

    for phrase in (
        "full cross-case journey",
        "candidate discovery",
        "review decisions",
        "confirmed-link registration",
        "graph projection",
        "impact analysis",
        "history and audit",
        "metrics and confidence",
        "closes v25",
        "before v26",
    ):
        assert phrase in note

    assert "socmint.cross_case_browser_e2e.v25_7" in script
    assert "product_checkpoint" in script
    assert "v25_closed" in script
    assert "begin_v26" in script
    assert migrations == []
