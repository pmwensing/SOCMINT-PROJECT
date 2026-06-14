from pathlib import Path

from src.socmint.dashboard import create_app
from src.socmint.dossier_assembly_routes_v21_0 import (
    register_dossier_assembly_routes_v21_0,
)
from src.socmint.dossier_product_review_checkpoint_v21_7 import (
    SCHEMA,
    build_dossier_product_review_checkpoint,
)


def _app(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    app = create_app()
    register_dossier_assembly_routes_v21_0(app)
    return app


def test_v21_7_checkpoint_passes_complete_product_slice(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    result = build_dossier_product_review_checkpoint(
        routes=list(app.url_map.iter_rules())
    )
    assert result["schema"] == SCHEMA
    assert result["status"] == "ready_for_browser_e2e"
    assert result["ready"] is True
    assert result["blocker_count"] == 0
    assert result["duplicate_routes"] == []
    assert result["migration_artifacts"] == []
    assert all(item["ok"] for item in result["module_checks"])
    assert all(item["ok"] for item in result["asset_checks"])
    assert all(item["ok"] for item in result["release_note_checks"])
    assert all(item["registered"] for item in result["route_checks"])


def test_v21_7_checkpoint_route_and_browser_runner(tmp_path, monkeypatch):
    client = _app(tmp_path, monkeypatch).test_client()
    assert client.get(
        "/api/v1/dossier-assembly/product-review-checkpoint"
    ).status_code == 401
    with client.session_transaction() as sess:
        sess["user"] = "supervisor"
    response = client.get(
        "/api/v1/dossier-assembly/product-review-checkpoint"
    )
    assert response.status_code == 200
    assert response.get_json()["ready"] is True

    script = Path("scripts/run_v21_7_dossier_browser_e2e.py").read_text(
        encoding="utf-8"
    )
    note = Path("release/V21_7_CHECKPOINT.md").read_text(encoding="utf-8")
    assert "package_import" in script
    assert "arrangement_saved" in script
    assert "draft_generation" in script
    assert "citation_mapping" in script
    assert "quality_review_ready" in script
    assert "supervisor_approval" in script
    assert "final_export_generated" in script
    assert "Product Checkpoint" in note
